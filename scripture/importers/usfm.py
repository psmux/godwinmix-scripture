"""USFM, the format Paratext and ebible.org publish in.

One file per book, starting with an \\id line naming the book. Verses are
\\v markers inside \\c chapters. Footnotes, cross references, headings and
Strong's numbers are dropped; the words of \\add, \\nd, \\wj and \\w are kept.
"""
import re

from .. import books
from .common import ImportError_, clean

NOTES = re.compile(r"\\(f|fe|x|ef|ex|fig)\s.*?\\\1\*", re.S)
ALT_NUMBERS = re.compile(r"\\(ca|va|vp)\s.*?\\\1\*", re.S)
# Lines that are not verse text: headings, titles, introductions, comments.
SKIP_LINE = re.compile(
    r"^\\(?:id|ide|h|toc\d*|toca\d*|mt\d*|mte\d*|ms\d*|mr|s\d*|sr|r|d|sp|cl|cp|rem|sts|usfm|"
    r"i[a-z]*\d*|periph|sd\d*|lit|restore|esb|esbe)\b.*$",
    re.M,
)
ATTRIBUTES = re.compile(r"\|[^\\]*(?=\\\+?[a-z]+\d*\*)")
# A marker, with the one space after an opening marker that belongs to it, so
# "doesn't" written as "doesn’\w t\w*" comes out whole.
MARKER = re.compile(r"\\\+?[a-z]+\d*(?:\*|\s?)")
TOKEN = re.compile(r"\\(c|v)\s+(\d+)[a-z]?(?:-\d+[a-z]?)?\s?")


def book_of(text, fallback=None):
    match = re.search(r"^\\id\s+([0-9A-Z]{3})", text, re.M)
    code = match.group(1) if match else fallback
    book = books.by_code(code) if code else None
    return book


def parse_book(text, name_hint=""):
    """Every (book number, chapter, verse, text) in one USFM book."""
    book = book_of(text)
    if book is None:
        if re.search(r"^\\id\s+(FRT|BAK|GLO|OTH|INT|CNC|TDX|NDX|XXA|XXB|XXC|XXD|XXE|XXF|XXG)",
                     text, re.M):
            return []
        match = re.search(r"\\id\s+(\S+)", text)
        if match and match.group(1)[:3].upper() in {
                "TOB", "JDT", "ESG", "WIS", "SIR", "BAR", "LJE", "S3Y", "SUS", "BEL",
                "1MA", "2MA", "3MA", "4MA", "1ES", "2ES", "MAN", "PS2", "DAG", "PSS",
                "EZA", "5EZ", "6EZ", "LAO"}:
            return []  # deuterocanonical books are outside the 66 this plugin knows
        raise ImportError_("%s has no \\id line naming a book of the Bible. Each USFM "
                           "file starts with one, such as \\id JHN." % (name_hint or "a file"))
    text = NOTES.sub(" ", text)
    text = ALT_NUMBERS.sub(" ", text)
    text = SKIP_LINE.sub("", text)
    text = ATTRIBUTES.sub("", text)
    rows = []
    chapter = 0
    verse = None
    buf = []

    def flush():
        if verse is not None and chapter:
            words = clean(MARKER.sub("", "".join(buf)))
            if words:
                rows.append((book.number, chapter, verse, words))

    pos = 0
    for match in TOKEN.finditer(text):
        buf.append(text[pos:match.start()])
        flush()
        buf = []
        kind, number = match.group(1), int(match.group(2))
        if kind == "c":
            chapter, verse = number, None
        else:
            verse = number
        pos = match.end()
    buf.append(text[pos:])
    flush()
    return rows


def parse(files):
    """`files` is a list of (name, text). Returns the rows of every book."""
    rows = []
    for name, text in files:
        rows.extend(parse_book(text, name))
    if not rows:
        raise ImportError_("no verses found. A USFM file has \\c and \\v markers; check "
                           "this is USFM and not USX or OSIS.")
    return rows
