"""The 66 books of the Protestant canon, with every name people type for them.

Each book has its USFM code (what ebible.org and Paratext use), its OSIS id
(what OSIS XML and SWORD use), the name shown on air, how many chapters it
has, and the abbreviations a person types in a hurry. Book numbers run 1 to
66 in canonical order, which is also the number Zefania XML uses.
"""

# (usfm, osis, display name, chapters, aliases)
BOOKS = [
    ("GEN", "Gen", "Genesis", 50, ["gn", "ge", "gen", "gns"]),
    ("EXO", "Exod", "Exodus", 40, ["ex", "exo", "exod", "exd"]),
    ("LEV", "Lev", "Leviticus", 27, ["lv", "le", "lev", "levi"]),
    ("NUM", "Num", "Numbers", 36, ["nm", "nu", "num", "numb"]),
    ("DEU", "Deut", "Deuteronomy", 34, ["dt", "de", "deu", "deut", "dtn"]),
    ("JOS", "Josh", "Joshua", 24, ["jos", "josh", "jsh"]),
    ("JDG", "Judg", "Judges", 21, ["jdg", "jdgs", "judg", "jg", "jgs"]),
    ("RUT", "Ruth", "Ruth", 4, ["ru", "rth", "rut"]),
    ("1SA", "1Sam", "1 Samuel", 31, ["1sa", "1sam", "1sm", "1s", "1samuel", "1kingdoms"]),
    ("2SA", "2Sam", "2 Samuel", 24, ["2sa", "2sam", "2sm", "2s", "2samuel", "2kingdoms"]),
    ("1KI", "1Kgs", "1 Kings", 22, ["1ki", "1kgs", "1kg", "1k", "1kin", "1kngs"]),
    ("2KI", "2Kgs", "2 Kings", 25, ["2ki", "2kgs", "2kg", "2k", "2kin", "2kngs"]),
    ("1CH", "1Chr", "1 Chronicles", 29, ["1ch", "1chr", "1chron", "1chro", "1cr"]),
    ("2CH", "2Chr", "2 Chronicles", 36, ["2ch", "2chr", "2chron", "2chro", "2cr"]),
    ("EZR", "Ezra", "Ezra", 10, ["ezr", "ez"]),
    ("NEH", "Neh", "Nehemiah", 13, ["ne", "neh", "nehe"]),
    ("EST", "Esth", "Esther", 10, ["es", "est", "esth", "ester"]),
    ("JOB", "Job", "Job", 42, ["jb"]),
    ("PSA", "Ps", "Psalms", 150, ["ps", "psa", "psm", "pss", "psalm", "pslm", "psalter"]),
    ("PRO", "Prov", "Proverbs", 31, ["pr", "pro", "prov", "prv", "prvbs"]),
    ("ECC", "Eccl", "Ecclesiastes", 12, ["ec", "ecc", "eccl", "eccles", "qoh", "qoheleth"]),
    ("SNG", "Song", "Song of Solomon", 8, ["so", "sos", "song", "sng", "songofsongs", "songs", "canticles", "cant", "ss"]),
    ("ISA", "Isa", "Isaiah", 66, ["is", "isa", "isai"]),
    ("JER", "Jer", "Jeremiah", 52, ["je", "jer", "jr", "jere"]),
    ("LAM", "Lam", "Lamentations", 5, ["la", "lam", "lament"]),
    ("EZK", "Ezek", "Ezekiel", 48, ["ezk", "eze", "ezek"]),
    ("DAN", "Dan", "Daniel", 12, ["da", "dan", "dn"]),
    ("HOS", "Hos", "Hosea", 14, ["ho", "hos"]),
    ("JOL", "Joel", "Joel", 3, ["jl", "joe", "jol"]),
    ("AMO", "Amos", "Amos", 9, ["am", "amo"]),
    ("OBA", "Obad", "Obadiah", 1, ["ob", "oba", "obad", "obd"]),
    ("JON", "Jonah", "Jonah", 4, ["jnh", "jon", "jona"]),
    ("MIC", "Mic", "Micah", 7, ["mi", "mic", "mc"]),
    ("NAM", "Nah", "Nahum", 3, ["na", "nah", "nam"]),
    ("HAB", "Hab", "Habakkuk", 3, ["hb", "hab", "habb"]),
    ("ZEP", "Zeph", "Zephaniah", 3, ["zp", "zep", "zeph"]),
    ("HAG", "Hag", "Haggai", 2, ["hg", "hag", "hagg"]),
    ("ZEC", "Zech", "Zechariah", 14, ["zc", "zec", "zech"]),
    ("MAL", "Mal", "Malachi", 4, ["ml", "mal"]),
    ("MAT", "Matt", "Matthew", 28, ["mt", "mat", "matt", "mtt"]),
    ("MRK", "Mark", "Mark", 16, ["mk", "mr", "mrk", "mar"]),
    ("LUK", "Luke", "Luke", 24, ["lk", "lu", "luk"]),
    ("JHN", "John", "John", 21, ["jn", "jhn", "joh", "jo"]),
    ("ACT", "Acts", "Acts", 28, ["ac", "act", "acts", "actsoftheapostles"]),
    ("ROM", "Rom", "Romans", 16, ["ro", "rom", "rm", "rmn"]),
    ("1CO", "1Cor", "1 Corinthians", 16, ["1co", "1cor", "1corin", "1corinth", "1c"]),
    ("2CO", "2Cor", "2 Corinthians", 13, ["2co", "2cor", "2corin", "2corinth", "2c"]),
    ("GAL", "Gal", "Galatians", 6, ["ga", "gal", "gltns"]),
    ("EPH", "Eph", "Ephesians", 6, ["ep", "eph", "ephes"]),
    ("PHP", "Phil", "Philippians", 4, ["php", "phil", "pp", "philip", "phi", "phl"]),
    ("COL", "Col", "Colossians", 4, ["co", "col", "colo"]),
    ("1TH", "1Thess", "1 Thessalonians", 5, ["1th", "1thes", "1thess", "1ts", "1thessa"]),
    ("2TH", "2Thess", "2 Thessalonians", 3, ["2th", "2thes", "2thess", "2ts", "2thessa"]),
    ("1TI", "1Tim", "1 Timothy", 6, ["1ti", "1tim", "1tm"]),
    ("2TI", "2Tim", "2 Timothy", 4, ["2ti", "2tim", "2tm"]),
    ("TIT", "Titus", "Titus", 3, ["ti", "tit", "tt"]),
    ("PHM", "Phlm", "Philemon", 1, ["phm", "phlm", "philem", "phile", "pm"]),
    ("HEB", "Heb", "Hebrews", 13, ["he", "heb", "hbr"]),
    ("JAS", "Jas", "James", 5, ["jas", "jm", "jam", "jms", "ja"]),
    ("1PE", "1Pet", "1 Peter", 5, ["1pe", "1pet", "1pt", "1p", "1ptr"]),
    ("2PE", "2Pet", "2 Peter", 3, ["2pe", "2pet", "2pt", "2p", "2ptr"]),
    ("1JN", "1John", "1 John", 5, ["1jn", "1jo", "1joh", "1jhn", "1j"]),
    ("2JN", "2John", "2 John", 1, ["2jn", "2jo", "2joh", "2jhn", "2j"]),
    ("3JN", "3John", "3 John", 1, ["3jn", "3jo", "3joh", "3jhn", "3j"]),
    ("JUD", "Jude", "Jude", 1, ["jud", "jd", "jde"]),
    ("REV", "Rev", "Revelation", 22, ["re", "rev", "rv", "revelations", "apocalypse", "apoc", "rvl"]),
]

COUNT = len(BOOKS)


class Book:
    __slots__ = ("number", "usfm", "osis", "name", "chapters", "aliases")

    def __init__(self, number, usfm, osis, name, chapters, aliases):
        self.number = number
        self.usfm = usfm
        self.osis = osis
        self.name = name
        self.chapters = chapters
        self.aliases = aliases

    def single_chapter(self):
        return self.chapters == 1

    def heading(self, chapter_only=False):
        """The name on air. Psalms is "Psalm 23" when one psalm is meant."""
        if self.usfm == "PSA" and chapter_only:
            return "Psalm"
        return self.name

    def __repr__(self):
        return "Book(%s)" % self.usfm


ALL = [Book(i + 1, *row) for i, row in enumerate(BOOKS)]
BY_NUMBER = {b.number: b for b in ALL}
BY_USFM = {b.usfm: b for b in ALL}
BY_OSIS = {b.osis.lower(): b for b in ALL}


def by_code(code):
    """A book from a USFM code, an OSIS id or a book number, or None."""
    if code is None:
        return None
    if isinstance(code, int):
        return BY_NUMBER.get(code)
    text = str(code).strip()
    if text.isdigit():
        return BY_NUMBER.get(int(text))
    return BY_USFM.get(text.upper()) or BY_OSIS.get(text.lower())
