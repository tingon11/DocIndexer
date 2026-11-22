# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Interfaccia grafica customtkinter."""
from __future__ import annotations

import os
import sys
from pathlib import Path
import queue

import threading
import time
import unicodedata
import tkinter as tk
from tkinter import filedialog, ttk

import customtkinter as ctk
from PIL import Image

from .config import RESOURCE_LEVELS, AppConfig, portable
from .db import Database
from . import __version__, ocr, portable_drive, preview, shellmenu, theme, tools
from .i18n import LANGUAGES, language, set_language, tr
from .textnorm import fold
from . import daemon_ui, frameless
from . import dialogs as messagebox   # avvisi e domande nel tema, senza barra di Windows
from .dialogs import apply_frameless, hide_until_ready, window_buttons
from .indexer import Indexer
from .regexlib import RegexEditor, validate as regex_error
from . import backup, dupes_ui, export, hotkey, manual, quick, regexworker, saved_ui, searches
from . import lang as lang_mod
from . import terms, welcome

class Worker:
    """Esegue un job in background e passa log/progresso alla GUI tramite coda."""

    def __init__(self, app: "App"):
        self.app = app
        self.thread: threading.Thread | None = None
        self.stop = threading.Event()

    @property
    def busy(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, target, on_log, on_progress, on_done):
        self.stop.clear()

        def log(msg):
            self.app.events.put((on_log, (msg,)))

        def progress(i, n):
            self.app.events.put((on_progress, (i, n)))

        def run():
            try:
                result = target(log, progress, self.stop)
                self.app.events.put((on_done, (result, None)))
            except Exception as exc:  # noqa: BLE001
                self.app.events.put((on_done, (None, exc)))

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()


# ======================================================================
class LogBox(ctk.CTkTextbox):
    def __init__(self, master, **kw):
        super().__init__(master, font=ctk.CTkFont(family=theme.mono_font(), size=12), **kw)
        self.configure(state="disabled")

    def write(self, msg: str):
        self.configure(state="normal")
        self.insert("end", msg + "\n")
        if int(self.index("end-1c").split(".")[0]) > 5000:
            self.delete("1.0", "1000.0")
        self.see("end")
        self.configure(state="disabled")


def _sort_value(v: str):
    """Chiave di ordinamento: numeri come numeri (anche 1.234), il resto senza maiuscole/accenti."""
    t = str(v).strip()
    num = t.replace(".", "").replace(",", ".") if t.count(",") <= 1 else t
    try:
        return (0, float(num), "")
    except ValueError:
        return (1, 0.0, fold(t)) if t else (2, 0.0, "")


def sort_tree(tree: ttk.Treeview, col: str | None = None) -> None:
    """Ordina la tabella per la colonna: un clic A-Z, un altro clic Z-A. Senza col riapplica l'ordine attuale."""
    if col is not None:
        tree._sort = (col, not tree._sort[1]) if tree._sort and tree._sort[0] == col else (col, False)
    if not tree._sort:
        return
    col, rev = tree._sort
    if col == "level" and getattr(tree, "_level_col", False):   # importanza come immagine nella colonna #0
        items = [(str(getattr(tree, "_levels", {}).get(i, 0) or ""), i) for i in tree.get_children("")]
    else:
        items = [(tree.set(i, col), i) for i in tree.get_children("")]
    empty = [i for v, i in items if not str(v).strip()]
    full = sorted(((v, i) for v, i in items if str(v).strip()), key=lambda x: _sort_value(x[0]), reverse=rev)
    for n, (_v, i) in enumerate(full):
        tree.move(i, "", n)
    for n, i in enumerate(empty, start=len(full)):      # le celle vuote sempre in fondo
        tree.move(i, "", n)
    for key, title in tree._titles.items():
        arrow = (" ▼" if rev else " ▲") if key == col else ""
        tree.heading("#0" if key == "level" and tree._level_col else key, text=tr(title) + arrow)


def make_tree(master, columns: list[tuple[str, str, int]]) -> ttk.Treeview:
    """Tabella ordinabile. Una colonna "level" (importanza) diventa la colonna #0 con i pallini colorati
    come immagine: si impostano con set_level(tree, iid, livello)."""
    frame = ctk.CTkFrame(master, fg_color="transparent")
    level_col = bool(columns) and columns[0][0] == "level"
    data = columns[1:] if level_col else columns
    tree = ttk.Treeview(frame, columns=[c[0] for c in data], show="tree headings" if level_col else "headings",
                        selectmode="browse")
    tree._sort = None
    tree._level_col = level_col
    tree._levels = {}
    tree._titles = {key: title for key, title, _w in columns}
    import tkinter.font as tkfont

    head_font = tkfont.Font(family=theme.mono_font(), size=9, weight="bold")

    def col_width(title: str, width: int) -> int:
        # Treeview widths are physical pixels: scale the logical width like the rest of the UI, and never
        # make a column narrower than its (translated) heading plus the sort arrow
        return max(theme.px(tree, width), head_font.measure(tr(title) + " ▼") + theme.px(tree, 20))

    if level_col:
        _k, title, width = columns[0]
        tree.heading("#0", text=tr(title), anchor="w", command=lambda: sort_tree(tree, "level"))
        tree.column("#0", width=col_width(title, width), minwidth=theme.px(tree, 34), anchor="w", stretch=False)
    else:
        tree.column("#0", width=0, stretch=False)
    for key, title, width in data:
        tree.heading(key, text=tr(title), command=lambda c=key: sort_tree(tree, c))
        tree.column(key, width=col_width(title, width), minwidth=theme.px(tree, 34), anchor="w", stretch=False)
    for lvl, color in theme.LEVEL_COLORS.items():      # righe colorate secondo l'importanza
        tree.tag_configure(f"lvl{lvl}", background=theme.tint(color))
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    tree.container = frame
    return tree


def set_level(tree: ttk.Treeview, iid: str, level: int) -> None:
    """Pallini colorati dell'importanza nella colonna #0 di una tabella di make_tree."""
    tree._levels[iid] = int(level or 0)
    tree.item(iid, image=theme.level_image(level, tree))


def attach_tree_tooltip(tree: ttk.Treeview, text_for=None):
    """Tooltip sulle celle. text_for(iid, colonna) può dare un testo da mostrare sempre (es. il percorso
    completo su Nome e Cartella); per le altre celle il tooltip compare solo se il testo è troncato."""
    import tkinter.font as tkfont

    font = tkfont.Font(family=theme.ui_font(), size=10)
    state = {"tip": None, "key": None}

    def hide(_e=None):
        if state["tip"] is not None:
            state["tip"].destroy()
        state["tip"] = state["key"] = None

    def motion(e):
        row, col = tree.identify_row(e.y), tree.identify_column(e.x)
        if not row or not col or tree.identify_region(e.x, e.y) not in ("cell", "tree"):
            return hide()
        if col == "#0":
            key_col, text, width = "#0", str(tree.item(row, "text")), tree.column("#0", "width")
        else:
            ci = int(col[1:]) - 1
            values = tree.item(row, "values")
            if ci >= len(values):
                return hide()
            key_col, text = tree["columns"][ci], str(values[ci])
            width = tree.column(key_col, "width")
        custom = text_for(row, key_col) if text_for else None
        if custom:
            text = custom
        elif not text.strip() or font.measure(text) + 12 <= width:
            return hide()  # il testo è intero
        key = (row, key_col)
        if key == state["key"] and state["tip"] is not None:
            state["tip"].geometry(f"+{e.x_root + 14}+{e.y_root + 18}")
            return
        hide()
        tip = tk.Toplevel(tree)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, bg=theme.PANEL_3, fg=theme.TEXT, relief="solid", bd=1, padx=6, pady=3,
                 font=(theme.ui_font(), 10), wraplength=theme.px(tree, 700), justify="left").pack()
        tip.geometry(f"+{e.x_root + 14}+{e.y_root + 18}")
        state["tip"], state["key"] = tip, key

    tree.bind("<Motion>", motion, add="+")
    tree.bind("<Leave>", hide, add="+")
    tree.bind("<ButtonPress>", hide, add="+")


def style_treeview():
    """Tabelle ttk con lo stile di PCSnex."""
    theme.style_tables(tk._default_root)


def reveal(path):
    """Apre Esplora risorse sulla cartella del file, con il file selezionato."""
    try:
        if sys.platform == "win32":
            import subprocess

            subprocess.Popen(["explorer", "/select,", os.path.normpath(str(path))],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            open_file(os.path.dirname(str(path)))
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror(tr("Errore"), tr("Impossibile aprire il file:\n{exc}", exc=exc))


def open_file(path):
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror(tr("Errore"), tr("Impossibile aprire il file:\n{exc}", exc=exc))


# ======================================================================
class OcrModelPicker(ctk.CTkFrame):
    """Modello OCR (alfabeto) condiviso tra Importa, Elaborazione e Impostazioni. La scelta viene salvata
    in config.json e ritrovata alla riapertura; la prima volta è il modello latino multilingue."""

    def __init__(self, master, app: "App", var: tk.StringVar | None = None):
        super().__init__(master, fg_color="transparent")
        self.var = var or app.ocr_var
        ctk.CTkLabel(self, text=tr("Modello OCR:")).pack(side="left", padx=(0, 8))
        self.by_name = {tr(ocr.AUTO_NAME): ocr.AUTO, **{tr(m.name): k for k, m in ocr.MODELS.items()}}
        self.menu = ctk.CTkOptionMenu(self, values=list(self.by_name), width=460, dynamic_resizing=False,
                                      command=lambda name: self.var.set(self.by_name[name]))
        self.menu.pack(side="left")
        self._trace = self.var.trace_add("write", lambda *_: self.update_label())
        self.update_label()

    def destroy(self):
        # la variabile sopravvive alla ricostruzione dell'interfaccia (cambio lingua): niente richiami orfani
        try:
            self.var.trace_remove("write", self._trace)
        except tk.TclError:
            pass
        super().destroy()

    def update_label(self):
        self.menu.set(tr(ocr.model_name(self.var.get())))


# ======================================================================
def make_snippet(text: str, groups: list[list], width: int = 220) -> str:
    text = unicodedata.normalize("NFC", text)
    hits = sorted(h for terms in groups for h in preview.find_hits(text, terms))
    if not hits:
        return text[:width]
    start = max(0, hits[0][0] - width // 3)
    return ("…" if start else "") + text[start:start + width] + "…"


def count_hits(text: str, pats: list, stop_at: int) -> int:
    """Occorrenze dei pattern nel testo (come preview.find_spans), fermandosi a stop_at: per sapere se sono
    "troppe" non serve trovarle tutte (un foglio pieno di codici fiscali ne ha migliaia)."""
    folded, n = None, 0
    for p in pats:
        if isinstance(p, preview.RawRegex):
            found = (m for m in p.rx.finditer(text) if m.end() > m.start())
        else:
            if folded is None:
                folded = preview.fold(text)
            found = p.finditer(folded)
        for _m in found:
            n += 1
            if n >= stop_at:
                return n
    return n


class PreviewPanel(ctk.CTkFrame):
    """Anteprima del documento originale: termini evidenziati con il colore della riga di ricerca,
    zoom con la rotellina (centrato sul puntatore) e spostamento trascinando con il tasto sinistro."""

    MIN_ZOOM, MAX_ZOOM = 0.2, 8.0
    MANY_HITS = 100     # oltre queste occorrenze nel documento l'anteprima non si carica da sola

    def __init__(self, master, app: "App"):
        super().__init__(master, corner_radius=8)
        self.app = app
        self.kind: str | None = None       # pdf | image | text
        self.path = None
        self.page = 0
        self.count = 0
        self.zoom = 1.0                    # 1.0 = adatta alla larghezza
        self.groups: list[list[str]] = []
        self.token = 0                     # scarta le conversioni arrivate in ritardo
        self.original = None
        self.title = ""
        self._photo = None
        self._img_box = (0, 0, 1, 1)       # x, y, larghezza, altezza dell'immagine sul canvas
        self._resize_job = None
        self._wheel_job = None
        self._anchor = None
        self.box_page = None               # pagina dei riquadri OCR quando si mostra un'immagine incollata
        self._temp_files: list[Path] = []  # anteprime temporanee di questo pannello (cancellate dopo)
        self._pending = None               # (riga, gruppi) del documento con troppe occorrenze, non caricato

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=(8, 4))
        self.btn_prev = ctk.CTkButton(bar, text="◀", width=34, command=lambda: self.goto(self.page - 1))
        self.btn_prev.pack(side="left")
        self.lbl_page = ctk.CTkLabel(bar, text="", width=100)
        self.lbl_page.pack(side="left", padx=4)
        self.btn_next = ctk.CTkButton(bar, text="▶", width=34, command=lambda: self.goto(self.page + 1))
        self.btn_next.pack(side="left")
        ctk.CTkButton(bar, text="−", width=34, command=lambda: self.zoom_at(1 / 1.25)).pack(side="left", padx=(14, 2))
        ctk.CTkButton(bar, text=tr("Adatta"), width=64, command=self.fit).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="+", width=34, command=lambda: self.zoom_at(1.25)).pack(side="left", padx=2)
        self.lbl_zoom = ctk.CTkLabel(bar, text="", width=50)
        self.lbl_zoom.pack(side="left", padx=4)
        self.info = InfoText(self)
        self.info.configure(text=tr("Seleziona un risultato per vedere l'anteprima. "
                                 "Rotellina: scorre.  +/−: zoom.  Tasto sinistro + trascina: sposta."))
        self.info.pack(fill="x", padx=10)

        occ_bar = ctk.CTkFrame(self, fg_color="transparent")
        occ_bar.pack(fill="x", padx=8, pady=(4, 0))
        # packed first: when the panel is narrow the occurrence label shrinks, not this button
        ctk.CTkButton(occ_bar, text=tr("Apri originale"), command=self.open_original).pack(side="right")
        self.btn_occ_prev = ctk.CTkButton(occ_bar, text=tr("◀ Occorrenza"), width=110,
                                          command=lambda: self.step_occ(-1))
        self.btn_occ_prev.pack(side="left")
        self.lbl_occ = ctk.CTkLabel(occ_bar, text="", width=60)
        self.lbl_occ.pack(side="left", padx=6)
        self.btn_occ_next = ctk.CTkButton(occ_bar, text=tr("Occorrenza ▶"), width=110,
                                          command=lambda: self.step_occ(1))
        self.btn_occ_next.pack(side="left")
        self.notes = AnnotationBar(self, app)
        self.notes.pack(fill="x", padx=8, pady=(6, 0))
        self.occ: list[tuple[int, int, tuple]] = []   # (pagina 0-based, gruppo, riquadro 0..1)
        self.occ_i = -1
        self.on_occurrence = None                     # callback(pagina 1-based, indice nella pagina)
        self._occ_state()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(body, bg=theme.INPUT, highlightthickness=0, cursor="fleur",
                                yscrollincrement=40, xscrollincrement=40)
        ys = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        xs = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.text = ctk.CTkTextbox(body, wrap="word")
        # documento con troppe occorrenze: al posto dell'anteprima un avviso e il file originale a un clic
        self.many = ctk.CTkFrame(body, fg_color="transparent")
        self.lbl_many = ctk.CTkLabel(self.many, text="", justify="center", wraplength=380)
        self.lbl_many.pack(pady=(40, 12), padx=16)
        ctk.CTkButton(self.many, text=tr("Apri file originale"), command=self.open_original).pack(pady=4)
        ctk.CTkButton(self.many, text=tr("Mostra comunque l'anteprima"), fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self._show_anyway).pack(pady=4)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self._update_nav()

    # ------------------------------------------------------------ carica
    def show(self, row: dict, groups: list[list[str]]):
        """Con una ricerca prima si contano le occorrenze del documento (in background, fermandosi a
        MANY_HITS + 1): se sono di più l'anteprima non si carica da sola, si avvisa e si propone l'originale.
        Es. un foglio Excel pieno di codici fiscali cercati con una regex: migliaia di evidenziazioni
        rallentavano molto l'anteprima."""
        if not groups or row.get("source") in ("archive", "db"):
            self._show_now(row, groups)     # nessun termine da evidenziare, o un testo breve già pronto
            return
        self.token += 1
        token = self.token
        self._pending = (row, groups)
        self.groups = groups
        self.occ, self.occ_i = [], -1
        self.original = Path(row["path"])
        self.title = row["original_name"]
        self.notes.load(row.get("id"))
        self._drop_temp(row)
        self._set_kind(None)
        self.info.configure(text=self._title_text())
        self._highlight_name()
        self._occ_state(tr("Conteggio delle occorrenze..."))
        limit = self.MANY_HITS
        if row.get("matches") is not None and (row.get("score") or 0) > limit:
            self._many_hits(token)          # regex: le occorrenze della pagina/foglio sono già contate
            return
        pats = [p for terms in groups for p in preview.term_patterns(terms)]
        sha, db = row["sha256"], self.app.db

        def work():
            n = 0
            try:
                for p in db.get_document_text(sha):
                    if token != self.token:
                        return          # nel frattempo è stato scelto un altro risultato
                    n += count_hits(p["content"], pats, limit + 1 - n)
                    if n > limit:
                        break
            except Exception:  # noqa: BLE001
                pass            # conteggio non riuscito: si mostra l'anteprima come sempre
            finally:
                db.close()
            self.app.events.put((self._counted, (token, n > limit)))

        threading.Thread(target=work, daemon=True).start()

    def _counted(self, token, many: bool):
        if token != self.token:
            return
        if many:
            self._many_hits(token)
        else:
            self._show_now(*self._pending, load_notes=False)

    def _many_hits(self, token):
        if token != self.token:
            return
        self._set_kind(None)
        self.canvas.grid_remove()
        self.lbl_many.configure(text=tr("Questo documento contiene più di {n} occorrenze: per non rallentare il "
                                        "programma l'anteprima non viene caricata automaticamente.",
                                        n=self.MANY_HITS))
        self.many.grid(row=0, column=0, sticky="nsew")
        self._occ_state(tr("Più di {n} occorrenze", n=self.MANY_HITS))

    def _show_anyway(self):
        if self._pending:
            self._show_now(*self._pending, load_notes=False)

    def _drop_temp(self, row: dict):
        """Cancella i file temporanei del documento mostrato prima (PDF convertito, immagine estratta)."""
        tag = f"p{id(self) % 100000}_"
        keep_prefix = f"{tag}{row['sha256'][:16]}"
        old = [p for p in self._temp_files if not p.name.startswith(keep_prefix)]
        preview.delete_temp(old)
        self._temp_files = [p for p in self._temp_files if p not in old]

    def _show_now(self, row: dict, groups: list[list[str]], load_notes: bool = True):
        self.token += 1
        token = self.token
        self.groups = groups
        self.zoom = 1.0
        self.occ, self.occ_i = [], -1
        self._occ_state(tr("Ricerca delle occorrenze..."))
        self.original = Path(row["path"])
        self.title = row["original_name"]
        if load_notes:      # già caricate da show(): ricaricarle cancellerebbe una nota che si sta scrivendo
            self.notes.load(row.get("id"))
        # i file temporanei del documento mostrato prima (PDF convertito, immagine estratta) si cancellano
        tag = f"p{id(self) % 100000}_"
        self._drop_temp(row)
        self.sha256 = row["sha256"]
        kind, path = preview.preview_source(self.app.cfg, self.original, row["doc_type"], row["sha256"], tag)
        if kind == "office":
            self._temp_files.append(path)
        # pagina del risultato (diapositiva, oppure foglio: viene convertito in pagina al caricamento)
        page = (row["page_no"] or 1) - 1
        self._text_page = row.get("page_no")
        self.doc_type = row["doc_type"]
        # testo trovato in un'immagine incollata nel documento: si mostra quell'immagine, con le parole
        # evidenziate dai riquadri OCR salvati per quella "pagina"
        self.box_page = None
        self._given_text = None
        meta_hit = row.get("source") == "meta"
        if row.get("source") in ("archive", "db") or (
                meta_hit and kind == "text" and not self.app.db.get_document_text(row["sha256"])):
            # risultato da una tabella dedicata senza un'anteprima del documento: si mostra quel testo
            # (file nell'archivio, tabella del database, metadati di un file senza testo)
            self._given_text = (self.app.db.meta_text(row["sha256"]) if meta_hit else None) or row["content"]
            self._loaded(token, "text", self.original, 0, None)
            return
        if meta_hit:
            # trovato nei metadati: l'anteprima mostra il documento dalla prima pagina; i metadati sono nel testo
            page = 0
        embedded = None if meta_hit else preview.embedded_image(self.original, row["doc_type"], row.get("label"),
                                                                row["sha256"], tag)
        if embedded is not None:
            self._temp_files.append(embedded)
            self.box_page = row["page_no"]
            self._loaded(token, "image", embedded, 0, None)
            return
        if kind == "sheet":
            self._set_kind(None)
            self.info.configure(text=tr("Lettura del foglio..."))
            src, doc_type = path, row["doc_type"]

            def read_sheet():
                try:
                    preview.load_sheets(src, doc_type)  # lettura lenta fuori dalla GUI, poi resta in cache
                    self.app.events.put((self._loaded, (token, "sheet", src, page, None)))
                except Exception as exc:  # noqa: BLE001
                    self.app.events.put((self._loaded, (token, "text", src, 0, exc)))

            threading.Thread(target=read_sheet, daemon=True).start()
            return
        if kind == "office" and not path.is_file():
            self._set_kind(None)
            self.info.configure(text=tr("Preparazione dell'anteprima con Office..."))
            doc_type, src = row["doc_type"], self.original

            def work():
                try:
                    out = preview.convert_to_pdf(src, doc_type, path)
                    if token != self.token:
                        # nel frattempo si è passati a un altro documento: il PDF non serve più
                        preview.delete_temp([out])
                        return
                    self.app.events.put((self._loaded, (token, "pdf", out, page, None)))
                except Exception as exc:  # noqa: BLE001
                    self.app.events.put((self._loaded, (token, "text", src, 0, exc)))

            threading.Thread(target=work, daemon=True).start()
            # se Office non risponde la GUI non resta in attesa: dopo 40 s si mostra il testo
            self.after(40000, lambda: token == self.token and self.kind is None and self._loaded(
                token, "text", src, 0, TimeoutError(tr("Office non ha risposto entro 40 secondi"))))
            return
        self._loaded(token, "pdf" if kind == "office" else kind, path, page, None)

    def _loaded(self, token, kind, path, page, exc):
        if token != self.token:
            return
        self.path = path
        self.page = page
        try:
            if kind == "pdf":
                self.count = preview.pdf_page_count(path)
            elif kind == "image":
                self.count = preview.image_frame_count(path)
            elif kind == "sheet":
                self.count = len(preview.sheet_pages(path, self.doc_type))
                self.page = page = preview.sheet_first_page(path, self.doc_type, page)
            else:
                self.count = 1
        except Exception as e:  # noqa: BLE001
            kind, exc = "text", e
        self._set_kind(kind)
        if exc:
            self.info.configure(text=tr("Anteprima grafica non disponibile ({exc}). Testo estratto:", exc=exc))
        else:
            self.info.configure(text=self._title_text())
            self._highlight_name()
        if kind == "text":
            self._show_text()
            self._occ_state("")
        else:
            self.render(reset_view=True)
            self._collect_occurrences(token, kind, path)

    def _highlight_name(self):
        """Colora nel nome originale le parti che corrispondono alla ricerca (colore della riga)."""
        if not self.groups:
            return
        text = self.info.cget("text")
        label = tr("Nome file:") + " "
        start = text.find(label)
        start = start + len(label) if start >= 0 else 0
        name = text[start:].split("\n")[0]
        # nei nomi file "_" separa le parole (stessa regola di "Cerca nel nome del file")
        spaced = name.replace("_", " ")
        for gi, terms in enumerate(self.groups):
            for a, b in preview.find_hits(spaced, terms):
                self.info.mark(start + a, start + b, preview.color(gi), f"hit{gi}")

    def _title_text(self) -> str:
        """Nome del file e, sotto, la cartella dove si trova."""
        if not self.original:
            return shorten(self.title)
        return f"{tr('Nome file:')} {shorten(self.title, 90)}\n{shorten(str(self.original.parent), 110)}"

    def clear(self):
        """Svuota l'anteprima (es. dopo aver eliminato il documento mostrato)."""
        self.token += 1
        self.occ, self.occ_i = [], -1
        self.path = self.original = None
        self.notes.load(None)
        preview.delete_temp(self._temp_files)
        self._temp_files = []
        self._set_kind(None)
        self.info.configure(text="")
        self._occ_state("")

    def _set_kind(self, kind):
        self.kind = kind
        self.many.grid_remove()
        if kind == "text":
            self.canvas.grid_remove()
            self.text.grid(row=0, column=0, sticky="nsew")
        else:
            self.text.grid_remove()
            self.canvas.grid(row=0, column=0, sticky="nsew")
            self.canvas.delete("all")
        self._update_nav()

    def _show_text(self):
        content = getattr(self, "_given_text", None)
        if content is None:
            try:
                pages = self.app.db.get_document_text(self.sha256)
                want = getattr(self, "_text_page", None)
                if want and want not in {p["page_no"] for p in pages}:
                    # file enorme (migliaia di pagine): si mostra la pagina del risultato, non l'inizio
                    pages = self.app.db.get_document_text(self.sha256, want) or pages
                content = " ".join(p["content"] for p in pages)
            except Exception:  # noqa: BLE001
                content = ""
        self.text.delete("1.0", "end")
        self.text.insert("1.0", preview.wrap_for_display(content) or tr("(nessun testo)"))
        highlight(self.text, content, self.groups)

    # ------------------------------------------------------------ render
    def render(self, reset_view: bool = False):
        if self.kind not in ("pdf", "image", "sheet") or not self.path:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        width = max(50, int((cw - 20) * self.zoom))
        try:
            # riquadri OCR salvati per questa pagina (solo pagine scansionate e immagini)
            boxes = []
            if self.kind != "sheet" and self.app.db and (self.path == self.original or self.box_page):
                boxes = self.app.db.get_ocr_boxes(self.sha256, self.box_page or self.page + 1)
            if self.kind == "sheet":
                img, n = preview.render_sheet(self.path, self.doc_type, self.page, width, self.groups), 0
            elif self.kind == "pdf":
                img, n = preview.render_pdf_page(self.path, self.page, width, self.groups, boxes)
            else:
                img, n = preview.render_image(self.path, self.page, width, self.groups, boxes)
            extra = "  " + tr("({n} evid.)", n=n) if n else ""
        except Exception as exc:  # noqa: BLE001
            self.info.configure(text=tr("Errore anteprima: {exc}", exc=exc))
            return
        from PIL import ImageTk

        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        x = max(10, (cw - img.width) // 2)
        y = 10 if img.height + 20 > ch else (ch - img.height) // 2
        self.canvas.create_image(x, y, image=self._photo, anchor="nw")
        sw, sh = max(cw, img.width + 20), max(ch, img.height + 20)
        self.canvas.configure(scrollregion=(0, 0, sw, sh))
        self._img_box = (x, y, img.width, img.height)
        if reset_view:
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
        elif self._anchor:
            # mantiene sotto il puntatore lo stesso punto del documento
            fx, fy, px, py = self._anchor
            nx, ny = x + fx * img.width, y + fy * img.height
            self.canvas.xview_moveto(max(0.0, (nx - px) / sw))
            self.canvas.yview_moveto(max(0.0, (ny - py) / sh))
        self._anchor = None
        self.lbl_zoom.configure(text=f"{int(self.zoom * 100)}%")
        self._update_nav(extra)
        self._draw_current()

    # -------------------------------------------------------- occorrenze
    def _collect_occurrences(self, token, kind, path):
        """Trova in background tutte le occorrenze del documento (tutte le pagine/fogli)."""
        groups, sha, count, doc_type = self.groups, self.sha256, self.count, self.doc_type
        use_ocr = path == self.original
        box_page = getattr(self, "box_page", None)
        db = self.app.db

        def work():
            occ = []
            try:
                if kind == "pdf":
                    import pymupdf

                    with pymupdf.open(path) as doc:
                        for i, page in enumerate(doc):
                            boxes = db.get_ocr_boxes(sha, i + 1) if use_ocr else []
                            marks = preview.pdf_page_marks(page, groups, boxes)
                            occ += [(i, gi, b) for gi, b in preview.reading_order(marks)]
                elif kind == "image":
                    for i in range(count):
                        marks = preview.ocr_marks(db.get_ocr_boxes(sha, box_page or i + 1), groups)
                        occ += [(i, gi, b) for gi, b in preview.reading_order(marks)]
                elif kind == "sheet":
                    for i in range(count):
                        if token != self.token:
                            break     # nel frattempo è stato scelto un altro risultato: lavoro inutile
                        time.sleep(0.003)   # fogli con centinaia di pagine: si lascia respirare la finestra
                        if not preview.sheet_page_has_hits(path, doc_type, i, groups):
                            continue  # si disegnano solo le pagine del foglio con risultati
                        marks = preview.sheet_marks(path, doc_type, i, groups)
                        occ += [(i, gi, b) for gi, b in preview.reading_order(marks)]
            except Exception:  # noqa: BLE001
                pass
            finally:
                db.close()
            self.app.events.put((self._occ_ready, (token, occ)))

        threading.Thread(target=work, daemon=True).start()

    def _occ_ready(self, token, occ):
        if token != self.token:
            return
        self.occ = occ
        if not occ:
            self.occ_i = -1
            self._occ_state(tr("Nessuna occorrenza visibile") if self.groups else "")
            return
        # si parte dalla prima occorrenza della pagina del risultato scelto (o della successiva)
        first = next((i for i, o in enumerate(occ) if o[0] >= self.page), 0)
        self.focus_occ(first)

    def step_occ(self, delta):
        if self.occ:
            self.focus_occ((self.occ_i + delta) % len(self.occ))

    def focus_occ(self, i):
        """Porta in vista l'occorrenza i: cambia pagina se serve e la centra."""
        self.occ_i = i
        page, gi, (x0, y0, x1, y1) = self.occ[i]
        if page != self.page:
            self.page = page
            self.render(reset_view=True)
        x, y, w, h = self._img_box
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        region = self.canvas.cget("scrollregion").split()
        sw, sh = (float(region[2]), float(region[3])) if len(region) == 4 else (cw, ch)
        cx, cy = x + (x0 + x1) / 2 * w, y + (y0 + y1) / 2 * h
        self.canvas.xview_moveto(max(0.0, (cx - cw / 2) / sw))
        self.canvas.yview_moveto(max(0.0, (cy - ch / 2) / sh))
        self._draw_current()
        if self.kind == "sheet":
            # il testo raw è per foglio intero, le pagine dell'anteprima sono blocchi di righe
            sp = preview.sheet_pages(self.path, self.doc_type)
            sheet = sp[page][0]
            same = [o for o in self.occ if sp[o[0]][0] == sheet]
            raw_page = sheet + 1
            where = preview.sheet_page_label(self.path, self.doc_type, page)
        else:
            same = [o for o in self.occ if o[0] == page]
            # immagine incollata nel documento (testo letto con l'OCR): il suo testo è la "pagina" box_page,
            # non la diapositiva 1; altrimenti il riquadro del testo saltava al testo della diapositiva
            raw_page = self.box_page or page + 1
            where = tr("pag. {n}", n=page + 1)
        self._occ_state(f"{i + 1} / {len(self.occ)}   ({where})")
        if self.on_occurrence:
            self.on_occurrence(raw_page, same.index(self.occ[i]))

    def _draw_current(self):
        self.canvas.delete("cur")
        if not (0 <= self.occ_i < len(self.occ)):
            return
        page, gi, (x0, y0, x1, y1) = self.occ[self.occ_i]
        if page != self.page:
            return
        x, y, w, h = self._img_box
        m = theme.px(self.canvas, 5)               # canvas units are physical pixels
        round_rect(self.canvas, x + x0 * w - m, y + y0 * h - m, x + x1 * w + m, y + y1 * h + m,
                   theme.px(self.canvas, 8), outline="#e8195a", width=theme.px(self.canvas, 3), fill="", tags="cur")

    def _occ_state(self, text=None):
        if text is not None:
            self.lbl_occ.configure(text=text)
        state = "normal" if len(self.occ) > 1 else "disabled"
        self.btn_occ_prev.configure(state=state)
        self.btn_occ_next.configure(state=state)

    def _on_resize(self, _e):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, self.render)

    def _on_wheel(self, e):
        """Rotellina: scorre il documento (Maiusc + rotellina: in orizzontale). Lo zoom è sui pulsanti."""
        if self.kind not in ("pdf", "image", "sheet"):
            return
        step = -3 if e.delta > 0 else 3
        if e.state & 0x0001:  # Maiusc
            self.canvas.xview_scroll(step, "units")
        else:
            self.canvas.yview_scroll(step, "units")

    def zoom_at(self, factor, px=None, py=None):
        if self.kind not in ("pdf", "image", "sheet"):
            return
        if px is None:
            px, py = self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2
        new = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if new == self.zoom:
            return
        if self._anchor is None:
            x, y, w, h = self._img_box
            cx, cy = self.canvas.canvasx(px), self.canvas.canvasy(py)
            self._anchor = ((cx - x) / w, (cy - y) / h, px, py)
        self.zoom = new
        self.lbl_zoom.configure(text=f"{int(self.zoom * 100)}%")
        # con la rotellina arrivano molti eventi: si renderizza una volta sola alla fine
        if self._wheel_job:
            self.after_cancel(self._wheel_job)
        self._wheel_job = self.after(60, self.render)

    def fit(self):
        self.zoom = 1.0
        self.render(reset_view=True)

    def goto(self, page):
        if self.kind in ("pdf", "image", "sheet") and 0 <= page < self.count:
            self.page = page
            self.render(reset_view=True)

    def _update_nav(self, extra=""):
        nav = self.kind in ("pdf", "image", "sheet") and self.count > 0
        self.lbl_page.configure(text=tr("Pagina {n}/{count}", n=self.page + 1, count=self.count) + extra if nav else "")
        self.btn_prev.configure(state="normal" if nav and self.page > 0 else "disabled")
        self.btn_next.configure(state="normal" if nav and self.page < self.count - 1 else "disabled")

    def open_original(self):
        if self.original:
            open_file(self.original)


class AnnotationBar(ctk.CTkFrame):
    """Importanza (5 colori) e nota del file mostrato nell'anteprima. Si salvano subito nel db e
    restano legate al file anche se viene spostato, rinominato o modificato."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.PANEL_2, corner_radius=4)
        self.app = app
        self.path_id = None
        self.level = 0
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(6, 2))
        theme.caption(row, tr("Importanza"), app.fonts).pack(side="left", padx=(0, 8))
        self.buttons = {}
        for lvl, color in theme.LEVEL_COLORS.items():
            b = ctk.CTkButton(row, text="", width=26, height=22, corner_radius=11, fg_color=color,
                              hover_color=color, border_width=0, text_color="#000000",
                              command=lambda v=lvl: self.set_level(v))
            b.pack(side="left", padx=2)
            self.buttons[lvl] = b
        ctk.CTkButton(row, text=tr("Nessuna"), height=22, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      font=app.fonts.small, command=lambda: self.set_level(0)).pack(side="left", padx=(6, 0))
        self.saved = ctk.CTkLabel(row, text="", text_color=theme.TEXT_DIM, font=app.fonts.small)
        self.saved.pack(side="right")
        nrow = ctk.CTkFrame(self, fg_color="transparent")
        nrow.pack(fill="x", padx=8, pady=(2, 6))
        self.note = ctk.CTkTextbox(nrow, height=46, wrap="word", border_width=1, border_color=theme.BORDER)
        self.note.pack(side="left", fill="x", expand=True)
        self.note.bind("<FocusOut>", lambda e: self.save_note())
        self.note.bind("<Control-s>", lambda e: (self.save_note(), "break")[1])
        nbtns = ctk.CTkFrame(nrow, fg_color="transparent")
        nbtns.pack(side="left", padx=(6, 0))
        ctk.CTkButton(nbtns, text=tr("Salva nota"), height=22, command=self.save_note).pack(fill="x")
        ctk.CTkButton(nbtns, text=tr("Cancella nota"), height=22, command=self.clear_note,
                      **theme.DANGER_STYLE).pack(fill="x", pady=(2, 0))
        self.load(None)

    def load(self, path_id):
        self.path_id = path_id
        level, note = (0, "")
        if path_id and self.app.db:
            level, note = self.app.db.annotation(path_id)
        self.level = level
        self.note.configure(state="normal")
        self.note.delete("1.0", "end")
        self.note.insert("1.0", note)
        if not path_id:
            self.note.configure(state="disabled")
        self._paint()
        self.saved.configure(text="")

    def _paint(self):
        for lvl, b in self.buttons.items():
            on = lvl == self.level
            b.configure(text="✓" if on else "", border_width=2 if on else 0, border_color=theme.TEXT)

    def set_level(self, level: int):
        if not self.path_id:
            return
        self.level = level
        self.app.db.set_annotation(self.path_id, level=level)
        self._paint()
        self.saved.configure(text=tr(theme.LEVEL_NAMES.get(level, "Nessuna")))
        self.app.annotations_changed(self.path_id)

    def clear_note(self):
        """Cancella la nota del file (dopo conferma, se c'è una nota salvata)."""
        if not self.path_id:
            return
        saved = self.app.db.annotation(self.path_id)[1]
        if saved and not messagebox.askyesno(tr("Cancella nota"), tr("Cancellare la nota di questo documento?"),
                                             icon="warning"):
            return
        self.note.delete("1.0", "end")
        if saved:
            self.app.db.set_annotation(self.path_id, note="")
            self.saved.configure(text=tr("Nota cancellata"))
            self.app.annotations_changed(self.path_id)

    def save_note(self):
        if not self.path_id:
            return
        text = self.note.get("1.0", "end").strip()
        if text != self.app.db.annotation(self.path_id)[1]:
            self.app.db.set_annotation(self.path_id, note=text)
            self.saved.configure(text=tr("Nota salvata"))
            self.app.annotations_changed(self.path_id)


def round_rect(canvas, x0, y0, x1, y1, r, **kw):
    """Rettangolo con angoli arrotondati sul canvas (poligono smussato)."""
    r = max(1, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
           x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return canvas.create_polygon(pts, smooth=True, **kw)


class InfoText(tk.Text):
    """Riga informativa sopra l'anteprima (nome archiviato e nome originale). È un Text in sola
    lettura invece di un'etichetta, così si possono colorare le parti del nome trovate."""

    def __init__(self, master):
        super().__init__(master, height=2, wrap="word", bd=0, highlightthickness=0, bg=theme.PANEL,
                         fg=theme.TEXT_SOFT, font=(theme.ui_font(), 10), cursor="arrow", padx=2, pady=2, takefocus=0)
        self._text = ""
        self.bind("<Key>", lambda e: "break")

    def configure(self, cnf=None, **kw):
        if "text" not in kw:
            return super().configure(cnf, **kw)
        self._text = kw.pop("text") or ""
        super().configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", self._text)
        lines = self._text.count("\n") + 1
        super().configure(state="disabled", height=min(3, max(1, lines)), **kw)

    def cget(self, key):
        return self._text if key == "text" else super().cget(key)

    def mark(self, a: int, b: int, color: str, tag: str):
        self.tag_configure(tag, background=color, foreground="#000000")
        self.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")


class ResultsList(tk.Frame):
    """Tabella dei risultati basata su un widget Text: a differenza di ttk.Treeview permette di
    colorare solo le parole trovate dentro l'estratto, con il colore della riga di ricerca.
    Espone la parte dell'interfaccia di Treeview usata dalla schermata di ricerca."""

    COLUMNS = (("Imp.", 66), ("Nome", 200), ("Cartella", 160), ("Pag.", 56), ("Rilev.", 50),
               ("Creato", 128), ("Estratto", 0))

    def __init__(self, master):
        self.bg, fg, head_bg = theme.PANEL, theme.TEXT, theme.BG
        self.sel_bg = theme.SELECT_BG
        super().__init__(master, bg=self.bg)
        self.container = self
        import tkinter.font as tkfont

        self.font = tkfont.Font(family=theme.ui_font(), size=10)
        bold = tkfont.Font(family=theme.mono_font(), size=9, weight="bold")
        # tab stops are physical pixels: scale the logical widths, and keep each column at least as wide
        # as its translated heading (plus room for the sort arrow)
        self.widths = [max(theme.px(self, w), bold.measure(tr(t) + " ▼") + theme.px(self, 14)) if w else 0
                       for t, w in self.COLUMNS]
        stops, x = [], 0
        for w in self.widths[:-1]:
            x += w
            stops.append(x)
        self.head = tk.Text(self, height=1, wrap="none", bd=0, padx=6, pady=6, font=bold, bg=head_bg, fg=theme.TEXT_DIM,
                            tabs=stops, cursor="arrow", highlightthickness=0)
        self.stops = stops
        self.on_sort = None            # callback(indice colonna) quando si clicca un'intestazione
        self.set_header()
        self.head.bind("<Button-1>", self._head_click)
        self.head.configure(cursor="hand2")
        self.text = tk.Text(self, wrap="none", bd=0, padx=6, pady=2, font=self.font, bg=self.bg, fg=fg,
                            tabs=stops, cursor="arrow", highlightthickness=0, spacing1=4, spacing3=4,
                            insertwidth=0, exportselection=False)
        ys = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xs = ttk.Scrollbar(self, orient="horizontal", command=self._xview)
        self.text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.head.grid(row=0, column=0, sticky="ew")
        self.text.grid(row=1, column=0, sticky="nsew")
        ys.grid(row=1, column=1, sticky="ns")
        xs.grid(row=2, column=0, sticky="ew")
        self.text.tag_configure("selrow", background=self.sel_bg, foreground="#ffffff")
        self.text.tag_lower("selrow")
        # è una lista, non un testo: niente selezione del testo col mouse (trascinamento, Maiusc/Ctrl+clic,
        # doppio/triplo clic), che colorava pezzi di righe e sembrava una selezione multipla
        self.text.configure(selectbackground=self.bg, inactiveselectbackground=self.bg, selectforeground=fg)
        for seq in ("<B1-Motion>", "<Shift-Button-1>", "<Control-Button-1>", "<Triple-1>",
                    "<B1-Leave>", "<ButtonRelease-1>", "<Shift-B1-Motion>"):
            self.text.bind(seq, lambda e: "break")
        self.text.bind("<Button-1>", self._click)
        self.text.bind("<Double-1>", self._double)
        self.text.bind("<Up>", lambda e: self._move(-1))
        self.text.bind("<Down>", lambda e: self._move(1))
        self.text.bind("<Key>", lambda e: "break" if e.keysym not in ("Up", "Down", "Prior", "Next") else None)
        self._items: list[str] = []
        self._full: list[list[str]] = []   # valori completi delle celle (per il tooltip)
        self._paths: list[str] = []        # percorso del file di ogni riga (tooltip di Nome e Cartella)
        for lvl, color in theme.LEVEL_COLORS.items():   # pallini dell'importanza nel loro colore
            self.text.tag_configure(f"dot{lvl}", foreground=color)
        self._sel: str | None = None
        self._tip: tk.Toplevel | None = None
        self._tip_key = None
        self.text.bind("<Motion>", self._on_motion)
        self.text.bind("<Leave>", lambda e: self._hide_tip())

    def set_header(self, col: int | None = None, rev: bool = False):
        titles = [tr(t) for t, _w in self.COLUMNS]
        if col is not None:
            titles[col] += " ▼" if rev else " ▲"
        self.head.configure(state="normal")
        self.head.delete("1.0", "end")
        self.head.insert("1.0", "\t".join(titles))
        self.head.configure(state="disabled")

    def _head_click(self, e):
        # colonna = numero di tabulazioni prima del punto cliccato (vale anche con la tabella scorsa)
        idx = self.head.index(f"@{e.x},{e.y}")
        col = min(self.head.get("1.0", idx).count("\t"), len(self.COLUMNS) - 1)
        if self.on_sort:
            self.on_sort(col)
        return "break"

    def _xview(self, *args):
        self.text.xview(*args)
        self.head.xview(*args)

    def _fit(self, value: str, width: int) -> str:
        if not width or self.font.measure(value) <= width - theme.px(self, 12):
            return value
        while value and self.font.measure(value + "…") > width - theme.px(self, 12):
            value = value[:-1]
        return value + "…"

    # --------------------------------------------------- API tipo Treeview
    def get_children(self):
        return list(self._items)

    def delete(self, *items):
        self.text.delete("1.0", "end")
        self._items.clear()
        self._full.clear()
        self._paths.clear()
        self._hide_tip()
        self._sel = None

    def insert(self, _parent, _index, values, groups=None, level: int = 0, path: str = ""):
        iid = f"r{len(self._items)}"
        cells = [self._fit(str(v), w) for v, w in zip(values[:-1], self.widths)]
        prefix = "\t".join(cells) + "\t"
        snippet = str(values[-1])
        line = len(self._items) + 1
        if self._items:
            self.text.insert("end", "\n")
        self.text.insert("end", prefix + snippet)
        # il testo inserito dopo una riga colorata ne erediterebbe il colore: si toglie, poi si mette il suo
        for lvl in theme.LEVEL_COLORS:
            self.text.tag_remove(f"lvl{lvl}", f"{line}.0", f"{line}.end+1c")
        if level:
            tag = f"lvl{level}"
            self.text.tag_configure(tag, background=theme.tint(theme.LEVEL_COLORS[level]))
            self.text.tag_add(tag, f"{line}.0", f"{line}.end+1c")
            self.text.tag_lower(tag)
            self.text.tag_add(f"dot{level}", f"{line}.0", f"{line}.{len(cells[0])}")
            self.text.tag_raise(f"dot{level}")
        for gi, terms in enumerate(groups or []):
            tag = f"hit{gi}"
            self.text.tag_configure(tag, background=preview.color(gi), foreground="#000000")
            for a, b in preview.find_hits(snippet, terms):
                self.text.tag_add(tag, f"{line}.{len(prefix) + a}", f"{line}.{len(prefix) + b}")
        self._items.append(iid)
        self._full.append([str(v) for v in values[:-1]])
        self._paths.append(path)
        return iid

    # ------------------------------------------------------------ tooltip
    def _on_motion(self, e):
        """Sul nome (o sulla colonna) troncato mostra il valore completo in un tooltip."""
        idx = self.text.index(f"@{e.x},{e.y}")
        line, col = (int(x) for x in idx.split("."))
        bbox = self.text.bbox(idx)
        if not (1 <= line <= len(self._full)) or not bbox or e.y > bbox[1] + bbox[3]:
            return self._hide_tip()
        ncol = self.text.get(f"{line}.0", idx).count("	")
        if ncol >= len(self._full[line - 1]):
            return self._hide_tip()   # colonna Estratto: niente tooltip
        full = self._full[line - 1][ncol]
        shown = self.text.get(f"{line}.0", f"{line}.end").split("	")[ncol]
        path = self._paths[line - 1]
        if ncol in (1, 2) and path:   # Nome e Cartella: sempre il percorso completo
            full = path if ncol == 1 else os.path.dirname(path)
        elif shown == full:
            return self._hide_tip()   # non troncato
        key = (line, ncol)
        if key != self._tip_key:
            self._show_tip(full, e.x_root + 14, e.y_root + 18)
            self._tip_key = key
        elif self._tip:
            self._tip.geometry(f"+{e.x_root + 14}+{e.y_root + 18}")

    def _show_tip(self, text, x, y):
        self._hide_tip()
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, bg=theme.PANEL_3, fg=theme.TEXT, relief="solid", bd=1, padx=6, pady=3,
                 font=(theme.ui_font(), 10), wraplength=theme.px(self, 700), justify="left").pack()
        tip.geometry(f"+{x}+{y}")
        self._tip = tip

    def _hide_tip(self):
        if self._tip is not None:
            self._tip.destroy()
        self._tip = None
        self._tip_key = None

    def selection(self):
        return (self._sel,) if self._sel else ()

    def selection_set(self, iid):
        if iid not in self._items:
            return
        self._sel = iid
        line = self._items.index(iid) + 1
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_remove("selrow", "1.0", "end")
        self.text.tag_add("selrow", f"{line}.0", f"{line}.end+1c")
        self.see(iid)
        self.event_generate("<<TreeviewSelect>>")

    def focus(self, iid=None):
        self.text.focus_set()

    def see(self, iid):
        if iid in self._items:
            self.text.see(f"{self._items.index(iid) + 1}.0")

    def _click(self, e):
        self.text.tag_remove("sel", "1.0", "end")
        line = int(self.text.index(f"@{e.x},{e.y}").split(".")[0])
        if 1 <= line <= len(self._items) and self._items[line - 1] != self._sel:
            self.selection_set(self._items[line - 1])
        self.text.focus_set()
        return "break"

    def _double(self, e):
        self._click(e)
        self.event_generate("<<ResultOpen>>")
        return "break"

    def _move(self, delta):
        if self._items:
            i = self._items.index(self._sel) if self._sel else -1
            self.selection_set(self._items[max(0, min(len(self._items) - 1, i + delta))])
        return "break"


def fmt_time(ts) -> str:
    """Data e ora da timestamp (creazione/modifica del file), ordinabile come testo."""
    import time as _t

    return _t.strftime("%Y-%m-%d %H:%M", _t.localtime(ts)) if ts else ""


def shorten(text: str, n: int = 80) -> str:
    return text if len(text) <= n else text[: n // 2 - 1] + "…" + text[-(n // 2 - 1):]


def highlight(textbox: ctk.CTkTextbox, content: str, groups: list[list[str]]):
    """Colora lo sfondo dei termini trovati con il colore della riga di ricerca."""
    tb = textbox._textbox
    for tag in tb.tag_names():
        if tag.startswith("hit"):
            tb.tag_remove(tag, "1.0", "end")
    # posizioni carattere -> "riga.colonna" del testo mostrato (a capo inseriti da wrap_for_display,
    # stessa lunghezza): molto più veloce di "1.0+Nc" quando i risultati sono migliaia
    import bisect

    shown = tb.get("1.0", "end-1c")
    starts = [0] + [i + 1 for i, ch in enumerate(shown) if ch == "\n"]

    def idx(pos):
        ln = bisect.bisect_right(starts, pos) - 1
        return f"{ln + 1}.{pos - starts[ln]}"

    found = set()
    for gi, terms in enumerate(groups):
        tag = f"hit{gi}"
        tb.tag_configure(tag, background=preview.color(gi), foreground="#000000")
        spans = []
        group_hits = preview.find_hits(content, terms)     # una sola ricerca per gruppo (serve anche sotto)
        found.update(group_hits)
        for start, end in group_hits:
            spans += [idx(start), idx(end)]
        for k in range(0, len(spans), 2000):  # tag_add accetta molti intervalli in una chiamata
            tb.tag_add(tag, *spans[k:k + 2000])
    hits = sorted(found)
    if hits:
        tb.see(idx(hits[0][0]))
    return [(idx(a), idx(b)) for a, b in hits]


class SearchPage(ctk.CTkFrame):
    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.results: dict[str, dict] = {}
        self.current: dict | None = None
        self.boolean = tk.BooleanVar(value=False)
        self.groups: list[list[str]] = []

        # ---- a sinistra: cartelle in cui cercare
        cfp = ctk.CTkFrame(self, width=250, corner_radius=8)
        cfp.pack(side="left", fill="y", padx=(0, 12))
        cfp.pack_propagate(False)
        theme.caption(cfp, tr("Cerca in"), app.fonts).pack(anchor="w", padx=10, pady=(10, 4))
        btns = ctk.CTkFrame(cfp, fg_color="transparent")
        btns.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkButton(btns, text=tr("Tutti"), width=60, height=26, command=lambda: self.check_all(True)).pack(side="left")
        ctk.CTkButton(btns, text=tr("Nessuno"), width=70, height=26, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=lambda: self.check_all(False)).pack(side="left", padx=6)
        self.cf_list = ctk.CTkScrollableFrame(cfp, fg_color="transparent")
        self.cf_list.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        self.cf_vars: dict[str, tk.BooleanVar] = {}
        self.filters: dict = {}

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(body, text=tr("Ricerca"), font=app.h1).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(body, text=tr("Una ricerca per riga, ognuna con il suo colore: le righe sono in OR. In ogni riga "
                                "devono comparire tutte le parole (anche come inizio parola); \"tra virgolette\" = frase. Avanzata: ogni riga usa "
                                'AND, OR, NOT, "frase esatta", radice*, NEAR(a b, 5).  Ctrl+Invio per cercare.')
                     + " " + tr("Regex: espressione regolare sul testo, con l'editor dei pattern pronti."),
                     wraplength=1000, justify="left", anchor="w",
                     text_color=theme.TEXT_DIM).pack(anchor="w", fill="x", pady=(0, 8))
        theme.autowrap(body.winfo_children()[-1], 1000)

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        self.query = ctk.CTkTextbox(row, height=96, wrap="none", border_width=2,
                                    font=ctk.CTkFont(size=14))
        self.query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.query.bind("<Control-Return>", lambda e=None: (self.search(), "break")[1])
        self.query.bind("<KeyRelease>", lambda e=None: self.color_query())
        self.query.bind("<<Paste>>", lambda e=None: self.after(10, self.color_query))
        side = ctk.CTkFrame(row, fg_color="transparent")
        side.pack(side="left", fill="y")
        ctk.CTkButton(side, text=tr("Cerca"), width=110, height=36, command=self.search).pack(pady=(0, 6))
        ctk.CTkCheckBox(side, text=tr("Avanzata"), variable=self.boolean).pack(anchor="w")
        self.important = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(side, text=tr("Solo documenti importanti"), variable=self.important).pack(anchor="w",
                                                                                              pady=(4, 0))
        # fonti in cui cercare: testo dei documenti e tabelle dedicate dei moduli aggiuntivi
        self.sources = {"text": tk.BooleanVar(value=True), "meta": tk.BooleanVar(value=False),
                        "archive": tk.BooleanVar(value=True), "db": tk.BooleanVar(value=True)}
        self.regex = tk.BooleanVar(value=False)
        rxrow = ctk.CTkFrame(side, fg_color="transparent")
        rxrow.pack(anchor="w", pady=(4, 0))
        ctk.CTkCheckBox(rxrow, text=tr("Regex"), variable=self.regex).pack(side="left")
        ctk.CTkButton(rxrow, text=tr("Editor regex..."), width=110, height=24, font=app.fonts.small,
                      fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.open_regex_editor).pack(side="left", padx=(6, 0))
        self.exact = tk.BooleanVar(value=False)
        self.in_names = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(side, text=tr("Cerca frase esatta"), variable=self.exact).pack(anchor="w", pady=(4, 0))
        ctk.CTkCheckBox(side, text=tr("Cerca nel nome del file"), variable=self.in_names).pack(anchor="w", pady=(4, 0))
        self.any_order = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(side, text=tr("Frase in qualsiasi ordine"), variable=self.any_order).pack(anchor="w", pady=(4, 0))
        # ---- filtri: periodo (data di modifica o di creazione) e dimensione del file
        flt = ctk.CTkFrame(cfp, fg_color="transparent")
        flt.pack(side="bottom", fill="x", padx=8, pady=(0, 10))
        theme.caption(flt, tr("Cerca nei dati"), app.fonts).pack(anchor="w", pady=(6, 2))
        for key, label in (("text", "Testo dei documenti"), ("meta", "Metadati (ExifTool)"),
                           ("archive", "File dentro gli archivi"), ("db", "Contenuto dei database")):
            ctk.CTkCheckBox(flt, text=tr(label), variable=self.sources[key], font=app.fonts.small,
                            checkbox_width=18, checkbox_height=18).pack(anchor="w", pady=1)
        theme.caption(flt, tr("Filtri"), app.fonts).pack(anchor="w", pady=(6, 4))
        self.date_field = tk.StringVar(value=tr("Modificato"))
        ctk.CTkSegmentedButton(flt, values=[tr("Modificato"), tr("Creato")], variable=self.date_field).pack(
            fill="x")
        self.flt = {k: tk.StringVar() for k in ("date_from", "date_to", "size_min", "size_max")}
        for row_label, a, b, hint in ((tr("Dal / al"), "date_from", "date_to", tr("aaaa-mm-gg")),
                                      (tr("MB da / a"), "size_min", "size_max", "0.5")):
            ctk.CTkLabel(flt, text=row_label, anchor="w", font=app.fonts.small,
                         text_color=theme.TEXT_DIM).pack(fill="x", pady=(6, 0))
            r = ctk.CTkFrame(flt, fg_color="transparent")
            r.pack(fill="x")
            ctk.CTkEntry(r, textvariable=self.flt[a], placeholder_text=hint, height=28, width=100).pack(
                side="left", fill="x", expand=True)
            ctk.CTkEntry(r, textvariable=self.flt[b], placeholder_text=hint, height=28, width=100).pack(
                side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(flt, text=tr("Lingua del documento"), anchor="w", font=app.fonts.small,
                     text_color=theme.TEXT_DIM).pack(fill="x", pady=(6, 0))
        self.all_langs = tr("Tutte le lingue")
        self.lang_codes: dict[str, str] = {}
        self.lang_var = tk.StringVar(value=self.all_langs)
        self.lang_menu = ctk.CTkOptionMenu(flt, values=[self.all_langs], variable=self.lang_var, height=28,
                                           dynamic_resizing=False)
        self.lang_menu.pack(fill="x")
        ctk.CTkButton(flt, text=tr("Azzera filtri"), height=24, font=app.fonts.small, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER,
                      command=self.clear_filters).pack(fill="x", pady=(6, 0))
        fz = ctk.CTkFrame(side, fg_color="transparent")
        fz.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(fz, text=tr("Fuzzy (errori):")).pack(side="left", padx=(0, 6))
        self.fuzzy = tk.StringVar(value="No")
        ctk.CTkSegmentedButton(fz, values=["No", "1", "2", "3", "4"], variable=self.fuzzy).pack(side="left")

        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        small_btn = {"height": 28, "fg_color": theme.NEUTRAL, "hover_color": theme.NEUTRAL_HOVER}
        ctk.CTkButton(bar, text=tr("Salva ricerca..."), width=140, command=self.save_search, **small_btn).pack(
            side="left")
        self.btn_saved = ctk.CTkButton(bar, text=tr("Ricerche salvate"), width=170, command=self.open_saved,
                                       **small_btn)
        self.btn_saved.pack(side="left", padx=6)
        ctk.CTkButton(bar, text=tr("Esporta risultati..."), width=160, command=self.export_results,
                      **small_btn).pack(side="left")
        # visibile solo mentre una ricerca regex lavora (gira in un processo separato, si può fermare)
        self.btn_stop = ctk.CTkButton(bar, text=tr("Ferma ricerca"), width=130, height=28, fg_color=theme.WARN_BTN,
                                      hover_color=theme.WARN_BTN_HOVER, command=self.stop_regex)
        self._rx_proc = None
        self._rx_groups: list = []
        self._reselect = None
        self.notice = ctk.CTkLabel(bar, text="", text_color=theme.WARN, anchor="w", corner_radius=6)
        self.notice.pack(side="left", padx=12)
        self._notice_job = None
        self.update_saved_badge()

        sash_bg = theme.BG
        px = lambda n: theme.px(body, n)       # plain tk PanedWindow sizes are physical pixels
        hpane = tk.PanedWindow(body, orient="horizontal", sashwidth=px(6), bd=0, bg=sash_bg)
        hpane.pack(fill="both", expand=True)

        left = tk.PanedWindow(hpane, orient="vertical", sashwidth=px(6), bd=0, bg=sash_bg)
        # sopra la tabella: un pulsante per ogni estensione presente nei risultati, per filtrarli
        results_box = tk.Frame(left, bg=theme.BG)
        self.ext_bar = tk.Frame(results_box, bg=theme.BG)
        self.ext_bar.pack(fill="x")
        self.ext_bar.bind("<Configure>", lambda e=None: self._flow_ext(getattr(e, "width", None)))
        self._ext_off: set[str] = set()
        self._ext_btns: dict[str, ctk.CTkButton] = {}
        self._ext_extra: list = []
        self._ext_width = 0
        self.tree = ResultsList(results_box)
        self.tree.pack(fill="both", expand=True)
        self.tree.on_sort = self.sort_results
        self._rows: list[tuple[dict, list]] = []
        self._sort = None
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<<ResultOpen>>", lambda e=None: self.preview.open_original())
        left.add(results_box, minsize=px(140), height=px(300))

        bottom = ctk.CTkFrame(left, fg_color="transparent")
        self.lbl = ctk.CTkLabel(bottom, text="", anchor="w")
        self.lbl.pack(fill="x", pady=(6, 2))
        self.raw = ctk.CTkTextbox(bottom, wrap="word")
        self.raw.pack(fill="both", expand=True)
        left.add(bottom, minsize=px(120))

        self.preview = PreviewPanel(hpane, app)
        self.preview.on_occurrence = self.sync_raw
        self.raw_hits: list[str] = []
        self.raw_page = None
        hpane.add(left, minsize=px(320), width=px(560))
        hpane.add(self.preview, minsize=px(300))

    def refresh_folders(self):
        """Cartelle monitorate con spunta (dove cercare); quelle nuove partono selezionate."""
        old = {d: v.get() for d, v in self.cf_vars.items()}
        for w in self.cf_list.winfo_children():
            w.destroy()
        self.cf_vars.clear()
        for d in self.app.cfg.watch_dirs:
            v = tk.BooleanVar(value=old.get(d, True))
            ctk.CTkCheckBox(self.cf_list, text=shorten(d, 34), variable=v).pack(anchor="w", pady=3, padx=4)
            self.cf_vars[d] = v
        if not self.app.cfg.watch_dirs:
            ctk.CTkLabel(self.cf_list, text=tr("Nessuna cartella monitorata.\nAggiungila in Impostazioni."),
                         justify="left", text_color=theme.TEXT_DIM).pack(anchor="w", padx=4)
        self.refresh_languages()
        self.update_saved_badge()

    def refresh_languages(self):
        from . import lang as lang_mod

        try:
            langs = self.app.db.languages() if self.app._db_ready else []
        except Exception:  # noqa: BLE001
            langs = []
        self.lang_codes = {f"{lang_mod.name(code)} ({n})": code for code, n in langs}
        current = self.lang_var.get()
        self.lang_menu.configure(values=[self.all_langs, *self.lang_codes])
        if current != self.all_langs and current not in self.lang_codes:
            code = next((c for name, c in self.lang_codes.items() if name.split(" (")[0] == current.split(" (")[0]),
                        None)
            self.lang_var.set(next((n for n, c in self.lang_codes.items() if c == code), self.all_langs))

    def clear_filters(self):
        for v in self.flt.values():
            v.set("")
        self.lang_var.set(self.all_langs)

    # ------------------------------------------------- ricerca come dizionario
    def raw_filters(self) -> dict:
        return {"date_field": "created" if self.date_field.get() == tr("Creato") else "modified",
                **{k: v.get().strip() for k, v in self.flt.items()},
                "lang": self.lang_codes.get(self.lang_var.get(), "")}

    def spec(self) -> dict:
        """La ricerca impostata nella pagina (per eseguirla, salvarla o esportarla)."""
        folders = self.selected_folders()
        return {"query": self.query.get("1.0", "end").strip(), "regex": self.regex.get(),
                "advanced": self.boolean.get(), "exact": self.exact.get(), "in_names": self.in_names.get(),
                "any_order": self.any_order.get(), "fuzzy": 0 if self.fuzzy.get() == "No" else int(self.fuzzy.get()),
                "important": self.important.get(), "sources": list(self.selected_sources()),
                # tutte le cartelle selezionate = tutte le monitorate, anche quelle aggiunte in futuro
                "folders": [] if len(folders) == len(self.cf_vars) else folders,
                "filters": self.raw_filters()}

    def load_spec(self, spec: dict):
        """Rimette nella pagina una ricerca salvata."""
        spec = {**searches.DEFAULT_SPEC, **spec}
        self.query.delete("1.0", "end")
        self.query.insert("1.0", spec["query"])
        for var, key in ((self.regex, "regex"), (self.boolean, "advanced"), (self.exact, "exact"),
                         (self.in_names, "in_names"), (self.any_order, "any_order"), (self.important, "important")):
            var.set(bool(spec[key]))
        self.fuzzy.set(str(spec["fuzzy"]) if spec["fuzzy"] else "No")
        for k, v in self.sources.items():
            v.set(k in spec["sources"])
        for d, v in self.cf_vars.items():
            v.set(not spec["folders"] or d in spec["folders"])
        f = spec["filters"] or {}
        self.date_field.set(tr("Creato") if f.get("date_field") == "created" else tr("Modificato"))
        for k, v in self.flt.items():
            v.set(f.get(k, ""))
        self.refresh_languages()
        self.lang_var.set(next((n for n, c in self.lang_codes.items() if c == f.get("lang")), self.all_langs))
        self.color_query()

    # ---------------------------------------------- ricerche salvate, export
    def update_saved_badge(self):
        n = self.app.saved.new_count()
        self.btn_saved.configure(text=tr("Ricerche salvate") + (f"  ({n} " + tr("nuovi") + ")" if n else ""),
                                 text_color=theme.WARN if n else theme.TEXT)

    def save_search(self):
        spec = self.spec()
        if getattr(self, "_auto_fuzzy", 0) and not spec["fuzzy"] and not spec["regex"]:
            spec["fuzzy"] = 1     # i risultati mostrati erano quelli tolleranti: si salva così
        if not spec["query"]:
            messagebox.showinfo(tr("Ricerca"), tr("Scrivi prima cosa cercare."))
            return
        try:
            searches.parse_filters(spec["filters"])
        except ValueError as exc:
            messagebox.showerror(tr("Ricerca"), str(exc))
            return
        saved_ui.SaveSearchDialog(self, self.app, spec)

    def open_saved(self):
        saved_ui.SavedSearchesWindow.open(self.app)

    def run_saved(self, item: dict, only_new: bool = False):
        """Apre una ricerca salvata: la rimette nella pagina e la esegue (only_new: solo i file nuovi)."""
        self.app.show("search")
        self.load_spec(item["spec"])
        new_ids = set(item.get("new") or [])
        self.search()
        if only_new and new_ids:
            self._rows = [x for x in self._rows if x[0]["id"] in new_ids]
            self._build_ext_bar(reset=True)
            self.show_results()
            self.set_notice(tr("Solo i file nuovi della ricerca salvata «{name}»", name=item["name"]))
        self.app.saved.mark_seen(item["id"])
        self.update_saved_badge()

    def export_results(self):
        if not self._rows:
            messagebox.showinfo(tr("Esporta"), tr("Nessun risultato da esportare: fai prima una ricerca."))
            return
        rows = [dict(r, snippet_text=r["snippet"] or make_snippet(r["content"], g, 300))
                for r, g in self._visible_rows()]
        if not rows:
            messagebox.showinfo(tr("Esporta"), tr("Nessun risultato da esportare: fai prima una ricerca."))
            return
        export.ask_and_export(self, rows, kind="results",
                              title=self.query.get("1.0", "end").strip().splitlines()[0][:80])

    def selected_sources(self) -> tuple:
        chosen = tuple(k for k, v in self.sources.items() if v.get())
        return chosen or ("text",)

    def read_filters(self) -> dict:
        """Filtri di data (aaaa-mm-gg, anche solo aaaa o aaaa-mm), di dimensione (MB) e di lingua."""
        return searches.parse_filters(self.raw_filters())

    def open_regex_editor(self):
        current = self.query.get("1.0", "end").strip() if self.regex.get() else ""

        def use(pattern):
            self.regex.set(True)
            self.query.delete("1.0", "end")
            self.query.insert("1.0", pattern)
            self.search()

        RegexEditor(self, current, use, self.app.fonts)

    def check_all(self, value: bool):
        for v in self.cf_vars.values():
            v.set(value)

    def selected_folders(self) -> list[str]:
        return [cid for cid, v in self.cf_vars.items() if v.get()]

    def meta_raw(self, r: dict) -> str:
        """Risultato nei metadati: tutti i metadati del file, una riga, poi il testo estratto."""
        parts = [self.app.db.meta_text(r["sha256"]) or r["content"]]
        pages = self.app.db.get_document_text(r["sha256"])
        if pages:
            body = []
            for p in pages:
                label = p["label"] or tr("pagina {n}", n=p["page_no"])
                body.append(f"[{label}]\n{p['content']}" if len(pages) > 1 else p["content"])
            line = "\u2500" * 32
            parts.append(line + "\n" + tr("Testo estratto") + "\n" + line + "\n" + "\n\n".join(body))
        return "\n".join(parts)

    RAW_LIMIT = 300_000     # caratteri mostrati nel riquadro del testo (fogli Excel enormi: milioni)

    def _raw_window(self, content: str, first: int | None) -> str:
        """Testo lunghissimo (es. un foglio da 50.000 righe): se ne mostra una parte, a partire dalla prima
        occorrenza. Tutto intero terrebbe ferma la finestra per molti secondi (colorare e disegnare)."""
        if len(content) <= self.RAW_LIMIT:
            return content
        if first is None:               # prima occorrenza: si cerca a blocchi, fermandosi al primo che ne ha
            first = 0
            pats = [p for terms in self.groups for p in preview.term_patterns(terms)]
            for off in range(0, len(content), 200_000):
                spans = preview.find_spans(content[off:off + 200_500], pats) if pats else []
                if spans:
                    first = off + min(a for a, _b in spans)
                    break
        start = max(0, min(first, len(content) - 1) - 2000)
        nl = content.rfind("\n", 0, start)
        if nl >= 0 and start - nl < 5000:
            start = nl + 1              # si parte dall'inizio di una riga
        return content[start:start + self.RAW_LIMIT]

    def show_raw(self, content: str, page_no, first: int | None = None):
        content = unicodedata.normalize("NFC", content)  # anche per testi estratti prima della correzione
        shown = self._raw_window(content, first)
        self.raw.delete("1.0", "end")
        self.raw.insert("1.0", preview.wrap_for_display(shown))
        self.raw_hits = highlight(self.raw, shown, self.groups)
        if len(shown) < len(content):
            self.raw.insert("end", "\n\n" + tr("[Testo molto lungo: qui ne sono mostrati {n} caratteri su {total}, a "
                                              "partire dalla prima occorrenza. L'anteprima a destra lo mostra tutto.]",
                                              n=f"{len(shown):,}".replace(",", "."),
                                              total=f"{len(content):,}".replace(",", ".")))
        self.raw_page = page_no

    def sync_raw(self, page_no: int, k: int):
        """Il testo raw segue l'occorrenza mostrata a destra: stessa pagina, k-esimo termine trovato."""
        if not self.current or self.current.get("source") == "meta":
            return      # metadati + testo intero: il riquadro non segue le pagine dell'anteprima
        if page_no != self.raw_page:
            pages = {p["page_no"]: p for p in self.app.db.get_document_text(self.current["sha256"], page_no)}
            if page_no not in pages:
                return
            self.show_raw(pages[page_no]["content"], page_no)
            label = pages[page_no]["label"] or tr("pagina {n}", n=page_no)
            self.lbl.configure(text=f"{shorten(self.current['original_name'], 60)}  –  {label}")
        tb = self.raw._textbox
        tb.tag_remove("cur", "1.0", "end")
        if 0 <= k < len(self.raw_hits):
            pos, end = self.raw_hits[k]
            tb.tag_configure("cur", underline=True, borderwidth=2, relief="solid")
            tb.tag_add("cur", pos, end)
            tb.tag_raise("cur")
            tb.see(pos)

    def color_query(self):
        """Sfondo di ogni riga non vuota della textarea con il suo colore."""
        tb = self.query._textbox
        for tag in tb.tag_names():
            if tag.startswith("line"):
                tb.tag_remove(tag, "1.0", "end")
        n_lines = int(tb.index("end-1c").split(".")[0])
        gi = 0
        for ln in range(1, n_lines + 1):
            if not tb.get(f"{ln}.0", f"{ln}.end").strip():
                continue
            tag = f"line{gi}"
            tb.tag_configure(tag, background=preview.color(gi), foreground="#000000")
            tb.tag_add(tag, f"{ln}.0", f"{ln}.end")
            gi += 1

    NOTICE_ALERT_BG = "#D32F2F"   # rosso pieno: leggibile con testo bianco nel tema chiaro e scuro

    def set_notice(self, text: str = "", alert: bool = False):
        """Avviso accanto a "Esporta risultati...". alert=True: testo bianco su sfondo rosso,
        con qualche lampeggio quando compare (es. risultati mostrati con 1 errore tollerato)."""
        if self._notice_job is not None:
            try:
                self.after_cancel(self._notice_job)
            except tk.TclError:
                pass
            self._notice_job = None
        if not alert or not text:
            self.notice.configure(text=text, fg_color="transparent", text_color=theme.WARN)
            return
        self.notice.configure(text=f"  ⚠  {text}  ", fg_color=self.NOTICE_ALERT_BG, text_color="#FFFFFF")
        self._blink_notice(6)

    def _blink_notice(self, left: int):
        """Alterna rosso pieno / testo rosso su sfondo trasparente; finisce sempre sul rosso pieno."""
        if left <= 0 or not self.winfo_exists():
            self._notice_job = None
            return
        on = left % 2 == 0
        self.notice.configure(fg_color="transparent" if on else self.NOTICE_ALERT_BG,
                              text_color=self.NOTICE_ALERT_BG if on else "#FFFFFF")
        self._notice_job = self.after(280, lambda: self._blink_notice(left - 1))

    def search(self):
        q = self.query.get("1.0", "end").strip()
        self.color_query()
        if not q or not self.app.ensure_db():
            return
        folders = self.selected_folders()
        if not folders:
            messagebox.showinfo(tr("Ricerca"), tr("Seleziona almeno una cartella nella lista a sinistra."))
            return
        try:
            self.filters = self.read_filters()
        except ValueError as exc:
            messagebox.showerror(tr("Ricerca"), str(exc))
            return
        self.set_notice("")
        self._cancel_regex()
        if self.regex.get():
            return self.search_regex(q, folders)
        preview.exact_words = self.exact.get()
        try:
            # "Cerca frase esatta": ogni riga è una frase di parole intere, una dopo l'altra.
            # Nessun risultato: si riprova da soli tollerando 1 errore di battitura o di OCR
            res = searches.run(self.app.db, self.spec(), self.app.cfg.watch_dirs, auto_fuzzy=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(tr("Ricerca"), tr("Ricerca non valida:\n{exc}", exc=exc))
            return
        self.groups = res.groups
        self._auto_fuzzy = res.fuzzy_used
        if res.fuzzy_used:
            self.set_notice(tr("Nessun risultato esatto: mostrati quelli con 1 errore di battitura o di OCR"), alert=True)
        self._rows = res.rows
        self._sort = None
        self._build_ext_bar(reset=True)
        self.raw.delete("1.0", "end")    # prima: show_results seleziona il primo risultato e riempie il testo
        self.show_results()

    def _cells(self, r: dict) -> tuple:
        page = r["label"] or str(r["page_no"])
        return (theme.level_mark(r.get("level")), r["original_name"], os.path.dirname(r["path"]), page,
                f"{r['score']:.1f}", fmt_time(r.get("ctime")))

    def _insert_row(self, r: dict, groups: list) -> str:
        snip = r["snippet"] or make_snippet(r["content"], groups, 160)
        iid = self.tree.insert("", "end", values=self._cells(r) + (snip,), groups=groups,
                               level=r.get("level") or 0, path=r.get("path") or "")
        self.results[iid] = r
        return iid

    def show_results(self, select_first: bool = True, keep: dict | None = None):
        """keep: risultato che resta selezionato dopo aver ridisegnato la tabella (senza ricaricare
        testo e anteprima, che sono già i suoi)."""
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        visible = self._visible_rows()
        for r, groups in visible:
            self._insert_row(r, groups)
        docs = len({r["sha256"] for r, _g in visible})
        text = tr("{n} risultati in {docs} documenti", n=len(visible), docs=docs)
        if len(visible) != len(self._rows):
            text += " · " + tr("filtro per estensione: {n} di {total}", n=len(visible), total=len(self._rows))
        self.lbl.configure(text=text)
        self.tree.set_header(*(self._sort or (None, False)))
        kids = self.tree.get_children()
        same = next((i for i in kids if self.results[i] is keep), None) if keep is not None else None
        if same is not None:
            self._reselect = keep
            self.tree.selection_set(same)
            self.tree.focus(same)
            self.tree.see(same)
            self.after(300, lambda: setattr(self, "_reselect", None))
        elif kids and select_first:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def sort_results(self, col: int):
        """Clic sull'intestazione: A-Z, di nuovo Z-A (la colonna Estratto non si ordina)."""
        if col >= len(ResultsList.COLUMNS) - 1 or not self._rows:
            return
        rev = not self._sort[1] if self._sort and self._sort[0] == col else False
        self._sort = (col, rev)
        full = [x for x in self._rows if str(self._cells(x[0])[col]).strip()]
        empty = [x for x in self._rows if not str(self._cells(x[0])[col]).strip()]
        full.sort(key=lambda x: _sort_value(self._cells(x[0])[col]), reverse=rev)
        self._rows = full + empty
        self.show_results(keep=self.current)

    # ------------------------------------------------- filtro per estensione
    @staticmethod
    def _ext_of(r: dict) -> str:
        return os.path.splitext(r.get("original_name") or r.get("path") or "")[1].lower()

    def _visible_rows(self) -> list[tuple[dict, list]]:
        """Risultati mostrati: quelli delle estensioni selezionate nei pulsanti sopra la tabella."""
        if not self._ext_off:
            return self._rows
        return [x for x in self._rows if self._ext_of(x[0]) not in self._ext_off]

    def _build_ext_bar(self, reset: bool = False):
        """Un pulsante per ogni estensione presente nei risultati (con il numero di risultati):
        acceso = mostrata, spento = nascosta. Con una ricerca nuova tornano tutte accese."""
        for w in self.ext_bar.winfo_children():
            w.destroy()
        self._ext_btns, self._ext_extra = {}, []
        counts: dict[str, int] = {}
        for r, _g in self._rows:
            e = self._ext_of(r)
            counts[e] = counts.get(e, 0) + 1
        self._ext_off = set() if reset else self._ext_off & set(counts)
        if not counts:
            self.ext_bar.configure(height=1)
            return
        small = {"height": 24, "font": self.app.fonts.small}
        if len(counts) > 2:
            for text, value in ((tr("Tutte"), True), (tr("Nessuna"), False)):
                b = ctk.CTkButton(self.ext_bar, text=text, width=60, fg_color=theme.NEUTRAL,
                                  hover_color=theme.NEUTRAL_HOVER, command=lambda v=value: self._ext_all(v), **small)
                self._ext_extra.append(b)
        for e, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            name = e or tr("senza estensione")
            self._ext_btns[e] = ctk.CTkButton(self.ext_bar, text=f"{name}  {n}", width=40,
                                              command=lambda x=e: self._toggle_ext(x), **small)
        self._paint_ext()
        self._ext_width = 0
        self.after_idle(self._flow_ext)

    def _flow_ext(self, width: int | None = None):
        """Dispone i pulsanti su più righe secondo la larghezza disponibile."""
        buttons = self._ext_extra + list(self._ext_btns.values())
        if not buttons:
            return
        width = width or self.ext_bar.winfo_width()
        if width <= 1 or width == self._ext_width:
            return
        self._ext_width = width
        row = col = used = 0
        for b in buttons:
            w = b.winfo_reqwidth() + 4
            if col and used + w > width:
                row, col, used = row + 1, 0, 0
            b.grid(row=row, column=col, padx=(0, 4), pady=(0, 4), sticky="w")
            col, used = col + 1, used + w

    def _paint_ext(self):
        for e, b in self._ext_btns.items():
            on = e not in self._ext_off
            b.configure(fg_color=theme.BTN if on else theme.NEUTRAL,
                        hover_color=theme.BTN_HOVER if on else theme.NEUTRAL_HOVER,
                        text_color=theme.BTN_TEXT if on else theme.TEXT_DIM)

    def _toggle_ext(self, ext: str):
        self._ext_off ^= {ext}
        self._paint_ext()
        self.show_results(keep=self.current)

    def _ext_all(self, on: bool):
        self._ext_off = set() if on else set(self._ext_btns)
        self._paint_ext()
        self.show_results(keep=self.current)

    # ------------------------------------------------------------- regex
    def search_regex(self, pattern: str, folders: list[str]):
        """Ricerca regex in un processo separato (vedi regexworker): un pattern lento su un testo lungo non
        congela la finestra, i risultati si contano man mano e la ricerca si può fermare."""
        pattern = " ".join(x.strip() for x in pattern.splitlines() if x.strip())
        err = regex_error(pattern)
        if err:
            messagebox.showerror(tr("Ricerca"), tr("Regex non valida: {err}", err=err))
            return
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self._rows = []
        self._build_ext_bar(reset=True)
        job = {"db": str(self.app.cfg.db_file), "spec": self.spec(), "folders": list(self.app.cfg.watch_dirs),
               "limit": 500, "parent": os.getpid()}
        try:
            proc = regexworker.start(job)
        except OSError as exc:
            messagebox.showerror(tr("Ricerca"), tr("Ricerca non valida:\n{exc}", exc=exc))
            return
        rows: list[dict] = []
        self._rx_proc, self._rx_rows, self._rx_t0 = proc, rows, time.monotonic()
        self._rx_groups = [[preview.RawRegex(pattern)]]
        self._sort = None
        self.current = None
        self.raw.delete("1.0", "end")
        self.btn_stop.pack(side="left", padx=(8, 0), before=self.notice)

        def reader():
            status = None
            for kind, data in regexworker.read(proc):
                if kind == "row":
                    rows.append(data)
                else:
                    status = (kind, data)
                    break
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()
            self.app.events.put((self._regex_done, (proc, rows, status)))

        threading.Thread(target=reader, daemon=True, name="regex-search").start()
        self._regex_tick(proc)

    def _regex_tick(self, proc):
        """Mentre la ricerca lavora: secondi trascorsi e risultati trovati finora."""
        if self._rx_proc is not proc or not self.winfo_exists():
            return
        self._regex_take_rows()
        self.lbl.configure(text=tr("Ricerca regex in corso...") + " " + tr(
            "{s} s · {n} risultati finora", s=int(time.monotonic() - self._rx_t0), n=len(self._rx_rows)))
        self.after(500, self._regex_tick, proc)

    def _regex_take_rows(self):
        """Mette in tabella i risultati arrivati dal processo dall'ultima volta (man mano che li trova)."""
        new = self._rx_rows[len(self._rows):]
        if not new:
            return
        first = not self._rows
        for r in new:
            self._rows.append((r, self._rx_groups))
            if self._ext_of(r) not in self._ext_off:
                self._insert_row(r, self._rx_groups)
        self._build_ext_bar()
        kids = self.tree.get_children()
        if first and kids:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def stop_regex(self):
        """Pulsante "Ferma ricerca": chiude il processo; restano i risultati trovati fin lì."""
        proc = self._rx_proc
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass

    def _cancel_regex(self):
        """Una ricerca nuova sostituisce quella regex in corso (i suoi risultati si scartano)."""
        proc, self._rx_proc = self._rx_proc, None
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass
            self.btn_stop.pack_forget()

    def _regex_done(self, proc, rows, status):
        if proc is not self._rx_proc:
            return                      # sostituita da un'altra ricerca
        self._rx_proc = None
        self.btn_stop.pack_forget()
        if status and status[0] == "error":
            self.lbl.configure(text="")
            messagebox.showerror(tr("Ricerca"), tr("Ricerca non valida:\n{exc}", exc=status[1]))
            return
        if status is None:              # processo chiuso prima della fine (Ferma ricerca)
            self.set_notice(tr("Ricerca regex fermata: mostrati i risultati trovati fin qui"))
        self._regex_take_rows()
        if self._sort is None:          # dal più ricco di occorrenze (se non hai già scelto un ordine)
            self._rows.sort(key=lambda x: -x[0]["score"])
        self._build_ext_bar()
        self.show_results(keep=self.current)
        if not self._rows:
            self.lbl.configure(text=tr("{n} risultati in {docs} documenti", n=0, docs=0))

    def on_select(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.results[sel[0]]
        if getattr(self, "_reselect", None) is r:
            self._reselect = None          # tabella ridisegnata: stesso risultato, niente da ricaricare
            return
        if r.get("matches") is not None:
            self.groups = self._rx_groups  # regex: si evidenzia tutto ciò che corrisponde all'espressione
        self.current = r
        if r.get("source") == "meta":
            self.show_raw(self.meta_raw(r), None)
        else:
            self.show_raw(r["content"], r["page_no"], first=r.get("first"))
        page = r["label"] or tr("pagina {n}", n=r["page_no"])
        text = f"{shorten(r['path'], 90)}  –  {page}  ({r['method']})"
        if r.get("matches") is not None:
            # regex: un risultato per pagina o foglio intero (un foglio Excel = una riga, anche se lungo
            # centinaia di pagine di anteprima); qui si dice quante occorrenze contiene
            text = (f"{shorten(r['path'], 60)}  –  {page}  ·  "
                    + tr("{n} occorrenze in questo foglio/pagina: scorrile con Occorrenza ◀ ▶",
                         n=f"{int(r['score']):,}".replace(",", ".")))
        self.lbl.configure(text=text)
        self.preview.show(r, self.groups)


# ======================================================================
class DocumentsPage(ctk.CTkFrame):
    """Elenco dei file indicizzati (restano al loro posto): filtro per nome, stato e cartella, anteprima.
    Con important=True è la scheda "Importanti": solo i file a cui è stato dato un colore, con la nota."""

    COLUMNS = [("level", "Imp.", 84), ("name", "Nome", 260), ("folder", "Cartella", 240), ("type", "Tipo", 60),
               ("status", "Stato", 110), ("lang", "Lingua", 90), ("pages", "Pagine", 60), ("ocr", "OCR", 45),
               ("chars", "Caratteri", 80),
               ("created", "Creato", 128), ("modified", "Modificato", 128), ("hash", "SHA-256", 200)]
    IMPORTANT_COLUMNS = [("level", "Imp.", 84), ("name", "Nome", 260), ("note", "Nota", 300),
                         ("folder", "Cartella", 240), ("created", "Creato", 128), ("modified", "Modificato", 128),
                         ("type", "Tipo", 60), ("lang", "Lingua", 90)]

    def __init__(self, master, app: "App", important: bool = False):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.important = important
        self.rows: dict[str, dict] = {}
        self.all_rows: list[dict] = []
        self.ALL = tr("Tutti")
        self.status_names = {self.ALL: None, tr("Indicizzati"): "done", tr("In coda"): "pending",
                             tr("Saltati"): "skipped", tr("Errori"): "error"}
        self.filter = tk.StringVar(value=self.ALL)
        self.text_filter = tk.StringVar()
        self._filter_job = None

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(0, 4 if important else 12))
        ctk.CTkLabel(head, text=tr("Importanti") if important else tr("Documenti"), font=app.h1).pack(side="left")
        self.big_panel = None
        if not important:
            # file oltre il limite di dimensione: si analizzano solo dopo l'approvazione, in una vista a parte
            self.btn_big = ctk.CTkButton(head, text=tr("File grandi"), width=150, fg_color=theme.NEUTRAL,
                                         hover_color=theme.NEUTRAL_HOVER, command=self.toggle_big)
            self.btn_big.pack(side="left", padx=(18, 0))
        if important:
            ctk.CTkLabel(self, text=tr("I documenti a cui hai dato un colore di importanza. Il colore e la nota si "
                                       "scelgono nell'anteprima, sotto il nome del file."),
                         text_color=theme.TEXT_DIM, anchor="w").pack(fill="x", pady=(0, 10))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(bar, text=tr("Cerca nel nome:")).pack(side="left", padx=(0, 6))
        entry = ctk.CTkEntry(bar, textvariable=self.text_filter, width=220)
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda e: self._schedule_filter())
        if not important:
            ctk.CTkSegmentedButton(bar, values=list(self.status_names), variable=self.filter,
                                   command=lambda _v: self.refresh()).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(bar, text=tr("Cartella:")).pack(side="left", padx=(12, 6))
        self.cf_filter = tk.StringVar(value=self.ALL)
        self.cf_menu = ctk.CTkOptionMenu(bar, variable=self.cf_filter, values=[self.ALL], width=200,
                                         dynamic_resizing=False, command=lambda _v: self.refresh())
        self.cf_menu.pack(side="left")
        ctk.CTkButton(bar, text=tr("Aggiorna"), command=self.refresh).pack(side="left", padx=8)
        # actions on the selected documents: on the title row, which has room for them; in a single row
        # with the filters they were pushed out of the window on narrow or zoomed screens
        actions = ctk.CTkFrame(head, fg_color="transparent")
        actions.pack(side="right")
        ctk.CTkButton(actions, text=tr("Esporta..."), width=110, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.export).pack(side="right", padx=(8, 0))
        ctk.CTkButton(actions, text=tr("Rianalizza"), fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.reanalyse).pack(side="right")
        ctk.CTkButton(actions, text=tr("Mostra in Esplora risorse"), fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.reveal).pack(side="right", padx=8)
        self.actions = actions

        self.bar = bar
        px = lambda n: theme.px(self, n)       # plain tk PanedWindow sizes are physical pixels
        hpane = tk.PanedWindow(self, orient="horizontal", sashwidth=px(6), bd=0, bg=theme.BG)
        hpane.pack(fill="both", expand=True)
        self.hpane = hpane
        if not important:
            self.big_panel = BigFilesPanel(self, app, self._big_changed)
        left = ctk.CTkFrame(hpane, fg_color="transparent")
        self.tree = make_tree(left, self.IMPORTANT_COLUMNS if important else self.COLUMNS)
        self.tree.configure(selectmode="extended")  # Ctrl / Maiusc + clic per selezionare più documenti
        if important:
            self.tree._sort = ("level", True)       # i più importanti in alto
        attach_tree_tooltip(self.tree, self._tooltip)
        self.tree.container.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.preview.open_original())
        self.tree.bind("<Control-a>", lambda e: (self.tree.selection_set(self.tree.get_children()), "break")[1])
        self.count = ctk.CTkLabel(left, text="", anchor="w")
        self.count.pack(fill="x", pady=(6, 0))
        self.preview = PreviewPanel(hpane, app)
        hpane.add(left, minsize=px(360), width=px(720))
        hpane.add(self.preview, minsize=px(420))

    # ------------------------------------------------------- file grandi
    def toggle_big(self):
        """Passa dall'elenco dei documenti alla sezione "File grandi" e ritorno."""
        showing = bool(self.big_panel.winfo_ismapped())
        if showing:
            self.big_panel.pack_forget()
            self.actions.pack(side="right")
            self.bar.pack(fill="x", pady=(0, 10))
            self.hpane.pack(fill="both", expand=True)
            self.refresh()
        else:
            self.bar.pack_forget()
            self.actions.pack_forget()
            self.hpane.pack_forget()
            self.big_panel.pack(fill="both", expand=True)
            self.big_panel.refresh()
        self._big_changed()

    def _big_changed(self):
        if self.big_panel is None or not self.app.ensure_db(quiet=True):
            return
        if self.big_panel.winfo_ismapped():
            self.btn_big.configure(text="\u2190 " + tr("Documenti"), fg_color=theme.BTN, hover_color=theme.BTN_HOVER)
            return
        n = sum(1 for r in self.app.db.big_files(self.app.cfg.max_file_mb * 1024 * 1024) if r["big"] != 2)
        self.btn_big.configure(text=tr("File grandi") + (f"  ({n})" if n else ""),
                               fg_color=theme.WARN_BTN if n else theme.NEUTRAL,
                               hover_color=theme.WARN_BTN_HOVER if n else theme.NEUTRAL_HOVER)

    # ------------------------------------------------------------ elenco
    def refresh(self):
        if not self.app.ensure_db(quiet=True):
            return
        self._big_changed()
        if self.big_panel is not None and self.big_panel.winfo_ismapped():
            self.big_panel.refresh()
            return
        status = None if self.important else self.status_names.get(self.filter.get())
        dirs = list(self.app.cfg.watch_dirs)
        self.cf_menu.configure(values=[self.ALL] + dirs)
        if self.cf_filter.get() not in dirs:
            self.cf_filter.set(self.ALL)
        folder = self.cf_filter.get() if self.cf_filter.get() in dirs else None
        self.all_rows = self.app.db.list_documents(status, folder, limit=200000, important=self.important)
        self.apply_filter()

    def _schedule_filter(self):
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(200, self.apply_filter)

    def _values(self, r: dict) -> tuple:
        cells = {"level": theme.level_mark(r["level"]), "name": r["original_name"],
                 "note": (r["note"] or "").replace("\n", " "), "folder": os.path.dirname(r["path"]),
                 "type": r["doc_type"], "status": tr(r["status"]), "pages": r["page_count"] or "",
                 "ocr": r["ocr_pages"] or "", "chars": r["char_count"] or "", "created": fmt_time(r["ctime"]),
                 "modified": fmt_time(r["mtime"]), "hash": r["sha256"], "lang": lang_mod.name(r.get("lang"))}
        return tuple(cells[k] for k, _t, _w in (self.IMPORTANT_COLUMNS if self.important else self.COLUMNS)
                     if k != "level")    # l'importanza è la colonna #0, con i pallini colorati

    def _tooltip(self, iid, col):
        r = self.rows.get(iid)
        if not r:
            return None
        if col == "name":
            return r["path"]
        if col == "folder":
            return os.path.dirname(r["path"])
        if col == "#0" and r.get("level"):
            return tr(theme.LEVEL_NAMES[r["level"]])
        return None

    def apply_filter(self):
        """Mostra i documenti il cui nome contiene tutte le parole scritte (senza accenti/maiuscole)."""
        words = [fold(w) for w in self.text_filter.get().split()]
        selected = {self.rows[i]["id"] for i in self.tree.selection() if i in self.rows}
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        for r in self.all_rows:
            if words and not all(w in fold(r["original_name"]) for w in words):
                continue
            tags = (f"lvl{r['level']}",) if r["level"] else ()
            iid = self.tree.insert("", "end", values=self._values(r), tags=tags)
            set_level(self.tree, iid, r["level"])
            self.rows[iid] = r
            if r["id"] in selected:
                self.tree.selection_add(iid)
        sort_tree(self.tree)
        shown = (tr("{n} documenti su {total}", n=len(self.rows), total=len(self.all_rows)) if words
                 else tr("{n} documenti", n=len(self.rows)))
        self.count.configure(text=shown)

    def export(self):
        """Esporta l'elenco come è mostrato (filtro e ordine compresi), con importanza e note."""
        rows = [self.rows[i] for i in self.tree.get_children() if i in self.rows]
        if not rows:
            messagebox.showinfo(tr("Esporta"), tr("L'elenco è vuoto."))
            return
        export.ask_and_export(self, rows, kind="documents", title=tr("Importanti") if self.important else tr("Documenti"))

    def update_row(self, path_id: int, level: int, note: str):
        for iid, r in self.rows.items():
            if r["id"] == path_id:
                r["level"], r["note"] = level, note or None
                self.tree.item(iid, values=self._values(r), tags=(f"lvl{level}",) if level else ())
                set_level(self.tree, iid, level)
        for r in self.all_rows:
            if r["id"] == path_id:
                r["level"], r["note"] = level, note or None

    # ---------------------------------------------------------- anteprima
    def on_select(self, _e=None):
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        r = dict(self.rows[sel[0]])
        r.setdefault("page_no", 1)
        r.setdefault("label", None)
        self.preview.show(r, [])

    def reveal(self):
        sel = self.tree.selection()
        if sel:
            reveal(self.rows[sel[0]]["path"])

    def reanalyse(self):
        """Estrae di nuovo il testo dei documenti selezionati (es. dopo aver cambiato modello OCR)."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(tr("Documenti"), tr("Seleziona uno o più documenti."))
            return
        shas = {self.rows[i]["sha256"] for i in sel}
        with self.app.db.transaction() as c:
            c.executemany("UPDATE files SET status='pending', error=NULL WHERE sha256=?", [(x,) for x in shas])
        self.app.indexer.wake.set()
        self.refresh()


# ======================================================================
class BigFilesPanel(ctk.CTkFrame):
    """Sezione "File grandi" di Documenti: i file oltre il limite di dimensione non si analizzano da soli.
    Sopra quelli in attesa (Analizza = in coda come un file normale, Blocca = messo da parte), sotto quelli
    bloccati (Sblocca = torna sopra)."""

    def __init__(self, master, app: "App", changed):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.changed = changed
        self._shown = None
        self.note = ctk.CTkLabel(self, text="", text_color=theme.TEXT_DIM, anchor="w", justify="left")
        self.note.pack(fill="x", pady=(0, 10))
        self.blocks = {}
        for key, title in (("wait", "In attesa di approvazione"), ("lock", "Bloccati")):
            self.lbl = ctk.CTkLabel(self, text=tr(title), font=app.fonts.bold, anchor="w")
            self.lbl.pack(fill="x", pady=(4, 4))
            box = ctk.CTkScrollableFrame(self, fg_color=theme.PANEL, border_width=1, border_color=theme.BORDER,
                                         corner_radius=8)
            box.pack(fill="both", expand=True, pady=(0, 10))
            box.grid_columnconfigure(0, weight=1)
            self.blocks[key] = (box, self.lbl, title)

    def refresh(self):
        if not self.app.ensure_db(quiet=True):
            return
        mb = self.app.cfg.max_file_mb
        rows = self.app.db.big_files(mb * 1024 * 1024)
        shown = (mb, [(r["sha256"], r["big"], r["path"]) for r in rows])
        if shown == self._shown:
            return
        self._shown = shown
        self.note.configure(text=tr(
            "I file più grandi di {mb} MB non vengono analizzati da soli: decidi tu. \"Analizza\" li mette in coda "
            "come file normali (i testi enormi, es. CSV da GB, vengono letti a pezzi senza bloccare il programma; "
            "l'indice può crescere molto). \"Blocca\" li mette da parte.", mb=mb))
        groups = {"wait": [r for r in rows if r["big"] != 2], "lock": [r for r in rows if r["big"] == 2]}
        empty = {"wait": "Nessun file in attesa.", "lock": "Nessun file bloccato."}
        for key, (box, lbl, title) in self.blocks.items():
            for w in box.winfo_children():
                w.destroy()
            items = groups[key]
            lbl.configure(text=tr(title) + f"  ({len(items)})")
            if not items:
                ctk.CTkLabel(box, text=tr(empty[key]), text_color=theme.TEXT_DIM, anchor="w").grid(
                    row=0, column=0, sticky="w", padx=12, pady=10)
            for i, r in enumerate(items):
                self._row(box, i, r, key)

    def _row(self, box, i: int, r: dict, key: str):
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.grid(row=i, column=0, sticky="ew", padx=6, pady=3)
        row.grid_columnconfigure(0, weight=1)
        size = r["size_bytes"]
        size_txt = f"{size / 1024 ** 3:.2f} GB" if size >= 1024 ** 3 else f"{size / 1024 ** 2:.0f} MB"
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(text, text=shorten(r["name"], 70) + "   ·   " + size_txt, font=self.app.fonts.bold,
                     anchor="w", height=18).pack(fill="x")
        ctk.CTkLabel(text, text=shorten(os.path.dirname(r["path"]), 110), text_color=theme.TEXT_DIM,
                     font=self.app.fonts.small, anchor="w", height=16).pack(fill="x")
        sha = r["sha256"]
        if key == "wait":
            ctk.CTkButton(row, text=tr("Analizza"), width=100, command=lambda: self._set(sha, 3)).grid(
                row=0, column=1, padx=(8, 0))
            ctk.CTkButton(row, text=tr("Blocca"), width=90, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                          command=lambda: self._set(sha, 2)).grid(row=0, column=2, padx=(8, 4))
        else:
            ctk.CTkButton(row, text=tr("Sblocca"), width=100, fg_color=theme.NEUTRAL,
                          hover_color=theme.NEUTRAL_HOVER, command=lambda: self._set(sha, 0)).grid(
                row=0, column=1, padx=(8, 4))

    def _set(self, sha: str, state: int):
        self.app.db.set_big(sha, state)
        if state == 3 and self.app.indexer:
            self.app.indexer.wake.set()         # approvato: in coda subito, come un file normale
        self.refresh()
        self.changed()


# ======================================================================
class ToolsPanel(ctk.CTkFrame):
    """Stato e installazione degli strumenti di terze parti."""

    def __init__(self, master, app: "App", settings: "SettingsPage"):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.settings = settings
        self.worker = Worker(app)
        ctk.CTkLabel(self, text=tr("Strumenti di terze parti necessari al programma. Vengono scaricati nella cartella "
                                "tools accanto al programma e funzionano in modo portatile, senza installazione."),
                     wraplength=820, justify="left", text_color=theme.TEXT_DIM).pack(anchor="w", pady=(4, 10))
        self.rows_frame = ctk.CTkScrollableFrame(self, corner_radius=10, height=330)
        self.rows_frame.pack(fill="x")
        self.rows_frame.grid_columnconfigure(1, weight=1)
        self.buttons: list[ctk.CTkButton] = []

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.btn_all = ctk.CTkButton(bar, text=tr("Installa tutto ciò che manca"), width=220, command=self.install_all)
        self.btn_all.pack(side="left")
        ctk.CTkButton(bar, text=tr("Ricontrolla"), width=110, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.refresh).pack(side="left", padx=8)
        self.dl_label = ctk.CTkLabel(self, text="", anchor="w")
        self.dl_label.pack(fill="x")
        self.dl_bar = ctk.CTkProgressBar(self)
        self.dl_bar.set(0)
        self.dl_bar.pack(fill="x", pady=(2, 10))
        self.log = LogBox(self, height=220)
        self.log.pack(fill="both", expand=True)
        self.after(200, self.refresh)

    def on_download(self, label: str, done: int, total: int):
        mb = 1_048_576
        if total:
            if self.dl_bar.cget("mode") != "determinate":
                self.dl_bar.stop()
                self.dl_bar.configure(mode="determinate")
            self.dl_bar.set(min(1.0, done / total))
            self.dl_label.configure(text=f"{label}   {done / mb:.1f} / {total / mb:.1f} MB  ({done * 100 // total}%)")
        else:
            # durata sconosciuta (estrazione o server senza dimensione)
            if self.dl_bar.cget("mode") != "indeterminate":
                self.dl_bar.configure(mode="indeterminate")
                self.dl_bar.start()
            self.dl_label.configure(text=f"{label}   {done / mb:.1f} MB" if done else f"{label}...")

    def _progress(self, label, done, total):
        self.app.events.put((self.on_download, (label, done, total)))

    def refresh(self):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.buttons.clear()
        statuses = tools.check_all(self.app.cfg)
        for i, s in enumerate(statuses):
            color = theme.OK if s.ok else (theme.WARN if s.optional else theme.ERR)
            ctk.CTkLabel(self.rows_frame, text="●", text_color=color, font=ctk.CTkFont(size=18)).grid(
                row=i, column=0, padx=(14, 8), pady=8)
            box = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
            box.grid(row=i, column=1, sticky="w")
            ctk.CTkLabel(box, text=s.name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(box, text=s.detail, text_color=theme.TEXT_DIM, font=ctk.CTkFont(size=12),
                         wraplength=560, justify="left").pack(anchor="w")
            if s.installable:
                b = ctk.CTkButton(self.rows_frame, text=tr("Reinstalla") if s.ok else tr("Installa"), width=110,
                                  fg_color=theme.NEUTRAL if s.ok else None, command=lambda k=s.key: self.install(k))
                b.grid(row=i, column=2, padx=14)
                self.buttons.append(b)
        return statuses

    def _busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_all.configure(state=state)
        for b in self.buttons:
            b.configure(state=state)

    def _start(self, job):
        if self.worker.busy:
            return
        self._busy(True)
        self.dl_bar.set(0)
        self.dl_label.configure(text="")
        self.worker.start(job, self.log.write, lambda i, n: None, self.on_done)

    def install(self, key: str):
        cfg = self.settings.apply()
        self._start(lambda log, progress, stop: tools.INSTALLERS[key](cfg, log, self._progress))

    def install_all(self):
        cfg = self.settings.apply()
        self._start(lambda log, progress, stop: tools.install_missing(cfg, log, self._progress))

    def on_done(self, _res, exc):
        self._busy(False)
        self.dl_bar.stop()
        self.dl_bar.configure(mode="determinate")
        self.dl_label.configure(text="")
        if exc:
            self.log.write(tr("ERRORE: {exc}", exc=exc))
        self.settings.reload_vars()
        self.app.save_config()
        self.refresh()
        self.log.write(tr("Fatto."))


# ======================================================================
class HotkeyError(ValueError):
    """Scorciatoia della ricerca rapida non valida (messaggio già tradotto)."""


class SettingsPage(ctk.CTkFrame):
    MODULES = (("mod_archives", "Archivi compressi: testo dei file contenuti (7-Zip)"),
            ("mod_sqlite", "Database SQLite"),
            ("mod_dbf", "Database dBASE / FoxPro (.dbf, dbfread)"),
            ("mod_access", "Database Access (.mdb/.accdb, driver Microsoft)"))
    NUMBERS = (("cpu_limit", "CPU massima mentre usi il PC (%)"),
               ("cpu_limit_idle", "CPU massima con il PC inattivo (%)"),
               ("idle_minutes", "PC inattivo dopo (minuti)"),
               ("busy_threshold", "Aspetta se gli altri programmi usano più di (% CPU)"),
               ("ocr_threads", "Thread OCR"),
               ("rescan_hours", "Controllo completo delle cartelle ogni (ore)"),
               ("max_file_mb", "Salta i file più grandi di (MB)"),
               ("ui_zoom", "Dimensione interfaccia (%) — 100 = come lo zoom di Windows"),
               ("ocr_dpi", "Risoluzione OCR (DPI)"))

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color="transparent")
        self.app = app
        cfg = app.cfg
        f = app.fonts
        self.vars = {"db_path": tk.StringVar(value=cfg.db_path), "ocr_model": tk.StringVar(value=cfg.ocr_model),
                     "quick_hotkey": tk.StringVar(value=cfg.quick_hotkey)}
        for key, _label in self.NUMBERS:
            self.vars[key] = tk.StringVar(value=str(getattr(cfg, key)))
        self.autostart = tk.BooleanVar(value=daemon_ui.autostart_enabled())   # stato reale di Windows
        self.exif = tk.BooleanVar(value=cfg.exif_enabled)
        self.mods = {k: tk.BooleanVar(value=getattr(cfg, k)) for k, _l in self.MODULES}
        ctk.CTkLabel(self, text=tr("Impostazioni"), font=app.h1).pack(anchor="w", pady=(0, 12))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        self.btn_save = ctk.CTkButton(actions, text=tr("Salva"), width=140, command=self.save)
        self.btn_save.pack(side="left")
        self.btn_undo = ctk.CTkButton(actions, text=tr("Annulla modifiche"), fg_color=theme.NEUTRAL,
                                      hover_color=theme.NEUTRAL_HOVER, command=self.discard)
        self.btn_undo.pack(side="left", padx=8)
        ctk.CTkButton(actions, text=tr("Ripristina impostazioni predefinite"), fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.defaults).pack(side="left")
        self.dirty_lbl = ctk.CTkLabel(actions, text="", text_color=theme.WARN, font=app.fonts.bold)
        self.dirty_lbl.pack(side="left", padx=14)
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True)
        folders_tab = tabs.add(tr("Cartelle ed estensioni"))
        cfg_tab = tabs.add(tr("Configurazione"))
        tools_tab = tabs.add(tr("Strumenti esterni"))
        backup_tab = tabs.add(tr("Backup"))
        self._build_backup(backup_tab)
        self.tools_panel = ToolsPanel(tools_tab, app, self)
        self.tools_panel.pack(fill="both", expand=True)
        self.tabs = tabs

        # ---- cartelle ed estensioni
        frow = ctk.CTkFrame(folders_tab, fg_color="transparent")
        frow.pack(fill="x", pady=(4, 8))
        self.folders = daemon_ui.FolderList(frow, cfg.watch_dirs, f)
        self.folders.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.excluded = daemon_ui.FolderList(frow, cfg.exclude_paths, f, title=tr("Sottocartelle escluse"))
        self.excluded.pack(side="left", fill="both", expand=True)
        tables = ctk.CTkFrame(folders_tab, fg_color="transparent")
        tables.pack(fill="both", expand=True)
        from .config import DEFAULT_EXCLUDE, DEFAULT_EXCLUDE_DIRS, DEFAULT_INCLUDE

        # skipped-folders list packed first (right): the extension tables must not squeeze it away
        self.dirs = daemon_ui.ListEditor(tables, tr("Cartelle saltate (per nome)"), cfg.exclude_dirs, f,
                                         DEFAULT_EXCLUDE_DIRS, kind="dir")
        self.dirs.pack(side="right", fill="y")
        self.inc, self.exc = daemon_ui.ext_tables(tables, cfg, f)

        # ---- configurazione
        form = ctk.CTkScrollableFrame(cfg_tab, fg_color="transparent")
        form.pack(fill="both", expand=True)
        form.grid_columnconfigure(1, weight=1)
        r = 0

        def section(title):
            nonlocal r
            theme.caption(form, tr(title), f).grid(row=r, column=0, columnspan=3, sticky="w", pady=(14, 6))
            r += 1

        def field(label, key, browse=None, width=None):
            nonlocal r
            ctk.CTkLabel(form, text=tr(label)).grid(row=r, column=0, sticky="w", padx=(0, 12), pady=4)
            e = ctk.CTkEntry(form, textvariable=self.vars[key], width=width or 140)
            e.grid(row=r, column=1, sticky="ew" if browse else "w", pady=4)
            if browse:
                ctk.CTkButton(form, text="...", width=40, command=browse).grid(row=r, column=2, padx=(6, 0))
            r += 1

        section("Avvio")
        # effetto immediato, come l'interruttore del Monitor e la voce del menu dell'icona
        ctk.CTkCheckBox(form, text=tr("Avvia DocIndexer con Windows (in background, icona vicino all'orologio)"),
                        variable=self.autostart, command=lambda: app.set_autostart(self.autostart.get())).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=4)
        r += 1
        # voce del tasto destro di Esplora file: effetto immediato, lo stato è quello del registro di Windows
        self.shellmenu = tk.BooleanVar(value=shellmenu.enabled())
        ctk.CTkCheckBox(form, text=tr("Aggiungi la voce «Aggiungi a DocIndexer» al menu del tasto destro delle "
                                      "cartelle in Esplora file"),
                        variable=self.shellmenu, command=lambda: app.set_context_menu(self.shellmenu.get())).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=4)
        r += 1
        ctk.CTkLabel(form, text=tr("Su Windows 11 la voce è in «Mostra altre opzioni» (o Maiusc+F10). Non servono "
                                   "permessi di amministratore."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        section("Ricerca rapida")
        ctk.CTkLabel(form, text=tr("Apre una barra di ricerca sopra qualsiasi programma. Esempi: ctrl+alt+d, ctrl+alt+space, "
                                   "ctrl+shift+f, win+alt+d, ctrl+alt+f9. Vuoto = disattivata. Si apre anche dal "
                                   "menu dell'icona vicino all'orologio."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        field("Scorciatoia da tastiera", "quick_hotkey", width=220)
        err = getattr(app, "hotkey_error", None)
        if err:
            ctk.CTkLabel(form, text=err, text_color=theme.WARN, anchor="w").grid(row=r, column=0, columnspan=3,
                                                                                 sticky="w")
            r += 1
        section("Lavoro in background")
        ctk.CTkLabel(form, text=tr("DocIndexer usa una parte del processore che sale quando il PC è inattivo e si "
                                   "ferma se gli altri programmi sono già impegnati: così non rallenta il lavoro "
                                   "e non scalda il processore."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        for key, label in self.NUMBERS[:-1]:
            field(label, key)
        section("Moduli aggiuntivi")
        ctk.CTkLabel(form, text=tr("Ogni modulo salva i suoi dati in una tabella dedicata; in Ricerca scegli in quali "
                                   "dati cercare. ExifTool e 7-Zip si scaricano da Strumenti esterni."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        ctk.CTkCheckBox(form, text=tr("Leggi i metadati con ExifTool (autore, date, fotocamera, GPS, software...), "
                                      "se è installato in Strumenti esterni"),
                        variable=self.exif).grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        r += 1
        for key, label in self.MODULES:
            ctk.CTkCheckBox(form, text=tr(label), variable=self.mods[key]).grid(row=r, column=0, columnspan=3,
                                                                                 sticky="w", pady=4)
            r += 1
        section("OCR (RapidOCR)")
        OcrModelPicker(form, app, self.vars["ocr_model"]).grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        r += 1
        ctk.CTkLabel(form, text=tr("Il modello latino riconosce insieme italiano, inglese, turco e le altre lingue "
                                "europee in alfabeto latino. Per cirillico, greco, arabo... scegli il modello e "
                                "scaricalo da Strumenti esterni."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        field(*self.NUMBERS[-1][::-1])
        section("Database SQLite")
        field("File database", "db_path", browse=self.pick_db)

        btns = ctk.CTkFrame(cfg_tab, fg_color="transparent")
        btns.pack(fill="x", pady=10)
        ctk.CTkButton(btns, text=tr("Verifica OCR"), width=160, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.test_ocr).pack(side="left", padx=8)

        self._saved = self.snapshot()
        self._blink_on = False
        self.after(600, self._watch)

    # ------------------------------------------------- modifiche non salvate
    def snapshot(self) -> tuple:
        """Stato del modulo: serve a capire se ci sono modifiche non salvate."""
        return (tuple(self.folders.get()), tuple(self.excluded.get()), tuple(self.inc.get()), tuple(self.exc.get()),
                tuple(self.dirs.get()), tuple((k, v.get().strip()) for k, v in sorted(self.vars.items())),
                bool(self.autostart.get()), bool(self.exif.get()),
                tuple((k, bool(v.get())) for k, v in self.mods.items()))

    def dirty(self) -> bool:
        try:
            return self.snapshot() != self._saved
        except (tk.TclError, AttributeError):
            return False

    def _watch(self):
        """Ogni 0,6 s: se ci sono modifiche il pulsante Salva lampeggia e compare l'avviso."""
        if not self.winfo_exists():
            return
        if self.dirty():
            self._blink_on = not self._blink_on
            self.btn_save.configure(fg_color=theme.WARN_BTN if self._blink_on else theme.BTN,
                                    hover_color=theme.WARN_BTN_HOVER)
            self.dirty_lbl.configure(text="● " + tr("Modifiche non salvate"))
            self.btn_undo.configure(state="normal")
        else:
            self.btn_save.configure(fg_color=theme.BTN, hover_color=theme.BTN_HOVER)
            self.dirty_lbl.configure(text="")
            self.btn_undo.configure(state="disabled")
        self.after(600, self._watch)

    def discard(self):
        """Annulla modifiche: il modulo torna alle impostazioni salvate."""
        self.app.call_in_gui(self.app._rebuild_settings)

    def defaults(self):
        """Riporta il modulo ai valori predefiniti (le cartelle monitorate e il database restano).
        Le modifiche vanno poi salvate con Salva."""
        if not messagebox.askyesno(tr("Impostazioni"), tr("Riportare estensioni, cartelle saltate, lavoro in "
                                                         "background, OCR e dimensione ai valori predefiniti? Le "
                                                         "cartelle monitorate e il database restano. Poi premi Salva.")):
            return
        d = AppConfig()
        self.inc.set(d.include_ext)
        self.exc.set(d.exclude_ext)
        self.dirs.set(d.exclude_dirs)
        for key, _label in self.NUMBERS:
            self.vars[key].set(str(getattr(d, key)))
        self.vars["ocr_model"].set(d.ocr_model)
        self.vars["quick_hotkey"].set(d.quick_hotkey)
        self.autostart.set(d.autostart)
        self.exif.set(d.exif_enabled)
        for k, v in self.mods.items():
            v.set(getattr(d, k))

    def reload_vars(self):
        self.vars["ocr_model"].set(self.app.cfg.ocr_model)
        self._saved = self.snapshot()

    def pick_db(self):
        f = filedialog.asksaveasfilename(title=tr("File database"), defaultextension=".db", confirmoverwrite=False,
                                         filetypes=[("SQLite", "*.db *.sqlite"), (tr("Tutti"), "*.*")])
        if f:
            self.vars["db_path"].set(f)

    def apply(self) -> AppConfig:
        cfg = self.app.cfg
        nums = {k: int(self.vars[k].get().strip() or getattr(cfg, k)) for k, _l in self.NUMBERS}
        dirs = [d for d in self.folders.get() if os.path.isdir(d)]
        dirs = [d for d in dirs if d not in daemon_ui.overlapping(dirs)]
        cfg.watch_dirs = dirs
        cfg.include_ext = self.inc.get()
        cfg.exclude_ext = self.exc.get()
        cfg.exclude_dirs = self.dirs.get()
        cfg.exclude_paths = self.excluded.get()
        for k, v in nums.items():
            setattr(cfg, k, max(1, v))
        cfg.cpu_limit, cfg.cpu_limit_idle = min(cfg.cpu_limit, 100), min(cfg.cpu_limit_idle, 100)
        hk = self.vars["quick_hotkey"].get().strip().lower()
        if hk:
            try:
                hotkey.parse(hk)
            except ValueError:
                raise HotkeyError(tr("Scorciatoia non valida: {text}. Esempio: ctrl+alt+d", text=hk)) from None
        cfg.quick_hotkey = hk
        v = self.vars["db_path"].get().strip()
        cfg.db_path = portable(v) if v else "data/docindexer.db"
        self.app.default_ocr = self.vars["ocr_model"].get() or ocr.DEFAULT_MODEL
        return cfg

    def save(self):
        old_db = self.app.cfg.db_path
        old_scale = self.app.cfg.ui_zoom
        old_hotkey = self.app.cfg.quick_hotkey
        try:
            default_model = self.vars["ocr_model"].get().strip() or ocr.DEFAULT_MODEL
            self.apply()
            self.app.default_ocr = default_model
            self.app.cfg.autostart = bool(self.autostart.get())
            self.app.cfg.exif_enabled = bool(self.exif.get())
            for k, v in self.mods.items():
                setattr(self.app.cfg, k, bool(v.get()))
            daemon_ui.set_autostart(self.app.cfg.autostart)
            self.app.save_config()
            self.app.ocr_var.set(default_model)
        except HotkeyError as exc:
            messagebox.showerror(tr("Impostazioni"), str(exc))
            return False
        except ValueError:
            messagebox.showerror(tr("Impostazioni"), tr("I valori numerici devono essere numeri interi."))
            return False
        self._saved = self.snapshot()
        if self.app.cfg.quick_hotkey != old_hotkey:
            self.app.start_hotkey()
            if self.app.hotkey_error:
                messagebox.showwarning(tr("Ricerca rapida"), self.app.hotkey_error)
        if self.app.cfg.db_path != old_db:
            self.app.reset_db()
        elif self.app.indexer:
            self.app.indexer.settings_changed()
        self.app.pages["search"].refresh_folders()
        msg = tr("Impostazioni salvate.")
        if self.app.cfg.ui_zoom != old_scale:
            msg += "\n\n" + tr("La nuova dimensione dell'interfaccia vale dal prossimo avvio di DocIndexer.")
        messagebox.showinfo(tr("Impostazioni"), msg)
        return True

    # ----------------------------------------------------------- backup
    def _build_backup(self, tab):
        box = ctk.CTkFrame(tab, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=8, pady=8)
        theme.caption(box, tr("Backup e ripristino"), self.app.fonts).pack(anchor="w", pady=(4, 6))
        ctk.CTkLabel(box, text=tr("Il backup è un file .zip con il database (indice, note, colori di importanza), "
                                  "le impostazioni, i pattern regex e le ricerche salvate. I documenti non sono "
                                  "inclusi: DocIndexer non li copia mai, ricorda solo dove sono. Si può fare anche "
                                  "mentre l'indicizzazione lavora."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").pack(anchor="w", pady=(0, 12))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(anchor="w")
        ctk.CTkButton(row, text=tr("Crea backup..."), width=180, command=self.app.do_backup).pack(side="left")
        ctk.CTkButton(row, text=tr("Ripristina da backup..."), width=200, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=self.app.do_restore).pack(side="left", padx=8)
        ctk.CTkLabel(box, text=tr("Il ripristino sostituisce database e impostazioni attuali e riavvia DocIndexer. "
                                  "Il database attuale resta accanto con l'estensione .before-restore."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left").pack(anchor="w", pady=(12, 0))

    def test_ocr(self):
        """Prova il modello scelto su una scritta disegnata al volo."""
        import time
        from PIL import ImageDraw, ImageFont

        key = self.vars["ocr_model"].get() or ocr.DEFAULT_MODEL
        sample = "Prova OCR 2026"
        img = Image.new("RGB", (900, 160), "white")
        try:
            font = ImageFont.truetype("arial.ttf", 64)
        except OSError:
            font = ImageFont.load_default(64)
        ImageDraw.Draw(img).text((30, 40), sample, fill="black", font=font)
        try:
            t = time.perf_counter()
            words = [w for w, _s, q in ocr.recognize(img, key) if q]
            ms = (time.perf_counter() - t) * 1000
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(tr("OCR"), tr("OCR non disponibile:\n{exc}", exc=exc))
            return
        m = ocr.get_model(key)
        messagebox.showinfo(tr("OCR"), f"RapidOCR {m.version}: {tr(m.name)}\n\n"
                            + tr("Testo di prova: {sample}", sample=sample) + "\n"
                            + tr("Riconosciuto: {text}", text=" ".join(words) or tr("(niente)")) + f"\n({ms:.0f} ms)")


# ======================================================================
class App(ctk.CTk):
    MENU = (("monitor", "Monitor"), ("search", "Ricerca"), ("important", "Importanti"),
            ("documents", "Documenti"), ("duplicates", "Duplicati"), ("settings", "Impostazioni"))

    def __init__(self, background: bool = False, add_folder: str | None = None):
        self.cfg = AppConfig.load()
        # portable mode: external disk with a different letter (E: -> F:) -> stored paths follow it
        self.relocated = portable_drive.relocate(self.cfg)
        # cartella da aggiungere chiesta dal tasto destro di Esplora file (--add-folder), con nessun DocIndexer aperto
        self.pending_folder = add_folder
        self.indexer: Indexer | None = None
        self.tray = None
        self.saved = searches.SavedSearches()      # ricerche salvate (con avviso sui file nuovi)
        self.hotkey = None
        self.hotkey_error: str | None = None
        self._saved_busy = False
        self._saved_mark = None
        self._ticks = 0
        set_language(self.cfg.language)
        theme.apply()                      # tema scuro di PCSnex, prima di creare i widget
        super().__init__()
        hide_until_ready(self)                         # niente lampo della barra bianca all'apertura
        theme.apply_ui_scale(self, self.cfg.ui_zoom)   # Windows zoom x user zoom
        self.title(tr("DocIndexer - Indicizzatore documenti"))
        theme.set_icon(self)
        theme.place_window(self, 1280, 800, min_size=(1000, 640))   # never larger than the screen
        self.fonts = theme.Fonts()
        self.h1 = self.fonts.page
        self.events: queue.Queue = queue.Queue()
        # modello OCR: salvato in config.json, si cambia da Importa / Elaborazione / Impostazioni
        self.default_ocr = (self.cfg.ocr_model if self.cfg.ocr_model in ocr.MODELS or self.cfg.ocr_model == ocr.AUTO
                            else ocr.DEFAULT_MODEL)
        self.ocr_var = tk.StringVar(master=self, value=self.default_ocr)
        self.ocr_var.trace_add("write", lambda *_: self._ocr_changed())
        self.db: Database | None = None
        self._db_ready = False
        self.current = "monitor"
        style_treeview()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # prima apertura (o termini nuovi): lingua e termini d'uso, prima di costruire l'interfaccia
        if welcome.needed(self.cfg):
            self.withdraw()
            welcome.run(self, self.cfg, on_accept=lambda: self._after_welcome(background), on_reject=self.destroy)
            return
        self._init_rest(background)

    def _after_welcome(self, background: bool) -> None:
        """Termini accettati: salva lingua e accettazione, poi completa l'avvio."""
        self.save_config()
        set_language(self.cfg.language)
        self.title(tr("DocIndexer - Indicizzatore documenti"))
        if not background:
            self.deiconify()
        self._init_rest(background)

    def _init_rest(self, background: bool) -> None:
        if background:
            self.withdraw()               # avvio automatico: solo l'icona vicino all'orologio
        self._build()
        self.after(100, self._pump)
        # niente barra di Windows (c'è l'intestazione del tema); poi si apre ingrandita nell'area di lavoro
        if not background:
            self.after(50, apply_frameless, self, 60, self.maximize)
        self.after(600, self._start_daemon)
        self.after(1000, self._tick)

    def _build(self):
        """Intestazione, schede e pagine (ricostruite quando cambia la lingua)."""
        self._build_header()
        theme.rule(self).pack(fill="x")
        tabs = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        tabs.pack(fill="x", padx=20, pady=(10, 0))
        self.tabbar = theme.TabBar(tabs, self.fonts, [(k, tr(t)) for k, t in self.MENU], self.show)
        self.tabbar.pack(side="left", anchor="sw")
        # manuale: si apre in una finestra a parte, nella lingua del programma (come in DroidSnex)
        ctk.CTkButton(tabs, text="📖  " + tr("Manuale"), command=self.open_manual, width=10, height=34,
                      corner_radius=4, fg_color="transparent", hover_color=theme.HOVER, text_color=theme.TEXT_DIM,
                      font=self.fonts.body).pack(side="right", anchor="sw")
        # termini d'uso accettati alla prima apertura, da rileggere quando si vuole
        ctk.CTkButton(tabs, text=terms.labels(language())[0], command=lambda: welcome.show_terms(self), width=10,
                      height=34, corner_radius=4, fg_color="transparent", hover_color=theme.HOVER,
                      text_color=theme.TEXT_DIM, font=self.fonts.body).pack(side="right", anchor="sw")
        theme.rule(self).pack(fill="x", padx=20)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(14, 16))
        self.pages = {
            "monitor": daemon_ui.MonitorPage(content, self),
            "search": SearchPage(content, self),
            "important": DocumentsPage(content, self, important=True),
            "documents": DocumentsPage(content, self),
            "duplicates": dupes_ui.DuplicatesPage(content, self),
            "settings": SettingsPage(content, self),
        }
        self.show(self.current)
        self.after(300, lambda: self.ensure_db(quiet=True) and self.refresh_stats())

    def _build_header(self):
        """Intestazione come in PCSnex: logo Panchang alto 17, versione, crediti; a destra lingua e stato."""
        header = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        window_buttons(self, header, self.on_close).pack(side="right", anchor="n")
        if frameless.IS_WINDOWS:
            frameless.enable_drag(self, header)
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", padx=(18, 0))
        if frameless.IS_WINDOWS:
            frameless.enable_drag(self, brand)
        logo = theme.logo(17)
        if logo is not None:
            ctk.CTkLabel(brand, text="", image=logo).pack(side="left")
        else:
            ctk.CTkLabel(brand, text="DOCINDEXER", font=(theme.mono_font(), 15, "bold")).pack(side="left")
        ctk.CTkLabel(brand, text=f"   v{__version__}", font=(theme.mono_font(), 10),
                     text_color=theme.TEXT_DIM).pack(side="left", pady=(3, 0))
        ctk.CTkLabel(brand, text="  ·  " + tr("indicizzatore documenti"), font=(theme.mono_font(), 10),
                     text_color=theme.TEXT_FAINT).pack(side="left", pady=(3, 0))

        # crediti, su tre righe (e-mail e sito cliccabili)
        credits = ctk.CTkFrame(header, fg_color="transparent")
        credits.pack(side="left", padx=(28, 0))
        small = self.fonts.small
        ctk.CTkLabel(credits, text="Cumini Andrea", font=(theme.ui_font(), 11, "bold"), text_color=theme.TEXT_SOFT,
                     height=14, anchor="w").pack(anchor="w")
        row = ctk.CTkFrame(credits, fg_color="transparent")
        row.pack(anchor="w")
        mail = ctk.CTkLabel(row, text="andrea@osintinfo.net", font=small, height=14, cursor="hand2",
                            text_color=theme.ACCENT)
        mail.pack(side="left")
        mail.bind("<Button-1>", lambda e: __import__("webbrowser").open("mailto:andrea@osintinfo.net"))
        ctk.CTkLabel(row, text=tr("   tel. +393394601972"), font=small, height=14,
                     text_color=theme.TEXT_DIM).pack(side="left")
        web = ctk.CTkLabel(credits, text="www.osintinfo.net", font=small, height=14, anchor="w", cursor="hand2",
                           text_color=theme.ACCENT)
        web.pack(anchor="w")
        web.bind("<Button-1>", lambda e: __import__("webbrowser").open("https://www.osintinfo.net"))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=(0, 14))
        self.status = ctk.CTkLabel(right, text="", font=self.fonts.caption, text_color=theme.TEXT_DIM)
        self.status.pack(side="left", padx=(0, 14))
        theme.caption(right, tr("Lingua"), self.fonts).pack(side="left", padx=(0, 8))
        self.lang_menu = ctk.CTkOptionMenu(right, values=list(LANGUAGES.values()), width=150, height=28,
                                           font=self.fonts.body, dropdown_font=self.fonts.body,
                                           command=self._set_language)
        self.lang_menu.set(LANGUAGES[language()])
        self.lang_menu.pack(side="left")
        # battito dell'indicizzazione: sempre visibile, in tutte le schede
        self.pulse = daemon_ui.ActivityPulse(header, self)
        self.pulse.pack(side="left", fill="x", expand=True, padx=(28, 18))

    # ---------------------------------------------------------------- lingua
    def _busy(self) -> bool:
        pages = getattr(self, "pages", {})
        workers = []
        if "settings" in pages:
            workers.append(pages["settings"].tools_panel.worker)
        return any(w.busy for w in workers)

    def _set_language(self, name: str) -> None:
        code = next((c for c, n in LANGUAGES.items() if n == name), "it")
        if code == language():
            return
        if self._busy():
            messagebox.showinfo(tr("Lingua"), tr("Attendi la fine del download in corso."))
            self.lang_menu.set(LANGUAGES[language()])
            return
        set_language(code)
        self.cfg.language = code
        self.save_config()
        shellmenu.refresh()                # testo del tasto destro di Esplora file nella nuova lingua
        # ricostruisce l'interfaccia nella nuova lingua, restando sulla stessa scheda
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.title(tr("DocIndexer - Indicizzatore documenti"))
        self._build()
        if self.tray:                      # menu dell'icona nella nuova lingua
            self.tray.stop()
            self.tray = daemon_ui.Tray(self)
            self.tray.start()

    # ---------------------------------------------------------------- manuale
    def open_manual(self):
        """Il manuale docs/manual/<lingua>/MANUAL.md in una finestra del programma (inglese se la lingua manca)."""
        path = manual.manual_path(language())
        if path is None:
            messagebox.showerror(tr("Manuale"), tr("Manuale non trovato: {p}",
                                                   p=os.path.join(manual.MANUAL_DIR, language(), "MANUAL.md")))
            return
        if self.state() == "withdrawn":              # dal menu dell'icona con la finestra nascosta
            self.show_window()
        try:
            manual.open_manual(self, path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(tr("Manuale"), tr("Impossibile aprire il manuale: {e}", e=exc))

    # ------------------------------------------------------------------
    def show(self, key: str):
        settings = getattr(self, "pages", {}).get("settings")
        if (key != "settings" and getattr(self, "current", None) == "settings" and settings is not None
                and settings.dirty()):
            answer = messagebox.askyesnocancel(
                tr("Impostazioni"), tr("Ci sono modifiche alle impostazioni non salvate.\n\n"
                                       "Sì = salva, No = annulla le modifiche, Annulla = resta nelle impostazioni."))
            if answer is None:
                self.tabbar.select("settings")
                return
            if answer:
                if not settings.save():
                    self.tabbar.select("settings")
                    return
            else:
                self.current = key
                self._rebuild_settings()      # modulo riportato alle impostazioni salvate
                return
        self.current = key
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.tabbar.select(key)
        if key in ("documents", "important"):
            self.pages[key].refresh()
        elif key == "search":
            self.pages[key].refresh_folders()
        elif key == "monitor":
            self.refresh_stats()

    # ---------------------------------------------------------------- demone
    def annotations_changed(self, path_id):
        """Colore o nota cambiati: la riga del file si aggiorna sul posto negli elenchi (senza ricaricarli,
        così la selezione e l'anteprima restano dove sono); la scheda Importanti si ricarica quando si apre."""
        level, note = self.db.annotation(path_id)
        for key in ("documents", "important"):
            self.pages[key].update_row(path_id, level, note)

    def call_in_gui(self, fn, *args):
        """Da altri thread (icona, istanza unica): esegue fn nel thread dell'interfaccia."""
        self.events.put((fn, args))

    def _start_daemon(self):
        preview.cleanup_temp(all_processes=True)   # resti di sessioni chiuse male e vecchie anteprime in cache
        if not self.ensure_db(quiet=False):
            return
        self.single = daemon_ui.SingleInstance()
        pending, self.pending_folder = self.pending_folder, None
        hello = daemon_ui.add_message(pending) if pending else b"show"
        if not self.single.acquire(lambda: self.call_in_gui(self.show_window),
                                   on_add=lambda p: self.call_in_gui(self.add_folder, p), hello=hello):
            # c'è già un DocIndexer attivo: gli si chiede di mostrarsi (o di aggiungere la cartella) e questa esce
            self.destroy()
            return
        shellmenu.refresh()      # voce del tasto destro: comando aggiornato se l'exe è stato spostato
        self.tray = daemon_ui.Tray(self)
        self.tray.start()
        self.start_hotkey()
        # mentre si usa la finestra (ricerca, anteprime, ricerca rapida) l'indicizzazione lascia il passo
        for seq in ("<KeyPress>", "<ButtonPress>", "<MouseWheel>"):
            self.bind_all(seq, self._user_input, add="+")
        if pending and self.add_folder(pending):
            pass                 # cartella aggiunta dal tasto destro: l'indicizzazione è già partita
        elif not self.cfg.watch_dirs:
            self.show_window()
            daemon_ui.SetupWizard(self, self.cfg, self.fonts, self._setup_done)
        else:
            self._run_indexer()
        self.after(1500, self.check_tools)

    def _setup_done(self, ok: bool):
        if not ok and not self.cfg.watch_dirs:
            if not messagebox.askyesno("DocIndexer", tr("Senza cartelle da monitorare DocIndexer non può "
                                                        "indicizzare nulla. Vuoi configurarle adesso?")):
                return
            daemon_ui.SetupWizard(self, self.cfg, self.fonts, self._setup_done)
            return
        self._run_indexer()
        self._rebuild_settings()

    def _rebuild_settings(self):
        """Ricrea la pagina Impostazioni dalle impostazioni salvate (Annulla modifiche, No al cambio scheda,
        fine della configurazione guidata). La pagina vecchia va distrutta: se restasse impacchettata
        resterebbe disegnata sopra le altre schede."""
        content = self.pages["monitor"].master
        old = self.pages.get("settings")
        sub = None
        if old is not None and old.winfo_exists():
            try:
                sub = old.tabs.get()            # resta sulla stessa sotto-scheda (es. Configurazione)
            except (tk.TclError, AttributeError):
                pass
            old.pack_forget()
            old.destroy()
        self.pages["settings"] = SettingsPage(content, self)
        if sub:
            try:
                self.pages["settings"].tabs.set(sub)
            except (tk.TclError, ValueError):
                pass
        self.pages["search"].refresh_folders()
        self.show(self.current)

    def _ensure_ocr_model(self):
        """Il modello OCR principale è incluso nel programma: va copiato in tools\\rapidocr PRIMA che parta
        l'indicizzazione, altrimenti al primo avvio le immagini lette subito finiscono in errore."""
        try:
            if not tools.check_model(self.cfg, ocr.DEFAULT_MODEL).ok:
                tools.install_model(self.cfg, lambda _m: None)
        except Exception:  # noqa: BLE001
            pass

    def _run_indexer(self):
        if self.indexer is None:
            self._ensure_ocr_model()
            self.indexer = Indexer(self.cfg, self.db)
            if self.relocated:
                old, new, n = self.relocated
                self.indexer.log(tr("Disco del programma passato da {old} a {new}: aggiornati {n} percorsi.",
                                    old=old, new=new, n=n))
                self.relocated = None
            self.indexer.start()
        else:
            self.indexer.settings_changed()

    def indexer_rescan(self):
        if self.indexer:
            self.indexer.rescan()

    # --------------------------------------------------------- ricerca rapida
    def quick_search(self):
        quick.QuickSearch.toggle(self)

    def start_hotkey(self):
        """(Ri)registra la scorciatoia globale della ricerca rapida."""
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None
        self.hotkey_error = None
        spec = (self.cfg.quick_hotkey or "").strip()
        if not spec:
            return
        self.hotkey = hotkey.start(spec, lambda: self.call_in_gui(self.quick_search))
        if self.hotkey and self.hotkey.error:
            self.hotkey_error = tr("La scorciatoia {key} non è disponibile (la usa già un altro programma?): "
                                   "scegline un'altra in Impostazioni > Configurazione.", key=hotkey.pretty(spec))
            self.hotkey = None

    # -------------------------------------------------------- ricerche salvate
    def check_saved(self, soon: bool = False):
        """Riesegue in background le ricerche salvate con avviso e segnala i file nuovi."""
        if self._saved_busy or not self._db_ready or not any(i.get("alert") for i in self.saved.items):
            return
        self._saved_busy = True
        db_path, watch = self.cfg.db_file, list(self.cfg.watch_dirs)

        def work():
            db = Database(db_path)
            try:
                found = self.saved.check(db, watch)
            except Exception:  # noqa: BLE001
                found = []
            finally:
                db.close()
            self.call_in_gui(self._saved_checked, found)

        threading.Thread(target=work, daemon=True, name="saved-searches").start()

    def _saved_checked(self, found):
        self._saved_busy = False
        if "search" in getattr(self, "pages", {}):
            self.pages["search"].update_saved_badge()
        saved_ui.SavedSearchesWindow.refresh_open(self)
        if found and self.tray:
            lines = [tr("«{name}»: {n} nuovi file", name=item["name"], n=n) for item, n in found]
            self.tray.notify("\n".join(lines[:4]), tr("Ricerche salvate"))

    def _index_mark(self):
        try:
            return tuple(self.db.conn.execute(
                "SELECT (SELECT COUNT(*) FROM paths), (SELECT MAX(id) FROM document_contents),"
                " (SELECT COUNT(*) FROM files WHERE status='done')").fetchone())
        except Exception:  # noqa: BLE001
            return None

    # ----------------------------------------------------------------- backup
    def do_backup(self):
        if not self.ensure_db():
            return
        target = filedialog.asksaveasfilename(title=tr("Crea backup"), initialfile=backup.default_name(),
                                              defaultextension=".zip", filetypes=[(tr("Backup DocIndexer"), "*.zip")])
        if not target:
            return
        self.status.configure(text=tr("Backup in corso..."))
        db = self.db

        def work():
            try:
                out = backup.create(db, target, __version__)
                self.call_in_gui(self._backup_done, out, None)
            except Exception as exc:  # noqa: BLE001
                self.call_in_gui(self._backup_done, None, exc)

        threading.Thread(target=work, daemon=True, name="backup").start()

    def _backup_done(self, out, exc):
        self.refresh_stats()
        if exc:
            messagebox.showerror(tr("Backup"), tr("Backup non riuscito:\n{exc}", exc=exc))
        else:
            size = os.path.getsize(out) / 1048576
            messagebox.showinfo(tr("Backup"), tr("Backup creato:\n{path}\n({mb} MB)", path=out, mb=f"{size:.1f}"))

    def do_restore(self):
        src = filedialog.askopenfilename(title=tr("Ripristina da backup"),
                                         filetypes=[(tr("Backup DocIndexer"), "*.zip")])
        if not src:
            return
        try:
            info = backup.inspect(src)
        except ValueError:
            messagebox.showerror(tr("Backup"), tr("Il file scelto non è un backup di DocIndexer."))
            return
        when = info.get("created") or "?"
        if not messagebox.askyesno(tr("Ripristina da backup"),
                                   tr("Ripristinare il backup del {when}?\n\nDatabase e impostazioni attuali vengono "
                                      "sostituiti e DocIndexer si riavvia.", when=when), icon="warning"):
            return
        if self.indexer:
            self.indexer.stop()
            self.indexer = None
        if self.db:
            self.db.close_all()
        self.db = None
        self._db_ready = False
        try:
            backup.restore(src, self.cfg.db_file)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(tr("Backup"), tr("Ripristino non riuscito:\n{exc}", exc=exc))
            self.reset_db()
            return
        self.restart()

    def restart(self):
        """Riavvia DocIndexer (dopo un ripristino): nuova istanza, poi questa si chiude."""
        import subprocess

        cmd = [sys.executable] + ([] if getattr(sys, "frozen", False) else [os.path.abspath(sys.argv[0])])
        if getattr(self, "single", None):
            self.single.release()
            self.single = None
        subprocess.Popen(cmd, close_fds=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.quit_app()

    # ------------------------------------------------ tasto destro di Esplora file
    def set_context_menu(self, enabled: bool) -> None:
        """Voce «Aggiungi a DocIndexer» del tasto destro attivata / disattivata subito (Impostazioni)."""
        if not shellmenu.set_enabled(bool(enabled)):
            messagebox.showerror("DocIndexer", tr("Impossibile modificare il menu del tasto destro di Esplora file."))
        settings = getattr(self, "pages", {}).get("settings")
        if settings is not None and settings.winfo_exists():
            settings.shellmenu.set(shellmenu.enabled())

    def add_folder(self, path: str) -> bool:
        """Aggiunge una cartella alle cartelle monitorate (tasto destro «Aggiungi a DocIndexer») e la indicizza.
        Niente doppioni: se c'è già, o è dentro una cartella monitorata, si avvisa e basta; se invece contiene
        cartelle già monitorate prende il loro posto. True se la configurazione è cambiata."""
        self.show_window()
        title = tr("Aggiungi a DocIndexer")
        path = os.path.normpath(os.path.abspath(path))
        if not os.path.isdir(path):
            messagebox.showerror(title, tr("Cartella non trovata:\n{path}", path=path))
            return False

        def key(d: str) -> str:
            return os.path.normcase(os.path.normpath(d))

        def inside(child: str, parent: str) -> bool:
            return key(child).startswith(key(parent).rstrip(os.sep) + os.sep)

        dirs = list(self.cfg.watch_dirs)
        excluded = [e for e in self.cfg.exclude_paths if key(e) == key(path)]
        if any(key(d) == key(path) for d in dirs):
            messagebox.showinfo(title, tr("La cartella è già monitorata:\n{path}", path=path))
            return False
        parent = next((d for d in dirs if inside(path, d)), None)
        children = [d for d in dirs if inside(d, path)]
        if parent and not excluded:
            messagebox.showinfo(title, tr("La cartella è già compresa in una cartella monitorata:\n{parent}",
                                          parent=parent))
            return False
        if parent:
            # era tra le sottocartelle escluse di una cartella monitorata: basta togliere l'esclusione
            msg = tr("La cartella era tra le sottocartelle escluse: ora viene indicizzata.\n{path}", path=path)
        else:
            dirs = [d for d in dirs if d not in children] + [path]
            msg = tr("Cartella aggiunta alle cartelle monitorate:\n{path}\n\nL'indicizzazione inizia subito.",
                     path=path)
            if children:
                msg += "\n\n" + tr("Le cartelle monitorate che contiene ({n}) ora sono comprese in questa.",
                                    n=len(children))
        self.cfg.watch_dirs = dirs
        self.cfg.exclude_paths = [e for e in self.cfg.exclude_paths if key(e) != key(path)]
        self.save_config()
        self._sync_settings_folders(path, children)
        self._run_indexer()
        messagebox.showinfo(title, msg)
        return True

    def _sync_settings_folders(self, path: str, children: list[str]) -> None:
        """La pagina Impostazioni mostra la nuova cartella. Con modifiche non salvate non si perde niente:
        la cartella entra nel modulo e il resto delle modifiche resta da salvare."""
        settings = getattr(self, "pages", {}).get("settings")
        if settings is None or not settings.winfo_exists():
            return
        if not settings.dirty():
            self._rebuild_settings()
            return
        key = lambda d: os.path.normcase(os.path.normpath(d))  # noqa: E731
        drop = {key(c) for c in children} | {key(path)}
        settings.folders.set([d for d in settings.folders.get() if key(d) not in drop] + list(
            d for d in self.cfg.watch_dirs if key(d) == key(path)))
        settings.excluded.set([e for e in settings.excluded.get() if key(e) != key(path)])
        saved = list(settings._saved)
        saved[0], saved[1] = tuple(self.cfg.watch_dirs), tuple(self.cfg.exclude_paths)
        settings._saved = tuple(saved)
        self.pages["search"].refresh_folders()

    def set_autostart(self, enabled: bool) -> None:
        """Avvio con Windows attivato / disattivato subito (Monitor, menu dell'icona, Impostazioni)."""
        enabled = bool(enabled)
        if not daemon_ui.set_autostart(enabled):
            messagebox.showerror("DocIndexer", tr("Impossibile modificare l'avvio automatico di Windows."))
            enabled = daemon_ui.autostart_enabled()
        self.cfg.autostart = enabled
        self.save_config()
        pages = getattr(self, "pages", {})
        if "monitor" in pages:
            pages["monitor"].autostart.set(enabled)
        settings = pages.get("settings")
        if settings is not None:
            settings.autostart.set(enabled)
            saved = list(settings._saved)       # già salvato: non conta come modifica in sospeso
            saved[6] = enabled
            settings._saved = tuple(saved)
        if self.tray and self.tray.icon is not None:
            try:
                self.tray.icon.update_menu()
            except Exception:  # noqa: BLE001
                pass

    def toggle_pause(self):
        self.cfg.paused = not self.cfg.paused
        self.save_config()
        if self.indexer:
            self.indexer.set_paused(self.cfg.paused)
        self.refresh_stats()

    def _user_input(self, _event=None):
        """Tasto, clic o rotellina nella finestra: l'indicizzazione si ferma al prossimo punto di pausa e
        riprende 2,5 s dopo l'ultimo input, così ricerca e interfaccia non diventano lente."""
        ix = self.indexer
        if ix is not None:
            ix.throttle.hold(2.5)

    def set_resource_level(self, level: int):
        """Slider "Risorse per l'indicizzazione" del Monitor (e "Riduci al minimo"): imposta tetto di CPU,
        thread OCR, priorità e risparmio energetico, li applica subito e li salva. Il modulo di Impostazioni
        si aggiorna con i nuovi valori (senza risultare modificato se non lo era già)."""
        level = max(1, min(len(RESOURCE_LEVELS), int(level)))
        _name, cpu, idle, threads = RESOURCE_LEVELS[level]
        cfg = self.cfg
        cfg.resource_level, cfg.cpu_limit, cfg.cpu_limit_idle, cfg.ocr_threads = level, cpu, idle, threads
        self.save_config()
        if self.indexer:
            self.indexer.apply_resources()
        settings = self.pages.get("settings") if hasattr(self, "pages") else None
        if settings is not None:
            try:
                was_dirty = settings.dirty()
                for key in ("cpu_limit", "cpu_limit_idle", "ocr_threads"):
                    settings.vars[key].set(str(getattr(cfg, key)))
                if not was_dirty:
                    settings._saved = settings.snapshot()
            except (tk.TclError, AttributeError, KeyError):
                pass

    def maximize(self):
        """Ingrandita nell'area di lavoro (sopra la barra delle applicazioni)."""
        try:
            if self.state() != "zoomed":
                self.state("zoomed")
        except tk.TclError:
            pass

    def show_window(self):
        was_hidden = self.state() == "withdrawn"
        hide_until_ready(self)
        self.deiconify()
        self.after(30, apply_frameless, self, 60, self.maximize if was_hidden else None)
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

    def _tick(self):
        """Ogni secondo: monitor, stato nell'intestazione, suggerimento dell'icona."""
        try:
            self.pages["monitor"].resources.sample()     # storico di CPU e RAM anche a finestra nascosta
            self._ticks += 1
            if self._ticks % 60 == 0 and self._db_ready:  # ogni minuto: indice cambiato -> ricerche salvate
                mark = self._index_mark()
                if mark is not None and mark != self._saved_mark:
                    self._saved_mark = mark
                    self.check_saved()
            if self.state() != "withdrawn":
                self.refresh_stats()
            elif self.tray and self._db_ready:
                s = self.db.stats()
                self.tray.update(self._tray_text(s))
        except Exception:  # noqa: BLE001
            pass
        self.after(1000, self._tick)

    def _tray_text(self, s: dict) -> str:
        if self.cfg.paused:
            return "DocIndexer · " + tr("In pausa")
        todo = s["pending"] + s["processing"]
        return "DocIndexer · " + tr("{done} indicizzati, {todo} da fare", done=s["done"], todo=todo)

    def quit_app(self):
        if self.hotkey:
            self.hotkey.stop()
        try:
            self.pages["search"]._cancel_regex()     # la ricerca regex in corso non resta accesa
        except (AttributeError, KeyError, tk.TclError):
            pass
        if self.indexer:
            self.indexer.stop()
        preview.cleanup_temp()             # nessuna anteprima resta sul disco
        if self.tray:
            self.tray.stop()
        if getattr(self, "single", None):
            self.single.release()
        self.destroy()

    def _ocr_changed(self):
        """Il modello scelto in Importa / Elaborazione resta salvato per le prossime aperture."""
        key = self.ocr_var.get() or ocr.DEFAULT_MODEL
        self.cfg.ocr_model = key
        self.default_ocr = key
        self.save_config()
        settings = self.pages.get("settings") if hasattr(self, "pages") else None
        if settings is not None and settings.vars["ocr_model"].get() != key:
            settings.vars["ocr_model"].set(key)

    def save_config(self):
        """Salva config.json mantenendo come modello OCR quello predefinito, non quello del lavoro corrente."""
        current = self.cfg.ocr_model
        self.cfg.ocr_model = self.default_ocr
        try:
            self.cfg.save()
        finally:
            self.cfg.ocr_model = current

    def check_tools(self):
        self._ensure_ocr_model()           # di solito già fatto all'avvio dell'indicizzazione
        missing = [s.name for s in tools.check_all(self.cfg) if not s.ok and not s.optional]
        if missing and messagebox.askyesno(
                tr("Strumenti mancanti"),
                tr("Mancano alcuni strumenti necessari:") + "\n\n- " + "\n- ".join(missing)
                + "\n\n" + tr("Vuoi aprire la pagina per installarli?")):
            self.show("settings")
            self.pages["settings"].tabs.set(tr("Strumenti esterni"))

    def _pump(self):
        try:
            for _ in range(200):
                fn, args = self.events.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(80, self._pump)

    def reset_db(self):
        if self.indexer:
            self.indexer.stop()
            self.indexer = None
        if self.db:
            self.db.close()
        self.db = None
        self._db_ready = False
        if self.ensure_db(quiet=True):
            self._run_indexer()
            self.refresh_stats()

    def ensure_db(self, quiet: bool = False) -> bool:
        if self._db_ready and self.db:
            return True
        try:
            self.db = Database(self.cfg.db_file)
            self.db.initialize()
            self._db_ready = True
            self.status.configure(text=f"DB: {os.path.basename(self.cfg.db_path)}")
            return True
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text=tr("DB non connesso"))
            if not quiet:
                messagebox.showerror(tr("Database"), tr("Impossibile aprire il database:\n{exc}\n\nControlla il percorso in Impostazioni.",
                                                    exc=exc))
            return False

    def refresh_stats(self):
        if not self._db_ready:
            return
        try:
            s = self.db.stats()
        except Exception:  # noqa: BLE001
            return
        if self.current == "monitor":
            self.pages["monitor"].refresh(s)
        self.status.configure(text=tr("{total} file, {done} indicizzati", total=s["total"], done=s["done"]))
        if self.tray:
            self.tray.update(self._tray_text(s))

    def on_close(self):
        """Chiudere la finestra la nasconde: DocIndexer continua a lavorare (icona vicino all'orologio)."""
        if self.tray and self.tray.icon is not None:
            self.withdraw()
        else:
            self.quit_app()


def main():
    folder = shellmenu.folder_from_argv(sys.argv)
    if folder and daemon_ui.send_to_running(daemon_ui.add_message(folder)):
        return       # tasto destro «Aggiungi a DocIndexer»: la cartella va al DocIndexer già aperto
    App(background="--background" in sys.argv and not folder, add_folder=folder).mainloop()
