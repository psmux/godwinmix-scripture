"""Read song words from plain text, OpenLyrics XML and ChordPro.

Every reader returns a song dictionary for songs.normalise: title, author,
copyright, ccli, sections and order. Chords are always stripped; this plugin
shows words to a congregation, not charts to a band.
"""
import os
import re
import xml.etree.ElementTree as ET

from .songs import SongError, section_id

HEADER = re.compile(r"^(title|author|authors|artist|words|copyright|ccli|ccli number|ccli song number|"
                    r"order|sequence|verse order)\s*[:=]\s*(.*)$", re.I)


def _blank_song(name=""):
    title = os.path.splitext(os.path.basename(name or ""))[0].replace("_", " ").strip()
    return {"title": title, "author": "", "copyright": "", "ccli": "", "sections": [], "order": None}


def _apply_header(song, key, value):
    key = key.lower()
    if key == "title":
        song["title"] = value
    elif key in ("author", "authors", "artist", "words"):
        song["author"] = value
    elif key == "copyright":
        song["copyright"] = value
    elif key.startswith("ccli"):
        song["ccli"] = value
    else:
        song["order"] = value


def _heading(line):
    """A section heading line, as a section id, or None."""
    text = line.strip()
    if not text or len(text) > 24:
        return None
    if text.startswith("[") and text.endswith("]"):
        return section_id(text[1:-1]) or "O"
    if text.endswith(":"):
        text = text[:-1]
    return section_id(text)


def parse_text(text, name=""):
    """Plain text: optional "Title:" style headers, then stanzas.

    A stanza starts at a heading line ([Verse 1], Chorus, V2:) or after a
    blank line. Stanzas with no heading are numbered as verses.
    """
    song = _blank_song(name)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        match = HEADER.match(lines[i].strip())
        if not match:
            break
        _apply_header(song, match.group(1), match.group(2).strip())
        i += 1
    current = None
    verse_no = 0
    for line in lines[i:]:
        sid = _heading(line)
        if sid:
            current = {"id": sid, "lines": []}
            song["sections"].append(current)
            continue
        if not line.strip():
            if current and current["lines"]:
                current = None
            continue
        if current is None:
            verse_no += 1
            current = {"id": "V%d" % verse_no, "lines": []}
            song["sections"].append(current)
        current["lines"].append(line.strip())
    _number_verses(song)
    if not song["title"] and song["sections"]:
        song["title"] = song["sections"][0]["lines"][0]
    return song


def _number_verses(song):
    """A bare "V" heading becomes V1, V2 in turn; an explicit number is kept."""
    count = 0
    for sec in song["sections"]:
        if sec["id"] == "V":
            count += 1
            sec["id"] = "V%d" % count
        elif re.fullmatch(r"V\d+", sec["id"]):
            count = int(sec["id"][1:])


# --- OpenLyrics -----------------------------------------------------------

def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _ol_lines(elem):
    """Text of a <lines> element: <br/> breaks a line, <chord> and <comment> vanish."""
    out = [""]

    def walk(node):
        if node.text and _local(node.tag) not in ("comment",):
            out[-1] += node.text
        for child in node:
            name = _local(child.tag)
            if name == "br":
                out.append("")
            elif name != "comment":
                walk(child)
            if child.tail:
                out[-1] += child.tail
    walk(elem)
    return [re.sub(r"\s+", " ", ln).strip() for ln in out if ln.strip()]


def parse_openlyrics(text, name=""):
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as e:
        raise SongError("the OpenLyrics file is not well formed XML: %s." % e)
    if _local(root.tag) != "song":
        raise SongError("this is not OpenLyrics: the root element is <%s>, not <song>." % _local(root.tag))
    song = _blank_song(name)
    for elem in root.iter():
        tag = _local(elem.tag)
        value = (elem.text or "").strip()
        if tag == "title" and value and not song.get("_titled"):
            song["title"], song["_titled"] = value, True
        elif tag == "author" and value:
            song["author"] = (song["author"] + ", " + value).strip(", ")
        elif tag == "copyright" and value:
            song["copyright"] = value
        elif tag == "ccliNo" and value:
            song["ccli"] = value
        elif tag == "verseOrder" and value:
            song["order"] = value
    song.pop("_titled", None)
    for verse in root.iter():
        if _local(verse.tag) != "verse":
            continue
        sid = section_id(verse.get("name", "")) or (verse.get("name") or "O").upper()
        lines = []
        for part in verse:
            if _local(part.tag) == "lines":
                if lines:
                    lines.append("")
                lines.extend(_ol_lines(part))
        song["sections"].append({"id": sid, "lines": lines})
    return song


# --- ChordPro -------------------------------------------------------------

CHORD = re.compile(r"\[[^\]]*\]")
DIRECTIVE = re.compile(r"^\{\s*([a-z_]+)\s*(?:[:\s]\s*(.*?))?\s*\}$", re.I)
STARTS = {"start_of_chorus": "C", "soc": "C", "start_of_verse": "V", "sov": "V",
          "start_of_bridge": "B", "sob": "B"}
ENDS = {"end_of_chorus", "eoc", "end_of_verse", "eov", "end_of_bridge", "eob"}
SKIP_BLOCKS = {"start_of_tab": "end_of_tab", "sot": "eot", "start_of_grid": "end_of_grid",
               "sog": "eog", "start_of_abc": "end_of_abc", "start_of_ly": "end_of_ly"}


def parse_chordpro(text, name=""):
    song = _blank_song(name)
    current = None
    skipping = None
    pending_label = None
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if skipping:
            if DIRECTIVE.match(line) and DIRECTIVE.match(line).group(1).lower() == skipping:
                skipping = None
            continue
        if line.startswith("#"):
            continue
        match = DIRECTIVE.match(line)
        if match:
            key, value = match.group(1).lower(), (match.group(2) or "").strip()
            if key in ("title", "t"):
                song["title"] = value
            elif key in ("artist", "composer", "lyricist", "subtitle", "st") and not song["author"]:
                song["author"] = value
            elif key == "copyright":
                song["copyright"] = value
            elif key == "ccli":
                song["ccli"] = value
            elif key in STARTS:
                sid = section_id(value) if value else None
                current = {"id": sid or STARTS[key], "lines": []}
                song["sections"].append(current)
            elif key in ENDS:
                current = None
            elif key in SKIP_BLOCKS:
                skipping = SKIP_BLOCKS[key]
            elif key in ("comment", "c", "comment_italic", "ci", "comment_box", "cb"):
                pending_label = section_id(value)
            continue
        words = re.sub(r"\s+", " ", CHORD.sub("", raw)).strip()
        if not words:
            if current and current["lines"] and current.get("loose"):
                current = None
            continue
        if current is None or pending_label:
            current = {"id": pending_label or "V", "lines": [], "loose": True}
            song["sections"].append(current)
            pending_label = None
        current["lines"].append(words)
    for sec in song["sections"]:
        sec.pop("loose", None)
    _number_verses(song)
    return song


def detect(name, text):
    lower = (name or "").lower()
    head = text[:2000]
    if "<song" in head and "openlyrics" in head.lower():
        return "openlyrics"
    if lower.endswith((".cho", ".chopro", ".chordpro", ".crd", ".pro")) or re.search(
            r"^\{\s*(title|t|start_of_chorus|soc)\b", head, re.M | re.I):
        return "chordpro"
    if head.lstrip().startswith("<") and "<song" in head:
        return "openlyrics"
    return "text"


def parse(text, name="", fmt=None):
    fmt = fmt or detect(name, text)
    reader = {"text": parse_text, "openlyrics": parse_openlyrics, "chordpro": parse_chordpro}.get(fmt)
    if reader is None:
        raise SongError("'%s' is not a lyrics format this reads. Use text, openlyrics or chordpro." % fmt)
    return fmt, reader(text, name)
