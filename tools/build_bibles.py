#!/usr/bin/env python3
"""Fetch the bundled translations from ebible.org and convert them.

    python tools/build_bibles.py            check the downloads against the
                                            recorded checksums, then convert
    python tools/build_bibles.py --update   record whatever ebible.org serves
                                            today as the new checksums

ebible.org rebuilds its files now and then, so a checksum that no longer
matches means the text changed upstream, not that something is wrong. Look at
what changed, then run with --update and commit the result.

The conversion goes through the plugin's own USFM importer, so the bundled
text is read the same way an operator's own USFM would be.
"""
import gzip
import hashlib
import io
import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripture.importers import usfm  # noqa: E402

OUT = os.path.join(ROOT, "bibles")
SOURCES = os.path.join(OUT, "sources.json")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "godwinmix-scripture build"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def convert(data):
    files = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in sorted(archive.namelist()):
            if name.lower().endswith(".usfm"):
                files.append((name, archive.read(name).decode("utf-8-sig")))
    return usfm.parse(files)


def write_tsv(rows, path):
    lines = ["%d\t%d\t%d\t%s\n" % (b, c, v, t.replace("\t", " ")) for b, c, v, t in rows]
    body = "".join(lines).encode("utf-8")
    # mtime=0 so the same text always gives the same bytes and the same checksum.
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as f:
            f.write(body)
    return hashlib.sha256(body).hexdigest()


def main():
    update = "--update" in sys.argv
    with open(SOURCES, encoding="utf-8") as f:
        sources = json.load(f)
    for entry in sources["translations"]:
        data = fetch(entry["url"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.get("sha256_download") and not update:
            sys.exit("%s changed upstream: recorded %s, got %s. Check what changed, then run "
                     "with --update." % (entry["url"], entry.get("sha256_download"), digest))
        entry["sha256_download"] = digest
        rows = convert(data)
        entry["verses"] = len(rows)
        entry["sha256_tsv"] = write_tsv(rows, os.path.join(OUT, entry["file"]))
        print("%s: %d verses from %s" % (entry["id"], len(rows), entry["url"]))
    with open(SOURCES, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
