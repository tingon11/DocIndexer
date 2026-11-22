# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Portable mode: the program folder on an external drive, together with the folders it indexes.

config.json and the database already live beside the program (config.DATA_DIR), so the whole
folder can be carried around. What breaks is the drive letter: a disk that was E: on one PC can
be F: on another, while config.json, saved_searches.json and the database store absolute paths
(E:\\Docs\\a.pdf). Results, "open file" and previews would then point to a missing drive.

At startup relocate() compares the drive the program runs from with the one recorded last time
(AppConfig.app_drive). When it changed, the monitored folders that were on the old drive are not
reachable there any more and are found under the new letter, every stored path on the old drive
is rewritten to the new one (config, saved searches, database), before the indexer starts.
Folders on other drives (e.g. C:) are left as they are.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

from .config import DATA_DIR, AppConfig

SAVED_SEARCHES = DATA_DIR / "saved_searches.json"


def drive_of(path: str | os.PathLike) -> str:
    """Drive letter of a path, upper case with the colon ("E:"); "" for UNC paths or other systems."""
    d = os.path.splitdrive(os.fspath(path))[0]
    return d.upper() if len(d) == 2 and d[1] == ":" else ""


def app_drive() -> str:
    return drive_of(DATA_DIR.resolve()) if sys.platform == "win32" else ""


def _swap(path: str, old: str, new: str) -> str:
    return new + path[2:] if drive_of(path) == old else path


def _must_move(cfg: AppConfig, old: str, new: str) -> bool:
    """The drive really changed letter: the folders on the old drive are gone, and are on the new one."""
    on_old = [d for d in cfg.watch_dirs if drive_of(d) == old]
    if not on_old:
        return False
    if any(os.path.isdir(d) for d in on_old):
        return False       # the old letter is still valid (e.g. program copied to another disk)
    return any(os.path.isdir(_swap(d, old, new)) for d in on_old)


def _move_db(db_file, old: str, new: str) -> int:
    """Rewrites the paths of the database from drive old to drive new. Returns the number of paths moved."""
    if not os.path.exists(db_file):
        return 0
    c = sqlite3.connect(str(db_file), timeout=60, isolation_level=None)
    try:
        c.execute("BEGIN IMMEDIATE")
        try:
            # UPDATE OR IGNORE: a path already present with the new letter keeps its row (unique index);
            # the leftover copy with the old letter is stale and removed
            n = c.execute("UPDATE OR IGNORE paths SET path = ? || substr(path, 3)"
                          " WHERE upper(substr(path, 1, 2)) = ?", (new, old)).rowcount
            c.execute("DELETE FROM paths WHERE upper(substr(path, 1, 2)) = ?", (old,))
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
    finally:
        c.close()
    return n


def _move_saved_searches(old: str, new: str) -> None:
    """Folder filters of the saved searches (they must match the monitored folders exactly)."""
    if not SAVED_SEARCHES.exists():
        return
    try:
        data = json.loads(SAVED_SEARCHES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    changed = False
    for item in data if isinstance(data, list) else []:
        spec = item.get("spec") if isinstance(item, dict) else None
        if isinstance(spec, dict) and isinstance(spec.get("folders"), list):
            moved = [_swap(f, old, new) if isinstance(f, str) else f for f in spec["folders"]]
            if moved != spec["folders"]:
                spec["folders"], changed = moved, True
    if changed:
        tmp = SAVED_SEARCHES.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(SAVED_SEARCHES)


def relocate(cfg: AppConfig) -> tuple[str, str, int] | None:
    """Call right after AppConfig.load(), before opening the database or starting the indexer.
    Returns (old drive, new drive, paths moved) when the drive letter changed, otherwise None."""
    new = app_drive()
    if not new:
        return None
    old = (cfg.app_drive or "").upper()
    if old == new:
        return None
    # first start with portable support (no drive recorded yet): the old drive is guessed from the
    # monitored folders, so an index built with an older version on E: still moves to F:
    candidates = [old] if old else sorted({drive_of(d) for d in cfg.watch_dirs} - {new, ""})
    old = next((d for d in candidates if _must_move(cfg, d, new)), "")
    if not old:
        cfg.app_drive = new          # first start, or the program moved to another disk on its own
        cfg.save()
        return None
    db_old = cfg.db_file
    db_new = _swap(str(db_old), old, new)          # db_path is relative by default; absolute on the old drive too
    try:
        n = _move_db(db_new if os.path.exists(db_new) else db_old, old, new)
    except sqlite3.Error:
        return None                  # database busy or damaged: config untouched, retried at next start
    _move_saved_searches(old, new)
    cfg.watch_dirs = [_swap(d, old, new) for d in cfg.watch_dirs]
    cfg.exclude_paths = [_swap(d, old, new) for d in cfg.exclude_paths]
    if os.path.isabs(cfg.db_path):
        cfg.db_path = _swap(cfg.db_path, old, new)
    cfg.app_drive = new
    cfg.save()
    return old, new, n
