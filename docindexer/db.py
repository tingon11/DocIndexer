# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Database SQLite portatile (singolo file) con ricerca full-text FTS5.

I file restano dove sono: il db ricorda solo dove si trovano e cosa contengono.

Tabelle:
  files              un record per contenuto distinto (hash SHA-256): tipo, stato dell'estrazione.
                     Lo stesso contenuto in più posti si estrae una sola volta
  paths              un record per file trovato nelle cartelle monitorate: percorso, dimensione,
                     data di modifica e hash (NULL finché non è stato calcolato)
  document_contents  il testo estratto (per pagina / foglio / tabella), compresso con zstd
  contents_fts       indice FTS5 "contentless": contiene solo l'indice, non una seconda copia del testo

Dimensione contenuta senza rallentare la ricerca:
  - il testo è salvato una volta sola, compresso (zstd), e si decomprime solo per i risultati mostrati
  - l'indice FTS5 non tiene il testo (content='', contentless_delete=1)
  - auto_vacuum incrementale: lo spazio liberato si restituisce al disco nei momenti di inattività
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import zstandard

from . import dupes, lang
from .textnorm import fold


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS files (
    sha256       TEXT    PRIMARY KEY,
    size_bytes   INTEGER NOT NULL,
    doc_type     TEXT,
    mime         TEXT,
    status       TEXT    NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','processing','done','error','skipped')),
    error        TEXT,
    page_count   INTEGER,
    ocr_pages    INTEGER NOT NULL DEFAULT 0,
    char_count   INTEGER,
    meta_done    INTEGER NOT NULL DEFAULT 0,   -- metadati (ExifTool) già letti per questo contenuto
    lang         TEXT,                         -- lingua del testo (it, en, ru...) o alfabeto (cyrillic...)
    simhash      INTEGER,                      -- impronta del testo per i quasi-duplicati (dupes.py)
    big          INTEGER NOT NULL DEFAULT 0,   -- file oltre il limite: 0 in attesa, 2 bloccato, 3 approvato
    extracted_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_files_status ON files(status);

CREATE TABLE IF NOT EXISTS paths (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    name        TEXT    NOT NULL,
    ext         TEXT    NOT NULL,
    size_bytes  INTEGER NOT NULL,
    mtime       REAL    NOT NULL,
    ctime       REAL,
    sha256      TEXT    REFERENCES files(sha256),   -- NULL = da (ri)calcolare
    error       TEXT,
    level       INTEGER NOT NULL DEFAULT 0,   -- importanza: 0 nessuna, 1 azzurro ... 5 rosso
    note        TEXT,                         -- nota dell'utente (resta se il file viene spostato o modificato)
    seen_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_paths_sha ON paths(sha256);
CREATE INDEX IF NOT EXISTS ix_paths_size ON paths(size_bytes, mtime);

CREATE TABLE IF NOT EXISTS document_contents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256       TEXT    NOT NULL REFERENCES files(sha256) ON DELETE CASCADE,
    page_no      INTEGER NOT NULL,
    label        TEXT,
    method       TEXT    NOT NULL,
    content      BLOB    NOT NULL,   -- testo compresso zstd
    ocr_boxes    BLOB                -- JSON compresso: [[parola, x0, y0, x1, y1], ...] coordinate 0..1
);
CREATE INDEX IF NOT EXISTS ix_contents_sha ON document_contents(sha256, page_no);

CREATE VIRTUAL TABLE IF NOT EXISTS contents_fts USING fts5(
    search_text,
    content='',
    contentless_delete=1,
    tokenize='unicode61 remove_diacritics 2'
);

-- tabelle dedicate ai moduli aggiuntivi, ognuna con il suo indice di ricerca
CREATE TABLE IF NOT EXISTS meta_items (            -- metadati letti da ExifTool
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256  TEXT NOT NULL REFERENCES files(sha256) ON DELETE CASCADE,
    tool    TEXT NOT NULL,
    tag     TEXT NOT NULL,        -- "Gruppo · Tag"
    value   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_meta_sha ON meta_items(sha256);
CREATE VIRTUAL TABLE IF NOT EXISTS meta_fts USING fts5(search_text, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');

CREATE TABLE IF NOT EXISTS archive_items (         -- testo dei file dentro gli archivi (7-Zip)
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256      TEXT NOT NULL REFERENCES files(sha256) ON DELETE CASCADE,
    inner_path  TEXT NOT NULL,    -- percorso del file dentro l'archivio
    page_no     INTEGER NOT NULL,
    label       TEXT,
    method      TEXT NOT NULL,
    content     BLOB NOT NULL     -- testo compresso zstd
);
CREATE INDEX IF NOT EXISTS ix_archive_sha ON archive_items(sha256);
CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(search_text, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');

CREATE TABLE IF NOT EXISTS db_items (              -- contenuto dei database (SQLite, DBF, Access)
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256      TEXT NOT NULL REFERENCES files(sha256) ON DELETE CASCADE,
    tool        TEXT NOT NULL,    -- sqlite | dbf | access
    table_name  TEXT NOT NULL,
    content     BLOB NOT NULL     -- testo compresso zstd: nomi delle colonne e righe
);
CREATE INDEX IF NOT EXISTS ix_db_sha ON db_items(sha256);
CREATE VIRTUAL TABLE IF NOT EXISTS db_fts USING fts5(search_text, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');

-- importance and note by content hash: they follow the file when it is moved or renamed, even if the
-- move is seen as delete + create (app closed, another disk, missed watcher event)
CREATE TABLE IF NOT EXISTS annotations (
    sha256      TEXT    PRIMARY KEY,
    level       INTEGER NOT NULL DEFAULT 0,
    note        TEXT,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- vocabolario dell'indice (per la ricerca fuzzy)
CREATE VIRTUAL TABLE IF NOT EXISTS contents_vocab USING fts5vocab(contents_fts, 'row');
"""

_ZC = zstandard.ZstdCompressor(level=9)
_ZD = zstandard.ZstdDecompressor()
_zlock = threading.Lock()   # gli oggetti zstd non sono thread-safe


def pack(text: str) -> bytes:
    with _zlock:
        return _ZC.compress(text.encode("utf-8"))


def unpack(blob) -> str:
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    with _zlock:
        return _ZD.decompress(blob).decode("utf-8")


# campi del documento restituiti da ricerche ed elenchi (un percorso + il suo contenuto)
_DOC_FIELDS = """p.id, p.path, p.name AS original_name, p.ext, p.size_bytes, p.mtime, p.ctime, p.seen_at,
                 p.level, p.note,
                 f.sha256, f.doc_type, f.status, f.error, f.page_count, f.ocr_pages, f.char_count, f.lang"""
_DOC_JOIN = "paths p JOIN files f ON f.sha256 = p.sha256"


def prepare_extraction(result) -> dict:
    """Tutto il lavoro di calcolo sul testo estratto (compressione, testo per l'indice, lingua, impronta dei
    quasi-duplicati), fatto nel processo che ha letto il file: al programma restano solo le scritture."""
    pages = result.pages
    body = "\n".join(p.text for p in pages) or "\n".join(a.text for a in result.archive)
    return {
        "doc_type": result.doc_type, "page_count": result.page_count, "ocr_pages": result.ocr_pages,
        "meta": [(tool, tag, value, fold(f"{tag} {value}")) for tool, tag, value in result.meta],
        "meta_read": result.meta_read,
        "archive": [(a.inner_path, a.page_no, a.label or None, a.method, pack(a.text),
                     fold(a.inner_path + "\n" + a.text)) for a in result.archive],
        "tables": [(t.tool, t.table, pack(t.text), fold(t.table + "\n" + t.text)) for t in result.tables],
        "pages": [(p.page_no, p.label or None, p.method, pack(p.text),
                   pack(json.dumps(p.boxes, ensure_ascii=False, separators=(",", ":"))) if p.boxes else None,
                   fold(p.text)) for p in pages],
        "chars": (sum(len(p.text) for p in pages) + sum(len(a.text) for a in result.archive)
                  + sum(len(t.text) for t in result.tables)),
        "lang": lang.detect(body), "simhash": dupes.simhash(body),
    }


class Database:
    """Una connessione SQLite per thread; WAL permette letture durante le scritture."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._all: list[sqlite3.Connection] = []      # connessioni di tutti i thread (per close_all)

    # ---------------------------------------------------------------- setup
    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.path.exists()
            c = sqlite3.connect(self.path, timeout=60, isolation_level=None, check_same_thread=False)
            c.row_factory = sqlite3.Row
            if new:
                c.execute("PRAGMA auto_vacuum=INCREMENTAL")   # va impostato prima della prima tabella
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA foreign_keys=ON")
            self._local.conn = c
            with self._write_lock:
                self._all.append(c)
        return c

    def initialize(self) -> None:
        # niente migrazioni: durante lo sviluppo, se lo schema cambia, si cancella il db e si reindicizza
        self.conn.executescript(SCHEMA)
        if not any(r[1] == "big" for r in self.conn.execute("PRAGMA table_info(files)")):
            with self.transaction() as c:      # db creato prima della sezione "File grandi"
                c.execute("ALTER TABLE files ADD COLUMN big INTEGER NOT NULL DEFAULT 0")
        # one-time migration: copy importance/notes already set on paths into the hash-keyed table
        if not self.conn.execute("SELECT 1 FROM meta WHERE key='annotations_v'").fetchone():
            with self.transaction() as c:
                c.execute("INSERT OR IGNORE INTO annotations (sha256, level, note)"
                          " SELECT sha256, MAX(level), MAX(note) FROM paths"
                          " WHERE sha256 IS NOT NULL AND (level > 0 OR note IS NOT NULL) GROUP BY sha256")
                c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('annotations_v', '1')")
        # file rimasti "processing" per un crash tornano in coda
        self.conn.execute("UPDATE files SET status='pending' WHERE status='processing'")
        # impronte dei quasi-duplicati calcolate in un modo vecchio: si ricalcolano quando servono
        row = self.conn.execute("SELECT value FROM meta WHERE key='simhash_v'").fetchone()
        if not row or row[0] != dupes.VERSION:
            with self.transaction() as c:
                c.execute("UPDATE files SET simhash=NULL")
                c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('simhash_v', ?)", (dupes.VERSION,))

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._write_lock:
            c = self.conn
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise

    def close(self) -> None:
        c = getattr(self._local, "conn", None)
        if c is not None:
            c.close()
            self._local.conn = None
            with self._write_lock:
                self._all = [x for x in self._all if x is not c]

    def close_all(self) -> None:
        """Chiude le connessioni di tutti i thread (prima di sostituire il file, es. ripristino di un backup)."""
        with self._write_lock:
            for c in self._all:
                try:
                    c.close()
                except sqlite3.Error:
                    pass
            self._all = []
        self._local = threading.local()

    # ------------------------------------------------------------ percorsi
    def known_paths(self) -> dict[str, tuple[int, float, str | None]]:
        """percorso (minuscolo) -> (dimensione, mtime, sha256) di tutti i file conosciuti."""
        return {r["path"].lower(): (r["size_bytes"], r["mtime"], r["sha256"])
                for r in self.conn.execute("SELECT path, size_bytes, mtime, sha256 FROM paths")}

    def all_paths(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT path FROM paths")]

    def upsert_paths(self, rows: list[tuple[str, int, float, float]]) -> int:
        """Aggiunge o aggiorna i percorsi (path, size, mtime, ctime). Se dimensione o data cambiano
        l'hash torna NULL: il file verrà ricalcolato (e rianalizzato solo se il contenuto è nuovo)."""
        if not rows:
            return 0
        with self.transaction() as c:
            n = 0
            for path, size, mtime, ctime in rows:
                p = Path(path)
                cur = c.execute(
                    "INSERT INTO paths (path, name, ext, size_bytes, mtime, ctime) VALUES (?,?,?,?,?,?)"
                    " ON CONFLICT(path) DO UPDATE SET"
                    " sha256=CASE WHEN paths.size_bytes=excluded.size_bytes AND paths.mtime=excluded.mtime"
                    "             THEN paths.sha256 ELSE NULL END,"
                    " error=CASE WHEN paths.size_bytes=excluded.size_bytes AND paths.mtime=excluded.mtime"
                    "             THEN paths.error ELSE NULL END,"
                    " size_bytes=excluded.size_bytes, mtime=excluded.mtime,"
                    " ctime=excluded.ctime, name=excluded.name, ext=excluded.ext,"
                    " seen_at=datetime('now','localtime')",
                    (str(p), p.name, p.suffix.lower(), size, mtime, ctime))
                n += cur.rowcount
            return n

    def remove_paths(self, paths: list[str]) -> int:
        """Dimentica i percorsi (file cancellati o non più da indicizzare). I contenuti rimasti senza
        percorso si eliminano con purge_orphans(), quando non ci sono hash in attesa (così un file
        spostato non viene rianalizzato)."""
        if not paths:
            return 0
        with self.transaction() as c:
            return sum(c.execute("DELETE FROM paths WHERE path=?", (p,)).rowcount for p in paths)

    def remove_under(self, folder: str) -> int:
        """Dimentica tutti i percorsi dentro una cartella (cartella cancellata o tolta dal monitoraggio)."""
        prefix = folder.rstrip("\\/") + os.sep
        with self.transaction() as c:
            return c.execute("DELETE FROM paths WHERE substr(lower(path), 1, ?) = lower(?)",
                             (len(prefix), prefix)).rowcount

    def move_path(self, old: str, new: str) -> bool:
        """Spostamento o rinomina: aggiorna il percorso senza rianalizzare il file."""
        p = Path(new)
        with self.transaction() as c:
            if c.execute("SELECT 1 FROM paths WHERE path=?", (old,)).fetchone() is None:
                return False
            if old.lower() != new.lower():
                c.execute("DELETE FROM paths WHERE path=?", (new,))
            c.execute("UPDATE paths SET path=?, name=?, ext=?, seen_at=datetime('now','localtime') WHERE path=?",
                      (str(p), p.name, p.suffix.lower(), old))
            return True

    def move_folder(self, old: str, new: str) -> int:
        """Cartella spostata o rinominata: aggiorna tutti i percorsi che contiene."""
        old_p, new_p = old.rstrip("\\/") + os.sep, new.rstrip("\\/") + os.sep
        rows = [r["path"] for r in self.conn.execute(
            "SELECT path FROM paths WHERE substr(lower(path), 1, ?) = lower(?)", (len(old_p), old_p))]
        return sum(self.move_path(path, new_p + path[len(old_p):]) for path in rows)

    def paths_to_hash(self, limit: int) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT id, path, size_bytes, mtime FROM paths WHERE sha256 IS NULL AND error IS NULL"
            " ORDER BY id LIMIT ?", (limit,))]

    def count_to_hash(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM paths WHERE sha256 IS NULL AND error IS NULL").fetchone()[0]

    def set_path_hash(self, path_id: int, sha256: str, size: int, doc_type: str, mime: str,
                      skip_reason: str | None = None) -> bool:
        """Collega il percorso al suo contenuto. Ritorna True se il contenuto è nuovo (da estrarre)."""
        with self.transaction() as c:
            cur = c.execute("INSERT OR IGNORE INTO files (sha256, size_bytes, doc_type, mime, status, error)"
                            " VALUES (?,?,?,?,?,?)",
                            (sha256, size, doc_type, mime, "skipped" if skip_reason else "pending", skip_reason))
            c.execute("UPDATE paths SET sha256=?, error=NULL WHERE id=?", (sha256, path_id))
            self._link_annotation(c, path_id, sha256)
            return cur.rowcount > 0

    @staticmethod
    def _link_annotation(c, path_id: int, sha256: str) -> None:
        """A path just got its hash. If that content already has an importance/note (file moved,
        renamed or copied), the path takes it; otherwise whatever the path already carries (file
        modified in place: new hash, same path) is saved under the new hash."""
        a = c.execute("SELECT level, note FROM annotations WHERE sha256=?", (sha256,)).fetchone()
        if a is not None:
            c.execute("UPDATE paths SET level=?, note=? WHERE id=?", (a["level"], a["note"], path_id))
            return
        p = c.execute("SELECT level, note FROM paths WHERE id=?", (path_id,)).fetchone()
        if p is not None and (p["level"] or p["note"]):
            c.execute("INSERT INTO annotations (sha256, level, note) VALUES (?,?,?)",
                      (sha256, p["level"], p["note"]))

    def set_path_error(self, path_id: int, message: str) -> None:
        with self.transaction() as c:
            c.execute("UPDATE paths SET error=? WHERE id=?", (message[:500], path_id))

    def find_moved(self, size: int, mtime: float, name: str) -> str | None:
        """Percorso di un file con stessa dimensione, data e nome che non esiste più (spostato)."""
        for r in self.conn.execute("SELECT path FROM paths WHERE size_bytes=? AND mtime=? AND name=? COLLATE NOCASE",
                                   (size, mtime, name)):
            if not os.path.exists(r["path"]):
                return r["path"]
        return None

    def purge_orphans(self) -> int:
        """Elimina i contenuti che non hanno più nessun percorso (con il loro testo e l'indice)."""
        with self.transaction() as c:
            orphans = [r[0] for r in c.execute(
                "SELECT sha256 FROM files WHERE sha256 NOT IN (SELECT sha256 FROM paths WHERE sha256 IS NOT NULL)")]
            for sha in orphans:
                self._delete_contents(c, sha)
                c.execute("DELETE FROM files WHERE sha256=?", (sha,))
            return len(orphans)

    @staticmethod
    def _delete_contents(c, sha256: str, sources=("text", "archive", "db", "meta")) -> None:
        for src in sources:
            table, fts = SOURCES[src]
            for (i,) in c.execute(f"SELECT id FROM {table} WHERE sha256=?", (sha256,)).fetchall():
                c.execute(f"DELETE FROM {fts} WHERE rowid=?", (i,))
            c.execute(f"DELETE FROM {table} WHERE sha256=?", (sha256,))

    # ------------------------------------------------------- estrazione
    def claim_pending(self, limit: int) -> list[dict]:
        with self.transaction() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT f.sha256, f.doc_type, f.big,"
                " (SELECT p.path FROM paths p WHERE p.sha256 = f.sha256 ORDER BY p.id LIMIT 1) AS path"
                " FROM files f WHERE f.status='pending'"
                " AND EXISTS (SELECT 1 FROM paths p WHERE p.sha256 = f.sha256)"     # non i contenuti senza più file
                " ORDER BY f.rowid LIMIT ?", (limit,))]
            rows = [r for r in rows if r["path"]]
            if rows:
                c.execute(f"UPDATE files SET status='processing' WHERE sha256 IN ({','.join('?' * len(rows))})",
                          [r["sha256"] for r in rows])
        return rows

    def unclaim(self, sha256: str) -> None:
        with self.transaction() as c:
            c.execute("UPDATE files SET status='pending' WHERE sha256=? AND status='processing'", (sha256,))

    def mark_skipped(self, sha256: str, reason: str) -> None:
        with self.transaction() as c:
            c.execute("UPDATE files SET status='skipped', error=? WHERE sha256=?", (reason[:500], sha256))

    def count_pending(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM files WHERE status IN ('pending','processing')").fetchone()[0]

    def save_extraction(self, sha256: str, result) -> None:
        """Salva il risultato dell'estrazione: testo (pagine), metadati, contenuto di archivi e database,
        ognuno nella sua tabella con il suo indice."""
        self.save_prepared(sha256, prepare_extraction(result))

    def save_prepared(self, sha256: str, d: dict) -> None:
        """Scrive nel db un risultato già preparato da prepare_extraction() (nel processo che ha letto il
        file): qui restano solo le scritture, che non tengono occupato l'interprete."""
        with self.transaction() as c:
            # "append": file letto a pezzi, le pagine sono già state scritte con append_pages()
            self._delete_contents(c, sha256, (() if d.get("append") else ("text", "archive", "db"))
                                  + (("meta",) if d["meta_read"] else ()))
            self._insert_meta(c, sha256, d["meta"])
            for inner_path, page_no, label, method, content, search in d["archive"]:
                rid = c.execute("INSERT INTO archive_items (sha256, inner_path, page_no, label, method, content)"
                                " VALUES (?,?,?,?,?,?)", (sha256, inner_path, page_no, label, method, content)).lastrowid
                c.execute("INSERT INTO archive_fts (rowid, search_text) VALUES (?,?)", (rid, search))
            for tool, table, content, search in d["tables"]:
                rid = c.execute("INSERT INTO db_items (sha256, tool, table_name, content) VALUES (?,?,?,?)",
                                (sha256, tool, table, content)).lastrowid
                c.execute("INSERT INTO db_fts (rowid, search_text) VALUES (?,?)", (rid, search))
            for page_no, label, method, content, boxes, search in d["pages"]:
                rid = c.execute(
                    "INSERT INTO document_contents (sha256, page_no, label, method, content, ocr_boxes)"
                    " VALUES (?,?,?,?,?,?)", (sha256, page_no, label, method, content, boxes)).lastrowid
                c.execute("INSERT INTO contents_fts (rowid, search_text) VALUES (?,?)", (rid, search))
            c.execute(
                "UPDATE files SET status='done', error=NULL, page_count=?, ocr_pages=?, char_count=?,"
                " doc_type=?, meta_done=CASE WHEN ? THEN 1 ELSE meta_done END, lang=?, simhash=?,"
                " extracted_at=datetime('now','localtime') WHERE sha256=?",
                (d["page_count"], d["ocr_pages"], d["chars"], d["doc_type"], int(d["meta_read"]),
                 d["lang"], d["simhash"], sha256),
            )

    @staticmethod
    def _insert_meta(c, sha256: str, items) -> None:
        for tool, tag, value, *search in items:
            rid = c.execute("INSERT INTO meta_items (sha256, tool, tag, value) VALUES (?,?,?,?)",
                            (sha256, tool, tag, value)).lastrowid
            c.execute("INSERT INTO meta_fts (rowid, search_text) VALUES (?,?)",
                      (rid, search[0] if search else fold(f"{tag} {value}")))

    def save_meta(self, sha256: str, items) -> None:
        """Solo i metadati (quando ExifTool viene attivato dopo l'estrazione del testo)."""
        with self.transaction() as c:
            self._delete_contents(c, sha256, ("meta",))
            self._insert_meta(c, sha256, items)
            c.execute("UPDATE files SET meta_done=1 WHERE sha256=?", (sha256,))

    def meta_todo(self, limit: int) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT f.sha256, (SELECT p.path FROM paths p WHERE p.sha256=f.sha256 ORDER BY p.id LIMIT 1) AS path"
            " FROM files f WHERE f.meta_done=0 AND f.status IN ('done','skipped','error') LIMIT ?", (limit,))]

    def requeue_skipped(self, doc_types: list[str], max_bytes: int = 1 << 62) -> int:
        """Moduli appena attivati: i file saltati di quei tipi tornano in coda (non quelli saltati perché
        troppo grandi: per quelli serve l'approvazione nella sezione "File grandi")."""
        if not doc_types:
            return 0
        with self.transaction() as c:
            return c.execute(f"UPDATE files SET status='pending', error=NULL WHERE status='skipped' AND doc_type IN"
                             f" ({','.join('?' * len(doc_types))}) AND (size_bytes <= ? OR big = 3)",
                             doc_types + [max_bytes]).rowcount

    # --------------------------------------------------------- file grandi
    def big_files(self, max_bytes: int) -> list[dict]:
        """File oltre il limite di dimensione non ancora approvati: in attesa (big=0) o bloccati (big=2)."""
        return [dict(r) for r in self.conn.execute(
            "SELECT f.sha256, f.size_bytes, f.big, p.path, p.name, p.mtime FROM files f"
            " JOIN paths p ON p.id = (SELECT MIN(id) FROM paths WHERE sha256 = f.sha256)"
            " WHERE f.size_bytes > ? AND f.big != 3 AND f.status = 'skipped' ORDER BY f.size_bytes DESC",
            (max_bytes,))]

    def set_big(self, sha256: str, state: int) -> None:
        """0 = in attesa, 2 = bloccato, 3 = approvato: va in coda come un file normale."""
        with self.transaction() as c:
            if state == 3:
                c.execute("UPDATE files SET big=3, status='pending', error=NULL WHERE sha256=?", (sha256,))
            else:
                c.execute("UPDATE files SET big=? WHERE sha256=?", (state, sha256))

    def begin_stream(self, sha256: str) -> None:
        """File letto a pezzi: si toglie il testo vecchio, le pagine arrivano con append_pages()."""
        with self.transaction() as c:
            self._delete_contents(c, sha256, ("text", "archive", "db"))

    def append_pages(self, sha256: str, pages: list) -> None:
        with self.transaction() as c:
            for page_no, label, method, content, boxes, search in pages:
                rid = c.execute(
                    "INSERT INTO document_contents (sha256, page_no, label, method, content, ocr_boxes)"
                    " VALUES (?,?,?,?,?,?)", (sha256, page_no, label, method, content, boxes)).lastrowid
                c.execute("INSERT INTO contents_fts (rowid, search_text) VALUES (?,?)", (rid, search))

    def mark_error(self, sha256: str, message: str) -> None:
        with self.transaction() as c:
            c.execute("UPDATE files SET status='error', error=?, extracted_at=datetime('now','localtime')"
                      " WHERE sha256=?", (message[:1000], sha256))

    def requeue_all(self) -> int:
        with self.transaction() as c:
            return c.execute("UPDATE files SET status='pending', error=NULL"
                             " WHERE status IN ('done','error')").rowcount

    def reset_errors(self) -> int:
        with self.transaction() as c:
            n = c.execute("UPDATE paths SET error=NULL WHERE error IS NOT NULL").rowcount
            return n + c.execute("UPDATE files SET status='pending', error=NULL WHERE status='error'").rowcount

    def stats(self) -> dict:
        """Conteggi per il monitor, per file trovati (percorsi). 'contents' = contenuti distinti indicizzati."""
        out = {"pending": 0, "processing": 0, "done": 0, "error": 0, "skipped": 0}
        for r in self.conn.execute(
                "SELECT CASE WHEN p.error IS NOT NULL THEN 'error' WHEN p.sha256 IS NULL THEN 'pending'"
                " ELSE f.status END AS st, COUNT(*) AS n"
                " FROM paths p LEFT JOIN files f ON f.sha256 = p.sha256 GROUP BY st"):
            out[r["st"]] = out.get(r["st"], 0) + r["n"]
        out["total"] = sum(out[k] for k in ("pending", "processing", "done", "error", "skipped"))
        out["contents"] = self.conn.execute("SELECT COUNT(*) FROM files WHERE status='done'").fetchone()[0]
        return out

    def db_size(self) -> int:
        size = 0
        for suffix in ("", "-wal"):
            try:
                size += os.path.getsize(str(self.path) + suffix)
            except OSError:
                pass
        return size

    def maintenance(self, pages: int = 2000) -> None:
        """Nei momenti di inattività: restituisce al disco lo spazio libero e compatta l'indice."""
        with self._write_lock:
            self.conn.execute(f"PRAGMA incremental_vacuum({int(pages)})")
            self.conn.execute("INSERT INTO contents_fts(contents_fts, rank) VALUES ('merge', 500)")
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # ------------------------------------------------------------ duplicati
    def duplicates_exact(self) -> list[list[dict]]:
        """Stesso contenuto (hash) in più percorsi: un gruppo per contenuto, i più pesanti per primi."""
        groups: dict[str, list[dict]] = {}
        for r in self.conn.execute(
                f"SELECT {_DOC_FIELDS} FROM {_DOC_JOIN} WHERE p.sha256 IN"
                " (SELECT sha256 FROM paths WHERE sha256 IS NOT NULL GROUP BY sha256 HAVING COUNT(*) > 1)"
                " ORDER BY p.size_bytes DESC, p.sha256, p.path"):
            groups.setdefault(r["sha256"], []).append(dict(r))
        return list(groups.values())

    def meta_text(self, sha256: str) -> str:
        """Tutti i metadati di un contenuto, una riga "Gruppo · Tag: valore" per voce."""
        return "\n".join(f"{r[0]}: {r[1]}" for r in self.conn.execute(
            "SELECT tag, value FROM meta_items WHERE sha256=? ORDER BY id", (sha256,)))

    def text_of(self, sha256: str) -> str:
        """Tutto il testo di un contenuto (pagine, oppure file dentro l'archivio)."""
        rows = self.conn.execute("SELECT content FROM document_contents WHERE sha256=? ORDER BY page_no",
                                 (sha256,)).fetchall()
        if not rows:
            rows = self.conn.execute("SELECT content FROM archive_items WHERE sha256=? ORDER BY id",
                                     (sha256,)).fetchall()
        return "\n".join(unpack(r[0]) for r in rows)

    def fill_simhashes(self, stop=None) -> int:
        """Calcola le impronte mancanti (documenti indicizzati prima di un cambio del metodo)."""
        todo = [r[0] for r in self.conn.execute(
            "SELECT sha256 FROM files WHERE status='done' AND simhash IS NULL AND char_count >= ?", (dupes.MIN_CHARS,))]
        done = 0
        for sha in todo:
            if stop is not None and stop.is_set():
                break
            h = dupes.simhash(self.text_of(sha))
            if h is not None:
                with self.transaction() as c:
                    c.execute("UPDATE files SET simhash=? WHERE sha256=?", (h, sha))
                done += 1
        return done

    def short_texts(self) -> list[tuple[str, str]]:
        """Contenuti indicizzati con poco testo (senza impronta): si confrontano direttamente."""
        shas = [r[0] for r in self.conn.execute(
            "SELECT sha256 FROM files WHERE status='done' AND simhash IS NULL AND char_count >= ?"
            " ORDER BY char_count LIMIT ?", (dupes.SHORT_MIN, dupes.SHORT_MAX_DOCS))]
        return [(s, self.text_of(s)) for s in shas]

    def simhashes(self) -> list[tuple[str, int]]:
        return [(r[0], r[1]) for r in self.conn.execute("SELECT sha256, simhash FROM files WHERE simhash IS NOT NULL")]

    def paths_of(self, shas: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(shas), 500):
            chunk = shas[i:i + 500]
            out += [dict(r) for r in self.conn.execute(
                f"SELECT {_DOC_FIELDS} FROM {_DOC_JOIN} WHERE p.sha256 IN ({','.join('?' * len(chunk))})", chunk)]
        return out

    def languages(self) -> list[tuple[str, int]]:
        """Lingue dei documenti indicizzati con il numero di file (per il filtro della ricerca)."""
        return [(r[0], r[1]) for r in self.conn.execute(
            "SELECT f.lang, COUNT(*) FROM paths p JOIN files f ON f.sha256 = p.sha256 WHERE f.lang IS NOT NULL"
            " GROUP BY f.lang ORDER BY COUNT(*) DESC")]

    def path_ids(self) -> set[int]:
        return {r[0] for r in self.conn.execute("SELECT id FROM paths")}

    # ------------------------------------------------------------ backup
    def backup_to(self, target: str | Path) -> None:
        """Copia coerente del database (anche mentre l'indicizzazione scrive), con l'API di backup di SQLite."""
        dst = sqlite3.connect(str(target))
        try:
            with self._write_lock:
                self.conn.backup(dst)
        finally:
            dst.close()

    # ------------------------------------------------------------ elenchi
    # ---------------------------------------------------------- note e importanza
    def set_annotation(self, path_id: int, level: int | None = None, note: str | None = None) -> None:
        """Importanza (0-5) e/o nota di un file. None = lascia com'è.
        The values belong to the content (hash): every copy of the same file gets them, and they come
        back when the file reappears elsewhere after a move or rename."""
        with self.transaction() as c:
            if level is not None:
                c.execute("UPDATE paths SET level=? WHERE id=?", (max(0, min(5, int(level))), path_id))
            if note is not None:
                c.execute("UPDATE paths SET note=? WHERE id=?", (note.strip() or None, path_id))
            r = c.execute("SELECT sha256, level, note FROM paths WHERE id=?", (path_id,)).fetchone()
            if r is None or r["sha256"] is None:
                return          # hash not computed yet: _link_annotation saves it when it is
            if r["level"] or r["note"]:
                c.execute("INSERT INTO annotations (sha256, level, note) VALUES (?,?,?)"
                          " ON CONFLICT(sha256) DO UPDATE SET level=excluded.level, note=excluded.note,"
                          " updated_at=datetime('now','localtime')", (r["sha256"], r["level"], r["note"]))
            else:
                c.execute("DELETE FROM annotations WHERE sha256=?", (r["sha256"],))
            c.execute("UPDATE paths SET level=?, note=? WHERE sha256=?", (r["level"], r["note"], r["sha256"]))

    def same_content_ids(self, path_id: int) -> list[int]:
        """Ids of all paths with the same content as path_id (path_id included)."""
        rows = self.conn.execute("SELECT q.id FROM paths p JOIN paths q ON q.sha256 = p.sha256"
                                 " WHERE p.id=?", (path_id,)).fetchall()
        return [r[0] for r in rows] or [path_id]

    def annotation(self, path_id: int) -> tuple[int, str]:
        r = self.conn.execute("SELECT level, note FROM paths WHERE id=?", (path_id,)).fetchone()
        return (r["level"], r["note"] or "") if r else (0, "")

    def list_documents(self, status: str | None = None, folder: str | None = None,
                       limit: int = 100000, important: bool = False) -> list[dict]:
        sql = f"SELECT {_DOC_FIELDS} FROM {_DOC_JOIN}"
        where, args = [], []
        if important:
            where.append("p.level > 0")
        if status:
            where.append("f.status=?")
            args.append(status)
        if folder:
            prefix = folder.rstrip("\\/") + os.sep
            where.append("substr(lower(p.path), 1, ?) = lower(?)")
            args += [len(prefix), prefix]
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY p.id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def get_ocr_boxes(self, sha256: str, page_no: int) -> list:
        row = self.conn.execute("SELECT ocr_boxes FROM document_contents WHERE sha256=? AND page_no=?",
                                (sha256, page_no)).fetchone()
        return json.loads(unpack(row["ocr_boxes"])) if row and row["ocr_boxes"] else []

    TEXT_CAP = 8_000_000      # caratteri caricati in una volta: i file enormi hanno migliaia di pagine

    def get_document_text(self, sha256: str, page_no: int | None = None) -> list[dict]:
        """Testo del documento, pagina per pagina (o solo la pagina chiesta). Per i file enormi ci si ferma
        dopo TEXT_CAP caratteri: caricarli tutti riempirebbe la memoria."""
        sql = "SELECT page_no, label, method, content FROM document_contents WHERE sha256=?"
        args: list = [sha256]
        if page_no is not None:
            sql += " AND page_no=?"
            args.append(page_no)
        out, total = [], 0
        for r in self.conn.execute(sql + " ORDER BY page_no", args):
            text = unpack(r["content"])
            out.append(dict(r, content=text))
            total += len(text)
            if total > self.TEXT_CAP:
                break
        return out

    # --------------------------------------------------------------- search
    @staticmethod
    def _folder_filter(folders: list[str] | None, important: bool = False,
                       filters: dict | None = None) -> tuple[str, list]:
        imp = " AND p.level > 0" if important else ""
        fargs: list = []
        f = filters or {}
        col = "p.ctime" if f.get("date_field") == "created" else "p.mtime"
        if f.get("date_from") is not None:
            imp += f" AND {col} >= ?"
            fargs.append(f["date_from"])
        if f.get("date_to") is not None:
            imp += f" AND {col} < ?"
            fargs.append(f["date_to"])
        if f.get("size_min") is not None:
            imp += " AND p.size_bytes >= ?"
            fargs.append(f["size_min"])
        if f.get("size_max") is not None:
            imp += " AND p.size_bytes <= ?"
            fargs.append(f["size_max"])
        if f.get("lang"):
            imp += " AND f.lang = ?"
            fargs.append(f["lang"])
        if not folders:
            return imp, fargs
        parts, args = [], []
        for f in folders:
            prefix = f.rstrip("\\/") + os.sep
            parts.append("substr(lower(p.path), 1, ?) = lower(?)")
            args += [len(prefix), prefix]
        return imp + " AND (" + " OR ".join(parts) + ")", fargs + args

    def search_names(self, line_patterns: list[list], folders: list[str] | None, limit: int = 300,
                     important: bool = False, filters: dict | None = None) -> list[dict]:
        """File il cui nome contiene tutte le parole di almeno una riga. Una riga per file, con la sua
        prima pagina (per l'anteprima)."""
        where, args = self._folder_filter(folders, important, filters)
        out = []
        for d in self.conn.execute(f"SELECT {_DOC_FIELDS} FROM {_DOC_JOIN} WHERE 1=1{where} ORDER BY p.id DESC",
                                   args):
            # nei nomi file "_", "-" e "." separano le parole
            name = re.sub(r"[_\-.]", " ", fold(d["original_name"]))
            if not any(pats and all(p.search(name) for p in pats) for pats in line_patterns):
                continue
            first = self.conn.execute(
                "SELECT page_no, label, method, content FROM document_contents WHERE sha256=?"
                " ORDER BY page_no LIMIT 1", (d["sha256"],)).fetchone()
            row = dict(d)
            row.update(page_no=first["page_no"] if first else 1, label=first["label"] if first else None,
                       method="nome file", content=unpack(first["content"]) if first else "",
                       snippet=d["original_name"], score=0.0)
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def vocabulary(self) -> list[str]:
        """Tutte le parole indicizzate (normalizzate), per trovare le varianti della ricerca fuzzy.
        Resta in memoria finché l'indice non cambia."""
        key = self.conn.execute("SELECT COUNT(*), MAX(id) FROM document_contents").fetchone()
        key = (key[0], key[1])
        if getattr(self, "_vocab_key", None) != key:
            self._vocab = [r[0] for r in self.conn.execute("SELECT term FROM contents_vocab")]
            self._vocab_key = key
        return self._vocab

    def search_fts(self, match: str, folders: list[str] | None = None, limit: int = 500,
                   important: bool = False, filters: dict | None = None,
                   sources=("text",)) -> list[dict]:
        """Esegue una query FTS5 già pronta (vedi query.build) nelle fonti scelte: testo dei documenti,
        metadati, contenuto degli archivi, contenuto dei database. Un risultato per pagina/voce e per file."""
        if not match:
            return []
        where, args = self._folder_filter(folders, important, filters)
        out = []
        for src in sources:
            table, fts = SOURCES[src]
            sql = f"""
                SELECT {_DOC_FIELDS}, {_SOURCE_COLUMNS[src]}, '{src}' AS source,
                       NULL AS snippet, -hits.score AS score
                FROM (SELECT rowid, bm25({fts}) AS score FROM {fts}
                      WHERE {fts} MATCH ? ORDER BY bm25({fts}) LIMIT ?) AS hits
                JOIN {table} c ON c.id = hits.rowid
                JOIN paths p ON p.sha256 = c.sha256
                JOIN files f ON f.sha256 = c.sha256
                WHERE 1=1{where}
                ORDER BY hits.score
                LIMIT ?
            """
            out += [dict(r, content=unpack(r["content"]))
                    for r in self.conn.execute(sql, [match, limit * 4] + args + [limit])]
        out.sort(key=lambda d: -d["score"])
        return out[:limit]

    def iter_regex(self, pattern: str, folders: list[str] | None = None, limit: int = 500,
                   stop: threading.Event | None = None, important: bool = False,
                   filters: dict | None = None, sources=("text",)):
        """Ricerca con espressione regolare sul testo (senza distinzione maiuscole/minuscole): genera un
        risultato per volta, così chi chiama può mostrarli man mano e fermarsi quando vuole.
        Il testo è compresso: si scorrono le pagine una per volta decomprimendole.
        Ogni risultato ha in 'matches' i testi trovati (per evidenziarli)."""
        rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        where, args = self._folder_filter(folders, important, filters)
        rows = []
        for src in sources:
            table, _fts = SOURCES[src]
            sql = (f"SELECT {_DOC_FIELDS}, {_SOURCE_COLUMNS[src]}, '{src}' AS source, NULL AS snippet,"
                   f" 0.0 AS score FROM {table} c JOIN files f ON f.sha256 = c.sha256"
                   f" JOIN paths p ON p.sha256 = c.sha256 WHERE 1=1{where} ORDER BY p.id DESC")
            rows.append(self.conn.execute(sql, args))
        import itertools

        n = 0
        for r in itertools.chain(*rows):
            if stop is not None and stop.is_set():
                break
            text = unpack(r["content"])
            hits = [m for m in rx.finditer(text) if m.group(0)]
            if not hits:
                continue
            found = [m.group(0) for m in hits]
            d = dict(r)
            d["content"] = text
            # estratto intorno alla prima occorrenza, già pronto: calcolarlo dopo nella finestra (cercando
            # di nuovo fino a 50 testi in ogni pagina di 500 risultati) la teneva ferma per molti secondi
            d["first"] = hits[0].start()      # per mostrare il testo a partire da lì se è lunghissimo
            start = max(0, hits[0].start() - 50)
            d["snippet"] = ("…" if start else "") + text[start:start + 300] + "…"
            d["score"] = float(len(found))
            d["matches"] = sorted(set(found), key=len, reverse=True)[:50]
            yield d
            n += 1
            if n >= limit:
                break

    def search_regex(self, pattern: str, folders: list[str] | None = None, limit: int = 500,
                     stop: threading.Event | None = None, important: bool = False,
                     filters: dict | None = None, sources=("text",)) -> list[dict]:
        """Tutti i risultati di iter_regex, dal più ricco di occorrenze."""
        out = list(self.iter_regex(pattern, folders, limit, stop, important, filters, sources))
        out.sort(key=lambda d: -d["score"])
        return out


# fonti di ricerca: tabella del contenuto e il suo indice FTS5
SOURCES = {
    "text": ("document_contents", "contents_fts"),
    "meta": ("meta_items", "meta_fts"),
    "archive": ("archive_items", "archive_fts"),
    "db": ("db_items", "db_fts"),
}
# colonne comuni dei risultati (page_no, label, method, content) per ogni fonte
_SOURCE_COLUMNS = {
    "text": "c.page_no, c.label, c.method, c.content",
    "meta": "0 AS page_no, c.tool || ' · ' || c.tag AS label, 'meta' AS method, c.tag || ': ' || c.value AS content",
    "archive": "c.page_no, c.inner_path || CASE WHEN c.label IS NOT NULL THEN ' · ' || c.label ELSE '' END AS label,"
               " c.method, c.content",
    "db": "1 AS page_no, c.tool || ' · ' || c.table_name AS label, 'table' AS method, c.content",
}

_FTS_OPERATORS = {"AND", "OR", "NOT", "NEAR"}


def _fold_query(line: str) -> str:
    """Normalizza le parole della ricerca come il testo indicizzato, lasciando intatti gli operatori."""
    return re.sub(r"\w+", lambda m: m.group(0) if m.group(0) in _FTS_OPERATORS else fold(m.group(0)), line)


def to_fts_query(text: str, advanced: bool = False, exact: bool = False) -> str:
    """exact=True: parole intere (senza il * del prefisso)."""
    star = "" if exact else "*"
    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if advanced:
            parts.append(f"({_fold_query(line)})")
        else:
            items = []
            for phrase, word in re.findall(r'"([^"]*)"|(\w+)', line):
                words = re.findall(r"\w+", phrase) if phrase else [word]
                if words and any(words):
                    items.append('"' + " ".join(fold(w) for w in words) + '"' + star)
            if items:
                parts.append("(" + " ".join(items) + ")")
    return " OR ".join(parts)
