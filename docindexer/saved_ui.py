# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Finestre delle ricerche salvate: salvataggio (nome + avviso) ed elenco con i file nuovi."""
from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from . import dialogs as messagebox
from . import searches, theme
from .dialogs import decorate
from .i18n import tr


def _center(win, master, w, h):
    theme.place_window(win, w, h, master=master)   # logical units, fits any screen/zoom


class SaveSearchDialog(ctk.CTkToplevel):
    """Nome della ricerca e avviso sui file nuovi."""

    def __init__(self, page, app, spec: dict):
        super().__init__(app)
        self.withdraw()
        self.app, self.page, self.spec = app, page, spec
        decorate(self, tr("Salva ricerca"), minimize=False, maximize=False)
        self.resizable(False, False)
        self.transient(app)
        body = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        body.pack(fill="both", expand=True)
        ctk.CTkLabel(body, text=searches.describe(spec), wraplength=480, justify="left", anchor="w",
                     text_color=theme.TEXT_DIM).pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(body, text=tr("Nome"), anchor="w").pack(fill="x", padx=20)
        self.name = tk.StringVar(value=searches.suggest_name(spec))
        e = ctk.CTkEntry(body, textvariable=self.name, width=480)
        e.pack(fill="x", padx=20, pady=(2, 10))
        self.alert = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(body, text=tr("Avvisami quando nuovi file corrispondono a questa ricerca"),
                        variable=self.alert).pack(anchor="w", padx=20)
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=16)
        ctk.CTkButton(btns, text=tr("Salva"), width=110, command=self.ok).pack(side="right")
        ctk.CTkButton(btns, text=tr("Annulla"), width=110, fg_color=theme.NEUTRAL, hover_color=theme.NEUTRAL_HOVER,
                      command=self.destroy).pack(side="right", padx=8)
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        _center(self, app, 540, None)   # None = height the content asks for
        self.deiconify()
        self.after(50, lambda: (e.focus_set(), e.select_range(0, "end")))
        self.grab_set()

    def ok(self):
        item = self.app.saved.add(self.name.get(), self.spec, self.alert.get())
        self.destroy()
        if item["alert"]:
            self.app.check_saved(soon=True)     # i file già presenti diventano "già visti"
        self.page.update_saved_badge()
        SavedSearchesWindow.refresh_open(self.app)


class SavedSearchesWindow(ctk.CTkToplevel):
    """Elenco delle ricerche salvate: apri, mostra solo i nuovi, avviso sì/no, elimina."""

    _instance = None

    @classmethod
    def open(cls, app):
        if cls._instance is not None and cls._instance.winfo_exists():
            cls._instance.fill()
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
            return cls._instance
        cls._instance = cls(app)
        return cls._instance

    @classmethod
    def refresh_open(cls, app):
        if cls._instance is not None and cls._instance.winfo_exists():
            cls._instance.fill()

    def __init__(self, app):
        super().__init__(app)
        self.withdraw()
        self.app = app
        decorate(self, tr("Ricerche salvate"), maximize=False)
        self.transient(app)
        body = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        body.pack(fill="both", expand=True)
        ctk.CTkLabel(body, text=tr("Con l'avviso attivo DocIndexer ripete la ricerca quando indicizza file nuovi e "
                                   "ti avvisa vicino all'orologio se ne trova."),
                     text_color=theme.TEXT_DIM, wraplength=760, justify="left", anchor="w").pack(
            fill="x", padx=16, pady=(12, 6))
        self.list = ctk.CTkScrollableFrame(body, fg_color=theme.BG)
        self.list.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        bottom = ctk.CTkFrame(body, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(bottom, text=tr("Controlla adesso"), width=150, fg_color=theme.NEUTRAL,
                      hover_color=theme.NEUTRAL_HOVER, command=lambda: app.check_saved(soon=True)).pack(side="left")
        ctk.CTkButton(bottom, text=tr("Chiudi"), width=110, command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.fill()
        _center(self, app, 820, 520)
        self.deiconify()

    def fill(self):
        for w in self.list.winfo_children():
            w.destroy()
        items = self.app.saved.items
        if not items:
            ctk.CTkLabel(self.list, text=tr("Nessuna ricerca salvata. In Ricerca usa «Salva ricerca...»."),
                         text_color=theme.TEXT_DIM).pack(anchor="w", padx=10, pady=10)
            return
        for item in items:
            self._row(item)

    def _row(self, item: dict):
        f = self.app.fonts
        row = ctk.CTkFrame(self.list, fg_color=theme.PANEL, corner_radius=4, border_width=1,
                           border_color=theme.BORDER)
        row.pack(fill="x", pady=3, padx=2)
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=6)
        new = len(item.get("new") or [])
        title = item["name"] + (f"   ·   {new} " + tr("nuovi") if new else "")
        ctk.CTkLabel(left, text=title, font=f.bold, anchor="w",
                     text_color=theme.WARN if new else theme.TEXT).pack(fill="x")
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["checked"])) if item.get("checked") else "-"
        ctk.CTkLabel(left, text=searches.describe(item["spec"]) + "   ·   " + tr("ultimo controllo: {when}", when=when),
                     anchor="w", text_color=theme.TEXT_DIM, font=f.small).pack(fill="x")
        btn = {"height": 28, "fg_color": theme.NEUTRAL, "hover_color": theme.NEUTRAL_HOVER}
        ctk.CTkButton(row, text="✕", width=34, command=lambda: self.delete(item), **btn).pack(side="right",
                                                                                            padx=(4, 10))
        if new:
            ctk.CTkButton(row, text=tr("Solo i nuovi"), width=100,
                          command=lambda: self.run(item, True)).pack(side="right", padx=4)
        ctk.CTkButton(row, text=tr("Apri"), width=70, command=lambda: self.run(item, False)).pack(side="right", padx=4)
        alert = tk.BooleanVar(value=bool(item.get("alert")))
        ctk.CTkSwitch(row, text=tr("Avviso"), variable=alert, width=90,
                      command=lambda: self.toggle(item, alert.get())).pack(side="right", padx=8)

    def toggle(self, item, on: bool):
        self.app.saved.update(item["id"], alert=bool(on), seen=None if on else item.get("seen"), new=[])
        if on:
            self.app.check_saved(soon=True)
        self.app.pages["search"].update_saved_badge()
        self.fill()

    def delete(self, item):
        if messagebox.askyesno(tr("Ricerche salvate"), tr("Eliminare la ricerca salvata «{name}»?", name=item["name"]),
                               parent=self):
            self.app.saved.remove(item["id"])
            self.app.pages["search"].update_saved_badge()
            self.fill()

    def run(self, item, only_new: bool):
        self.app.show_window()
        self.app.pages["search"].run_saved(item, only_new)
        self.fill()
