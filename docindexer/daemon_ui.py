# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Parte "demone" dell'interfaccia: monitor dell'indicizzazione, configurazione guidata del primo avvio,
editor di cartelle ed estensioni, icona nell'area di notifica, avvio con Windows, istanza unica."""
from __future__ import annotations

import os
import socket
import sys
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import extractworker, theme
from . import dialogs as messagebox   # avvisi nel tema
from .dialogs import decorate
from .config import (BASE_DIR, DEFAULT_EXCLUDE, DEFAULT_EXCLUDE_DIRS, DEFAULT_INCLUDE, EXT_GROUPS, FROZEN,
                     ECO_MAX_LEVEL, RESOURCE_LEVELS, AppConfig, norm_ext)
from .i18n import tr

APP_NAME = "DocIndexer"
# porta locale per i messaggi della seconda istanza ("mostra", "aggiungi cartella"); ogni cartella dati
# (DOCINDEXER_HOME) ha la sua, così un profilo di prova non si confonde con quello principale
INSTANCE_PORT = 47613 + (sum(map(ord, os.environ.get("DOCINDEXER_HOME", ""))) % 997 + 1
                         if os.environ.get("DOCINDEXER_HOME") else 0)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

PHASES = {
    "idle": "In attesa di modifiche", "scanning": "Conteggio dei file", "hashing": "Calcolo degli hash",
    "extracting": "Estrazione del testo", "paused": "In pausa", "error": "Errore", "waiting": "In attesa",
}
MODES = {"normal": "PC in uso: ritmo ridotto", "idle": "PC inattivo: ritmo pieno",
         "busy": "PC impegnato: in attesa", "battery": "A batteria: ritmo minimo"}


# ====================================================== equalizzatore dell'indice
class ActivityPulse(tk.Canvas):
    """L'attività dell'indicizzazione, sempre visibile nell'intestazione, come l'equalizzatore di uno stereo:
    colonne di segmenti luminosi che salgono e scendono, con il "picco" che resta un attimo in alto e poi cade.

    Non è decorazione: l'altezza media segue la CPU usata dall'indicizzazione; ogni file appena letto dà un
    colpo alla sua zona (da sinistra: PDF, Office, immagini, testo e altro); un errore accende i picchi di
    rosso. Colori dal verde (in basso) al rosso (in cima). Una sola riga spenta quando non c'è lavoro, ambra
    fissa in pausa.

    Costa pochissimo: si aggiornano solo i segmenti che cambiano, 12 volte al secondo, e solo mentre si lavora."""

    BARS, SEGS = 32, 7
    GRADIENT = ("#22c55e", "#4ade80", "#a3e635", "#facc15", "#fb923c", "#f97316", "#ef4444")
    BANDS = {"pdf": 0, "office": 1, "image": 2}        # zona colpita da ogni tipo di file (3 = tutto il resto)
    OFFICE = ("docx", "doc", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "odp", "rtf")

    def __init__(self, master, app, height=38):
        super().__init__(master, height=height, bg=theme.BG, highlightthickness=0, bd=0)
        self.app = app
        self.h = height
        self.levels = [0.0] * self.BARS
        self.peaks = [0.0] * self.BARS
        self.seen = 0.0
        self.energy = 0.0
        self.err_until = 0.0
        self.state = ""
        self._lit: dict[int, str] = {}
        self.cells = [[self.create_rectangle(0, 0, 0, 0, outline="", fill=theme.PANEL) for _ in range(self.SEGS)]
                      for _ in range(self.BARS)]
        self._width = 0
        self.bind("<Configure>", lambda _e: self._layout())
        self.after(400, self._tick)

    def _layout(self):
        w = max(60, self.winfo_width())
        if w == self._width:
            return
        self._width = w
        bar_w = max(3.0, min(14.0, w / self.BARS))
        x0 = (w - bar_w * self.BARS) / 2
        seg_h = (self.h - 4) / self.SEGS
        for i, col in enumerate(self.cells):
            for j, cell in enumerate(col):
                y = self.h - 2 - (j + 1) * seg_h
                self.coords(cell, x0 + i * bar_w, y + 1, x0 + (i + 1) * bar_w - 2, y + seg_h - 1)
        self._paint()

    def _tick(self):
        try:
            delay = self._step()
        except Exception:  # noqa: BLE001  (l'indicatore non deve mai disturbare il programma)
            delay = 500
        try:
            self.after(delay, self._tick)
        except tk.TclError:
            pass

    def _step(self) -> int:
        import random
        import time

        ix = self.app.indexer
        st = ix.status if ix else None
        paused = bool(self.app.cfg.paused)
        working = bool(st and not paused and st.phase in ("scanning", "hashing", "extracting"))
        throttled = bool(ix and working and (ix.pool.throttled or ix.pool.thermal.factor < 1.0))
        state = "paused" if paused else "hot" if throttled else "work" if working else "idle"
        per_band = self.BARS // 4
        if st:
            for t, doc_type, ok in list(st.pulses):
                if t <= self.seen:
                    continue
                self.seen = t
                band = self.BANDS.get("office" if doc_type in self.OFFICE else doc_type, 3)
                for k in range(per_band):               # colpo sulla zona del tipo di file, più forte al centro
                    i = band * per_band + k
                    self.levels[i] = max(self.levels[i], 1.0 - 0.12 * abs(k - (per_band - 1) / 2) - random.random() * 0.15)
                if not ok:
                    self.err_until = time.monotonic() + 1.5
        if not working and max(self.levels) < 0.02 and max(self.peaks) < 0.02:
            if state != self.state:
                self.state = state
                self._paint()
            return 400
        self.state = state
        cpu = (ix.pool.cpu_pct if ix else 0.0) / 100.0
        self.energy += ((0.22 + 0.6 * min(1.0, cpu * 2.5) if working else 0.0) - self.energy) * 0.2
        for i in range(self.BARS):
            lvl = self.levels[i] * 0.80                                   # ogni colonna ricade...
            if working:
                lvl = max(lvl, self.energy * (0.35 + 0.65 * random.random()))   # ...e la musica la rialza
            self.levels[i] = min(1.0, lvl)
            self.peaks[i] = max(self.levels[i], self.peaks[i] - 0.035)   # il picco resta su e scende piano
        self._paint()
        return 80

    def _paint(self):
        import time

        err = time.monotonic() < self.err_until
        for i, col in enumerate(self.cells):
            lit = int(round(self.levels[i] * self.SEGS))
            peak = int(round(self.peaks[i] * self.SEGS)) - 1
            for j, cell in enumerate(col):
                if self.state == "paused":
                    color = theme.WARN if j == 0 else theme.PANEL
                elif self.state == "idle" and lit == 0 and peak < 0:
                    color = theme.BORDER_STRONG if j == 0 else theme.PANEL
                elif j < lit:
                    color = self.GRADIENT[j]            # dal verde in basso al rosso in cima
                elif j == peak and j >= lit:
                    color = theme.ERR if err else theme.TEXT_SOFT
                else:
                    color = theme.PANEL
                if self._lit.get(cell) != color:
                    self._lit[cell] = color
                    self.itemconfigure(cell, fill=color)


# ================================================================ avvio con Windows
def launch_command() -> str:
    """Comando che avvia DocIndexer in background (finestra nascosta, solo icona)."""
    if FROZEN:
        return f'"{sys.executable}" --background'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{BASE_DIR / "main.py"}" --background'


def set_autostart(enabled: bool) -> bool:
    """Avvio automatico all'accesso dell'utente (chiave Run dell'utente, nessun permesso di amministratore)."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


# ======================================================================== istanza unica
ADD_PREFIX = b"add\n"


def add_message(path: str) -> bytes:
    return ADD_PREFIX + path.encode("utf-8")


def _read_all(conn, limit: int = 65536) -> bytes:
    conn.settimeout(2)
    data = b""
    try:
        while len(data) < limit:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    return data


def send_to_running(msg: bytes) -> bool:
    """Passa un messaggio al DocIndexer già aperto. False se non ce n'è uno in ascolto."""
    try:
        with socket.create_connection(("127.0.0.1", INSTANCE_PORT), timeout=2) as c:
            c.sendall(msg)
            c.shutdown(socket.SHUT_WR)
        return True
    except OSError:
        return False


class SingleInstance:
    """La prima istanza ascolta su una porta locale; una seconda istanza le passa un messaggio ed esce:
    "show" (mostrati) oppure "add" + cartella (clic destro «Aggiungi a DocIndexer» in Esplora file)."""

    def __init__(self):
        self.sock = None

    def acquire(self, on_show, on_add=None, hello: bytes = b"show") -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", INSTANCE_PORT))
        except OSError:
            s.close()
            send_to_running(hello)
            return False
        s.listen(4)
        self.sock = s

        def serve():
            while True:
                try:
                    conn, _ = s.accept()
                except OSError:
                    return
                with conn:
                    msg = _read_all(conn)
                if msg == b"show":
                    on_show()
                elif msg.startswith(ADD_PREFIX):
                    path = msg[len(ADD_PREFIX):].decode("utf-8", "replace")
                    (on_add or (lambda _p: on_show()))(path)

        threading.Thread(target=serve, name="instance", daemon=True).start()
        return True

    def release(self):
        if self.sock:
            self.sock.close()


# ============================================================================ tray
class Tray:
    """Icona nell'area di notifica: apri, pausa/riprendi, ricerca rapida, manuale, esci.
    Il programma resta attivo a finestra chiusa."""

    def __init__(self, app):
        self.app = app
        self.icon = None

    def start(self) -> None:
        try:
            import pystray
            from PIL import Image
        except ImportError:
            return
        try:
            image = Image.open(theme.ICON_PNG)
        except OSError:
            image = Image.new("RGB", (64, 64), theme.ACCENT)
        call = self.app.call_in_gui

        menu = pystray.Menu(
            pystray.MenuItem(tr("Apri DocIndexer"), lambda: call(self.app.show_window), default=True),
            pystray.MenuItem(lambda _i: tr("Riprendi l'indicizzazione") if self.app.cfg.paused
                             else tr("Metti in pausa l'indicizzazione"),
                             lambda: call(self.app.toggle_pause)),
            pystray.MenuItem(tr("Controlla subito le cartelle"), lambda: call(self.app.indexer_rescan)),
            pystray.MenuItem(tr("Ricerca rapida"), lambda: call(self.app.quick_search)),
            pystray.MenuItem(tr("Manuale"), lambda: call(self.app.open_manual)),
            pystray.Menu.SEPARATOR,
            # spunta = DocIndexer parte da solo all'accesso a Windows; un clic lo attiva o disattiva
            pystray.MenuItem(tr("Avvia con Windows"), lambda: call(self.app.set_autostart, not autostart_enabled()),
                             checked=lambda _i: autostart_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(tr("Esci"), lambda: call(self.app.quit_app)),
        )
        self.icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
        self.icon.run_detached()

    def update(self, tooltip: str) -> None:
        if self.icon is not None:
            try:
                self.icon.title = tooltip[:120]
                self.icon.update_menu()
            except Exception:  # noqa: BLE001
                pass

    def notify(self, message: str, title: str = APP_NAME) -> None:
        """Avviso di Windows vicino all'orologio."""
        if self.icon is not None:
            try:
                self.icon.notify(message[:250], title[:60])
            except Exception:  # noqa: BLE001
                pass

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:  # noqa: BLE001
                pass
            self.icon = None


# ===================================================================== grafico a torta
class Pie(tk.Canvas):
    """Grafico a torta (ad anello) con legenda: indicizzati, da fare, saltati, errori."""

    def __init__(self, master, size=220):
        super().__init__(master, width=size, height=size, bg=theme.PANEL, highlightthickness=0)
        self.size = size

    def draw(self, parts: list[tuple[str, int, str]], center_text: str, sub: str = ""):
        self.delete("all")
        s, pad = self.size, 10
        total = sum(v for _l, v, _c in parts)
        box = (pad, pad, s - pad, s - pad)
        if total <= 0:
            self.create_oval(*box, outline=theme.BORDER_STRONG, width=18)
        else:
            start = 90.0
            shown = [(v, c) for _l, v, c in parts if v > 0]
            extents = [360.0 * v / total for v, _c in shown]
            if len(shown) > 1:
                extents = [max(2.0, e) for e in extents]
                big = extents.index(max(extents))
                extents[big] -= sum(extents) - 360.0
            for (value, color), extent in zip(shown, extents):
                extent = -extent
                if abs(extent) >= 359.99:
                    self.create_oval(*box, outline=color, width=18)
                else:
                    self.create_arc(*box, start=start, extent=extent, style="arc", outline=color, width=18)
                start += extent
        self.create_text(s / 2, s / 2 - 8, text=center_text, fill=theme.TEXT,
                         font=(theme.ui_font(), 20, "bold"))
        if sub:
            self.create_text(s / 2, s / 2 + 18, text=sub, fill=theme.TEXT_DIM, font=(theme.mono_font(), 9))


# ===================================================================== risorse
class Sparkline(tk.Canvas):
    """Andamento degli ultimi valori (es. CPU negli ultimi 2 minuti), con linea del limite."""

    def __init__(self, master, width=260, height=44, color=theme.ACCENT):
        super().__init__(master, width=width, height=height, bg=theme.INPUT, highlightthickness=0)
        self.w, self.h, self.color = width, height, color

    def draw(self, values: list[float], top: float, limit: float | None = None):
        self.delete("all")
        w, h = self.winfo_width() or self.w, self.winfo_height() or self.h
        top = max(top, 1e-6)
        if limit is not None and limit < top:
            y = h - 2 - (h - 4) * limit / top
            self.create_line(0, y, w, y, fill=theme.WARN, dash=(3, 3))
        if len(values) < 2:
            return
        n = len(values)
        pts = []
        for i, v in enumerate(values):
            pts += [w * i / (n - 1), h - 2 - (h - 4) * min(v, top) / top]
        self.create_polygon(*pts, w, h, 0, h, fill=theme.tint(self.color, 0.25, theme.INPUT), outline="")
        self.create_line(*pts, fill=self.color, width=2)


class ResourceCard(ctk.CTkFrame):
    """CPU e RAM usate da DocIndexer (solo questo processo), con l'andamento degli ultimi 2 minuti."""

    HISTORY = 120

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER)
        import psutil

        self.app = app
        self.proc = psutil.Process()
        self.ncpu = psutil.cpu_count() or 1
        self.proc.cpu_percent(None)
        psutil.cpu_percent(None)
        self.cpu: list[float] = []
        self.ram: list[float] = []
        f = app.fonts
        theme.caption(self, tr("Risorse usate da DocIndexer"), f).grid(row=0, column=0, columnspan=4, sticky="w",
                                                                      padx=12, pady=(10, 4))
        self.cpu_lbl = ctk.CTkLabel(self, text="", anchor="w", font=f.bold)
        self.cpu_lbl.grid(row=1, column=0, sticky="w", padx=(12, 8))
        self.cpu_graph = Sparkline(self, color=theme.ACCENT)
        self.cpu_graph.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=(0, 4))
        self.ram_lbl = ctk.CTkLabel(self, text="", anchor="w", font=f.bold)
        self.ram_lbl.grid(row=1, column=2, sticky="w", padx=(0, 8))
        self.ram_graph = Sparkline(self, color=theme.OK)
        self.ram_graph.grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=(0, 4))
        self.detail = ctk.CTkLabel(self, text="", anchor="w", text_color=theme.TEXT_DIM, font=f.small)
        self.detail.grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 8))
        self.grid_columnconfigure((1, 3), weight=1)

    def sample(self):
        """Una misura al secondo (anche quando il monitor non è visibile, per avere lo storico)."""
        import psutil

        try:
            cpu = self.proc.cpu_percent(None) / self.ncpu        # % di tutto il processore
            mem = self.proc.memory_info().rss / 1048576
            ix = self.app.indexer
            if ix is not None:          # anche i processi che leggono i file: sono lavoro di DocIndexer
                cpu += ix.pool.cpu_pct
                mem += sum(w.rss() for w in list(ix.pool.workers)) / 1048576
            self._threads = self.proc.num_threads()
            self._system = psutil.cpu_percent(None)
            self._avail = psutil.virtual_memory().available / 1048576
        except psutil.Error:
            return
        self.cpu = (self.cpu + [cpu])[-self.HISTORY:]
        self.ram = (self.ram + [mem])[-self.HISTORY:]

    def refresh(self):
        if not self.cpu:
            return
        cfg = self.app.cfg
        ix = self.app.indexer
        idle_mode = ix is not None and ix.throttle.mode == "idle"
        limit = cfg.cpu_limit_idle if idle_mode else cfg.cpu_limit
        if ix is not None and ix.pool.allowed:
            limit = round(ix.pool.allowed)          # tetto reale di questo momento (utente al PC, temperatura)
        cpu, mem = self.cpu[-1], self.ram[-1]
        avg = sum(self.cpu) / len(self.cpu)
        self.cpu_lbl.configure(text=tr("CPU {v}%", v=f"{cpu:.0f}"),
                               text_color=theme.WARN if cpu > limit * 1.2 else theme.TEXT)
        self.ram_lbl.configure(text=tr("RAM {v} MB", v=f"{mem:.0f}"))
        self.cpu_graph.draw(self.cpu, max(limit * 1.5, max(self.cpu), 10), limit)
        self.ram_graph.draw(self.ram, max(self.ram) * 1.15)
        self.detail.configure(text=tr("Media CPU 2 min: {avg}% · limite attuale {limit}% · processore del PC: {sys}% · "
                                      "thread: {th} · RAM libera del PC: {free} MB",
                                      avg=f"{avg:.1f}", limit=limit, sys=f"{getattr(self, '_system', 0):.0f}",
                                      th=getattr(self, "_threads", 0), free=f"{getattr(self, '_avail', 0):.0f}"))


class ResourceControl(ctk.CTkFrame):
    """Slider delle risorse da dedicare all'indicizzazione e pulsante "Riduci al minimo".
    Effetto immediato anche a lavoro in corso; il livello resta salvato in config.json."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER)
        self.app = app
        f = app.fonts
        theme.caption(self, tr("Risorse per l'indicizzazione"), f).grid(row=0, column=0, columnspan=4, sticky="w",
                                                                       padx=12, pady=(10, 4))
        ctk.CTkLabel(self, text=tr("Minimo"), text_color=theme.TEXT_DIM, font=f.small).grid(row=1, column=0,
                                                                                         padx=(12, 8))
        self.slider = ctk.CTkSlider(self, from_=1, to=len(RESOURCE_LEVELS), number_of_steps=len(RESOURCE_LEVELS) - 1,
                                    command=self._moved)
        self.slider.grid(row=1, column=1, sticky="ew")
        ctk.CTkLabel(self, text=tr("Massimo"), text_color=theme.TEXT_DIM, font=f.small).grid(row=1, column=2,
                                                                                          padx=(8, 16))
        self.btn_min = ctk.CTkButton(self, text=tr("Riduci al minimo"), width=170, command=self.minimum)
        self.btn_min.grid(row=1, column=3, padx=(0, 12))
        self.info = ctk.CTkLabel(self, text="", anchor="w", justify="left", font=f.bold)
        self.info.grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=(6, 0))
        ctk.CTkLabel(self, text=tr("Effetto immediato, anche durante l'indicizzazione. Più a sinistra: meno calore e "
                                   "ventole più silenziose, ma l'indicizzazione va più piano."),
                     text_color=theme.TEXT_DIM, font=f.small, anchor="w", justify="left", wraplength=1000).grid(
            row=3, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 6))
        # temperature di CPU e GPU con la soglia a cui l'indicizzazione rallenta da sola
        temps = ctk.CTkFrame(self, fg_color="transparent")
        temps.grid(row=4, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 4))
        self.temp = {}
        self._temp_job = None
        for col, (key, name) in enumerate((("temp_cpu_max", "CPU"), ("temp_gpu_max", "GPU"))):
            temps.grid_columnconfigure(col * 3 + 1, weight=1)
            now = ctk.CTkLabel(temps, text=name, font=f.bold, width=150, anchor="w")
            now.grid(row=0, column=col * 3, sticky="w", padx=(0 if col == 0 else 28, 8))
            slider = ctk.CTkSlider(temps, from_=50, to=100, number_of_steps=50,
                                   command=lambda v, k=key: self._temp_moved(k, v))
            slider.set(max(50, min(100, int(getattr(app.cfg, key)))))
            slider.grid(row=0, column=col * 3 + 1, sticky="ew")
            limit = ctk.CTkLabel(temps, text="", text_color=theme.TEXT_DIM, font=f.small, width=130, anchor="w")
            limit.grid(row=0, column=col * 3 + 2, sticky="w", padx=(8, 0))
            self.temp[key] = (name, now, slider, limit)
        ctk.CTkLabel(self, text=tr("Soglie di temperatura: quando CPU o GPU le raggiungono l'indicizzazione rallenta da "
                                   "sola (meno CPU, meno file insieme) e riprende quando si sono raffreddate."),
                     text_color=theme.TEXT_DIM, font=f.small, anchor="w", justify="left", wraplength=1000).grid(
            row=5, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 10))
        self.grid_columnconfigure(1, weight=1)
        self._shown = None
        self.sync()

    def _moved(self, value):
        level = int(round(float(value)))
        if level != self.app.cfg.resource_level:
            self.app.set_resource_level(level)
            self.sync()

    def _temp_moved(self, key: str, value):
        """Soglia di temperatura spostata: vale subito, si salva appena lo slider si ferma."""
        setattr(self.app.cfg, key, int(round(float(value))))
        self._sync_temps()
        if self._temp_job:
            self.after_cancel(self._temp_job)
        self._temp_job = self.after(600, self.app.save_config)

    def _sync_temps(self):
        ix = self.app.indexer
        th = ix.pool.thermal if ix else None
        values = {"temp_cpu_max": th.value if th else None, "temp_gpu_max": th.gpu if th else None}
        for key, (name, now, slider, limit) in self.temp.items():
            lim = int(getattr(self.app.cfg, key))
            t = values[key]
            if t is None:
                now.configure(text=f"{name}  " + tr("non rilevabile"), text_color=theme.TEXT_DIM)
            else:
                color = theme.ERR if t >= lim else theme.WARN if t >= lim - 8 else theme.OK
                now.configure(text=f"{name}  {t:.0f} °C", text_color=color)
            limit.configure(text=tr("rallenta a {t} °C", t=lim))

    def minimum(self):
        self.slider.set(1)
        self.app.set_resource_level(1)
        self.sync()

    def sync(self):
        """Posizione dello slider e descrizione del livello (anche se cambiati da Impostazioni)."""
        cfg = self.app.cfg
        self._sync_temps()
        level = max(1, min(len(RESOURCE_LEVELS), int(cfg.resource_level)))
        if int(round(self.slider.get())) != level:
            self.slider.set(level)
        name, cpu, idle, threads = RESOURCE_LEVELS[level]
        custom = (cfg.cpu_limit, cfg.cpu_limit_idle, cfg.ocr_threads) != (cpu, idle, threads)
        ix = self.app.indexer
        workers = ix.pool.target() if ix else extractworker.max_workers(level)
        allowed = round(ix.pool.allowed) if ix else 0
        factor = ix.pool.thermal.factor if ix else 1.0
        hot = ix.pool.thermal.hot if ix else None
        share = ix.pool.share if ix else 1.0
        shown = (level, custom, cfg.cpu_limit, cfg.cpu_limit_idle, workers, allowed, bool(cfg.paused),
                 hot and (hot[0], round(hot[1]), hot[2]), 0 if share <= 0 else 2 if share >= 1 else 1)
        if shown == self._shown:
            return
        self._shown = shown
        head = tr("Personalizzato (da Impostazioni)") if custom else tr(name)
        # prima riga: cosa succede adesso e perché; seconda: cosa prevede il livello scelto
        if cfg.paused:
            now = tr("In pausa")
        elif not allowed:
            now = ""
        else:
            now = tr("Adesso: CPU fino al {n}% · file insieme: {w}", n=allowed, w=workers) + " · "
            if hot:
                now += tr("rallentato dal calore ({what} {t} °C, soglia {lim} °C)", what=hot[0], t=f"{hot[1]:.0f}",
                          lim=f"{hot[2]:.0f}")
            elif share >= 1.0:
                now += tr("PC fermo: piena potenza")
            elif share > 0.0:
                now += tr("PC fermo da poco: sta salendo")
            else:
                now += tr("stai usando il PC: a PC fermo sale da solo")
        text = tr("Livello {name}: fino al {cpu}% di CPU mentre usi il PC, {idle}% a PC fermo, fino a {n} file insieme",
                  name=head, cpu=cfg.cpu_limit, idle=cfg.cpu_limit_idle, n=extractworker.max_workers(level))
        if level <= ECO_MAX_LEVEL:
            text += " · " + tr("risparmio energetico di Windows")
        text = (now + "\n" if now else "") + text
        self.info.configure(text=text)
        at_min = level <= 1
        self.btn_min.configure(fg_color=theme.NEUTRAL if at_min else theme.BTN,
                               hover_color=theme.NEUTRAL_HOVER if at_min else theme.BTN_HOVER)


# ===================================================================== monitor
class MonitorPage(ctk.CTkFrame):
    """Stato dell'indicizzazione: torta, barra di avanzamento, conteggi, file corrente, registro."""

    COLORS = {"done": theme.OK, "todo": theme.ACCENT, "skipped": theme.TEXT_FAINT, "error": theme.ERR}

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        f = app.fonts
        ctk.CTkLabel(self, text=tr("Monitor"), font=app.h1).pack(anchor="w", pady=(0, 4))
        self.subtitle = ctk.CTkLabel(self, text="", text_color=theme.TEXT_DIM, anchor="w", justify="left",
                                     wraplength=1100)
        self.subtitle.pack(anchor="w", fill="x", pady=(0, 12))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        card = ctk.CTkFrame(top, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER)
        card.pack(side="left", padx=(0, 12))
        self.pie = Pie(card)
        self.pie.pack(padx=14, pady=14)

        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        cards = ctk.CTkFrame(right, fg_color="transparent")
        cards.pack(fill="x")
        self.cards = {}
        for key, title in (("total", "File da analizzare"), ("done", "Indicizzati"), ("todo", "Da fare"),
                           ("skipped", "Saltati"), ("error", "Errori")):
            c = ctk.CTkFrame(cards, corner_radius=4, fg_color=theme.PANEL, border_width=1, border_color=theme.BORDER)
            c.pack(side="left", fill="x", expand=True, padx=(0, 8))
            head = ctk.CTkFrame(c, fg_color="transparent")
            head.pack(anchor="w", padx=12, pady=(10, 0))
            if key in self.COLORS:
                ctk.CTkFrame(head, fg_color=self.COLORS[key], width=8, height=8, corner_radius=4).pack(
                    side="left", padx=(0, 6))
            theme.caption(head, tr(title), f).pack(side="left")
            lbl = ctk.CTkLabel(c, text="-", font=ctk.CTkFont(family=theme.ui_font(), size=22, weight="bold"))
            lbl.pack(anchor="w", padx=12, pady=(0, 10))
            self.cards[key] = lbl

        self.phase = ctk.CTkLabel(right, text="", anchor="w", font=f.bold)
        self.phase.pack(fill="x", pady=(12, 2))
        self.bar = ctk.CTkProgressBar(right, height=12)
        self.bar.set(0)
        self.bar.pack(fill="x", pady=(2, 4))
        self.pct = ctk.CTkLabel(right, text="", anchor="w", text_color=theme.TEXT_DIM, font=f.small)
        self.pct.pack(fill="x")
        self.current = ctk.CTkLabel(right, text="", anchor="w", text_color=theme.TEXT_SOFT, font=f.small)
        self.current.pack(fill="x", pady=(4, 0))
        self.mode = ctk.CTkLabel(right, text="", anchor="w", text_color=theme.TEXT_DIM, font=f.small)
        self.mode.pack(fill="x")

        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.pack(fill="x", pady=(10, 0))
        self.btn_pause = ctk.CTkButton(btns, text="", width=150, command=app.toggle_pause)
        self.btn_pause.pack(side="left")
        ctk.CTkButton(btns, text=tr("Controlla subito le cartelle"), width=210, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=app.indexer_rescan).pack(side="left", padx=8)
        ctk.CTkButton(btns, text=tr("Rimetti in coda gli errori"), width=190, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.retry_errors).pack(side="left")
        # avvio automatico con Windows: effetto immediato (lo stesso interruttore è nel menu dell'icona
        # vicino all'orologio e in Impostazioni > Configurazione)
        self.autostart = tk.BooleanVar(value=autostart_enabled())
        ctk.CTkSwitch(btns, text=tr("Avvia con Windows"), variable=self.autostart,
                      command=lambda: app.set_autostart(self.autostart.get())).pack(side="left", padx=(16, 0))
        self.db_size = ctk.CTkLabel(btns, text="", text_color=theme.TEXT_DIM, font=f.small)
        self.db_size.pack(side="right")

        self.res_control = ResourceControl(self, app)
        self.res_control.pack(fill="x", pady=(14, 0))
        self.resources = ResourceCard(self, app)
        self.resources.pack(fill="x", pady=(8, 0))
        theme.caption(self, tr("Registro"), f).pack(anchor="w", pady=(14, 4))
        self.log = ctk.CTkTextbox(self, font=ctk.CTkFont(family=theme.mono_font(), size=11), wrap="none")
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")
        self._log_len = 0

    def retry_errors(self):
        if self.app.ensure_db():
            self.app.db.reset_errors()
            self.app.indexer.wake.set()

    def refresh(self, s: dict | None = None):
        ix = self.app.indexer
        if s is None:
            return
        todo = s["pending"] + s["processing"]
        analysed = s["done"] + s["skipped"] + s["error"]
        total = s["total"]
        st = ix.status if ix else None
        folders = ", ".join(self.app.cfg.watch_dirs) or tr("(nessuna)")
        self.subtitle.configure(text=tr("Cartelle monitorate: {dirs}", dirs=folders))
        self.cards["total"].configure(text=f"{total:,}".replace(",", "."))
        self.cards["done"].configure(text=f"{s['done']:,}".replace(",", "."))
        self.cards["todo"].configure(text=f"{todo:,}".replace(",", "."))
        self.cards["skipped"].configure(text=f"{s['skipped']:,}".replace(",", "."))
        self.cards["error"].configure(text=f"{s['error']:,}".replace(",", "."))
        pct = analysed / total if total else 0.0
        self.pie.draw([("done", s["done"], self.COLORS["done"]), ("todo", todo, self.COLORS["todo"]),
                       ("skipped", s["skipped"], self.COLORS["skipped"]), ("error", s["error"], self.COLORS["error"])],
                      f"{pct * 100:.0f}%", tr("completato"))
        self.bar.set(pct)
        self.pct.configure(text=tr("{done} di {total} file analizzati · {contents} contenuti distinti nell'indice",
                                   done=analysed, total=total, contents=s.get("contents", 0)))
        if st:
            phase = "paused" if self.app.cfg.paused else st.phase
            label = tr(PHASES.get(phase, phase))
            if phase == "scanning":
                label += " · " + tr("{n} file trovati", n=st.found)
            self.phase.configure(text=label, text_color=theme.ERR if phase == "error" else theme.TEXT)
            self.current.configure(text=st.current if phase in ("scanning", "hashing", "extracting") else "")
            self.mode.configure(text=tr(MODES.get(ix.throttle.mode, "")) if not self.app.cfg.paused else "")
            if len(st.log) != self._log_len or (st.log and self._log_len == 300):
                self._log_len = len(st.log)
                self.log.configure(state="normal")
                self.log.delete("1.0", "end")
                self.log.insert("end", "\n".join(st.log[-300:]))
                self.log.see("end")
                self.log.configure(state="disabled")
        self.btn_pause.configure(text=tr("Riprendi") if self.app.cfg.paused else tr("Metti in pausa"))
        size = self.app.db.db_size() if self.app.db else 0
        self.db_size.configure(text=tr("Database: {mb} MB", mb=f"{size / 1048576:.1f}"))
        self.resources.refresh()
        self.res_control.sync()


# ========================================================== tabelle estensioni / cartelle
class ListEditor(ctk.CTkFrame):
    """Tabella modificabile di valori (estensioni o cartelle): aggiungi, togli, ripristina predefiniti."""

    def __init__(self, master, title: str, values: list[str], fonts, default: list[str] | None = None,
                 kind: str = "ext", height: int = 220, width: int = 260):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER,
                         width=width)
        self.kind = kind
        self.default = default
        theme.caption(self, title, fonts).pack(anchor="w", padx=10, pady=(10, 4))
        frame = tk.Frame(self, bg=theme.PANEL)
        frame.pack(fill="both", expand=True, padx=8)
        self.lb = tk.Listbox(frame, bg=theme.INPUT, fg=theme.TEXT, selectbackground=theme.SELECT_BG,
                             selectforeground="#ffffff", highlightthickness=0, bd=0, activestyle="none",
                             selectmode="extended", font=(theme.mono_font(), 10), height=max(4, height // 20))
        from tkinter import ttk

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        self.entry = ctk.CTkEntry(row, height=28, width=110, placeholder_text=".ext" if kind == "ext" else tr("nome cartella"))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add())
        ctk.CTkButton(row, text="+", width=30, height=28, command=self.add).pack(side="left", padx=(4, 0))
        ctk.CTkButton(row, text="−", width=30, height=28, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.remove).pack(side="left", padx=(4, 0))
        if default is not None:
            ctk.CTkButton(self, text=tr("Valori predefiniti"), height=24, font=fonts.small, fg_color=theme.NEUTRAL,
                          hover_color=theme.NEUTRAL_HOVER, command=lambda: self.set(default)).pack(
                fill="x", padx=8, pady=(6, 8))
        self.set(values)

    def _norm(self, v: str) -> str:
        v = v.strip()
        return norm_ext(v) if self.kind == "ext" else v

    def set(self, values: list[str]):
        self.lb.delete(0, "end")
        for v in sorted({self._norm(v) for v in values if v.strip()}, key=str.lower):
            self.lb.insert("end", v)
        self._paint_groups()

    def _paint_groups(self):
        pass

    def get(self) -> list[str]:
        return list(self.lb.get(0, "end"))

    def add(self):
        new = [self._norm(x) for x in self.entry.get().replace(";", ",").replace(" ", ",").split(",")]
        self.set(self.get() + [x for x in new if x and x != "."])
        self.entry.delete(0, "end")

    def remove(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i)
        self._paint_groups()


class ExtTable(ctk.CTkFrame):
    """Tabella delle estensioni con le spunte, divisa per gruppi. I pulsanti dei gruppi spuntano tutte le
    estensioni del gruppo; un secondo clic le toglie. Le estensioni fuori dai gruppi stanno in "Altre"."""

    COLS = 6

    def __init__(self, master, title: str, values: list[str], fonts, default: list[str] | None = None):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER)
        self.fonts = fonts
        self.default = default
        self.vars: dict[str, tk.BooleanVar] = {}
        theme.caption(self, title, fonts).pack(anchor="w", padx=10, pady=(10, 4))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=6)
        self.group_buttons = {}
        for i, (name, exts) in enumerate(EXT_GROUPS):
            b = ctk.CTkButton(grid, text=tr(name), height=24, font=fonts.small,
                              command=lambda e=exts: self.toggle_group(e))
            b.grid(row=i // 4, column=i % 4, sticky="ew", padx=2, pady=2)
            self.group_buttons[name] = (b, exts)
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.area = ctk.CTkScrollableFrame(self, fg_color=theme.INPUT, corner_radius=4, height=230)
        self.area.pack(fill="both", expand=True, padx=8, pady=(6, 4))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(2, 8))
        self.entry = ctk.CTkEntry(row, height=28, placeholder_text=tr("altra estensione, es. .xyz"))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add())
        ctk.CTkButton(row, text="+", width=30, height=28, command=self.add).pack(side="left", padx=(4, 0))
        ctk.CTkButton(row, text=tr("Tutte"), width=60, height=28, font=fonts.small, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=lambda: self._all(True)).pack(side="left", padx=(4, 0))
        ctk.CTkButton(row, text=tr("Nessuna"), width=70, height=28, font=fonts.small, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=lambda: self._all(False)).pack(side="left", padx=(4, 0))
        if default is not None:
            ctk.CTkButton(row, text=tr("Predefiniti"), width=90, height=28, font=fonts.small, fg_color=theme.NEUTRAL,
                          hover_color=theme.NEUTRAL_HOVER, command=lambda: self.set(default)).pack(
                side="left", padx=(4, 0))
        self._extra: list[str] = []
        self.set(values)

    def _build(self, checked: set[str]):
        for w in self.area.winfo_children():
            w.destroy()
        self.vars = {}
        grouped = {norm_ext(e) for _n, exts in EXT_GROUPS for e in exts}
        self._extra = sorted({e for e in checked | set(self._extra) if e not in grouped})
        sections = [(tr(n), [norm_ext(e) for e in exts]) for n, exts in EXT_GROUPS]
        if self._extra:
            sections.append((tr("Altre"), self._extra))
        r = 0
        for name, exts in sections:
            tk.Label(self.area, text=name.upper(), bg=theme.INPUT, fg=theme.TEXT_FAINT,
                     font=(theme.mono_font(), 8, "bold"), anchor="w").grid(row=r, column=0, columnspan=self.COLS,
                                                                          sticky="w", padx=4, pady=(6, 1))
            r += 1
            unique = list(dict.fromkeys(exts))
            for i, e in enumerate(unique):
                var = self.vars.get(e)
                if var is None:
                    var = self.vars[e] = tk.BooleanVar(value=e in checked)
                cb = tk.Checkbutton(self.area, text=e, variable=var, command=self._paint_groups,
                                    bg=theme.INPUT, fg=theme.TEXT, activebackground=theme.INPUT,
                                    activeforeground=theme.TEXT, selectcolor=theme.PANEL_3, bd=0,
                                    highlightthickness=0, font=(theme.mono_font(), 9), anchor="w")
                cb.grid(row=r + i // self.COLS, column=i % self.COLS, sticky="w", padx=2)
            r += (len(unique) + self.COLS - 1) // self.COLS
        self._paint_groups()

    def set(self, values: list[str]):
        self._build({norm_ext(v) for v in values if v.strip()})

    def get(self) -> list[str]:
        return sorted(e for e, v in self.vars.items() if v.get())

    def add(self):
        new = {norm_ext(x) for x in self.entry.get().replace(";", ",").replace(" ", ",").split(",")} - {"", "."}
        self.entry.delete(0, "end")
        if new:
            self._build(set(self.get()) | new)

    def _all(self, value: bool):
        for v in self.vars.values():
            v.set(value)
        self._paint_groups()

    def toggle_group(self, exts: list[str]):
        group = {norm_ext(e) for e in exts}
        full = all(self.vars[e].get() for e in group if e in self.vars)
        for e in group:
            if e in self.vars:
                self.vars[e].set(not full)
        self._paint_groups()

    def _paint_groups(self):
        """Gruppo tutto spuntato = pulsante pieno con ✓; in parte = ◐; nessuna spunta = +."""
        have = set(self.get())
        for name, (b, exts) in self.group_buttons.items():
            group = {norm_ext(e) for e in exts}
            full = group <= have
            part = bool(group & have) and not full
            b.configure(fg_color=theme.BTN if full else theme.NEUTRAL,
                        hover_color=theme.BTN_HOVER if full else theme.NEUTRAL_HOVER,
                        text=("✓ " if full else "◐ " if part else "+ ") + tr(name))


class FolderList(ctk.CTkFrame):
    """Cartelle di lavoro da monitorare."""

    def __init__(self, master, values: list[str], fonts, title: str | None = None):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=4, border_width=1, border_color=theme.BORDER)
        theme.caption(self, title or tr("Cartelle di lavoro monitorate"), fonts).pack(anchor="w", padx=10,
                                                                                  pady=(10, 4))
        frame = tk.Frame(self, bg=theme.PANEL)
        frame.pack(fill="both", expand=True, padx=8)
        self.lb = tk.Listbox(frame, bg=theme.INPUT, fg=theme.TEXT, selectbackground=theme.SELECT_BG,
                             selectforeground="#ffffff", highlightthickness=0, bd=0, activestyle="none",
                             font=(theme.ui_font(), 10), height=4)
        self.lb.pack(fill="both", expand=True)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(row, text=tr("Aggiungi cartella..."), command=self.add, height=28).pack(side="left")
        ctk.CTkButton(row, text=tr("Togli"), width=80, height=28, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.remove).pack(side="left", padx=6)
        for v in values:
            self.lb.insert("end", v)

    def add(self):
        d = filedialog.askdirectory(title=tr("Cartella da monitorare"))
        if d:
            d = os.path.normpath(d)
            if d not in self.get():
                self.lb.insert("end", d)

    def remove(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i)

    def get(self) -> list[str]:
        return list(self.lb.get(0, "end"))

    def set(self, values: list[str]) -> None:
        self.lb.delete(0, "end")
        for v in values:
            self.lb.insert("end", v)


def overlapping(dirs: list[str]) -> list[str]:
    """Cartelle contenute in un'altra della lista (verrebbero analizzate due volte)."""
    norm = [os.path.normcase(os.path.normpath(d)) + os.sep for d in dirs]
    return [dirs[i] for i, a in enumerate(norm) if any(a != b and a.startswith(b) for b in norm)]


# ===================================================================== primo avvio
class SetupWizard(ctk.CTkToplevel):
    """Configurazione del primo avvio: cartelle di lavoro, estensioni incluse/escluse, cartelle saltate,
    avvio con Windows."""

    def __init__(self, master, cfg: AppConfig, fonts, on_done):
        super().__init__(master, fg_color=theme.BG)
        self.cfg = cfg
        self.on_done = on_done
        decorate(self, tr("DocIndexer - configurazione iniziale"), on_close=self.cancel)
        theme.place_window(self, 1360, 860, master=master, min_size=(1100, 700))
        try:
            self.transient(master)
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        logo = theme.logo(22)
        if logo is not None:
            ctk.CTkLabel(self, text="", image=logo).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(self, text=tr("Benvenuto! Scegli dove DocIndexer deve cercare."), font=fonts.page,
                     anchor="w").pack(fill="x", padx=20)
        ctk.CTkLabel(self, text=tr("DocIndexer resta attivo in background, analizza i file delle cartelle scelte "
                                   "senza spostarli né copiarli (nel database vanno solo il testo e il percorso) e "
                                   "segue nuovi file, modifiche, spostamenti e cancellazioni. Lavora piano mentre usi "
                                   "il PC e più veloce quando è inattivo."),
                     text_color=theme.TEXT_DIM, anchor="w", justify="left", wraplength=1040).pack(
            fill="x", padx=20, pady=(4, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)
        home = os.path.expanduser("~")
        start = cfg.watch_dirs or [d for d in (os.path.join(home, "Documents"), os.path.join(home, "Desktop"))
                                   if os.path.isdir(d)]
        frow = ctk.CTkFrame(body, fg_color="transparent")
        frow.pack(fill="x", pady=(0, 10))
        self.folders = FolderList(frow, start, fonts)
        self.folders.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.excluded = FolderList(frow, cfg.exclude_paths, fonts, title=tr("Sottocartelle escluse"))
        self.excluded.pack(side="left", fill="both", expand=True)
        tables = ctk.CTkFrame(body, fg_color="transparent")
        tables.pack(fill="both", expand=True)
        self.inc = ExtTable(tables, tr("Estensioni incluse"), cfg.include_ext, fonts, DEFAULT_INCLUDE)
        self.inc.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.exc = ExtTable(tables, tr("Estensioni escluse"), cfg.exclude_ext, fonts, DEFAULT_EXCLUDE)
        self.exc.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.dirs = ListEditor(tables, tr("Cartelle saltate (per nome)"), cfg.exclude_dirs, fonts,
                               DEFAULT_EXCLUDE_DIRS, kind="dir")
        self.dirs.pack(side="left", fill="y")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=20, pady=14, before=body)   # sempre visibile, anche su schermi bassi
        self.autostart = tk.BooleanVar(value=cfg.autostart)
        ctk.CTkCheckBox(bottom, text=tr("Avvia DocIndexer con Windows (in background, icona vicino all'orologio)"),
                        variable=self.autostart).pack(side="left")
        ctk.CTkButton(bottom, text=tr("Inizia l'indicizzazione"), width=200, command=self.ok).pack(side="right")
        self.after(200, self.lift)
        self.after(350, lambda: self.winfo_exists() and self.state("zoomed"))   # si apre ingrandita

    def ok(self):
        dirs = [d for d in self.folders.get() if os.path.isdir(d)]
        if not dirs:
            messagebox.showwarning(APP_NAME, tr("Aggiungi almeno una cartella da monitorare."), parent=self)
            return
        dup = overlapping(dirs)
        if dup:
            dirs = [d for d in dirs if d not in dup]
        self.cfg.watch_dirs = dirs
        self.cfg.include_ext = self.inc.get()
        self.cfg.exclude_ext = self.exc.get()
        self.cfg.exclude_dirs = self.dirs.get()
        self.cfg.exclude_paths = self.excluded.get()
        self.cfg.autostart = bool(self.autostart.get())
        set_autostart(self.cfg.autostart)
        self.cfg.save()
        self.destroy()
        self.on_done(True)

    def cancel(self):
        self.destroy()
        self.on_done(False)
