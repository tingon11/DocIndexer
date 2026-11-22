# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Ricerca rapida: una barra di ricerca che si apre sopra qualsiasi programma con la scorciatoia
(predefinita Ctrl+Alt+D) o dal menu dell'icona.

Si cerca mentre si scrive (un risultato per file); se non c'è nulla si riprova tollerando un errore di
battitura o di OCR. Invio apre il file, Ctrl+Invio apre la ricerca completa in DocIndexer,
Alt+Invio mostra il file nella cartella, Esc chiude.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from . import searches, theme
from .dialogs import decorate
from .i18n import tr


class QuickSearch(ctk.CTkToplevel):
    _instance = None

    @classmethod
    def toggle(cls, app):
        """Apre la barra (o la riporta in primo piano); se è già in primo piano la chiude."""
        inst = cls._instance
        if inst is not None and inst.winfo_exists():
            try:
                if inst.focus_displayof() is not None:
                    inst.destroy()
                    return None
            except (tk.TclError, KeyError):
                pass
            inst.bring_up()
            return inst
        cls._instance = cls(app)
        return cls._instance

    def __init__(self, app):
        super().__init__(app)
        self.withdraw()
        self.app = app
        self._job = None
        self.rows: dict[str, dict] = {}
        decorate(self, tr("Ricerca rapida"), maximize=False, minimize=False)
        body = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        body.pack(fill="both", expand=True)
        self.var = tk.StringVar()
        self.entry = ctk.CTkEntry(body, textvariable=self.var, height=44, font=ctk.CTkFont(size=18),
                                  placeholder_text=tr("Cerca nei documenti..."))
        self.entry.pack(fill="x", padx=14, pady=(12, 6))
        self.info = ctk.CTkLabel(body, text=self._hint(), anchor="w", text_color=theme.TEXT_DIM,
                                 font=app.fonts.small)
        self.info.pack(fill="x", padx=16)
        frame = tk.Frame(body, bg=theme.PANEL)
        frame.pack(fill="both", expand=True, padx=14, pady=(6, 14))
        cols = (("name", tr("Nome"), 280), ("folder", tr("Cartella"), 300), ("page", tr("Pagina"), 90),
                ("date", tr("Modificato"), 130))
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="tree headings", selectmode="browse")
        self.tree.heading("#0", text=tr("Imp."), anchor="w")
        # Treeview widths are physical pixels: scale the logical widths like the rest of the UI
        self.tree.column("#0", width=theme.px(self.tree, 84), stretch=False)
        for key, title, width in cols:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=theme.px(self.tree, width), anchor="w", stretch=key in ("name", "folder"))
        sb = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        from .gui import attach_tree_tooltip

        attach_tree_tooltip(self.tree, self._tooltip)

        self.var.trace_add("write", lambda *_: self._schedule())
        for w in (self.entry, self.tree):
            w.bind("<Return>", lambda e: (self.open_file(), "break")[1])
            w.bind("<Control-Return>", lambda e: (self.open_in_app(), "break")[1])
            w.bind("<Alt-Return>", lambda e: (self.reveal(), "break")[1])
            w.bind("<Escape>", lambda e: self.destroy())
        self.entry.bind("<Down>", lambda e: (self._move(1), "break")[1])
        self.entry.bind("<Up>", lambda e: (self._move(-1), "break")[1])
        self.tree.bind("<Double-1>", lambda e: self.open_file())
        theme.place_window(self, 900, 520, y_frac=0.12)   # logical units, fits any screen/zoom
        self.bring_up()

    def _hint(self) -> str:
        return tr("Invio apre il file · Ctrl+Invio apre la ricerca in DocIndexer · Alt+Invio mostra nella cartella · "
                  "Esc chiude")

    def bring_up(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.after(80, lambda: self.winfo_exists() and (self.entry.focus_force(), self.entry.select_range(0, "end")))

    # ----------------------------------------------------------- ricerca
    def _schedule(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.search)

    def search(self):
        self._job = None
        q = self.var.get().strip()
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        if len(q) < 2:
            self.info.configure(text=self._hint(), text_color=theme.TEXT_DIM)
            return
        if not self.app.ensure_db(quiet=True):
            self.info.configure(text=tr("DB non connesso"), text_color=theme.ERR)
            return
        spec = {"query": q, "sources": ["text", "archive", "db"], "in_names": True}
        try:
            res = searches.run(self.app.db, spec, self.app.cfg.watch_dirs, limit=200, auto_fuzzy=True)
        except Exception:  # noqa: BLE001  ricerca a metà mentre si scrive (es. virgolette aperte)
            return
        seen = set()
        for r, _g in res.rows:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            page = r.get("label") or (str(r["page_no"]) if r.get("page_no") else "")
            lv = int(r.get("level") or 0)
            iid = self.tree.insert("", "end", image=theme.level_image(lv, self.tree),
                                   values=(r["original_name"], os.path.dirname(r["path"]), page, _when(r.get("mtime"))))
            self.rows[iid] = r
            if len(seen) >= 50:
                break
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
            self.tree.see(kids[0])
        if not kids:
            self.info.configure(text=tr("Nessun risultato"), text_color=theme.TEXT_DIM)
        elif res.fuzzy_used:
            self.info.configure(text=tr("Nessun risultato esatto: mostrati quelli con 1 errore di battitura o di OCR"),
                                text_color=theme.WARN)
        else:
            self.info.configure(text=tr("{n} file", n=len(kids)) + "   ·   " + self._hint(), text_color=theme.TEXT_DIM)

    def _tooltip(self, iid, col):
        r = self.rows.get(iid)
        if not r:
            return None
        return r["path"] if col == "name" else os.path.dirname(r["path"]) if col == "folder" else None

    def _move(self, delta: int):
        kids = self.tree.get_children()
        if not kids:
            return
        sel = self.tree.selection()
        i = kids.index(sel[0]) if sel else -1
        i = max(0, min(len(kids) - 1, i + delta))
        self.tree.selection_set(kids[i])
        self.tree.see(kids[i])

    def _current(self) -> dict | None:
        sel = self.tree.selection() or self.tree.get_children()[:1]
        return self.rows.get(sel[0]) if sel else None

    # ------------------------------------------------------------ azioni
    def open_file(self):
        from .gui import open_file

        r = self._current()
        if r:
            open_file(r["path"])
            self.destroy()

    def reveal(self):
        from .gui import reveal

        r = self._current()
        if r:
            reveal(r["path"])
            self.destroy()

    def open_in_app(self):
        q = self.var.get().strip()
        r = self._current()
        self.destroy()
        self.app.show_window()
        page = self.app.pages["search"]
        self.app.show("search")
        page.load_spec({"query": q, "sources": ["text", "archive", "db"], "in_names": True})
        page.search()
        if r:
            for iid, row in page.results.items():
                if row["id"] == r["id"]:
                    page.tree.selection_set(iid)
                    page.tree.see(iid)
                    page.on_select()
                    break


def _when(ts) -> str:
    import time

    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)) if ts else ""
