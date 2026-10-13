"""Range reading and slide cutting: a passage or a song into slides that fit."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripture import bible, refparse, slides, songs, styles  # noqa: E402

WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu".split()


def verse(n, words):
    return (43, 3, n, " ".join(WORDS[i % len(WORDS)] for i in range(words)))


class Ranges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kjv = bible.Library(os.path.join(ROOT, "bibles"), cls.tmp.name).get("kjv")

    @classmethod
    def tearDownClass(cls):
        cls.kjv.close()
        cls.tmp.cleanup()

    def read(self, typed):
        return self.kjv.passage(refparse.parse(typed))

    def test_a_single_verse(self):
        rows = self.read("John 3:16")
        self.assertEqual([(r[1], r[2]) for r in rows], [(3, 16)])
        self.assertTrue(rows[0][3].startswith("For God so loved"))

    def test_a_range_in_one_chapter(self):
        self.assertEqual([r[2] for r in self.read("1 Cor 13:4-7")], [4, 5, 6, 7])

    def test_a_range_across_chapters(self):
        rows = self.read("Gen 1:30-2:3")
        self.assertEqual([(r[1], r[2]) for r in rows], [(1, 30), (1, 31), (2, 1), (2, 2), (2, 3)])

    def test_a_whole_chapter(self):
        self.assertEqual(len(self.read("Ps 23")), 6)
        self.assertEqual(len(self.read("Ps 117")), 2)

    def test_a_chapter_range(self):
        rows = self.read("Ps 23-24")
        self.assertEqual(len(rows), 16)

    def test_pieces_with_commas(self):
        self.assertEqual([r[2] for r in self.read("Rom 8:28, 31-32")], [28, 31, 32])

    def test_a_range_past_the_end_stops_at_the_last_verse(self):
        self.assertEqual(self.read("John 3:35-40")[-1][2], 36)

    def test_a_verse_past_the_end_is_refused(self):
        with self.assertRaises(refparse.RefError) as caught:
            self.read("John 3:40")
        self.assertIn("36 verses", str(caught.exception))

    def test_the_label_of_what_a_slide_holds(self):
        self.assertEqual(bible.label(self.read("John 3:16-17")), "John 3:16-17")
        self.assertEqual(bible.label(self.read("Gen 1:31-2:1")), "Genesis 1:31-2:1")
        self.assertEqual(bible.label(self.read("Ps 23:1")), "Psalm 23:1")

    def test_search_finds_a_phrase(self):
        found = [bible.label([r]) for r in self.kjv.search("lamp unto my feet")]
        self.assertEqual(found[0], "Psalm 119:105")


class Wrapping(unittest.TestCase):
    def test_wrap_breaks_at_spaces(self):
        self.assertEqual(slides.wrap("aaa bbb ccc", 7), ["aaa bbb", "ccc"])
        self.assertEqual(slides.line_count("one\ntwo three", 20), 2)

    def test_superscript_numbers(self):
        self.assertEqual(slides.superscript(16), chr(0xB9) + chr(0x2076))


class BibleSlides(unittest.TestCase):
    CAP = (40, 3)  # 40 characters a line, 3 lines a slide

    def test_short_verses_share_a_slide(self):
        rows = [verse(1, 4), verse(2, 4), verse(3, 4)]
        made = slides.bible_slides(rows, "KJV", self.CAP)
        self.assertEqual(len(made), 1)
        self.assertEqual(made[0]["ref"], "John 3:1-3 KJV")
        self.assertTrue(made[0]["text"].startswith(chr(0xB9) + " alpha"))

    def test_one_verse_has_no_number(self):
        made = slides.bible_slides([verse(16, 5)], "KJV", self.CAP)
        self.assertFalse(made[0]["text"][0].isdigit() or made[0]["text"][0] == chr(0xB9))
        self.assertEqual(made[0]["label"], "3:16")

    def test_verse_numbers_can_be_turned_off(self):
        made = slides.bible_slides([verse(1, 3), verse(2, 3)], "KJV", self.CAP, numbers=False)
        self.assertTrue(made[0]["text"].startswith("alpha"))

    def test_a_long_passage_splits_at_verse_ends(self):
        rows = [verse(n, 12) for n in range(1, 9)]
        made = slides.bible_slides(rows, "KJV", self.CAP)
        self.assertGreater(len(made), 2)
        seen = [v for s in made for v in s["verses"]]
        self.assertEqual([v[1] for v in seen], list(range(1, 9)))
        for s in made:
            self.assertLessEqual(slides.line_count(s["text"], 40), 3, s["text"])

    def test_a_verse_too_long_for_a_slide_is_cut_at_a_sentence(self):
        text = "First part of this verse is here. Second part goes on and on. Third part ends it all."
        made = slides.bible_slides([(43, 3, 16, text)], "KJV", (30, 2))
        self.assertGreater(len(made), 1)
        self.assertTrue(all(s["text"].endswith(".") for s in made))
        self.assertEqual(made[0]["label"], "3:16 (1/%d)" % len(made))
        self.assertEqual(" ".join(s["text"] for s in made), text)

    def test_no_words_are_lost(self):
        rows = [verse(n, 7 + n * 3) for n in range(1, 12)]
        made = slides.bible_slides(rows, "KJV", (36, 4), numbers=False)
        self.assertEqual(" ".join(s["text"] for s in made).split(), " ".join(r[3] for r in rows).split())

    def test_the_last_slide_is_not_a_stub_when_it_can_be_helped(self):
        rows = [verse(n, 5) for n in range(1, 8)]
        made = slides.bible_slides(rows, "", (30, 4), numbers=False)
        sizes = [slides.line_count(s["text"], 30) for s in made]
        self.assertLessEqual(max(sizes) - min(sizes), 2, sizes)


class SongSlides(unittest.TestCase):
    def song(self):
        return songs.normalise({
            "title": "Test Hymn", "author": "A. Writer", "ccli": "123", "copyright": "Public domain",
            "sections": [
                {"id": "V1", "lines": ["one", "two", "three", "four"]},
                {"id": "C", "lines": ["chorus a", "chorus b"]},
                {"id": "V2", "lines": ["l%d" % i for i in range(1, 10)]},
            ],
            "order": "V1 C V2 C",
        })

    def test_order_is_followed(self):
        made = slides.song_slides(self.song(), (40, 4))
        self.assertEqual([s["section"] for s in made], ["V1", "C", "V2", "V2", "V2", "C"])

    def test_a_long_section_is_split_evenly(self):
        made = slides.song_slides(self.song(), (40, 4))
        parts = [s["text"].count("\n") + 1 for s in made if s["section"] == "V2"]
        self.assertEqual(parts, [3, 3, 3])
        self.assertEqual(made[2]["label"], "V2 (1/3)")

    def test_credit_on_first_and_last_slides(self):
        made = slides.song_slides(self.song(), (40, 4), licence="999")
        self.assertIn("CCLI Song # 123", made[0]["ref"])
        self.assertIn("CCLI Licence # 999", made[0]["ref"])
        self.assertEqual(made[1]["ref"], "")
        self.assertTrue(made[-1]["ref"])

    def test_credit_can_be_left_off(self):
        made = slides.song_slides(self.song(), (40, 4), footer="none")
        self.assertTrue(all(not s["ref"] for s in made))

    def test_an_order_naming_a_missing_section_is_refused(self):
        with self.assertRaises(songs.SongError) as caught:
            songs.parse_order("V1 B", self.song()["sections"])
        self.assertIn("B", str(caught.exception))

    def test_a_chorus_written_twice_is_one_section_sung_twice(self):
        song = songs.normalise({"title": "x", "sections": [
            {"id": "V1", "lines": ["a"]}, {"id": "C", "lines": ["c"]},
            {"id": "V2", "lines": ["b"]}, {"id": "C", "lines": ["c"]}]})
        self.assertEqual([s["id"] for s in song["sections"]], ["V1", "C", "V2"])
        self.assertEqual(song["order"], ["V1", "C", "V2", "C"])


class Styles(unittest.TestCase):
    def test_every_style_gives_two_layers_inside_the_canvas(self):
        for canvas in ({"width": 1280, "height": 720}, {"width": 1920, "height": 1080}):
            for sid in styles.STYLES:
                with self.subTest(style=sid, canvas=canvas["width"]):
                    style = styles.resolve(sid)
                    layers = styles.layers(style, {"text": "words", "ref": "John 3:16 KJV"}, canvas)
                    self.assertEqual([l["id"] for l in layers], ["scripture-body", "scripture-ref"])
                    for l in layers:
                        r = l["rect"]
                        self.assertGreaterEqual(r["x"], 0)
                        self.assertGreaterEqual(r["y"], 0)
                        self.assertLessEqual(r["x"] + r["w"], canvas["width"])
                        self.assertLessEqual(r["y"] + r["h"], canvas["height"])
                        self.assertEqual(l["params"]["width"], r["w"])

    def test_capacity_is_the_same_at_720p_and_1080p(self):
        style = styles.resolve("lower-third")
        self.assertEqual(styles.capacity(style), styles.capacity(styles.resolve("lower-third")))
        self.assertGreaterEqual(styles.capacity(style)[1], 3)

    def test_overrides(self):
        style = styles.resolve("lower-third", {"scale": 1.5, "color": "#ffcc00", "box": "", "align": "center"})
        self.assertEqual(style["body"]["size"], round(styles.STYLES["lower-third"]["body"]["size"] * 1.5))
        self.assertEqual(style["body"]["color"], "#ffcc00")
        self.assertEqual(style["body"]["background"], "")
        self.assertTrue(style["body"]["shadow"])
        bigger = styles.capacity(style)
        self.assertLess(bigger[0], styles.capacity(styles.resolve("lower-third"))[0])

    def test_margin_pulls_boxes_in(self):
        plain = styles.resolve("lower-third")["body"]["rect"]
        inset = styles.resolve("lower-third", {"margin": 5})["body"]["rect"]
        self.assertGreater(inset[0], plain[0])
        self.assertLess(inset[2], plain[2])

    def test_bad_overrides_are_refused(self):
        with self.assertRaises(styles.StyleError):
            styles.resolve("lower-third", {"color": "red"})
        with self.assertRaises(styles.StyleError):
            styles.resolve("lower-third", {"sparkle": True})
        with self.assertRaises(styles.StyleError):
            styles.resolve("no-such-style")

    def test_an_empty_reference_hides_its_layer(self):
        layers = styles.layers(styles.resolve("lyrics-lower"), {"text": "a line", "ref": ""}, {"width": 1280, "height": 720})
        self.assertFalse(layers[1]["visible"])


if __name__ == "__main__":
    unittest.main()
