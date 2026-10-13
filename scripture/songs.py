"""Songs: what one is, the library on disk, and the order sections are sung in.

A song is a title, an author, a copyright line, a CCLI song number, its
sections (verses, choruses, a bridge and so on, each a list of lines) and an
order such as "V1 C V2 C B C". Section ids are short and upper case: V1, V2,
C, C2, B, P (pre chorus), T (tag), I (intro), E (ending).

The library is one JSON file per song in the data folder, named after the
song's id, so a church can back it up by copying a folder and a person can
read a song in a text editor.
"""
import json
import os
import re
import threading

KINDS = {
    "v": ("V", "Verse"), "verse": ("V", "Verse"),
    "c": ("C", "Chorus"), "chorus": ("C", "Chorus"), "refrain": ("C", "Chorus"),
    "r": ("C", "Chorus"),
    "b": ("B", "Bridge"), "bridge": ("B", "Bridge"),
    "p": ("P", "Pre chorus"), "pre": ("P", "Pre chorus"), "prechorus": ("P", "Pre chorus"),
    "pre-chorus": ("P", "Pre chorus"),
    "t": ("T", "Tag"), "tag": ("T", "Tag"),
    "i": ("I", "Intro"), "intro": ("I", "Intro"),
    "e": ("E", "Ending"), "ending": ("E", "Ending"), "outro": ("E", "Ending"),
    "o": ("O", "Other"), "other": ("O", "Other"), "interlude": ("O", "Interlude"),
}


class SongError(ValueError):
    pass


def section_id(label):
    """"Verse 2" to V2, "Chorus" to C, "pre-chorus" to P, "v1" to V1. None if not a heading."""
    text = label.strip().strip("[]():").strip().lower()
    match = re.fullmatch(r"([a-z][a-z\- ]*?)\s*(\d+[a-z]?)?", text)
    if not match:
        return None
    word = match.group(1).replace(" ", "")
    kind = KINDS.get(word) or KINDS.get(match.group(1).replace(" ", "-"))
    if kind is None:
        return None
    return kind[0] + (match.group(2) or "")


def section_label(sid):
    """V2 to "Verse 2", C to "Chorus"."""
    match = re.fullmatch(r"([A-Z])(\d*)([a-z]?)", sid or "")
    if not match:
        return sid
    name = {v[0]: v[1] for v in KINDS.values()}.get(match.group(1), sid)
    return (name + " " + match.group(2) + match.group(3)).strip()


def parse_order(text, sections):
    """"V1 C V2 C B C" to a list of section ids that exist in the song."""
    have = {s["id"] for s in sections}
    order = []
    unknown = []
    for token in re.split(r"[\s,;]+", (text or "").strip()):
        if not token:
            continue
        sid = section_id(token) or token.upper()
        if sid in have:
            order.append(sid)
        elif sid + "1" in have:
            order.append(sid + "1")
        else:
            unknown.append(token)
    if unknown:
        raise SongError("the order names %s, which this song does not have. It has: %s." % (
            ", ".join(unknown), " ".join(s["id"] for s in sections)))
    return order


def slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return value[:60] or "song"


def normalise(song):
    """Fill in what a song may leave out, and check what it must have."""
    title = (song.get("title") or "").strip()
    if not title:
        raise SongError("a song needs a title.")
    sections = []
    seen = {}
    written = []  # the order the sections were written in, repeats included
    for i, sec in enumerate(song.get("sections") or []):
        lines = [ln.rstrip() for ln in sec.get("lines") or [] if ln is not None]
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            continue
        sid = sec.get("id") or "V%d" % (i + 1)
        if sid in seen and seen[sid] == lines:
            written.append(sid)  # the chorus written out a second time is a repeat
            continue
        base, n = sid, 2
        while sid in seen:
            sid = "%s%d" % (base, n)
            n += 1
        seen[sid] = lines
        written.append(sid)
        sections.append({"id": sid, "label": sec.get("label") or section_label(sid), "lines": lines})
    if not sections:
        raise SongError("'%s' has no words. Add at least one verse." % title)
    order = song.get("order")
    if isinstance(order, str):
        order = parse_order(order, sections)
    order = [o for o in (order or []) if o in seen] or written
    return {
        "id": song.get("id") or slug(title),
        "title": title,
        "author": (song.get("author") or "").strip(),
        "copyright": (song.get("copyright") or "").strip(),
        "ccli": re.sub(r"\D", "", str(song.get("ccli") or "")),
        "sections": sections,
        "order": order,
    }


def to_text(song):
    """The plain text form, which is also what the panel's editor shows."""
    out = ["Title: " + song["title"]]
    for key, name in (("author", "Author"), ("copyright", "Copyright"), ("ccli", "CCLI")):
        if song.get(key):
            out.append("%s: %s" % (name, song[key]))
    out.append("Order: " + " ".join(song["order"]))
    for sec in song["sections"]:
        out.append("")
        out.append("[%s]" % section_label(sec["id"]))
        out.extend(sec["lines"])
    return "\n".join(out) + "\n"


class Library:
    def __init__(self, data_dir):
        self.dir = os.path.join(data_dir, "songs")
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, sid):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", sid or ""):
            raise SongError("'%s' is not a song id. Ids are lower case words joined by dashes." % sid)
        return os.path.join(self.dir, sid + ".json")

    def list(self, query=""):
        words = [w for w in re.findall(r"\w+", (query or "").lower())]
        out = []
        for name in sorted(os.listdir(self.dir)):
            if not name.endswith(".json"):
                continue
            try:
                song = self.get(name[:-5])
            except (SongError, ValueError, OSError):
                continue
            hay = " ".join([song["title"], song["author"], song["ccli"]] +
                           [" ".join(s["lines"]) for s in song["sections"]]).lower()
            if all(w in hay for w in words):
                first = song["sections"][0]["lines"][0] if song["sections"] else ""
                title_hit = all(w in song["title"].lower() for w in words)
                out.append(({"id": song["id"], "title": song["title"], "author": song["author"],
                             "ccli": song["ccli"], "first_line": first}, title_hit))
        out.sort(key=lambda pair: (not pair[1], pair[0]["title"].lower()))
        return [pair[0] for pair in out]

    def get(self, sid):
        path = self._path(sid)
        if not os.path.exists(path):
            raise SongError("there is no song '%s'. `songs` lists the library." % sid)
        with open(path, encoding="utf-8") as f:
            return normalise(json.load(f))

    def save(self, song, replace=True):
        song = normalise(song)
        with self._lock:
            path = self._path(song["id"])
            if os.path.exists(path) and not replace:
                base, n = song["id"], 2
                while os.path.exists(self._path("%s-%d" % (base, n))):
                    n += 1
                song["id"] = "%s-%d" % (base, n)
                path = self._path(song["id"])
            tmp = path + ".part"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump(song, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        return song

    def delete(self, sid):
        path = self._path(sid)
        if not os.path.exists(path):
            raise SongError("there is no song '%s'." % sid)
        os.remove(path)
        return {"deleted": sid}
