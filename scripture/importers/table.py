"""A plain table: book, chapter, verse, text. Comma or tab separated.

The book is a name ("John", "1 Corinthians"), an abbreviation ("Jn"), a USFM
code ("JHN"), an OSIS id ("John") or a number from 1 to 66. A header line is
allowed and skipped. This is also the format the bundled translations ship
in, gzipped and tab separated.
"""
import csv
import io

from .. import books
from ..refparse import RefError, find_book
from .common import ImportError_, clean

_CACHE = {}


def _book(value):
    value = value.strip()
    if value in _CACHE:
        return _CACHE[value]
    book = books.by_code(value)
    if book is None:
        head = value.split(" ", 1)
        try:
            if head[0] in ("1", "2", "3") and len(head) == 2:
                book = find_book(head[1], head[0])
            else:
                book = find_book(value)
        except RefError:
            book = None
    _CACHE[value] = book
    return book


def parse(text):
    sample = text[:4096]
    delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = []
    problems = []
    for line_no, cells in enumerate(reader, 1):
        if not cells or not "".join(cells).strip():
            continue
        if len(cells) < 4:
            problems.append(line_no)
            continue
        book = _book(cells[0])
        try:
            chapter, verse = int(cells[1]), int(cells[2])
        except ValueError:
            if line_no == 1:
                continue  # a header
            problems.append(line_no)
            continue
        if book is None:
            problems.append(line_no)
            continue
        words = clean(delimiter.join(cells[3:]))
        if words:
            rows.append((book.number, chapter, verse, words))
    if not rows:
        raise ImportError_("no verses found. Each line should be book,chapter,verse,text, "
                           "for example: John,3,16,For God so loved the world...")
    if problems and len(problems) > len(rows) // 10:
        raise ImportError_("%d lines could not be read, the first at line %d. Each line "
                           "should be book,chapter,verse,text." % (len(problems), problems[0]),
                           )
    return rows
