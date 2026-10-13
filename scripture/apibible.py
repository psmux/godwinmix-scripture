"""API.Bible, for a translation the church may show but cannot download.

The operator brings their own key from https://scripture.api.bible and puts it
in the plugin's settings. Passages are fetched when they are looked up and
kept in memory only for this session, never written to disk, and the
copyright line API.Bible returns is shown with the words.

API.Bible's terms also ask for usage reports through its Fair Use Management
System; this plugin does not send them, so read those terms before using a
key on air.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .refparse import RefError

BASE = "https://api.scripture.api.bible/v1"


class ApiBible:
    def __init__(self, key, base=BASE, opener=None):
        self.key = (key or "").strip()
        self.base = base.rstrip("/")
        self.opener = opener or urllib.request.urlopen
        self._bibles = None
        self._cache = {}

    def _get(self, path, query=None):
        if not self.key:
            raise RefError("there is no API.Bible key in the plugin's settings. Get one at "
                           "https://scripture.api.bible and set api_bible_key.")
        url = self.base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        request = urllib.request.Request(url, headers={"api-key": self.key, "accept": "application/json"})
        try:
            with self.opener(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RefError("API.Bible refused the key (%d). Check api_bible_key in the "
                               "plugin's settings." % e.code)
            raise RefError("API.Bible answered %d for %s." % (e.code, path))
        except (urllib.error.URLError, OSError) as e:
            raise RefError("could not reach API.Bible: %s. Check this machine is online." % e)

    def bibles(self, language="eng"):
        if self._bibles is None:
            data = self._get("/bibles", {"language": language})["data"]
            self._bibles = [{"id": "api:" + b["id"], "name": b.get("name", ""),
                             "abbreviation": b.get("abbreviationLocal") or b.get("abbreviation") or "",
                             "licence": "Through API.Bible with this church's key", "bundled": False,
                             "api": True} for b in data]
        return self._bibles

    def passage(self, bible_id, ref):
        """Rows for a Reference, and meta with the abbreviation and copyright."""
        rows = []
        copyright_line = ""
        for seg in ref.segments:
            pid = self._passage_id(ref.book.usfm, seg)
            key = (bible_id, pid)
            if key not in self._cache:
                self._cache[key] = self._get("/bibles/%s/passages/%s" % (bible_id, pid), {
                    "content-type": "text", "include-notes": "false", "include-titles": "false",
                    "include-chapter-numbers": "false", "include-verse-numbers": "true",
                    "include-verse-spans": "false"})["data"]
            data = self._cache[key]
            copyright_line = (data.get("copyright") or "").strip()
            rows.extend(split_verses(ref.book.number, seg.c1, data.get("content", "")))
        meta = {"id": "api:" + bible_id, "abbreviation": self._abbreviation(bible_id),
                "copyright": copyright_line}
        if not rows:
            raise RefError("API.Bible returned no verses for %s." % ref.display())
        return rows, meta

    def _abbreviation(self, bible_id):
        for b in self._bibles or []:
            if b["id"] == "api:" + bible_id:
                return b["abbreviation"]
        return ""

    @staticmethod
    def _passage_id(usfm, seg):
        if seg.v1 is None and seg.v2 is None and seg.c1 == seg.c2:
            return "%s.%d" % (usfm, seg.c1)
        start = "%s.%d.%d" % (usfm, seg.c1, seg.v1 or 1)
        end = "%s.%d" % (usfm, seg.c2) if seg.v2 is None else "%s.%d.%d" % (usfm, seg.c2, seg.v2)
        return start if start == end else "%s-%s" % (start, end)


def split_verses(book, chapter, content):
    """"[16] For God ... [17] For God sent" into rows. A verse number going
    down means the passage has crossed into the next chapter."""
    rows = []
    last = 0
    parts = re.split(r"\[(\d+)\]", content)
    for i in range(1, len(parts) - 1, 2):
        verse = int(parts[i])
        if verse < last:
            chapter += 1
        last = verse
        words = re.sub(r"\s+", " ", parts[i + 1]).strip()
        if words:
            rows.append((book, chapter, verse, words))
    return rows
