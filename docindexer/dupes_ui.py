# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Scheda Duplicati: file identici (stesso contenuto) e documenti quasi uguali (testo simile)."""
from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from . import dupes, export, theme
from .i18n import tr


def _when(ts) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)) if ts else ""


def _size(n: int) -> str:
    n = n or 0
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


class DuplicatesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.rows: dict[str, dict] = {}
        self.export_rows: list[dict] = []
        self._stop = threading.Event()
        self._running = False
        ctk.CTkLabel(self, text=tr("Duplicati"), font=app.h1).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(self, text=tr("Identici: lo stesso file (stesso contenuto) in più cartelle. Simili: documenti con "
                                   "testo quasi uguale, per esempio versioni corrette, lo stesso testo in PDF e in Word "
                                   "o una scansione rifatta."),
                     text_color=theme.TEXT_DIM, wraplength=1100, justify="left", anchor="w").pack(
            anchor="w", fill="x", pady=(0, 10))
        theme.autowrap(self.pack_slaves()[-1], 1100)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        self.mode = tk.StringVar(value=tr("Identici"))
        ctk.CTkSegmentedButton(bar, values=[tr("Identici"), tr("Simili")], variable=self.mode,
                               command=lambda _v: self.find()).pack(side="left")
        ctk.CTkLabel(bar, text=tr("Somiglianza minima"), text_color=theme.TEXT_DIM).pack(side="left", padx=(16, 6))
        self.threshold = tk.StringVar(value=f"{dupes.DEFAULT_MIN}%")
        ctk.CTkSegmentedButton(bar, values=["97%", "93%", "90%", "85%", "80%"], variable=self.threshold,
                               command=lambda _v: self.mode.get() == tr("Simili") and self.find()).pack(side="left")
        ctk.CTkButton(bar, text=tr("Cerca duplicati"), width=150, command=self.find).pack(side="left", padx=(16, 0))
        btn = {"fg_color": theme.NEUTRAL, "hover_color": theme.NEUTRAL_HOVER}
        ctk.CTkButton(bar, text=tr("Esporta..."), width=110, command=self.export, **btn).pack(side="right")
        ctk.CTkButton(bar, text=tr("Mostra nella cartella"), width=170, command=self.reveal, **btn).pack(
            side="right", padx=6)
        ctk.CTkButton(bar, text=tr("Apri"), width=80, command=self.open, **btn).pack(side="right")
        self.status = ctk.CTkLabel(self, text=tr("Premi «Cerca duplicati»."), anchor="w", text_color=theme.TEXT_SOFT)
        self.status.pack(fill="x", pady=(0, 6))
        self.progress = ctk.CTkProgressBar(self, height=6)
        self.progress.set(0)

        frame = tk.Frame(self, bg=theme.BG)
        frame.pack(fill="both", expand=True)
        cols = (("folder", tr("Cartella"), 420), ("size", tr("Dimensione"), 90), ("date", tr("Modificato"), 130),
                ("sim", tr("Somiglianza"), 100))
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="tree headings", selectmode="browse")
        self.tree.heading("#0", text=tr("Nome"), anchor="w")
        # Treeview widths are physical pixels: scale the logical widths like the rest of the UI
        self.tree.column("#0", width=theme.px(self.tree, 380), anchor="w")
        for key, title, width in cols:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=theme.px(self.tree, width), anchor="w", stretch=key == "folder")
        sb = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("group", foreground=theme.ACCENT)
        self.tree.bind("<Double-1>", lambda e: self.open())
        from .gui import attach_tree_tooltip

        attach_tree_tooltip(self.tree, self._tooltip)

    # ------------------------------------------------------------- ricerca
    def min_similarity(self) -> int:
        return int(self.threshold.get().rstrip("%"))

    def find(self):
        if self._running or not self.app.ensure_db():
            return
        self._running = True
        self._stop.clear()
        similar = self.mode.get() == tr("Simili")
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        self.status.configure(text=tr("Ricerca dei duplicati in corso..."))
        self.progress.pack(fill="x", pady=(0, 6), before=self.tree.master)
        self.progress.set(0)
        db_path, min_sim = self.app.cfg.db_file, self.min_similarity()

        def work():
            from .db import Database

            db = Database(db_path)
            try:
                if similar:
                    db.fill_simhashes(self._stop)
                    groups = dupes.similar_groups(
                        db.simhashes(), db.text_of, min_sim, self._stop,
                        lambda f: self.app.call_in_gui(self.progress.set, f * 0.8))
                    # documenti con poco testo (niente impronta): confronto diretto
                    groups += dupes.short_groups(
                        db.short_texts(), min_sim, self._stop,
                        lambda f: self.app.call_in_gui(self.progress.set, 0.8 + f * 0.2))
                    by_sha = {}
                    for d in db.paths_of([s for g in groups for s, _d in g]):
                        by_sha.setdefault(d["sha256"], []).append(d)
                    out = []
                    for g in groups:
                        rows = []
                        for sha, dist in sorted(g, key=lambda x: -x[1]):
                            for d in by_sha.get(sha, []):
                                rows.append(dict(d, similarity=dist))
                        if len(rows) > 1:
                            out.append(rows)
                else:
                    out = db.duplicates_exact()
                self.app.call_in_gui(self._done, out, similar, None)
            except Exception as exc:  # noqa: BLE001
                self.app.call_in_gui(self._done, [], similar, exc)
            finally:
                db.close()

        threading.Thread(target=work, daemon=True).start()

    def _done(self, groups: list[list[dict]], similar: bool, exc):
        self._running = False
        self.progress.pack_forget()
        if exc:
            self.status.configure(text=tr("Errore: {exc}", exc=exc))
            return
        self.export_rows = []
        wasted = 0
        for n, rows in enumerate(groups, start=1):
            first = rows[0]
            if similar:
                label = tr("Gruppo {n}: {k} documenti simili", n=n, k=len(rows))
            else:
                label = tr("Gruppo {n}: {k} copie di «{name}»", n=n, k=len(rows), name=first["original_name"])
                wasted += (first["size_bytes"] or 0) * (len(rows) - 1)
            gid = self.tree.insert("", "end", text=label, open=True, tags=("group",),
                                   values=("", _size(sum(r["size_bytes"] or 0 for r in rows)), "", ""))
            for r in rows:
                lv = int(r.get("level") or 0)
                sim = f"{r['similarity']}%" if similar else "100%"
                # pallini colorati dell'importanza prima del nome (immagine: il testo di una cella è di un colore solo)
                iid = self.tree.insert(gid, "end", text=" " + r["original_name"], image=theme.level_image(lv, self.tree),
                                       values=(os.path.dirname(r["path"]), _size(r["size_bytes"]), _when(r["mtime"]),
                                               sim))
                self.rows[iid] = r
                self.export_rows.append(dict(r, group=n, similarity=sim))
        if not groups:
            self.status.configure(text=tr("Nessun duplicato trovato."))
        elif similar:
            self.status.configure(text=tr("Gruppi di documenti simili: {g} ({n} file)", g=len(groups),
                                          n=len(self.export_rows)))
        else:
            self.status.configure(text=tr("Gruppi di file identici: {g} ({n} file) · spazio occupato dalle copie in "
                                          "più: {mb}", g=len(groups), n=len(self.export_rows), mb=_size(wasted)))

    def _tooltip(self, iid, col):
        r = self.rows.get(iid)
        if not r:
            return None
        return r["path"] if col == "#0" else os.path.dirname(r["path"]) if col == "folder" else None

    # -------------------------------------------------------------- azioni
    def _current(self) -> dict | None:
        sel = self.tree.selection()
        return self.rows.get(sel[0]) if sel else None

    def open(self):
        from .gui import open_file

        r = self._current()
        if r:
            open_file(r["path"])

    def reveal(self):
        from .gui import reveal

        r = self._current()
        if r:
            reveal(r["path"])

    def export(self):
        from . import dialogs

        if not self.export_rows:
            dialogs.showinfo(tr("Esporta"), tr("Nessun risultato da esportare: cerca prima i duplicati."))
            return
        title = tr("Duplicati") + " - " + self.mode.get()
        export.ask_and_export(self, self.export_rows, kind="duplicates", title=title)
