# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Il demone di indicizzazione: gira in background e tiene il db allineato alle cartelle monitorate.

Ciclo di lavoro (un solo thread, così l'impatto sul PC resta basso e prevedibile):
  1. scansione: conta i file da analizzare (estensioni incluse meno escluse, cartelle escluse saltate),
     confronta con il db: nuovi e modificati vanno in coda, i mancanti si tolgono, gli spostati
     (stesso nome, dimensione e data) aggiornano solo il percorso
  2. hash: SHA-256 dei file in coda; se il contenuto è già noto (copia o spostamento) non si rianalizza
  3. estrazione del testo (con OCR per scansioni e foto) dei contenuti nuovi
  4. pulizia: contenuti senza più nessun percorso, compattazione del db nei momenti di inattività

Il monitoraggio in tempo reale (watchdog) aggiunge, aggiorna, sposta e cancella i file appena cambiano;
un controllo completo periodico (rescan_hours) recupera ciò che il watcher può perdere (es. dischi
scollegati, modifiche mentre il programma era chiuso).

Per non disturbare l'utente: priorità bassa del processo (CPU e disco), tetto di CPU con pause
calcolate dopo ogni file e tra le pagine, tetto più alto quando il PC è inattivo, attesa se gli altri
programmi stanno già usando molto processore, ritmo ridotto a batteria.
"""
from __future__ import annotations

import hashlib
import os
import queue
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import psutil

from . import detect as dt
from . import extractworker, ocr
from .config import ECO_MAX_LEVEL, AppConfig
from .db import Database
from .extractors import ExtractionError, Extractor
from .i18n import language, tr

CHUNK = 1024 * 1024
UNSUPPORTED = {dt.UNKNOWN}


# ======================================================================= ritmo
def idle_seconds() -> float:
    """Secondi dall'ultimo input dell'utente (tastiera/mouse). 0 se non si può sapere."""
    if sys.platform != "win32":
        return 0.0
    import ctypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return max(0.0, (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0)


def lower_priority() -> None:
    """Priorità bassa per CPU e disco: Windows dà la precedenza a tutti gli altri programmi."""
    try:
        p = psutil.Process()
        if sys.platform == "win32":
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            p.ionice(psutil.IOPRIO_LOW)
        else:
            p.nice(10)
    except (psutil.Error, AttributeError, OSError):
        pass


def tune_threads(tids, level: int) -> None:
    """Priorità e risparmio energetico dei soli thread che indicizzano (demone e thread OCR), non di tutto
    il processo: la finestra e la ricerca restano a piena velocità.
    Livelli bassi: EcoQoS di Windows 10 1709+ / 11 (core efficienti, frequenza bassa, niente turbo: è il turbo
    che fa girare le ventole anche con poca CPU in media) e priorità del thread più bassa."""
    tids = [t for t in tids if t]
    if sys.platform != "win32" or not tids:
        return
    try:
        import ctypes
        from ctypes import wintypes

        class PowerThrottlingState(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenThread.restype = wintypes.HANDLE
        k32.SetThreadPriority.argtypes = [wintypes.HANDLE, ctypes.c_int]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        set_info = getattr(k32, "SetThreadInformation", None)
        if set_info is not None:
            set_info.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            set_info.restype = wintypes.BOOL
        eco = level <= ECO_MAX_LEVEL
        # THREAD_PRIORITY_LOWEST / BELOW_NORMAL / NORMAL (non IDLE: il demone a volte tiene il GIL di Python
        # e con priorità IDLE la finestra potrebbe restare ad aspettarlo quando il PC è carico)
        prio = -2 if level <= 1 else -1 if level <= 3 else 0
        # ThreadPowerThrottling = 3, THREAD_POWER_THROTTLING_EXECUTION_SPEED = 1 (maschera 0 = decide Windows)
        state = PowerThrottlingState(1, 1 if eco else 0, 1 if eco else 0)
        for tid in tids:
            h = k32.OpenThread(0x0020 | 0x0400, False, int(tid))   # THREAD_SET_(LIMITED_)INFORMATION
            if not h:
                continue
            try:
                k32.SetThreadPriority(h, prio)
                if set_info is not None:
                    set_info(h, 3, ctypes.byref(state), ctypes.sizeof(state))
            finally:
                k32.CloseHandle(h)
    except (OSError, AttributeError, ValueError, TypeError):
        pass


_thread_handles: dict[int, int] = {}


def threads_cpu(tids, proc) -> float:
    """Secondi di CPU (utente + sistema) usati dai thread `tids` di questo processo.
    Su Windows con GetThreadTimes sugli handle tenuti aperti (veloce: psutil.threads() fotografa tutti i
    thread del sistema); altrove con psutil."""
    tids = {t for t in tids if t}
    if not tids:
        return 0.0
    if sys.platform != "win32":
        return sum(t.user_time + t.system_time for t in proc.threads() if t.id in tids)
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenThread.restype = wintypes.HANDLE
    k32.GetThreadTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k32.GetThreadTimes.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    for tid in [t for t in _thread_handles if t not in tids]:     # thread non più seguiti
        k32.CloseHandle(_thread_handles.pop(tid))
    total = 0
    for tid in tids:
        h = _thread_handles.get(tid)
        if h is None:
            h = k32.OpenThread(0x0800, False, int(tid))             # THREAD_QUERY_LIMITED_INFORMATION
            if not h:
                continue
            _thread_handles[tid] = h
        c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
        if k32.GetThreadTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            for ft in (kt, ut):
                total += (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    return total / 1e7          # FILETIME: unità da 100 ns


class Throttle:
    """Tetto di CPU a ciclo di lavoro: dopo ogni pezzo di lavoro si dorme quanto serve perché il
    processo non superi la percentuale consentita del processore. Il tetto dipende da cosa fa l'utente."""

    def __init__(self, cfg: AppConfig, stop: threading.Event, paused, tids=None):
        self.cfg = cfg
        self.stop = stop
        self.paused = paused
        # thread di cui contare la CPU (demone + OCR): la CPU della finestra non toglie tempo all'indicizzazione
        # e non crea attese lunghe (es. all'avvio, mentre si costruisce l'interfaccia). None = tutto il processo
        self.tids = tids
        self.proc = psutil.Process()
        self.ncpu = psutil.cpu_count() or 1
        self.mode = "normal"
        self.hold_until = 0.0        # fino a quando lasciare il passo all'utente (ricerca nella finestra)
        self._mark()
        self._load_t, self._load_v = 0.0, 0.0
        self.extra_load = lambda: 0.0   # CPU dei processi operai (% di tutto il processore): è nostra, non "altri"
        self._sys0 = psutil.cpu_times()
        self.proc.cpu_percent(None)

    def hold(self, seconds: float) -> None:
        """L'utente sta usando DocIndexer: l'indicizzazione si ferma al prossimo punto di pausa e riprende
        `seconds` dopo l'ultimo tasto o clic, così ricerca e finestra restano fluide."""
        self.hold_until = max(self.hold_until, time.monotonic() + seconds)

    def _yield_to_user(self) -> None:
        while time.monotonic() < self.hold_until and not self.stop.is_set():
            self.stop.wait(min(0.25, max(0.01, self.hold_until - time.monotonic())))

    def _cpu(self) -> float:
        """Secondi di CPU usati finora dai thread dell'indicizzazione (o da tutto il processo)."""
        try:
            if self.tids is not None:
                return threads_cpu(self.tids(), self.proc)
            t = self.proc.cpu_times()
            return t.user + t.system
        except (psutil.Error, OSError, AttributeError, ValueError):
            return self._cpu0 if hasattr(self, "_cpu0") else 0.0

    def _mark(self):
        self._cpu0, self._wall0 = self._cpu(), time.monotonic()

    def limit(self) -> float:
        """Percentuale di CPU consentita adesso (di tutto il processore)."""
        idle = idle_seconds() >= self.cfg.idle_minutes * 60
        lim = self.cfg.cpu_limit_idle if idle else self.cfg.cpu_limit
        self.mode = "idle" if idle else "normal"
        try:
            bat = psutil.sensors_battery()
            if bat is not None and not bat.power_plugged:
                lim = min(lim, self.cfg.cpu_limit) / 2      # a batteria si va piano
                self.mode = "battery"
        except (psutil.Error, AttributeError, OSError):
            pass
        return max(2.0, min(100.0, float(lim)))

    def others_load(self) -> float:
        """CPU usata dagli altri programmi (% di tutto il processore), misurata su almeno 1 secondo.
        Con intervalli di pochi millisecondi (un file dopo l'altro) la misura saltava a valori altissimi
        e l'indicizzazione aspettava 5 secondi senza motivo. Calcolata da cpu_times, così non interferisce
        con le misure del riquadro Risorse del Monitor."""
        now = time.monotonic()
        if now - self._load_t < 1.0:
            return self._load_v
        try:
            t = psutil.cpu_times()
            a, b = self._sys0, t
            busy = lambda x: sum(x) - x.idle - getattr(x, "iowait", 0.0)  # noqa: E731
            dt_all = sum(b) - sum(a)
            total = 100.0 * (busy(b) - busy(a)) / dt_all if dt_all > 0 else 0.0
            mine = self.proc.cpu_percent(None) / self.ncpu + self.extra_load()
            self._sys0 = t
        except (psutil.Error, OSError, AttributeError):
            return self._load_v
        self._load_t, self._load_v = now, max(0.0, total - mine)
        return self._load_v

    def busy_now(self) -> bool:
        """Gli altri programmi stanno usando molta CPU e l'utente è al PC? (senza aspettare)"""
        if self.others_load() < self.cfg.busy_threshold or idle_seconds() >= self.cfg.idle_minutes * 60:
            return False
        self.mode = "busy"
        return True

    def wait_if_busy(self) -> None:
        """Se gli altri programmi usano già molta CPU (e l'utente è al PC) si aspetta."""
        while not self.stop.is_set():
            if self.paused():
                self.stop.wait(1.0)
                continue
            self._yield_to_user()
            if self.others_load() < self.cfg.busy_threshold or idle_seconds() >= self.cfg.idle_minutes * 60:
                return
            self.mode = "busy"
            self.stop.wait(5.0)

    def pace(self) -> None:
        """Da chiamare dopo ogni pezzo di lavoro (file, pagina, blocco letto)."""
        used = max(0.0, self._cpu() - self._cpu0)
        start = time.monotonic()
        # attesa a passi di 1 s ricalcolata col tetto attuale: se si sposta lo slider delle risorse
        # (o si preme "Riduci al minimo") il nuovo tetto vale subito, anche a metà di una pausa
        while not self.stop.is_set():
            rate = self.limit() / 100.0 * self.ncpu    # secondi di CPU consentiti per secondo
            need = used / rate - (time.monotonic() - self._wall0)
            left = 30.0 - (time.monotonic() - start)
            if need <= 0 or left <= 0:
                break
            self.stop.wait(min(need, left, 1.0))
        self._yield_to_user()
        while self.paused() and not self.stop.is_set():
            self.stop.wait(1.0)
        self._mark()


# ===================================================================== stato
@dataclass
class Status:
    phase: str = "idle"          # idle | scanning | hashing | extracting | paused | waiting | error
    found: int = 0               # file contati durante la scansione
    current: str = ""            # file in lavorazione
    mode: str = "normal"         # normal | idle | busy | battery
    last_scan: float = 0.0
    message: str = ""
    log: list = field(default_factory=list)
    pulses: list = field(default_factory=list)   # (istante, tipo di documento, ok) dei file appena letti
    active: int = 0              # file in lettura in questo momento (processi operai)
    done_count: int = 0          # file letti da quando il programma è aperto

    def add_log(self, msg: str) -> None:
        self.log.append(time.strftime("%H:%M:%S ") + msg)
        del self.log[:-300]


# ================================================================= scansione
def wanted(cfg_ext: set[str], path: str) -> bool:
    name = os.path.basename(path)
    if name.startswith("~$") or name.startswith(".~lock"):   # file temporanei di Office/LibreOffice
        return False
    return os.path.splitext(name)[1].lower() in cfg_ext


def in_excluded_dir(path: str, root: str, excluded: set[str]) -> bool:
    rel = os.path.relpath(os.path.dirname(path), root)
    return any(part.lower() in excluded for part in Path(rel).parts if part not in (".", ""))


def under_excluded(path: str, excluded_paths: set[str]) -> bool:
    """Il percorso sta dentro una delle sottocartelle escluse per percorso completo?"""
    p = os.path.normcase(os.path.normpath(path))
    return any(p == x or p.startswith(x + os.sep) for x in excluded_paths)


def walk(root: str, exts: set[str], excluded_dirs: set[str], stop: threading.Event, on_found=None,
         excluded_paths: set[str] | frozenset = frozenset()):
    """Tutti i file da analizzare sotto root: (percorso, dimensione, mtime, ctime). Veloce (os.scandir)."""
    stack = [root]
    while stack and not stop.is_set():
        folder = stack.pop()
        try:
            with os.scandir(folder) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if (e.name.lower() not in excluded_dirs and not e.name.startswith("$")
                                    and not under_excluded(e.path, excluded_paths)):
                                stack.append(e.path)
                        elif e.is_file(follow_symlinks=False) and wanted(exts, e.name):
                            st = e.stat(follow_symlinks=False)
                            yield e.path, st.st_size, st.st_mtime, getattr(st, "st_birthtime", st.st_ctime)
                            if on_found:
                                on_found()
                    except OSError:
                        continue
        except OSError:
            continue


# ================================================================== watcher
class Watcher:
    """Monitoraggio in tempo reale delle cartelle (watchdog): gli eventi vanno nella coda del demone."""

    def __init__(self, dirs: list[str], events: queue.Queue):
        self.dirs = dirs
        self.events = events
        self.observer = None

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            return
        q = self.events

        class Handler(FileSystemEventHandler):
            def on_any_event(self, ev):
                if ev.event_type in ("created", "modified", "deleted", "moved"):
                    q.put((ev.event_type, ev.is_directory, ev.src_path, getattr(ev, "dest_path", "")))

        self.observer = Observer()
        for d in self.dirs:
            if os.path.isdir(d):
                try:
                    self.observer.schedule(Handler(), d, recursive=True)
                except OSError:
                    pass
        self.observer.daemon = True
        self.observer.start()

    def stop(self) -> None:
        if self.observer is not None:
            try:
                self.observer.stop()
                self.observer.join(timeout=3)
            except RuntimeError:
                pass
            self.observer = None


# =================================================================== demone
class Indexer:
    def __init__(self, cfg: AppConfig, db: Database):
        self.cfg = cfg
        self.db = db
        self.status = Status()
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.events: queue.Queue = queue.Queue()
        self.thread: threading.Thread | None = None
        self.watcher: Watcher | None = None
        self.throttle = Throttle(cfg, self.stop_event, lambda: self.cfg.paused, tids=self._work_tids)
        self.extractor = Extractor(cfg, pace=self._pace_file)
        # lettura dei file e OCR in processi separati: la finestra non si blocca mai, più file insieme
        self.pool = extractworker.Pool(cfg, self.stop_event, self.throttle.limit, self.log)
        self.throttle.extra_load = lambda: self.pool.cpu_pct
        if sys.platform == "win32":
            self.pool.idle_fn = idle_seconds      # tempi morti: a PC fermo si spinge, con l'utente ci si fa da parte
        self.pool.battery = lambda: self.throttle.mode == "battery"
        self._file_name, self._file_t0, self._file_noted = "", 0.0, True
        self._rescan = True
        self._last_maint = 0.0

    # ------------------------------------------------------------ controllo
    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        lower_priority()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="indexer", daemon=True)
        self.thread.start()
        self.apply_resources()
        self._start_watcher()

    def _start_watcher(self) -> None:
        if self.watcher:
            self.watcher.stop()
        self.watcher = Watcher(list(self.cfg.watch_dirs), self.events)
        self.watcher.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake.set()
        if self.watcher:
            self.watcher.stop()
        if self.thread:
            self.thread.join(timeout=10)
        self.pool.close()
        self.extractor.close()

    def rescan(self) -> None:
        """Controllo completo delle cartelle (anche dopo aver cambiato cartelle o estensioni)."""
        self._rescan = True
        self.wake.set()

    def apply_resources(self) -> None:
        """Livello di risorse (slider del Monitor / Impostazioni) applicato subito, anche a lavoro in corso:
        il tetto di CPU vale dalla prossima pausa (Throttle legge la configurazione ogni volta), i thread
        OCR dalla prossima pagina, priorità e risparmio energetico dei thread all'istante."""
        ocr.TUNE = self._tune
        ocr.set_threads(self.cfg.ocr_threads)
        self._tune([])
        self.pool.retune()

    def _work_tids(self) -> set[int]:
        """Thread che indicizzano: il demone e i thread OCR di onnxruntime."""
        tids = set(ocr.WORKER_TIDS)
        if self.thread is not None and self.thread.native_id:
            tids.add(self.thread.native_id)
        return tids

    def _tune(self, new_tids) -> None:
        """Priorità / risparmio energetico del thread del demone e dei thread OCR (anche appena creati)."""
        level = max(1, min(5, int(self.cfg.resource_level)))
        tune_threads(set(new_tids) | self._work_tids(), level)

    def settings_changed(self) -> None:
        self.apply_resources()
        self.modules_changed()
        self._start_watcher()
        self.rescan()

    def set_paused(self, paused: bool) -> None:
        self.cfg.paused = paused
        self.wake.set()

    def log(self, msg: str) -> None:
        self.status.add_log(msg)

    # --------------------------------------------------------------- ciclo
    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                if self.cfg.paused:
                    self.status.phase = "paused"
                    self.wake.wait(2.0)
                    self.wake.clear()
                    continue
                if not self.cfg.watch_dirs:
                    if self._rescan:
                        # nessuna cartella monitorata: la scansione toglie dall'indice i file delle cartelle rimosse
                        self._rescan = False
                        self._scan()
                        if self.db.purge_orphans():
                            self.log(tr("Rimossi dall'indice i contenuti dei file cancellati."))
                    self.status.phase = "idle"
                    self.status.current = ""
                    self.wake.wait(5.0)
                    self.wake.clear()
                    continue
                self._drain_events()
                due = time.time() - self.status.last_scan > self.cfg.rescan_hours * 3600
                if self._rescan or due:
                    self._rescan = False
                    self._scan()
                    continue
                if self._hash_some():
                    continue
                if self._extract_some():
                    continue
                if self._meta_some():
                    continue
                # niente da fare: pulizia e attesa di eventi
                if self.db.purge_orphans():
                    self.log(tr("Rimossi dall'indice i contenuti dei file cancellati."))
                if time.time() - self._last_maint > 3600 and idle_seconds() > 60:
                    self.db.maintenance()
                    self._last_maint = time.time()
                self.status.phase = "idle"
                self.status.current = ""
                self.wake.wait(3.0)
                self.wake.clear()
            except Exception as exc:  # noqa: BLE001  (il demone non deve morire)
                self.status.phase = "error"
                self.status.message = str(exc)
                self.log(tr("ERRORE: {exc}", exc=exc))
                traceback.print_exc()
                self.stop_event.wait(10)

    # ---------------------------------------------------------- scansione
    def _scan(self) -> None:
        """Conta i file da analizzare e allinea il db: nuovi/modificati in coda, mancanti tolti."""
        self.status.phase = "scanning"
        self.status.found = 0
        exts = self.cfg.included()
        excluded = self.cfg.excluded_dir_names()
        excluded_paths = self.cfg.excluded_paths()
        known = self.db.known_paths()
        seen: set[str] = set()
        batch: list[tuple] = []
        added = 0

        def found():
            self.status.found += 1
            if self.status.found % 2000 == 0:
                self.throttle.pace()

        for root in self.cfg.watch_dirs:
            if not os.path.isdir(root):
                self.log(tr("Cartella non raggiungibile: {dir}", dir=root))
                continue
            self.status.current = root
            for path, size, mtime, ctime in walk(root, exts, excluded, self.stop_event, found, excluded_paths):
                key = path.lower()
                seen.add(key)
                old = known.get(key)
                if old is None or old[0] != size or old[1] != mtime:
                    batch.append((path, size, mtime, ctime))
                    if len(batch) >= 500:
                        added += self.db.upsert_paths(batch)
                        batch.clear()
        if self.stop_event.is_set():
            return
        added += self.db.upsert_paths(batch)
        # file conosciuti che non ci sono più (cancellati, o cartella/estensione non più monitorata).
        # Le cartelle non raggiungibili (es. disco scollegato) non si toccano.
        reachable = [r for r in self.cfg.watch_dirs if os.path.isdir(r)]
        gone = [p for p in self.db.all_paths()
                if p.lower() not in seen
                and (any(_under(p, r) for r in reachable)                         # sparito da una cartella
                     or not any(_under(p, r) for r in self.cfg.watch_dirs))]      # cartella tolta
        removed = self.db.remove_paths(gone)
        self.status.last_scan = time.time()
        self.log(tr("Scansione: {found} file da indicizzare, {new} nuovi o modificati, {gone} non più presenti.",
                    found=self.status.found, new=added, gone=removed))

    # --------------------------------------------------------------- hash
    def _hash_some(self, n: int = 20) -> bool:
        rows = self.db.paths_to_hash(n)
        if not rows:
            return False
        self.status.phase = "hashing"
        max_bytes = self.cfg.max_file_mb * 1024 * 1024
        for r in rows:
            if self.stop_event.is_set() or not self.events.empty():
                break
            self.throttle.wait_if_busy()
            path = r["path"]
            self.status.current = path
            try:
                st = os.stat(path)
            except OSError:
                self.db.remove_paths([path])
                continue
            try:
                if st.st_size > max_bytes:
                    sha = self._sha256(path)
                    self.db.set_path_hash(r["id"], sha, st.st_size, dt.UNKNOWN, "",
                                          skip_reason=tr("File troppo grande (oltre {mb} MB)", mb=self.cfg.max_file_mb))
                    continue
                sha = self._sha256(path)
                doc_type, mime = dt.detect(path)
                if doc_type in UNSUPPORTED and self.extractor.exif_on():
                    doc_type = dt.META          # niente testo, ma i metadati sì (audio, video, raw...)
                skip = tr("Formato non leggibile") if doc_type in UNSUPPORTED else None
                if skip is None and not self.extractor.module_on(doc_type):
                    skip = tr("Modulo disattivato o non installato: {name}", name=doc_type)
                self.db.set_path_hash(r["id"], sha, st.st_size, doc_type, mime, skip_reason=skip)
            except OSError as exc:
                # file bloccato da un altro programma o permessi: si riprova alla prossima scansione
                self.db.set_path_error(r["id"], str(exc))
            self.throttle.pace()
        return True

    def _sha256(self, path: str) -> str:
        h = hashlib.sha256()
        read = 0
        with open(path, "rb") as fh:
            while chunk := fh.read(CHUNK):
                h.update(chunk)
                read += len(chunk)
                if read % (32 * CHUNK) == 0:      # file grandi: pause anche durante la lettura
                    self.throttle.pace()
        return h.hexdigest()

    # --------------------------------------------------------- estrazione
    def _too_big(self, r: dict) -> bool:
        """File oltre il limite di dimensione finito comunque in coda (es. rimesso in coda a mano o da un
        cambio di moduli): si salta qui, senza nemmeno aprirlo."""
        try:
            size = os.path.getsize(r["path"])
        except OSError:
            return False
        if size <= self.cfg.max_file_mb * 1024 * 1024 or r.get("big") == 3:
            return False                    # big = 3: file grande approvato a mano nella sezione "File grandi"
        reason = tr("File troppo grande (oltre {mb} MB)", mb=self.cfg.max_file_mb)
        self.db.mark_skipped(r["sha256"], reason)
        self.log(f"[-] {os.path.basename(r['path'])}: {reason}")
        return True

    def _ocr_threads(self) -> int:
        """Thread OCR per operaio: con più operai insieme ne basta uno o due ciascuno."""
        n = self.pool.target()
        return max(1, min(int(self.cfg.ocr_threads), 2 if n > 1 else 4, max(1, (psutil.cpu_count() or 2) // n)))

    def _extract_some(self) -> bool:
        """Affida i file in coda ai processi operai (quanti ne prevede il livello di risorse) e salva i
        risultati man mano che arrivano."""
        pool = self.pool
        if pool.broken:
            return self._extract_one()
        while pool.free_slot() and not self.stop_event.is_set() and not self.cfg.paused:
            if pool.busy() and self.throttle.busy_now():
                break                       # PC occupato da altri programmi: non si aggiunge altro lavoro
            rows = self.db.claim_pending(1)
            if not rows:
                break
            r = rows[0]
            if self._too_big(r):
                continue
            job = {"sha": r["sha256"], "path": r["path"], "doc_type": r.get("doc_type"), "cfg": self.cfg,
                   "lang": language(), "threads": self._ocr_threads()}
            if not pool.submit(job):
                self.db.unclaim(r["sha256"])
                break
        busy = pool.busy()
        self.status.active = len(busy)
        if not busy:
            return False
        self.status.phase = "extracting"
        first = min(busy, key=lambda w: w.t0)
        self.status.current = first.job["path"] + (f"   (+{len(busy) - 1})" if len(busy) > 1 else "")
        try:
            item = pool.results.get(timeout=0.5)
        except queue.Empty:
            for w in busy:
                if not w.noted and time.monotonic() - w.t0 > 10:
                    w.noted = True
                    self.log(tr("[...] {name}: in lavorazione (OCR o file lungo)",
                                name=os.path.basename(w.job["path"])))
            return True
        while item is not None:
            w, msg = item
            if msg is not None and msg[0] == "begin":       # file enorme letto a pezzi
                self.db.begin_stream(msg[1])
            elif msg is not None and msg[0] == "part":
                self.db.append_pages(msg[1], msg[2])
                self.status.pulses.append((time.monotonic(), dt.TEXT, True))    # il battito segue ogni pezzo
                del self.status.pulses[:-60]
            else:
                self._finish(w, msg)
            try:
                item = pool.results.get_nowait()
            except queue.Empty:
                item = None
        self.status.active = len(pool.busy())
        return True

    def _finish(self, w, msg) -> None:
        """Risultato di un operaio: testo salvato nel db, oppure errore annotato sul file."""
        job = w.job
        self.pool.finished(w)
        if job is None:
            return                          # operaio chiuso mentre era fermo: niente da salvare
        name = os.path.basename(job["path"])
        ok, doc_type = False, job.get("doc_type") or ""
        try:
            if msg is None:
                if self.stop_event.is_set():
                    return
                if w.killed_for == "memory":
                    err = tr("File troppo pesante: la lettura usa troppa memoria")
                else:
                    err = tr("Lettura interrotta: il processo di lettura si è chiuso")
                self.db.mark_error(job["sha"], err)
                self.log(f"[!] {name}: {err}")
            elif msg[0] == "ok":
                d = msg[2]
                self.db.save_prepared(job["sha"], d)
                info = f"{d['doc_type']}, " + tr("{n} pag.", n=d["page_count"])
                if d["ocr_pages"]:
                    info += ", " + tr("OCR su {n}", n=d["ocr_pages"])
                self.log(f"[ok] {name} ({info})")
                ok, doc_type = True, d["doc_type"]
            else:
                self.db.mark_error(job["sha"], msg[2] + ("\n" + msg[3] if msg[3] else ""))
                self.log(f"[!] {name}: {msg[2]}")
        finally:
            self.status.done_count += 1
            self.status.pulses.append((time.monotonic(), doc_type, ok))
            del self.status.pulses[:-60]

    def _extract_one(self) -> bool:
        """Riserva: lettura nel processo del programma, se i processi operai non si possono avviare."""
        rows = self.db.claim_pending(1)
        if not rows:
            return False
        self.throttle.wait_if_busy()
        r = rows[0]
        if self._too_big(r):
            return True
        self.status.phase = "extracting"
        self.status.current = r["path"]
        name = os.path.basename(r["path"])
        self._file_name, self._file_t0, self._file_noted = name, time.monotonic(), False
        try:
            result = self.extractor.extract(r["path"], r.get("doc_type"))
            self.db.save_extraction(r["sha256"], result)
            info = f"{result.doc_type}, " + tr("{n} pag.", n=result.page_count)
            if result.ocr_pages:
                info += ", " + tr("OCR su {n}", n=result.ocr_pages)
            self.log(f"[ok] {name} ({info})")
        except (ExtractionError, OSError) as exc:
            self.db.mark_error(r["sha256"], str(exc))
            self.log(f"[!] {name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.db.mark_error(r["sha256"], f"{exc}\n{traceback.format_exc()}")
            self.log(f"[!] {name}: {type(exc).__name__}: {exc}")
        self.throttle.pace()
        return True

    def _pace_file(self) -> None:
        """Pausa tra le pagine di un file. Se il file richiede tempo (es. PDF scansionato lungo, OCR) il
        registro lo dice subito, invece di restare fermo fino alla fine del file."""
        if not self._file_noted and time.monotonic() - self._file_t0 > 10:
            self._file_noted = True
            self.log(tr("[...] {name}: in lavorazione (OCR o file lungo)", name=self._file_name))
        self.throttle.pace()

    def _meta_some(self, n: int = 20) -> bool:
        """ExifTool attivato dopo: si leggono i metadati dei file già indicizzati, senza rifare il testo."""
        if not self.extractor.exif_on():
            return False
        rows = self.db.meta_todo(n)
        if not rows:
            return False
        self.status.phase = "extracting"
        for r in rows:
            if self.stop_event.is_set() or not self.events.empty():
                break
            self.throttle.wait_if_busy()
            self.status.current = r["path"] or ""
            items, read = self.extractor.metadata(Path(r["path"])) if r["path"] else ([], True)
            self.db.save_meta(r["sha256"], items)
            self.throttle.pace()
        return True

    def modules_changed(self) -> None:
        """Moduli attivati: i file di quei tipi saltati prima tornano in coda."""
        types = [t for t in (dt.ARCHIVE, dt.SQLITE, dt.DBF, dt.ACCESS) if self.extractor.module_on(t)]
        if self.extractor.exif_on():
            types.append(dt.UNKNOWN)        # file senza testo: ora se ne leggono i metadati
        if self.db.requeue_skipped(types, self.cfg.max_file_mb * 1024 * 1024):
            self.wake.set()

    # ------------------------------------------------- eventi in tempo reale
    def _drain_events(self) -> None:
        exts = self.cfg.included()
        excluded = self.cfg.excluded_dir_names()
        excluded_paths = self.cfg.excluded_paths()
        roots = list(self.cfg.watch_dirs)
        upserts: dict[str, tuple] = {}

        def monitored(p: str) -> bool:
            root = next((r for r in roots if _under(p, r)), None)
            return (root is not None and wanted(exts, p) and not in_excluded_dir(p, root, excluded)
                    and not under_excluded(p, excluded_paths))

        while True:
            try:
                kind, is_dir, src, dest = self.events.get_nowait()
            except queue.Empty:
                break
            if kind in ("created", "modified") and not is_dir:
                if monitored(src):
                    try:
                        st = os.stat(src)
                    except OSError:
                        continue
                    upserts[src.lower()] = (src, st.st_size, st.st_mtime, getattr(st, "st_birthtime", st.st_ctime))
            elif kind == "deleted":
                upserts.pop(src.lower(), None)
                if is_dir:
                    n = self.db.remove_under(src)
                else:
                    n = self.db.remove_paths([src])
                if n:
                    self.log(tr("Cancellato: {path}", path=src))
            elif kind == "moved":
                if is_dir:
                    n = self.db.move_folder(src, dest)
                    if n:
                        self.log(tr("Spostata cartella: {old} → {new}", old=src, new=dest))
                    if not any(_under(dest, r) for r in roots) or under_excluded(dest, excluded_paths):
                        self.db.remove_under(dest)
                    continue
                upserts.pop(src.lower(), None)
                if monitored(dest):
                    if self.db.move_path(src, dest):
                        self.log(tr("Spostato: {old} → {new}", old=src, new=dest))
                    else:
                        try:
                            st = os.stat(dest)
                            upserts[dest.lower()] = (dest, st.st_size, st.st_mtime,
                                                     getattr(st, "st_birthtime", st.st_ctime))
                        except OSError:
                            pass
                else:
                    self.db.remove_paths([src])
        if upserts:
            rows = list(upserts.values())
            # spostamento visto come cancellazione + creazione (es. tra dischi): stesso nome, dimensione e data
            fresh = []
            for path, size, mtime, ctime in rows:
                old = self.db.find_moved(size, mtime, os.path.basename(path))
                if old and old.lower() != path.lower() and self.db.move_path(old, path):
                    self.log(tr("Spostato: {old} → {new}", old=old, new=path))
                else:
                    fresh.append((path, size, mtime, ctime))
            if self.db.upsert_paths(fresh):
                self.wake.set()


def _under(path: str, root: str) -> bool:
    root = root.rstrip("\\/") + os.sep
    return path.lower().startswith(root.lower())
