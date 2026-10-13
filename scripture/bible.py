"""Translations on disk, and reading passages and searching words in them.

Each translation is one SQLite file in the data folder. The two that ship
with the plugin are gzipped tables under bibles/ and are turned into SQLite
the first time they are opened, which takes about a second. An imported
translation is written straight to SQLite. Nothing is loaded into memory
beyond what a query returns, so a Raspberry Pi holds a dozen translations
as easily as one.
"""
import gzip
import json
import os
import re
import sqlite3
import threading

from . import books
from .refparse import RefError

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS verses (book INTEGER, chapter INTEGER, verse INTEGER, text TEXT,
                                   PRIMARY KEY (book, chapter, verse));
"""


def slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return value[:32] or "bible"


class Translation:
    def __init__(self, path, meta):
        self.path = path
        self.meta = meta
        self.id = meta["id"]
        self._local = threading.local()

    def _db(self):
        db = getattr(self._local, "db", None)
        if db is None:
            db = sqlite3.connect(self.path, check_same_thread=False)
            self._local.db = db
        return db

    def close(self):
        db = getattr(self._local, "db", None)
        if db is not None:
            db.close()
            self._local.db = None

    def last_verse(self, book, chapter):
        row = self._db().execute("SELECT MAX(verse) FROM verses WHERE book=? AND chapter=?",
                                 (book, chapter)).fetchone()
        return row[0] if row and row[0] else 0

    def has_book(self, book):
        return self._db().execute("SELECT 1 FROM verses WHERE book=? LIMIT 1", (book,)).fetchone() is not None

    def passage(self, ref):
        """Every verse a Reference names, as (book, chapter, verse, text)."""
        book = ref.book.number
        if not self.has_book(book):
            raise RefError("%s has no %s. It may be a New Testament only, or the import "
                           "missed that book." % (self.meta.get("name", self.id), ref.book.name),
                           translation=self.id, book=ref.book.name)
        rows = []
        for seg in ref.segments:
            v1 = seg.v1 or 1
            last = self.last_verse(book, seg.c2)
            v2 = seg.v2 if seg.v2 is not None else last
            if last == 0:
                raise RefError("%s has no chapter %d in %s." % (ref.book.name, seg.c2, self.id.upper()))
            if seg.v1 is not None and seg.c1 == seg.c2 and seg.v1 > last:
                raise RefError("%s %d has %d verses, so there is no verse %d. Pick 1 to %d." % (
                    ref.book.name, seg.c1, last, seg.v1, last),
                    book=ref.book.name, chapter=seg.c1, verses=last)
            v2 = min(v2, last)
            found = self._db().execute(
                "SELECT book, chapter, verse, text FROM verses WHERE book=? AND "
                "(chapter, verse) >= (?, ?) AND (chapter, verse) <= (?, ?) ORDER BY chapter, verse",
                (book, seg.c1, v1, seg.c2, v2)).fetchall()
            rows.extend(found)
        if not rows:
            raise RefError("%s is not in %s." % (ref.display(), self.id.upper()))
        return rows

    def search(self, query, limit=50):
        """Verses holding every word of the query, phrase matches first."""
        words = [w for w in re.findall(r"[\w']+", query.lower()) if len(w) > 1 or w.isdigit()]
        if not words:
            return []
        sql = "SELECT book, chapter, verse, text FROM verses WHERE " + " AND ".join(
            ["text LIKE ?"] * len(words)) + " ORDER BY book, chapter, verse LIMIT 2000"
        found = self._db().execute(sql, ["%" + w + "%" for w in words]).fetchall()
        phrase = " ".join(words)
        bounded = [re.compile(r"\b" + re.escape(w) + r"\b") for w in words]

        def score(row):
            low = row[3].lower()
            whole = sum(1 for b in bounded if b.search(low))
            return (phrase in low, whole)

        ranked = sorted(found, key=lambda r: score(r), reverse=True)
        ranked = [r for r in ranked if score(r)[1] == len(words)] or ranked
        return ranked[:limit]


class Library:
    """Every translation: the bundled ones and the ones an operator imported."""

    def __init__(self, bundled_dir, data_dir):
        self.bundled_dir = bundled_dir
        self.dir = os.path.join(data_dir, "bibles")
        os.makedirs(self.dir, exist_ok=True)
        self._open = {}
        self._lock = threading.Lock()

    # --- what there is ------------------------------------------------------

    def bundled(self):
        path = os.path.join(self.bundled_dir, "sources.json")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)["translations"]

    def list(self):
        out = []
        for meta in self.bundled():
            out.append(dict(meta, bundled=True))
        for name in sorted(os.listdir(self.dir)):
            if not name.endswith(".sqlite"):
                continue
            tid = name[:-7]
            if any(m["id"] == tid for m in out):
                continue
            meta = self._read_meta(os.path.join(self.dir, name))
            if meta:
                out.append(dict(meta, bundled=False))
        return out

    def ids(self):
        return [m["id"] for m in self.list()]

    def _read_meta(self, path):
        try:
            db = sqlite3.connect(path)
            meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
            db.close()
            return meta
        except sqlite3.Error:
            return None

    # --- opening ------------------------------------------------------------

    def get(self, tid):
        tid = (tid or "").lower()
        with self._lock:
            if tid in self._open:
                return self._open[tid]
            meta = next((m for m in self.list() if m["id"] == tid), None)
            if meta is None:
                raise RefError("there is no translation '%s'. These are installed: %s." % (
                    tid, ", ".join(self.ids())), translations=self.ids())
            path = os.path.join(self.dir, tid + ".sqlite")
            if meta.get("bundled"):
                self._materialise(meta, path)
            trans = Translation(path, meta)
            self._open[tid] = trans
            return trans

    def _materialise(self, meta, path):
        """Turn a bundled .tsv.gz into SQLite once, and again when it changes."""
        current = self._read_meta(path) if os.path.exists(path) else None
        if current and current.get("sha256") == meta.get("sha256_tsv"):
            return
        rows = []
        with gzip.open(os.path.join(self.bundled_dir, meta["file"]), "rt", encoding="utf-8") as f:
            for line in f:
                b, c, v, text = line.rstrip("\n").split("\t", 3)
                rows.append((int(b), int(c), int(v), text))
        stored = {k: v for k, v in meta.items() if isinstance(v, str)}
        stored["sha256"] = meta.get("sha256_tsv", "")
        self.write(path, stored, rows)

    def write(self, path, meta, rows):
        tmp = path + ".part"
        if os.path.exists(tmp):
            os.remove(tmp)
        db = sqlite3.connect(tmp)
        db.executescript(SCHEMA)
        db.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", list(meta.items()))
        db.executemany("INSERT OR REPLACE INTO verses VALUES (?, ?, ?, ?)", rows)
        db.commit()
        db.close()
        os.replace(tmp, path)

    def add(self, meta, rows):
        """Store an imported translation. Replaces one with the same id."""
        tid = slug(meta.get("id") or meta.get("name"))
        if any(m["id"] == tid and m.get("bundled") for m in self.list()):
            raise RefError("'%s' is the id of a translation that ships with the plugin. "
                           "Give yours another abbreviation." % tid)
        meta = dict(meta, id=tid)
        with self._lock:
            old = self._open.pop(tid, None)
            if old:
                old.close()
            self.write(os.path.join(self.dir, tid + ".sqlite"),
                       {k: str(v) for k, v in meta.items()}, rows)
        books_found = len({r[0] for r in rows})
        return dict(meta, verses=len(rows), books=books_found)

    def remove(self, tid):
        tid = (tid or "").lower()
        if any(m["id"] == tid and m.get("bundled") for m in self.list()):
            raise RefError("'%s' ships with the plugin and cannot be removed." % tid)
        path = os.path.join(self.dir, tid + ".sqlite")
        if not os.path.exists(path):
            raise RefError("there is no imported translation '%s'." % tid)
        with self._lock:
            old = self._open.pop(tid, None)
            if old:
                old.close()
            os.remove(path)
        return {"removed": tid}


def label(rows, book=None):
    """The reference a run of verses covers: "John 3:16-18", "Genesis 1:31-2:3"."""
    if not rows:
        return ""
    b = book or books.BY_NUMBER[rows[0][0]]
    first, last = rows[0], rows[-1]
    one_chapter = first[1] == last[1]
    name = b.heading(chapter_only=one_chapter)
    if first[1:3] == last[1:3]:
        return "%s %d:%d" % (name, first[1], first[2])
    if one_chapter:
        return "%s %d:%d-%d" % (name, first[1], first[2], last[2])
    return "%s %d:%d-%d:%d" % (name, first[1], first[2], last[1], last[2])
