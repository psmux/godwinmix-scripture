"""OSIS XML, the format SWORD modules and many Bible societies publish in.

Verses come two ways and both are read: as containers,
<verse osisID="John.3.16">words</verse>, and as milestones,
<verse sID="John.3.16" osisID="John.3.16"/>words<verse eID="John.3.16"/>.
Notes, titles and cross references are left out.
"""
import xml.etree.ElementTree as ET

from .. import books
from .common import ImportError_, clean, local

SKIP = {"note", "title", "reference", "rdg", "header", "figure", "milestone"}


def _verse_key(osis_id):
    first = osis_id.split()[0]
    parts = first.split(".")
    if len(parts) < 3:
        return None
    book = books.by_code(parts[-3].split(":")[-1])
    if book is None:
        return None
    try:
        return book.number, int(parts[-2]), int(parts[-1].split("!")[0])
    except ValueError:
        return None


class _Walk:
    def __init__(self):
        self.current = None
        self.texts = {}
        self.order = []

    def add(self, text):
        if text and self.current is not None:
            if self.current not in self.texts:
                self.texts[self.current] = []
                self.order.append(self.current)
            self.texts[self.current].append(text)

    def walk(self, elem):
        name = local(elem.tag)
        if name in SKIP:
            return
        if name == "verse":
            if elem.get("eID") is not None:
                self.current = None
                return
            key = _verse_key(elem.get("osisID") or elem.get("sID") or "")
            if elem.get("sID") is not None:
                self.current = key
                return
            previous, self.current = self.current, key
            self._inside(elem)
            self.current = previous
            return
        self._inside(elem)

    def _inside(self, elem):
        self.add(elem.text)
        for child in elem:
            self.walk(child)
            self.add(child.tail)


def parse(text):
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError as e:
        raise ImportError_("the OSIS file is not well formed XML: %s. Open it in a text editor "
                           "at that line, or export it again." % e)
    walker = _Walk()
    walker.walk(root)
    rows = []
    for key in walker.order:
        words = clean(" ".join(walker.texts[key]))
        if words:
            rows.append((key[0], key[1], key[2], words))
    if not rows:
        raise ImportError_("no verses found. OSIS verses are <verse osisID=\"John.3.16\"> "
                           "elements; check this is OSIS and not USX or Zefania.")
    return rows


def name_of(text):
    """The work's title from the OSIS header, when it has one."""
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError:
        return None
    for elem in root.iter():
        if local(elem.tag) == "title" and elem.text and elem.text.strip():
            return elem.text.strip()
    return None
