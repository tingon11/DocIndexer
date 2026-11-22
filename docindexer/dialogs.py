# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Finestre senza barra del titolo, nel tema del programma (come PCSnex).

- decorate(win, title): toglie la barra di Windows e mette in cima l'intestazione del tema
  (logo, titolo trascinabile, riduci / massimizza / chiudi)
- showinfo / showwarning / showerror / askyesno / askyesnocancel: stessi nomi e parametri di
  tkinter.messagebox, ma con finestre del tema. I moduli dell'interfaccia le importano come
  "messagebox", così tutti gli avvisi e le domande del programma hanno lo stesso aspetto.

Le finestre di Windows per scegliere file e cartelle restano quelle del sistema.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from . import frameless, theme
from .i18n import tr

# glifi di Segoe Fluent Icons / MDL2 (come PCSnex); senza quel carattere si usano simboli comuni
GLYPH_MINIMIZE, GLYPH_MAXIMIZE, GLYPH_RESTORE, GLYPH_CLOSE = "", "", "", ""


def window_buttons(win, master, on_close, minimize: bool = True, maximize: bool = True) -> ctk.CTkFrame:
    """Riduci / massimizza / chiudi disegnati nell'intestazione."""
    family = theme.icon_font()
    glyphs = (GLYPH_MINIMIZE, GLYPH_MAXIMIZE, GLYPH_CLOSE) if family else ("—", "□", "✕")
    restore = GLYPH_RESTORE if family else "❐"
    font = ctk.CTkFont(family=family or theme.ui_font(), size=10 if family else 13)
    box = ctk.CTkFrame(master, fg_color="transparent", corner_radius=0)
    items = []
    if minimize:
        items.append((glyphs[0], win.iconify, theme.HOVER))
    if maximize:
        items.append((glyphs[1], lambda: frameless.toggle_maximize(win), theme.HOVER))
    items.append((glyphs[2], on_close, theme.CLOSE_HOVER))
    buttons = []
    for glyph, command, hover in items:
        b = ctk.CTkButton(box, text=glyph, command=command, width=46, height=34, corner_radius=0,
                          fg_color="transparent", hover_color=hover, text_color=theme.TEXT_DIM, font=font)
        b.pack(side="left")
        buttons.append(b)
    if maximize:
        max_btn = buttons[1 if minimize else 0]

        def sync(event=None):
            if event is not None and event.widget is not win:
                return
            try:
                glyph = restore if win.state() == "zoomed" else glyphs[1]
                if max_btn.winfo_exists() and max_btn.cget("text") != glyph:
                    max_btn.configure(text=glyph)
            except tk.TclError:
                pass

        win.bind("<Configure>", sync, add="+")
    return box


def hide_until_ready(win) -> None:
    """La finestra resta trasparente finché la barra bianca di Windows non è stata tolta: così non si
    vede il lampo bianco all'apertura. apply_frameless la rende visibile appena è pronta."""
    if frameless.IS_WINDOWS and not getattr(win, "_frameless_done", False):
        try:
            win.attributes("-alpha", 0.0)
        except tk.TclError:
            pass


def _reveal(win) -> None:
    try:
        win.attributes("-alpha", 1.0)
    except tk.TclError:
        pass


def apply_frameless(win, tries: int = 60, on_ready=None) -> None:
    """Toglie la barra di Windows appena la finestra è sullo schermo (prima non ha la sua cornice),
    poi la rende visibile. Se non ci riesce entro 3 secondi la mostra comunque."""
    if not frameless.IS_WINDOWS:
        return
    try:
        if not win.winfo_exists():
            return
        if getattr(win, "_frameless_done", False):
            if on_ready:
                on_ready()
            _reveal(win)
            return
        if win.winfo_viewable() and frameless.toplevel_ready(win):
            frameless.make_frameless(win, border_color=theme.BORDER_STRONG)
            win._frameless_done = True
            if on_ready:
                on_ready()
            win.after(30, _reveal, win)      # un attimo per ridisegnare senza barra, poi visibile
            return
    except tk.TclError:
        return
    if tries > 0:
        win.after(50, apply_frameless, win, tries - 1, on_ready)
    else:
        _reveal(win)


def decorate(win, title: str, on_close=None, minimize: bool = True, maximize: bool = True,
             logo: bool = True) -> ctk.CTkFrame:
    """Intestazione del tema in cima alla finestra (va chiamata prima di aggiungere il contenuto)."""
    on_close = on_close or win.destroy
    hide_until_ready(win)
    win.title(title)
    win.configure(fg_color=theme.BG)
    bar = ctk.CTkFrame(win, fg_color=theme.BG, corner_radius=0, height=34)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)
    img = theme.logo(12) if logo else None
    drag = [bar]
    if img is not None:
        lbl = ctk.CTkLabel(bar, text="", image=img)
        lbl.pack(side="left", padx=(12, 0))
        drag.append(lbl)
    t = ctk.CTkLabel(bar, text=("   ·   " if img is not None else "   ") + title, font=(theme.ui_font(), 12, "bold"),
                     text_color=theme.TEXT_SOFT)
    t.pack(side="left")
    drag.append(t)
    window_buttons(win, bar, on_close, minimize, maximize).pack(side="right")
    theme.rule(win).pack(side="top", fill="x")
    if frameless.IS_WINDOWS:
        for w in drag:
            frameless.enable_drag(win, w)
    win.protocol("WM_DELETE_WINDOW", on_close)
    try:
        theme.set_icon(win)
    except tk.TclError:
        pass
    win.after(30, apply_frameless, win)
    return bar


# ===================================================================== avvisi e domande
_KIND = {"info": (theme.ACCENT, "i"), "warning": (theme.WARN, "!"), "error": (theme.ERR, "✕"),
         "question": (theme.ACCENT, "?")}


def _root(parent):
    if parent is not None:
        try:
            return parent.winfo_toplevel()
        except tk.TclError:
            pass
    return tk._default_root


def _dialog(title: str, message: str, kind: str, buttons: list[tuple[str, object, bool]], parent=None,
            default=None, cancel=None):
    """Finestra modale del tema: ritorna il valore del pulsante premuto (cancel se si chiude)."""
    master = _root(parent)
    win = ctk.CTkToplevel(master)
    win.withdraw()
    result = {"value": cancel}

    def close(value=cancel):
        result["value"] = value
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    decorate(win, title or "DocIndexer", on_close=lambda: close(cancel), minimize=False, maximize=False)
    win.resizable(False, False)
    try:
        win.transient(master)
    except tk.TclError:
        pass
    body = ctk.CTkFrame(win, fg_color=theme.PANEL, corner_radius=0)
    body.pack(fill="both", expand=True)
    color, sign = _KIND.get(kind, _KIND["info"])
    row = ctk.CTkFrame(body, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=(18, 10))
    badge = ctk.CTkLabel(row, text=sign, width=34, height=34, corner_radius=17, fg_color=color,
                         text_color=theme.BG, font=(theme.ui_font(), 16, "bold"))
    badge.pack(side="left", anchor="n", padx=(0, 14))
    ctk.CTkLabel(row, text=message, justify="left", anchor="w", wraplength=440, font=(theme.ui_font(), 13),
                 text_color=theme.TEXT).pack(side="left", fill="x", expand=True)
    btns = ctk.CTkFrame(body, fg_color="transparent")
    btns.pack(fill="x", padx=20, pady=(6, 18))
    focus = None
    for label, value, primary in reversed(buttons):
        b = ctk.CTkButton(btns, text=label, width=110, command=lambda v=value: close(v),
                          **({} if primary else {"fg_color": theme.NEUTRAL, "hover_color": theme.NEUTRAL_HOVER}))
        b.pack(side="right", padx=(8, 0))
        if value == default:
            focus = b
    win.bind("<Escape>", lambda e: close(cancel))
    win.bind("<Return>", lambda e: close(default))
    # position only: the dialog keeps the size its content asks for (logical units, any zoom)
    win.update_idletasks()
    s = theme.window_scaling(win)
    theme.place_window(win, max(420, win.winfo_reqwidth() / s), win.winfo_reqheight() / s, master=master,
                       size=False)
    win.deiconify()
    win.lift()
    win.attributes("-topmost", True)
    win.after(200, lambda: win.winfo_exists() and win.attributes("-topmost", False))
    try:
        win.grab_set()
    except tk.TclError:
        pass
    (focus or win).focus_force()
    master.wait_window(win)
    return result["value"]


def showinfo(title=None, message=None, parent=None, **_kw):
    _dialog(title, message, "info", [(tr("OK"), True, True)], parent, default=True, cancel=True)
    return "ok"


def showwarning(title=None, message=None, parent=None, **_kw):
    _dialog(title, message, "warning", [(tr("OK"), True, True)], parent, default=True, cancel=True)
    return "ok"


def showerror(title=None, message=None, parent=None, **_kw):
    _dialog(title, message, "error", [(tr("OK"), True, True)], parent, default=True, cancel=True)
    return "ok"


def askyesno(title=None, message=None, parent=None, icon=None, **_kw) -> bool:
    return bool(_dialog(title, message, "warning" if icon == "warning" else "question",
                        [(tr("Sì"), True, True), (tr("No"), False, False)], parent, default=True, cancel=False))


def askyesnocancel(title=None, message=None, parent=None, icon=None, **_kw):
    return _dialog(title, message, "warning" if icon == "warning" else "question",
                   [(tr("Sì"), True, True), (tr("No"), False, False), (tr("Annulla"), None, False)],
                   parent, default=True, cancel=None)
