"""What every importer shares."""
import re

PILCROW = chr(0x00B6)


class ImportError_(ValueError):
    """A file that could not be imported, with what to do about it."""


def clean(text):
    """Collapse whitespace and drop the paragraph sign some editions carry."""
    text = text.replace(PILCROW, " ")
    text = re.sub(r"\s+", " ", text).strip()
    # A space left in front of punctuation by a dropped marker.
    return re.sub(r"\s+([,.;:!?\)])", r"\1", text)


def local(tag):
    """An XML tag without its namespace, lower case."""
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""
