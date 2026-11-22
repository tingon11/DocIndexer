# DocIndexer — tema grafico di PCSnex (ripreso da AndrOsint).  Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net>
"""Aspetto dell'interfaccia: tema scuro stile Seity, identico a PCSnex e AndrOsint.

Palette, caratteri, tema CustomTkinter e stile delle tabelle ttk. Il tema e'
solo scuro: apply() va chiamata una volta, prima di creare qualsiasi widget.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import customtkinter as ctk

from .config import ASSETS_DIR

ASSETS = ASSETS_DIR
LOGO_FILE = ASSETS / "logo.png"
ICON_FILE = ASSETS / "docindexer.ico"
ICON_PNG = ASSETS / "docindexer.png"
APP_USER_MODEL_ID = "SeityAI.DocIndexer"

PAD = 12
GAP = 8

# ------------------------------------------- palette: scuro, essenziale, un accento
BG = "#07090c"
PANEL = "#0d1117"
PANEL_2 = "#121821"
PANEL_3 = "#161d27"
BORDER = "#1c2530"
BORDER_STRONG = "#2a3644"
HOVER = "#18212c"
INPUT = "#0a0e13"
TEXT = "#d5dde6"
TEXT_SOFT = "#aab6c3"
TEXT_DIM = "#6e7b89"
TEXT_FAINT = "#3e4955"
# accento = colore della seconda parte del logo
ACCENT = "#7b95dd"
ACCENT_DIM = "#4a63b5"
ACCENT_BG = "#141c33"
SELECT_BG = "#1d2847"
OK = "#34d399"
WARN = "#fbbf24"
ERR = "#f87171"

# pulsanti pieni: testo chiaro leggibile su tutti
BTN = "#4a63b5"
BTN_HOVER = "#3d54a0"   # più scuro di BTN (in PCSnex era più chiaro): il testo chiaro resta leggibile
DANGER = "#b42335"
DANGER_HOVER = "#8f1c2a"
WARN_BTN = "#b45309"
WARN_BTN_HOVER = "#92400e"
NEUTRAL = "#1f2a36"
NEUTRAL_HOVER = "#2a3746"
BTN_TEXT = "#f1f4fd"
CLOSE_HOVER = "#c42b1c"

# pulsante distruttivo come in PCSnex: bordo e testo rossi su fondo trasparente (testo sempre leggibile)
DANGER_STYLE = {"fg_color": "transparent", "hover_color": HOVER, "border_width": 1, "border_color": ERR,
                "text_color": ERR}
# pulsante disattivato: fondo neutro e testo attenuato ma leggibile, qualunque fosse il colore del pulsante
DISABLED_BG = PANEL_3
DISABLED_TEXT = TEXT_DIM

# nomi usati dalle pagine
MUTED = TEXT_DIM
ERROR = ERR

# ----------------------------------------------------------------- caratteri
UI_FONTS = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans"]
MONO_FONTS = ["Cascadia Mono", "JetBrains Mono", "Consolas", "DejaVu Sans Mono", "Menlo"]
ICON_FONTS = ["Segoe Fluent Icons", "Segoe MDL2 Assets"]
_picked: dict[str, str] = {}


def _pick(key: str, candidates: list[str], fallback: str) -> str:
    if key in _picked:
        return _picked[key]
    root = tk._default_root
    if root is None:
        return fallback  # nessuna finestra ancora: non si memorizza
    try:
        available = {name.lower(): name for name in tkfont.families(root)}
    except tk.TclError:
        return fallback
    _picked[key] = next((available[c.lower()] for c in candidates if c.lower() in available), fallback)
    return _picked[key]


def ui_font() -> str:
    return _pick("ui", UI_FONTS, "Segoe UI")


def mono_font() -> str:
    return _pick("mono", MONO_FONTS, "Consolas")


def icon_font() -> str:
    """Carattere delle icone di Windows; stringa vuota se non c'e'."""
    return _pick("icons", ICON_FONTS, "")


class Fonts:
    """Caratteri condivisi: vanno creati dopo la finestra principale."""

    def __init__(self) -> None:
        ui, mono = ui_font(), mono_font()
        self.body = ctk.CTkFont(family=ui, size=12)
        self.small = ctk.CTkFont(family=ui, size=11)
        self.bold = ctk.CTkFont(family=ui, size=12, weight="bold")
        self.title = ctk.CTkFont(family=mono, size=10, weight="bold")   # titoli dei riquadri
        self.page = ctk.CTkFont(family=ui, size=19, weight="bold")      # titolo della pagina
        self.button = ctk.CTkFont(family=ui, size=12, weight="bold")
        self.mono = ctk.CTkFont(family=mono, size=12)
        self.caption = ctk.CTkFont(family=mono, size=9, weight="bold")  # etichette maiuscole
        self.tiny = ctk.CTkFont(family=mono, size=9)

    def icon(self, size: int) -> ctk.CTkFont:
        return ctk.CTkFont(family=icon_font() or mono_font(), size=size)


# --------------------------------------------------------- tema CustomTkinter
_THEME = {
    "CTk": {"fg_color": [BG, BG]},
    "CTkToplevel": {"fg_color": [BG, BG]},
    "CTkFrame": {
        "corner_radius": 4, "border_width": 0,
        "fg_color": [PANEL, PANEL],
        "top_fg_color": [PANEL_2, PANEL_2],
        "border_color": [BORDER, BORDER],
    },
    "CTkButton": {
        "corner_radius": 4, "border_width": 0,
        "fg_color": [BTN, BTN],
        "hover_color": [BTN_HOVER, BTN_HOVER],
        "border_color": [BORDER, BORDER],
        "text_color": [BTN_TEXT, BTN_TEXT],
        "text_color_disabled": [DISABLED_TEXT, DISABLED_TEXT],
    },
    "CTkLabel": {
        "corner_radius": 0, "fg_color": "transparent",
        "text_color": [TEXT, TEXT],
    },
    "CTkEntry": {
        "corner_radius": 4, "border_width": 1,
        "fg_color": [INPUT, INPUT],
        "border_color": [BORDER, BORDER],
        "text_color": [TEXT, TEXT],
        "placeholder_text_color": [TEXT_FAINT, TEXT_FAINT],
    },
    "CTkCheckBox": {
        "corner_radius": 3, "border_width": 2,
        "fg_color": [ACCENT_DIM, ACCENT_DIM],
        "border_color": [BORDER_STRONG, BORDER_STRONG],
        "hover_color": [BTN_HOVER, BTN_HOVER],
        "checkmark_color": [BTN_TEXT, BTN_TEXT],
        "text_color": [TEXT, TEXT],
        "text_color_disabled": [TEXT_FAINT, TEXT_FAINT],
    },
    "CTkSwitch": {
        "corner_radius": 1000, "border_width": 3, "button_length": 0,
        "fg_color": [BORDER_STRONG, BORDER_STRONG],
        "progress_color": [ACCENT_DIM, ACCENT_DIM],
        "button_color": [TEXT_SOFT, TEXT_SOFT],
        "button_hover_color": ["#ffffff", "#ffffff"],
        "text_color": [TEXT, TEXT],
        "text_color_disabled": [TEXT_FAINT, TEXT_FAINT],
    },
    "CTkProgressBar": {
        "corner_radius": 1000, "border_width": 0,
        "fg_color": [PANEL_3, PANEL_3],
        "progress_color": [ACCENT, ACCENT],
        "border_color": [BORDER, BORDER],
    },
    "CTkOptionMenu": {
        "corner_radius": 4,
        "fg_color": [PANEL_2, PANEL_2],
        "button_color": [PANEL_3, PANEL_3],
        "button_hover_color": [HOVER, HOVER],
        "text_color": [TEXT, TEXT],
        "text_color_disabled": [TEXT_FAINT, TEXT_FAINT],
    },
    "CTkScrollbar": {
        "corner_radius": 1000, "border_spacing": 4, "fg_color": "transparent",
        "button_color": [BORDER, BORDER],
        "button_hover_color": [BORDER_STRONG, BORDER_STRONG],
    },
    "CTkTextbox": {
        "corner_radius": 4, "border_width": 0,
        "fg_color": [INPUT, INPUT],
        "border_color": [BORDER, BORDER],
        "text_color": [TEXT, TEXT],
        "scrollbar_button_color": [BORDER, BORDER],
        "scrollbar_button_hover_color": [BORDER_STRONG, BORDER_STRONG],
    },
    "CTkSegmentedButton": {
        "corner_radius": 4, "border_width": 2,
        "fg_color": [PANEL_2, PANEL_2],
        "selected_color": [BTN, BTN],
        "selected_hover_color": [BTN_HOVER, BTN_HOVER],
        "unselected_color": [PANEL_2, PANEL_2],
        "unselected_hover_color": [HOVER, HOVER],
        "text_color": [BTN_TEXT, BTN_TEXT],
        "text_color_disabled": [TEXT_FAINT, TEXT_FAINT],
    },
    "CTkTabview": {
        "corner_radius": 4, "border_width": 1,
        "fg_color": [PANEL, PANEL],
        "border_color": [BORDER, BORDER],
        "segmented_button_fg_color": [PANEL_2, PANEL_2],
        "segmented_button_selected_color": [BTN, BTN],
        "segmented_button_selected_hover_color": [BTN_HOVER, BTN_HOVER],
        "segmented_button_unselected_color": [PANEL_2, PANEL_2],
        "segmented_button_unselected_hover_color": [HOVER, HOVER],
        "text_color": [BTN_TEXT, BTN_TEXT],
        "text_color_disabled": [TEXT_FAINT, TEXT_FAINT],
    },
    "DropdownMenu": {
        "fg_color": [PANEL_2, PANEL_2],
        "hover_color": [SELECT_BG, SELECT_BG],
        "text_color": [TEXT, TEXT],
    },
}


def _deep_update(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _patch_buttons() -> None:
    """customtkinter lascia il colore di fondo quando un pulsante è disattivato: su un pulsante pieno
    (blu, rosso) il testo attenuato non si leggerebbe. Qui un pulsante disattivato prende sempre il fondo
    neutro DISABLED_BG (e il bordo attenuato) e ritrova i suoi colori quando torna attivo."""
    if getattr(ctk.CTkButton, "_docindexer_patched", False):
        return
    orig_init, orig_configure = ctk.CTkButton.__init__, ctk.CTkButton.configure

    def sync(btn) -> None:
        disabled = btn.cget("state") == "disabled"
        saved = getattr(btn, "_enabled_colors", None)
        if disabled and saved is None:
            btn._enabled_colors = (btn.cget("fg_color"), btn.cget("border_color"))
            orig_configure(btn, fg_color=DISABLED_BG, border_color=BORDER, text_color_disabled=DISABLED_TEXT)
        elif not disabled and saved is not None:
            btn._enabled_colors = None
            orig_configure(btn, fg_color=saved[0], border_color=saved[1])

    def init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        sync(self)

    def configure(self, require_redraw=False, **kwargs):
        saved = getattr(self, "_enabled_colors", None)
        if saved is not None and ("fg_color" in kwargs or "border_color" in kwargs):
            # colori nuovi mentre è disattivato: valgono da quando torna attivo
            self._enabled_colors = (kwargs.pop("fg_color", saved[0]), kwargs.pop("border_color", saved[1]))
        orig_configure(self, require_redraw=require_redraw, **kwargs)
        if "state" in kwargs:
            sync(self)

    ctk.CTkButton.__init__ = init
    ctk.CTkButton.configure = configure
    ctk.CTkButton._docindexer_patched = True


def apply() -> None:
    """Imposta il tema: va chiamata una volta, prima di creare qualsiasi widget."""
    if sys.platform == "win32":
        # Identita' propria nella barra di Windows: senza, le finestre finiscono
        # sotto python.exe con l'icona di Python.
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            pass
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")  # base, poi sovrascritta
    _deep_update(ctk.ThemeManager.theme, _THEME)
    _patch_buttons()
    # carattere predefinito dei widget: lo stesso di PCSnex (i widget di DocIndexer spesso non lo indicano)
    for platform_fonts in ctk.ThemeManager.theme.get("CTkFont", {}).values():
        if isinstance(platform_fonts, dict):
            platform_fonts.update({"family": UI_FONTS[1], "size": 13})


def set_icon(window) -> None:
    """Icona dell'applicazione sulla finestra (e, per la principale, nella barra di Windows)."""
    if sys.platform != "win32":
        if ICON_PNG.is_file():
            try:
                window._docindexer_icon = tk.PhotoImage(file=str(ICON_PNG))
                window.iconphoto(True, window._docindexer_icon)
            except tk.TclError:
                pass
        return
    if not ICON_FILE.is_file():
        return
    try:
        if isinstance(window, ctk.CTk):
            window.iconbitmap(default=str(ICON_FILE))
        window.iconbitmap(str(ICON_FILE))
    except tk.TclError:
        pass


def logo(height: int) -> ctk.CTkImage | None:
    """Logo alto `height` punti logici; None se il file manca."""
    try:
        from PIL import Image

        image = Image.open(LOGO_FILE).convert("RGBA")
    except (OSError, ImportError):
        return None
    width = round(image.width * height / image.height)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def scaling(widget) -> float:
    return ctk.ScalingTracker.get_widget_scaling(widget)


def px(widget, n: float) -> int:
    """Logical size -> physical pixels, for plain tk/ttk widgets (Canvas, Treeview columns, PanedWindow),
    which CustomTkinter does not scale. CTk widgets take logical sizes and must not use this."""
    return int(round(n * (scaling(widget) or 1.0)))


def autowrap(label, max_width: int | None = None, pad: int = 0):
    """Wrap a CTkLabel's text at the width it is actually given (it must be packed with fill="x" or
    gridded with sticky "ew"), so long sentences never run past the window on small or zoomed screens.
    max_width (logical) keeps lines readable on very wide windows."""
    def on_configure(e):
        w = int(e.width / (scaling(label) or 1.0)) - pad
        if max_width:
            w = min(w, max_width)
        w = max(120, w)
        if abs(w - getattr(label, "_autowrap_w", 0)) > 3:
            label._autowrap_w = w
            label.configure(wraplength=w)

    tk.Misc.bind(label, "<Configure>", on_configure, add="+")   # the outer frame, in physical pixels
    return label


_CHECK_IMAGES: dict = {}


def check_images(widget):
    """(off, on) images for plain tk.Checkbuttons, sized with the UI zoom: the native Windows indicator
    stays 13 px at any DPI and becomes a speck on 4K screens."""
    from PIL import Image, ImageDraw, ImageTk

    s = scaling(widget) or 1.0
    key = round(s, 2)
    if key not in _CHECK_IMAGES:
        n = max(12, round(14 * s))
        big = n * 4                                     # drawn large and reduced: soft edges
        pics = []
        for on in (False, True):
            img = Image.new("RGBA", (big + 4 * max(2, round(4 * s)), big), (0, 0, 0, 0))   # + gap to the text
            d = ImageDraw.Draw(img)
            r = big // 5
            if on:
                d.rounded_rectangle((0, 0, big - 1, big - 1), r, fill=BTN)
                w = max(4, big // 8)
                d.line([(big * 0.22, big * 0.52), (big * 0.42, big * 0.72), (big * 0.78, big * 0.3)],
                       fill="#ffffff", width=w, joint="curve")
            else:
                d.rounded_rectangle((0, 0, big - 1, big - 1), r, outline=BORDER_STRONG, width=max(4, big // 10))
            pics.append(ImageTk.PhotoImage(img.resize((img.width // 4, n), Image.LANCZOS), master=widget))
        _CHECK_IMAGES[key] = tuple(pics)
    return _CHECK_IMAGES[key]


def window_scaling(window) -> float:
    return ctk.ScalingTracker.get_window_scaling(window) or 1.0


def style_tables(root) -> None:
    """Stile scuro piatto per le tabelle ttk (Treeview), allineato allo zoom dello schermo.

    customtkinter non ha una tabella: Treeview resta di gran lunga la piu'
    veloce con centinaia di righe, quindi la si veste con gli stessi colori.
    """
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Treeview",
        background=PANEL,
        fieldbackground=PANEL,
        foreground=TEXT,
        borderwidth=0,
        relief="flat",
        rowheight=int(27 * scaling(root)),
        font=(ui_font(), 10),
    )
    style.configure(
        "Treeview.Heading",
        background=BG,
        foreground=TEXT_DIM,
        borderwidth=0,
        relief="flat",
        padding=(px(root, 8), px(root, 6)),
        font=(mono_font(), 9, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", HOVER)])
    style.map(
        "Treeview",
        background=[("selected", SELECT_BG)],
        foreground=[("selected", "#ffffff")],
    )
    # Solo l'area delle righe, senza la cornice incassata del tema predefinito.
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    # barre di scorrimento ttk (tabelle, anteprima) con gli stessi colori
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background=BORDER, troughcolor=PANEL, bordercolor=PANEL,
                        arrowcolor=TEXT_DIM, lightcolor=BORDER, darkcolor=BORDER, relief="flat")
        style.map(f"{orient}.TScrollbar", background=[("active", BORDER_STRONG)])


# ------------------------------------------------------------ widget comuni
def caption(parent, text: str, fonts: Fonts) -> ctk.CTkLabel:
    """Etichetta di sezione in maiuscolo, attenuata (come il titolo della barra laterale)."""
    return ctk.CTkLabel(parent, text=text.upper(), anchor="w", font=fonts.caption, text_color=TEXT_FAINT)


def rule(parent, horizontal: bool = True) -> ctk.CTkFrame:
    """Filetto di separazione da un pixel."""
    size = {"height": 1} if horizontal else {"width": 1}
    return ctk.CTkFrame(parent, fg_color=BORDER, corner_radius=0, **size)


class TabBar(ctk.CTkFrame):
    """Schede orizzontali con lo stesso aspetto della navigazione di PCSnex / AndrOsint:
    scheda attiva su fondo d'accento con barretta sotto, le altre attenuate.

    `items`: lista di (chiave, etichetta).
    """

    def __init__(self, parent, fonts: Fonts, items, on_select) -> None:
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self._fonts = fonts
        self._on_select = on_select
        self._tabs: dict[str, dict] = {}
        self.current = ""
        for key, label in items:
            box = ctk.CTkFrame(self, fg_color="transparent", corner_radius=4, width=10, height=34)
            box.pack(side="left", padx=(0, 2))
            inner = ctk.CTkFrame(box, fg_color="transparent", corner_radius=0, width=10, height=10)
            inner.pack(fill="both", expand=True, padx=12, pady=(5, 0))
            text = ctk.CTkLabel(inner, text=label, font=fonts.body, text_color=TEXT_DIM, height=22)
            text.pack(side="left")
            bar = ctk.CTkFrame(box, fg_color="transparent", width=1, height=2, corner_radius=0)
            bar.pack(fill="x", side="bottom")
            self._tabs[key] = {"box": box, "text": text, "bar": bar, "hover": False}
            for w in (box, inner, text):
                w.bind("<Button-1>", lambda _e, k=key: self._on_select(k))
                w.bind("<Enter>", lambda _e, k=key: self._hover(k, True))
                w.bind("<Leave>", lambda _e, k=key: self._hover(k, False))
                w.configure(cursor="hand2")

    def select(self, key: str) -> None:
        previous, self.current = self.current, key
        if previous in self._tabs:
            self._paint(previous)
        self._paint(key)

    def _hover(self, key: str, on: bool) -> None:
        self._tabs[key]["hover"] = on
        self._paint(key)

    def _paint(self, key: str) -> None:
        tab = self._tabs[key]
        if key == self.current:
            tab["box"].configure(fg_color=ACCENT_BG)
            tab["bar"].configure(fg_color=ACCENT)
            tab["text"].configure(text_color=TEXT, font=self._fonts.bold)
        else:
            tab["box"].configure(fg_color=HOVER if tab["hover"] else "transparent")
            tab["bar"].configure(fg_color="transparent")
            tab["text"].configure(text_color=TEXT_SOFT if tab["hover"] else TEXT_DIM, font=self._fonts.body)


# ------------------------------------------------------------ importanza dei documenti
LEVEL_COLORS = {1: "#38bdf8", 2: "#34d399", 3: "#facc15", 4: "#fb923c", 5: "#f87171"}
LEVEL_NAMES = {1: "Azzurro", 2: "Verde", 3: "Giallo", 4: "Arancio", 5: "Rosso"}


def tint(color: str, amount: float = 0.28, base: str = PANEL) -> str:
    """Colore mescolato con lo sfondo: per colorare una riga senza rendere illeggibile il testo."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * amount + y * (1 - amount)):02x}" for x, y in zip(a, b))


_LEVEL_IMAGES: dict = {}


def level_image(level: int, widget):
    """Pallini dell'importanza nel loro colore, come immagine per le tabelle ttk (una cella di Treeview
    non può avere testo colorato). Immagine vuota trasparente per "nessuna importanza"."""
    from PIL import Image, ImageDraw, ImageTk

    level = int(level or 0)
    s = scaling(widget)
    key = (level, round(s, 2))
    if key not in _LEVEL_IMAGES:
        d = max(7, round(8 * s))           # diametro di un pallino
        gap = max(2, round(2 * s))
        w = max(1, 5 * (d + gap))
        img = Image.new("RGBA", (w * 4, d * 4), (0, 0, 0, 0))   # disegnato in grande e ridotto: bordi morbidi
        draw = ImageDraw.Draw(img)
        color = LEVEL_COLORS.get(level)
        for i in range(level if color else 0):
            x = i * (d + gap) * 4
            draw.ellipse((x, 0, x + d * 4 - 1, d * 4 - 1), fill=color)
        _LEVEL_IMAGES[key] = ImageTk.PhotoImage(img.resize((w, d), Image.LANCZOS), master=widget)
    return _LEVEL_IMAGES[key]


def level_mark(level: int) -> str:
    """Pallini nella colonna dell'importanza (l'ordinamento alfabetico li mette in ordine di importanza)."""
    return "●" * int(level or 0)


def apply_ui_scale(window, percent: int) -> None:
    """Interface size on top of the Windows display zoom (100 = same size as other Windows apps).

    CustomTkinter already makes the process per-monitor DPI aware and multiplies every size by
    the monitor's DPI factor; `percent` is an extra user zoom applied on top of it. Plain tk/ttk
    widgets (tables, lists, text boxes) size their point fonts with `tk scaling`, which is kept
    in step with the same factor, also when the window moves to a monitor with another zoom.
    Call it before creating the widgets.
    """
    f = max(50, min(300, int(percent or 100))) / 100.0
    ctk.set_widget_scaling(f)
    ctk.set_window_scaling(f)
    try:
        dpi = ctk.ScalingTracker.get_window_dpi_scaling(window) or 1.0
    except Exception:  # noqa: BLE001
        dpi = 1.0
    _set_tk_scaling(window, dpi * f)

    def _on_dpi_change(widget_scaling, _window_scaling):
        # moved to a monitor with a different zoom: refresh point fonts and table rows too
        _set_tk_scaling(window, widget_scaling)
        try:
            style_tables(window)
        except Exception:  # noqa: BLE001
            pass

    try:
        ctk.ScalingTracker.add_widget(_on_dpi_change, window)
    except Exception:  # noqa: BLE001
        pass


def _set_tk_scaling(window, factor: float) -> None:
    import tkinter as _tk

    try:
        window.tk.call("tk", "scaling", 96 / 72 * factor)
    except _tk.TclError:
        pass


def place_window(window, width: float | None = None, height: float | None = None, master=None,
                 min_size: tuple[int, int] | None = None, y_frac: float = 1 / 3, center: bool = True,
                 size: bool = True) -> None:
    """Size and position a window in logical units (the ones CustomTkinter's geometry() expects).

    CustomTkinter multiplies the whole "WxH+X+Y" string by the window scaling, while winfo_*()
    return physical pixels: everything is converted here, so windows stay centered and are never
    larger than the screen, at any resolution and zoom. width/height None = requested size.
    """
    s = window_scaling(window) or 1.0
    try:
        window.update_idletasks()
    except Exception:  # noqa: BLE001
        pass
    sw = window.winfo_screenwidth() / s
    sh = window.winfo_screenheight() / s - 48          # taskbar
    w = width if width is not None else window.winfo_reqwidth() / s
    h = height if height is not None else window.winfo_reqheight() / s
    w, h = int(min(w, sw * 0.96)), int(min(h, sh * 0.96))
    if min_size:
        window.minsize(int(min(min_size[0], w)), int(min(min_size[1], h)))
    spec = f"{w}x{h}" if size else ""
    if center:
        x = y = None
        try:
            if master is not None and master.winfo_viewable():
                x = master.winfo_rootx() / s + (master.winfo_width() / s - w) / 2
                y = master.winfo_rooty() / s + (master.winfo_height() / s - h) * y_frac
        except Exception:  # noqa: BLE001
            x = y = None
        if x is None:
            x = max(0, min((sw - w) / 2, sw - w))
            y = max(0, min((sh - h) * y_frac, sh - h))
        spec += f"+{max(0, int(x))}+{max(0, int(y))}"
    if spec:
        window.geometry(spec)
