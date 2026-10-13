"""Read a translation from USFM, OSIS XML, Zefania XML or a book,chapter,verse,text table."""
import io
import re
import zipfile

from . import osis, table, usfm, zefania
from .common import ImportError_

FORMATS = ("usfm", "osis", "zefania", "csv")


def detect(name, text):
    head = text[:4000].lower()
    if "<xmlbible" in head or "<biblebook" in head:
        return "zefania"
    if "<osis" in head:
        return "osis"
    if re.search(r"^\s*\\id\s", text[:4000], re.M) or name.lower().endswith((".usfm", ".sfm")):
        return "usfm"
    return "csv"


def decode(data):
    """Bytes to text: UTF-8 with or without a byte order mark, else Latin 1."""
    if isinstance(data, str):
        return data
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(encoding)
            if encoding == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return text
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def unpack(name, data):
    """A list of (name, text): the files inside a zip, or the one file given."""
    if isinstance(data, bytes) and data[:2] == b"PK":
        files = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                lower = info.filename.lower()
                if info.is_dir() or not lower.endswith((".usfm", ".sfm", ".xml", ".osis", ".csv",
                                                        ".tsv", ".txt")):
                    continue
                if info.file_size > 64 * 1024 * 1024:
                    raise ImportError_("%s in the zip is over 64 MB, which is no Bible." % info.filename)
                files.append((info.filename, decode(archive.read(info))))
        if not files:
            raise ImportError_("the zip holds no .usfm, .xml, .csv or .txt files.")
        return files
    return [(name, decode(data))]


def parse(name, data, fmt=None):
    """Every verse in an upload, as (book number, chapter, verse, text) rows."""
    files = unpack(name, data)
    fmt = (fmt or "").lower() or detect(files[0][0], files[0][1])
    if fmt not in FORMATS:
        raise ImportError_("'%s' is not a format this reads. Use one of: %s." % (fmt, ", ".join(FORMATS)))
    if fmt == "usfm":
        rows = usfm.parse([f for f in files if detect(f[0], f[1]) == "usfm"] or files)
    else:
        module = {"osis": osis, "zefania": zefania, "csv": table}[fmt]
        rows = []
        for _, text in files:
            rows.extend(module.parse(text))
    title = None
    if fmt in ("osis", "zefania"):
        title = {"osis": osis, "zefania": zefania}[fmt].name_of(files[0][1])
    return fmt, rows, title
