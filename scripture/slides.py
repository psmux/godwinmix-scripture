"""Cut a passage or a song into slides that fit the box they are shown in.

A slide is {text, ref, label}. `text` is the words, `ref` the line under or
over them (the reference, or a song's credit line), `label` what the operator
sees in the slide list ("3:16", "V1", "C (2/2)").

The size of a slide comes from the style: so many characters a line, so many
lines a slide. A passage is packed verse by verse; a verse too long for one
slide is cut at the end of a sentence or a clause, and only as a last resort
between words. A song section longer than a slide is cut into even parts at
line ends.
"""
import math
import re

from . import bible, books

SUPERSCRIPT = str.maketrans("0123456789", "".join(chr(c) for c in (
    0x2070, 0x00B9, 0x00B2, 0x00B3, 0x2074, 0x2075, 0x2076, 0x2077, 0x2078, 0x2079)))


def superscript(number):
    return str(number).translate(SUPERSCRIPT)


def wrap(text, per_line):
    """Lines of at most per_line characters, broken at spaces. Long words stay whole."""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            if current and len(current) + 1 + len(word) > per_line:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word) if current else word
        lines.append(current)
    return lines


def line_count(text, per_line):
    return len(wrap(text, per_line))


def _pieces(text, per_line, max_lines):
    """Cut one over long verse into pieces that each fit a slide."""
    if line_count(text, per_line) <= max_lines:
        return [text]
    for pattern in (r"(?<=[.!?])\s+", r"(?<=[;:])\s+", r"(?<=,)\s+", r"\s+"):
        parts = [p for p in re.split(pattern, text) if p]
        if len(parts) < 2:
            continue
        out, current = [], ""
        for part in parts:
            joined = (current + " " + part) if current else part
            if current and line_count(joined, per_line) > max_lines:
                out.append(current)
                current = part
            else:
                current = joined
        out.append(current)
        if all(line_count(p, per_line) <= max_lines for p in out):
            return out
        # Something still too long: cut that piece again with a finer break.
        finer = []
        for p in out:
            finer.extend(_pieces(p, per_line, max_lines) if line_count(p, per_line) > max_lines
                         and p != text else [p])
        if all(line_count(p, per_line) <= max_lines for p in finer):
            return finer
    return [text]


def bible_slides(rows, abbreviation, cap, numbers=True):
    """Slides for a passage. rows are (book, chapter, verse, text)."""
    per_line, max_lines = cap
    units = []  # (row, words) with a long verse split into several units
    show_numbers = numbers and len(rows) > 1
    for row in rows:
        lead = superscript(row[2]) + " " if show_numbers else ""
        for i, piece in enumerate(_pieces(row[3], per_line, max_lines)):
            units.append((row, (lead if i == 0 else "") + piece))
    groups, current = [], []
    for unit in units:
        trial = " ".join(u[1] for u in current + [unit])
        if current and line_count(trial, per_line) > max_lines:
            groups.append(current)
            current = [unit]
        else:
            current.append(unit)
    if current:
        groups.append(current)
    groups = _balance(groups, per_line, max_lines)
    book = books.BY_NUMBER[rows[0][0]] if rows else None
    slides = []
    for group in groups:
        verse_rows = []
        for row, _ in group:
            if not verse_rows or verse_rows[-1] != row:
                verse_rows.append(row)
        ref = bible.label(verse_rows, book)
        part = ""
        if len(verse_rows) == 1:
            same = [i for i, g in enumerate(groups) if any(r is verse_rows[0] for r, _ in g)]
            if len(same) > 1:
                part = " (%d/%d)" % (same.index(groups.index(group)) + 1, len(same))
        slides.append({
            "text": " ".join(u[1] for u in group),
            "ref": (ref + " " + abbreviation).strip(),
            "label": ref.split(" ")[-1] + part,
            "verses": [[r[1], r[2]] for r in verse_rows],
        })
    return slides


def _balance(groups, per_line, max_lines):
    """Move verses back from a crowded slide so the last one is not a stub."""
    if len(groups) < 2:
        return groups
    last, prev = groups[-1], groups[-2]
    while len(prev) > 1:
        moved = [prev[-1]] + last
        if line_count(" ".join(u[1] for u in moved), per_line) > max_lines:
            break
        if line_count(" ".join(u[1] for u in moved), per_line) > \
                line_count(" ".join(u[1] for u in prev[:-1]), per_line) + 1:
            break
        prev, last = prev[:-1], moved
    return groups[:-2] + [prev, last]


def _chunks(lines, per_line, max_lines):
    """Split a section's lines into even parts that each fit a slide."""
    heights = [max(1, line_count(ln, per_line)) for ln in lines]
    if sum(heights) <= max_lines:
        return [lines]
    parts = max(2, math.ceil(sum(heights) / float(max_lines)))
    while True:
        target = math.ceil(sum(heights) / float(parts))
        out, current, used = [], [], 0
        for ln, h in zip(lines, heights):
            if current and (used + h > max_lines or (used >= target and len(out) < parts - 1)):
                out.append(current)
                current, used = [], 0
            current.append(ln)
            used += h
        out.append(current)
        if all(sum(max(1, line_count(x, per_line)) for x in c) <= max_lines for c in out) or parts > 40:
            return out
        parts += 1


def credit(song, licence="", style="full"):
    """The line a church's CCLI licence asks to be shown with the words."""
    bits = [song["title"]]
    if song.get("author"):
        bits.append(song["author"])
    if song.get("copyright"):
        bits.append(chr(0x00A9) + " " + song["copyright"].lstrip(chr(0x00A9) + " ").strip())
    if song.get("ccli"):
        bits.append("CCLI Song # " + song["ccli"])
    if licence:
        bits.append("CCLI Licence # " + licence)
    return ". ".join(b.rstrip(".") for b in bits)


def song_slides(song, cap, order=None, licence="", footer="first"):
    """Slides for a song in the given order (the song's own when None)."""
    per_line, max_lines = cap
    by_id = {s["id"]: s for s in song["sections"]}
    order = order or song["order"]
    slides = []
    line = credit(song, licence)
    for n, sid in enumerate(order):
        section = by_id[sid]
        chunks = _chunks(section["lines"], per_line, max_lines)
        for i, chunk in enumerate(chunks):
            label = sid if len(chunks) == 1 else "%s (%d/%d)" % (sid, i + 1, len(chunks))
            slides.append({"text": "\n".join(chunk), "ref": "", "label": label, "section": sid,
                           "order_index": n})
    if slides and footer in ("first", "every"):
        for i, slide in enumerate(slides):
            if footer == "every" or i == 0 or i == len(slides) - 1:
                slide["ref"] = line
    return slides
