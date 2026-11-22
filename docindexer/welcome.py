# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Finestra della prima apertura: lingua e termini d'uso (come in DroidSnex).

Passo 1, solo se i termini non sono mai stati accettati: scelta della lingua.
Passo 2: termini d'uso / esclusione di responsabilità (terms.py) nella lingua scelta. "Accetto" si
attiva dopo aver fatto scorrere il testo fino in fondo e salva in config.json la versione dei
termini, la data e la lingua; "Rifiuto" (o la chiusura della finestra) chiude il programma.
Quando TERMS_VERSION cambia, i termini vengono richiesti di nuovo (senza ripetere la lingua).

    welcome.needed(cfg)                                   # True se vanno mostrati all'avvio
    welcome.run(app, cfg, on_accept, on_reject)           # all'avvio, finestra principale nascosta
    welcome.show_terms(app)                               # sola lettura, dal pulsante "Termini d'uso"
"""
from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from . import __version__, terms, theme
from .dialogs import decorate
from .i18n import LANGUAGES, set_language

WIDTH, HEIGHT = 780, 580


def needed(cfg) -> bool:
    return getattr(cfg, "terms_accepted", "") != terms.TERMS_VERSION


class WelcomeWindow(ctk.CTkToplevel):
    def __init__(self, root, cfg, need_language: bool, on_accept=None, on_reject=None, read_only: bool = False):
        super().__init__(root, fg_color=theme.BG)
        self.withdraw()
        self.cfg = cfg
        self.on_accept, self.on_reject = on_accept, on_reject
        self.read_only = read_only
        self.lang = (getattr(cfg, "language", "") or "it") if cfg is not None else "it"
        self.fonts = theme.Fonts()
        self._accept_ready = False
        self._closed = False
        decorate(self, "DocIndexer", on_close=self._close if read_only else self._reject,
                 minimize=False, maximize=False, logo=False)
        self.resizable(False, False)
        self.bind("<Escape>", lambda _e: self._close() if read_only else None)
        self.body = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        self.body.pack(fill="both", expand=True)
        if need_language and not read_only:
            self._build_language()
        else:
            self._build_terms()
        self._place()
        self.deiconify()
        self.after(60, self._raise)

    # ---------------------------------------------------------------- finestra
    def _place(self) -> None:
        # logical units, centered, never larger than the screen at any zoom
        theme.place_window(self, WIDTH, HEIGHT)

    def _raise(self) -> None:
        """Davanti a tutto e modale: chi apre il programma deve rispondere prima di proseguire."""
        if self._closed or not self.winfo_exists():
            return
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            self.grab_set()
            self.after(400, lambda: self.winfo_exists() and self.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    # ---------------------------------------------------------------- passo 1: lingua
    def _build_language(self) -> None:
        self._clear()
        box = ctk.CTkFrame(self.body, fg_color="transparent")
        box.place(relx=0.5, rely=0.5, anchor="center")
        logo = theme.logo(22)
        if logo is not None:
            ctk.CTkLabel(box, text="", image=logo).pack(pady=(0, 6))
        ctk.CTkLabel(box, text=f"v{__version__}", font=self.fonts.tiny, text_color=theme.TEXT_DIM).pack(pady=(0, 22))
        # "Scegli la lingua" in tutte le lingue: chi apre il programma non ha ancora scelto
        codes = list(LANGUAGES)
        ctk.CTkLabel(box, text="  ·  ".join(terms.labels(c)[3] for c in codes[:4]),
                     font=self.fonts.bold, text_color=theme.TEXT).pack(pady=(0, 2))
        ctk.CTkLabel(box, text="  ·  ".join(terms.labels(c)[3] for c in codes[4:]),
                     font=self.fonts.small, text_color=theme.TEXT_DIM).pack(pady=(0, 18))
        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack()
        for i, (code, name) in enumerate(LANGUAGES.items()):
            ctk.CTkButton(grid, text=name, width=160, height=40, corner_radius=4, font=self.fonts.body,
                          fg_color=theme.PANEL_3, hover_color=theme.ACCENT_DIM, text_color=theme.TEXT,
                          border_width=1, border_color=theme.BORDER_STRONG,
                          command=lambda c=code: self._pick_language(c)).grid(row=i // 4, column=i % 4, padx=6, pady=6)

    def _pick_language(self, code: str) -> None:
        self.lang = code
        set_language(code)
        self._build_terms()

    # ---------------------------------------------------------------- passo 2: termini
    def _build_terms(self) -> None:
        self._clear()
        title, ok, no, _lang, note = terms.labels(self.lang)
        self.title(f"DocIndexer · {title}")
        ctk.CTkLabel(self.body, text=title.upper(), font=self.fonts.caption, text_color=theme.ACCENT,
                     anchor="w").pack(fill="x", padx=20, pady=(14, 6))
        self.text = ctk.CTkTextbox(self.body, fg_color=theme.BG, text_color=theme.TEXT, font=self.fonts.body,
                                   wrap="word", border_width=1, border_color=theme.BORDER, corner_radius=4,
                                   scrollbar_button_color=theme.BORDER_STRONG,
                                   scrollbar_button_hover_color=theme.ACCENT_DIM)
        self.text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.text.insert("1.0", terms.text(self.lang))
        self.text.configure(state="disabled")
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))
        if self.read_only:
            ctk.CTkButton(row, text="OK", width=120, command=self._close).pack(side="right")
            ctk.CTkLabel(row, text=f"v{terms.TERMS_VERSION} · {terms.TERMS_DATE}", font=self.fonts.small,
                         text_color=theme.TEXT_DIM).pack(side="left")
            return
        self.btn_ok = ctk.CTkButton(row, text=ok, width=130, command=self._accept)
        self.btn_ok.pack(side="right")
        self.btn_ok.configure(state="disabled")
        ctk.CTkButton(row, text=no, width=130, command=self._reject, **theme.DANGER_STYLE
                      ).pack(side="right", padx=(0, 10))
        self.note = ctk.CTkLabel(row, text=note, font=self.fonts.small, text_color=theme.TEXT_DIM, anchor="w",
                                 justify="left", wraplength=420)
        self.note.pack(side="left", fill="x", expand=True)
        self.after(300, self._watch_scroll)

    def _watch_scroll(self) -> None:
        """"Accetto" si attiva solo quando il testo è stato fatto scorrere fino in fondo."""
        if self._closed or self._accept_ready or not self.winfo_exists():
            return
        try:
            _top, bottom = self.text.yview()
        except tk.TclError:
            return
        if bottom >= 0.999:
            self._accept_ready = True
            self.btn_ok.configure(state="normal")
            self.note.configure(text_color=theme.OK)
            return
        self.after(250, self._watch_scroll)

    # ---------------------------------------------------------------- risposta
    def _accept(self) -> None:
        if not self._accept_ready:
            return
        if self.cfg is not None:
            self.cfg.terms_accepted = terms.TERMS_VERSION
            self.cfg.terms_accepted_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self.cfg.language = self.lang
        self._close()
        if self.on_accept:
            self.on_accept()

    def _reject(self) -> None:
        self._close()
        if self.on_reject:
            self.on_reject()

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


def run(app, cfg, on_accept, on_reject) -> WelcomeWindow:
    """All'avvio: lingua (solo se i termini non sono mai stati accettati) e termini."""
    return WelcomeWindow(app, cfg, not getattr(cfg, "terms_accepted", ""), on_accept, on_reject)


def show_terms(app) -> WelcomeWindow:
    """Solo lettura, nella lingua corrente."""
    from .i18n import language

    class _Cfg:
        pass
    cfg = _Cfg()
    cfg.language = language()
    return WelcomeWindow(app, cfg, False, read_only=True)
