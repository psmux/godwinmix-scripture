"""Every import format, read from sample files in tests/samples."""
import base64
import gzip
import hashlib
import io
import json
import os
import sys
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "tests", "samples")
sys.path.insert(0, ROOT)

from scripture import importers, lyrics, songs  # noqa: E402
from scripture.importers.common import ImportError_  # noqa: E402


def sample(name, mode="r"):
    with open(os.path.join(SAMPLES, name), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def by_ref(rows):
    return {(r[0], r[1], r[2]): r[3] for r in rows}


class BibleFormats(unittest.TestCase):
    def test_usfm(self):
        fmt, rows, _ = importers.parse("sample.usfm", sample("sample.usfm"))
        self.assertEqual(fmt, "usfm")
        verses = by_ref(rows)
        self.assertEqual(sorted(verses), [(43, 3, 16), (43, 3, 17), (43, 4, 1), (43, 4, 2)])
        v16 = verses[(43, 3, 16)]
        self.assertTrue(v16.startswith("For God so loved the world"))
        self.assertNotIn("footnote", v16)
        self.assertNotIn("strong", v16)
        self.assertNotIn("\\", v16)
        self.assertIn("didn" + chr(0x2019) + "t send", verses[(43, 3, 17)])
        self.assertNotIn("heading", " ".join(verses.values()))

    def test_usfm_in_a_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("44-JHN.usfm", sample("sample.usfm"))
            z.writestr("readme.htm", "<p>not a book</p>")
        fmt, rows, _ = importers.parse("bible.zip", buf.getvalue())
        self.assertEqual(fmt, "usfm")
        self.assertEqual(len(rows), 4)

    def test_osis_containers_and_milestones(self):
        fmt, rows, title = importers.parse("sample.osis.xml", sample("sample.osis.xml"))
        self.assertEqual(fmt, "osis")
        self.assertEqual(title, "Sample King James Version")
        verses = by_ref(rows)
        self.assertEqual(verses[(19, 23, 1)], "The LORD is my shepherd; I shall not want.")
        self.assertNotIn("note", verses[(19, 23, 2)])
        self.assertNotIn("Psalm of David", " ".join(verses.values()))
        self.assertEqual(verses[(43, 11, 35)], "Jesus wept.")
        self.assertTrue(verses[(43, 11, 36)].startswith("Then said the Jews"))

    def test_zefania(self):
        fmt, rows, title = importers.parse("sample.zefania.xml", sample("sample.zefania.xml"))
        self.assertEqual(fmt, "zefania")
        self.assertEqual(title, "Sample Zefania Bible")
        verses = by_ref(rows)
        self.assertEqual(verses[(1, 1, 1)], "In the beginning God created the heaven and the earth.")
        self.assertNotIn("note", verses[(1, 1, 2)].lower())
        self.assertEqual(verses[(62, 4, 8)], "He that loveth not knoweth not God; for God is love.")

    def test_csv_with_names_abbreviations_and_codes(self):
        fmt, rows, _ = importers.parse("sample.csv", sample("sample.csv"))
        self.assertEqual(fmt, "csv")
        self.assertEqual(sorted(by_ref(rows)), [(45, 8, 28), (45, 8, 31), (46, 13, 13), (50, 4, 13)])
        self.assertIn("If God be for us", by_ref(rows)[(45, 8, 31)])

    def test_tab_separated_with_numbers(self):
        _, rows, _ = importers.parse("t.tsv", "43\t11\t35\tJesus wept.\n")
        self.assertEqual(rows, [(43, 11, 35, "Jesus wept.")])

    def test_a_file_that_is_not_a_bible(self):
        with self.assertRaises(ImportError_) as caught:
            importers.parse("notes.txt", "shopping list\nmilk\n")
        self.assertIn("book,chapter,verse,text", str(caught.exception))

    def test_broken_xml_says_so(self):
        with self.assertRaises(ImportError_) as caught:
            importers.parse("x.xml", "<osis><verse osisID='John.1.1'>unclosed")
        self.assertIn("not well formed", str(caught.exception))

    def test_bytes_with_a_byte_order_mark(self):
        data = b"\xef\xbb\xbf" + sample("sample.csv").encode("utf-8")
        self.assertEqual(len(importers.parse("s.csv", data)[1]), 4)


class LyricFormats(unittest.TestCase):
    def test_plain_text_with_bare_headings(self):
        fmt, song = lyrics.parse(sample("abide-with-me.txt"), "abide-with-me.txt")
        song = songs.normalise(song)
        self.assertEqual(fmt, "text")
        self.assertEqual(song["title"], "Abide With Me")
        self.assertEqual(song["author"], "Henry Francis Lyte")
        self.assertEqual([s["id"] for s in song["sections"]], ["V1", "V2"])
        self.assertEqual(len(song["sections"][0]["lines"]), 4)

    def test_plain_text_with_a_chorus_written_out_twice(self):
        _, song = lyrics.parse(sample("it-is-well.txt"), "it-is-well.txt")
        song = songs.normalise(song)
        self.assertEqual(song["title"], "It Is Well")
        self.assertEqual([s["id"] for s in song["sections"]], ["V1", "C", "V2"])
        self.assertEqual(song["order"], ["V1", "C", "V2", "C"])

    def test_openlyrics(self):
        fmt, song = lyrics.parse(sample("holy-holy-holy.xml"), "holy-holy-holy.xml")
        song = songs.normalise(song)
        self.assertEqual(fmt, "openlyrics")
        self.assertEqual(song["title"], "Holy, Holy, Holy")
        self.assertEqual(song["author"], "Reginald Heber")
        self.assertEqual(song["ccli"], "1156")
        self.assertEqual(song["order"], ["V1", "V2", "V1"])
        v2 = song["sections"][1]["lines"]
        self.assertEqual(len(v2), 4)
        self.assertNotIn("quietly", " ".join(v2))
        self.assertTrue(song["sections"][0]["lines"][0].startswith("Holy, holy, holy!"))

    def test_chordpro_strips_chords_and_tabs(self):
        fmt, song = lyrics.parse(sample("be-thou-my-vision.cho"), "be-thou-my-vision.cho")
        song = songs.normalise(song)
        self.assertEqual(fmt, "chordpro")
        self.assertEqual(song["title"], "Be Thou My Vision")
        self.assertEqual([s["id"] for s in song["sections"]], ["V1", "V2"])
        words = " ".join(" ".join(s["lines"]) for s in song["sections"])
        self.assertNotIn("[", words)
        self.assertNotIn("e|", words)
        self.assertNotIn("comment", words)
        self.assertTrue(song["sections"][0]["lines"][0].startswith("Be Thou my Vision, O Lord"))

    def test_chordpro_chorus_block(self):
        _, song = lyrics.parse("{t: Short}\n{soc}\n[C]Sing [G]out\n{eoc}\nA verse line\n", "s.cho")
        song = songs.normalise(song)
        self.assertEqual([s["id"] for s in song["sections"]], ["C", "V1"])
        self.assertEqual(song["sections"][0]["lines"], ["Sing out"])

    def test_round_trip_through_the_editor_text(self):
        _, song = lyrics.parse(sample("holy-holy-holy.xml"), "x.xml")
        song = songs.normalise(song)
        _, again = lyrics.parse(songs.to_text(song), "", "text")
        again = songs.normalise(again)
        self.assertEqual(again["sections"], song["sections"])
        self.assertEqual(again["order"], song["order"])
        self.assertEqual(again["ccli"], song["ccli"])

    def test_a_song_with_no_words_is_refused(self):
        with self.assertRaises(songs.SongError):
            songs.normalise({"title": "Empty", "sections": []})


class Bundled(unittest.TestCase):
    def test_bundled_files_match_their_recorded_checksums(self):
        with open(os.path.join(ROOT, "bibles", "sources.json"), encoding="utf-8") as f:
            sources = json.load(f)["translations"]
        self.assertEqual({t["id"] for t in sources}, {"kjv", "web"})
        for t in sources:
            with gzip.open(os.path.join(ROOT, "bibles", t["file"]), "rb") as f:
                body = f.read()
            self.assertEqual(hashlib.sha256(body).hexdigest(), t["sha256_tsv"], t["id"])
            self.assertEqual(body.count(b"\n"), t["verses"])
            self.assertTrue(t["url"].startswith("https://ebible.org/"))
            self.assertIn("ublic domain", t["licence"])

    def test_the_kjv_has_every_verse(self):
        with open(os.path.join(ROOT, "bibles", "sources.json"), encoding="utf-8") as f:
            kjv = [t for t in json.load(f)["translations"] if t["id"] == "kjv"][0]
        self.assertEqual(kjv["verses"], 31102)


class Base64Upload(unittest.TestCase):
    def test_decode_upload(self):
        from scripture.service import decode_upload
        self.assertEqual(decode_upload({"data_base64": base64.b64encode(b"abc").decode()}), b"abc")
        self.assertEqual(decode_upload({"content": "x"}), "x")
        self.assertIsNone(decode_upload({}))


if __name__ == "__main__":
    unittest.main()
