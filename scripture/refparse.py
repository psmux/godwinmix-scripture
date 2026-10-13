"""Read a Bible reference the way people type it.

"John 3:16", "jn 3 16", "1 Cor 13:4-7", "Ps 23", "Gen 1:1-2:3", "1jn1:9",
"Romans 8:28, 31-39", "jhon 3.16 KJV". A book name is matched exactly, then
as an abbreviation, then by prefix, then by spelling distance, so a slip of
the finger still finds the book. Chapter and verse numbers are checked against
the book's chapter count here; verse counts are checked against the text when
the passage is read.
"""
import difflib
import re

from . import books

# Every dash a phone keyboard or a word processor might put between two verse
# numbers, written as code points so this file stays plain ASCII.
DASHES = "".join(chr(c) for c in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015,
                                  0x2212, 0xFE58, 0xFE63, 0xFF0D))
ORDINALS = {"1": "1", "2": "2", "3": "3", "i": "1", "ii": "2", "iii": "3",
            "first": "1", "second": "2", "third": "3",
            "1st": "1", "2nd": "2", "3rd": "3"}

HEAD = re.compile(
    r"^\s*(?:(?P<ord>[123]|1st|2nd|3rd)\s*\.?\s*|(?P<rord>iii|ii|i|first|second|third)\s+)?"
    r"(?P<name>[a-z][a-z.' ]*?)\s*\.?\s*(?P<rest>\d.*)?$",
    re.IGNORECASE,
)


class RefError(ValueError):
    """A reference that could not be read, with what to do about it."""

    def __init__(self, message, **data):
        super().__init__(message)
        self.data = data


class Segment:
    """One run of text: from (chapter, verse) to (chapter, verse).

    A verse of None means the whole chapter: the first verse at the start,
    the last verse at the end.
    """
    __slots__ = ("c1", "v1", "c2", "v2")

    def __init__(self, c1, v1, c2, v2):
        self.c1, self.v1, self.c2, self.v2 = c1, v1, c2, v2

    def as_tuple(self):
        return (self.c1, self.v1, self.c2, self.v2)

    def __eq__(self, other):
        return isinstance(other, Segment) and self.as_tuple() == other.as_tuple()

    def __repr__(self):
        return "Segment%r" % (self.as_tuple(),)

    def label(self):
        c1, v1, c2, v2 = self.as_tuple()
        if v1 is None and v2 is None:
            return str(c1) if c1 == c2 else "%d-%d" % (c1, c2)
        start = "%d:%d" % (c1, v1 or 1)
        if c1 == c2 and v1 == v2:
            return start
        if c1 == c2:
            return "%s-%d" % (start, v2) if v2 is not None else "%s-end" % start
        end = "%d:%d" % (c2, v2) if v2 is not None else str(c2)
        return "%s-%s" % (start, end)


class Reference:
    __slots__ = ("book", "segments", "translation")

    def __init__(self, book, segments, translation=None):
        self.book = book
        self.segments = segments
        self.translation = translation

    def display(self):
        chapters = {s.c1 for s in self.segments} | {s.c2 for s in self.segments}
        name = self.book.heading(chapter_only=len(chapters) == 1)
        parts = []
        last_chapter = None
        for seg in self.segments:
            text = seg.label()
            # "Romans 8:28, 31-39": a later piece in the same chapter drops it.
            if last_chapter == seg.c1 and seg.v1 is not None and seg.c1 == seg.c2:
                text = text.split(":", 1)[1]
            parts.append(text)
            last_chapter = seg.c2
        return "%s %s" % (name, ", ".join(parts))

    def __repr__(self):
        return "Reference(%s %r)" % (self.book.usfm, self.segments)


def _key(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _build_index():
    exact = {}
    names = {}
    for book in books.ALL:
        for key in [book.name, book.osis, book.usfm] + book.aliases:
            exact.setdefault(_key(key), book)
        names[_key(book.name)] = book
    # Titles people use for the book itself.
    for extra, code in (("songofsongs", "SNG"), ("psalm", "PSA"), ("canticleofcanticles", "SNG")):
        exact.setdefault(extra, books.BY_USFM[code])
    return exact, names


EXACT, NAMES = _build_index()
NUMBERED = {}
for _b in books.ALL:
    if _b.name[0].isdigit():
        NUMBERED.setdefault(_key(_b.name[2:]), []).append(_b)


def _closest(key, pool):
    """The nearest spelling, preferring two swapped letters over a dropped one.

    "jhon" is as close to "jon" (Jonah) as to "john" by edit ratio, but it has
    exactly the letters of "john", and a swapped pair is the commonest slip on
    a keyboard.
    """
    scored = []
    for cand in set(pool):
        ratio = difflib.SequenceMatcher(None, key, cand).ratio()
        if ratio >= 0.7:
            scored.append((sorted(key) == sorted(cand), ratio, -abs(len(cand) - len(key)), cand))
    return max(scored)[3] if scored else None


def find_book(name, ordinal=None):
    """The book a typed name means, or a RefError saying what was meant."""
    base = _key(name)
    if not base:
        raise RefError("there is no book name in that. Type one, such as John 3:16.")
    key = (ordinal or "") + base
    if key in EXACT:
        return EXACT[key]
    if not ordinal and base in NUMBERED and len(NUMBERED[base]) > 1:
        options = [b.name for b in NUMBERED[base]]
        raise RefError("'%s' is more than one book. Say which: %s." % (
            name.strip(), " or ".join(options)), options=options)
    if len(key) >= 2:
        prefixed = [b for k, b in NAMES.items() if k.startswith(key)]
        if prefixed:
            return min(prefixed, key=lambda b: b.number)
    if len(base) >= 3:
        pool = [k for k in list(EXACT) + list(NAMES) if k[0].isdigit() == bool(ordinal)]
        if ordinal:
            pool = [k for k in pool if k.startswith(ordinal)]
        best = _closest(key, pool)
        if best:
            return EXACT.get(best) or NAMES[best]
    suggestions = [NAMES[s].name for s in difflib.get_close_matches(key, list(NAMES), n=3, cutoff=0.4)]
    raise RefError("no book called '%s'. Try the full name, such as %s." % (
        name.strip(), " or ".join(suggestions) or "Genesis or John"), suggestions=suggestions)


def _normalise_numbers(rest):
    text = rest.lower()
    for dash in DASHES:
        text = text.replace(dash, "-")
    text = re.sub(r"\s*(?:vv?\.?|verses?)\s*", ":", text)
    text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1:\2", text)
    text = re.sub(r"\s*([-,;:])\s*", r"\1", text)
    if ":" not in text:
        # "3 16" and "3 16-18": a chapter and a verse with a space between.
        text = re.sub(r"^(\d+)\s+(\d+)", r"\1:\2", text)
    text = re.sub(r"\s+", ",", text.strip())
    text = text.replace("::", ":").strip(",;-")
    if not re.fullmatch(r"[\d:,;\-]+", text):
        raise RefError("could not read the numbers in '%s'. Write them as chapter:verse, "
                       "for example 3:16 or 13:4-7." % rest.strip(), numbers=rest.strip())
    return text


def _point(text):
    if ":" in text:
        c, v = text.split(":", 1)
        if not c or not v or ":" in v:
            raise RefError("'%s' is not a chapter and verse. Write it as 3:16." % text)
        return int(c), int(v)
    return int(text), None


def _segments(numbers, book):
    segs = []
    chapter = None      # the chapter a bare verse number belongs to
    for group in numbers.split(";"):
        verse_mode = False  # whether the last piece in this group named verses
        for piece in filter(None, group.split(",")):
            start, _, end = piece.partition("-")
            if not start:
                raise RefError("'%s' starts with a dash. Write a range as 13:4-7." % piece)
            c1, v1 = _point(start)
            if v1 is None and verse_mode:
                c1, v1 = chapter, c1
            elif v1 is None and book.single_chapter():
                c1, v1 = 1, c1
            if end:
                c2, v2 = _point(end)
                if v2 is None and v1 is not None:
                    c2, v2 = c1, c2
                elif v2 is not None and v1 is None:
                    v1 = 1
            else:
                c2, v2 = c1, v1
            segs.append(Segment(c1, v1, c2, v2))
            chapter = c2
            verse_mode = v2 is not None
    return segs


def _check(book, segs):
    for seg in segs:
        for c in (seg.c1, seg.c2):
            if c < 1 or c > book.chapters:
                raise RefError("%s has %d chapter%s, so there is no chapter %d. Pick 1 to %d." % (
                    book.name, book.chapters, "" if book.chapters == 1 else "s", c, book.chapters),
                    book=book.name, chapters=book.chapters)
        for v in (seg.v1, seg.v2):
            if v is not None and v < 1:
                raise RefError("verse numbers start at 1.")
        start = (seg.c1, seg.v1 or 0)
        end = (seg.c2, seg.v2 if seg.v2 is not None else 10 ** 6)
        if end < start:
            raise RefError("the range %s runs backwards. Put the earlier verse first." % seg.label())


def split_translation(text, translations=()):
    """Take a translation id off the end: "John 3:16 KJV" or "John 3:16 (web)"."""
    wanted = {t.lower(): t for t in translations}
    match = re.search(r"[\s(\[]+([A-Za-z][A-Za-z0-9-]{1,15})[)\]]?\s*$", text)
    if match and match.group(1).lower() in wanted:
        return text[:match.start()].strip(), wanted[match.group(1).lower()]
    return text, None


def parse(text, translations=()):
    """Read a reference. Raises RefError with a message an operator can act on."""
    if not text or not text.strip():
        raise RefError("type a reference, such as John 3:16 or Ps 23.")
    body, translation = split_translation(text.strip(), translations)
    match = HEAD.match(body)
    if not match:
        raise RefError("could not read '%s' as a reference. Start with a book name, "
                       "such as John 3:16." % text.strip())
    ordinal = match.group("ord") or match.group("rord")
    ordinal = ORDINALS.get(ordinal.lower()) if ordinal else None
    book = find_book(match.group("name"), ordinal)
    rest = match.group("rest")
    if rest:
        segs = _segments(_normalise_numbers(rest), book)
    else:
        # "Jude" or "Psalms": the first chapter, which for Jude is the book.
        segs = [Segment(1, None, 1, None)]
    if not segs:
        raise RefError("no chapter in '%s'. Add one, such as %s 1." % (text.strip(), book.name))
    _check(book, segs)
    return Reference(book, segs, translation)


def try_parse(text, translations=()):
    """A Reference when the words read as one with a number in them, else None.

    "love one another" is a search; "am 5 24" is Amos. A bare book name with
    no number is treated as a search too, because "acts" and "job" are words.
    """
    if not re.search(r"\d", text or ""):
        return None
    try:
        return parse(text, translations)
    except RefError:
        return None
