"""Zefania XML: <XMLBIBLE><BIBLEBOOK bnumber><CHAPTER cnumber><VERS vnumber>.

Book numbers are 1 to 66 in canonical order, which is how this plugin numbers
them too. Notes and Strong's markup inside a verse are dropped or flattened.
"""
import xml.etree.ElementTree as ET

from .. import books
from .common import ImportError_, clean, local

SKIP = {"note", "xref", "caption", "remark"}


def _words(elem):
    parts = [elem.text or ""]
    for child in elem:
        if local(child.tag) not in SKIP:
            parts.append(" " if local(child.tag) == "br" else _words(child))
        parts.append(child.tail or "")
    return "".join(parts)


def _attr(elem, name):
    for key, value in elem.attrib.items():
        if key.lower() == name:
            return value
    return None


def parse(text):
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError as e:
        raise ImportError_("the Zefania file is not well formed XML: %s." % e)
    rows = []
    for book_elem in root.iter():
        if local(book_elem.tag) != "biblebook":
            continue
        book = books.by_code(_attr(book_elem, "bnumber"))
        if book is None:
            continue
        for chapter in book_elem:
            if local(chapter.tag) != "chapter":
                continue
            c = int(_attr(chapter, "cnumber") or 0)
            for vers in chapter:
                if local(vers.tag) != "vers":
                    continue
                v = int((_attr(vers, "vnumber") or "0").split("-")[0])
                words = clean(_words(vers))
                if c and v and words:
                    rows.append((book.number, c, v, words))
    if not rows:
        raise ImportError_("no verses found. Zefania verses are <VERS vnumber=\"16\"> inside "
                           "<CHAPTER> inside <BIBLEBOOK bnumber=\"43\">.")
    return rows


def name_of(text):
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError:
        return None
    name = _attr(root, "biblename")
    if name:
        return name.strip()
    for elem in root.iter():
        if local(elem.tag) == "title" and elem.text and elem.text.strip():
            return elem.text.strip()
    return None
