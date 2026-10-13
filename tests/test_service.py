"""The tools, called the way the panel calls them, and the stdio protocol."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "tests", "samples")
sys.path.insert(0, ROOT)

from scripture import apibible, refparse  # noqa: E402
from scripture.service import Service, ToolError  # noqa: E402
from scripture.tools import TOOLS  # noqa: E402

CANVAS = {"width": 1280, "height": 720, "fps": 30}


class Tools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.svc = Service(ROOT, CANVAS, {"data_dir": self.tmp.name, "stage_port": 23098,
                                           "stage_bind": "127.0.0.1", "ccli_licence": "7654321"})

    def tearDown(self):
        if self.svc.stage:
            self.svc.stage.stop()
        for t in list(self.svc.bibles._open.values()):
            t.close()
        self.tmp.cleanup()

    def call(self, _tool, **args):
        return TOOLS[_tool](self.svc, args)

    def test_find_a_reference_then_go_live_and_step(self):
        found = self.call("find", query="jn 3 16-18")
        self.assertEqual(found["kind"], "reference")
        deck = found["deck"]
        self.assertTrue(deck["title"].startswith("John 3:16"))
        self.assertTrue(all(len(s["layers"]) == 2 for s in deck["slides"]))
        live = self.call("go", deck=deck["id"], index=0)
        self.assertTrue(live["on_air"])
        self.assertEqual(live["layers"][0]["id"], "scripture-body")
        self.assertIn("For God so loved", live["layers"][0]["params"]["text"])
        nxt = self.call("step", by=1)
        self.assertEqual(nxt["index"], 1)
        self.assertGreater(nxt["version"], live["version"])
        back = self.call("step", by=-5)
        self.assertEqual(back["index"], 0)

    def test_find_words_is_a_search(self):
        found = self.call("find", query="love one another", translation="kjv")
        self.assertEqual(found["kind"], "search")
        self.assertIn("John 13:34", [r["reference"] for r in found["results"]])

    def test_blank_and_clear(self):
        deck = self.call("lookup", reference="Ps 23")["deck"]
        self.call("go", deck=deck["id"])
        self.assertTrue(self.call("blank")["blank"])
        self.assertFalse(self.call("blank")["blank"])
        self.assertTrue(self.call("blank", on=True)["blank"])
        cleared = self.call("clear")
        self.assertFalse(cleared["on_air"])
        self.assertFalse(cleared["blank"])

    def test_step_with_nothing_live_says_what_to_do(self):
        with self.assertRaises(ToolError) as caught:
            self.call("step", by=1)
        self.assertIn("Go live", str(caught.exception))

    def test_a_deck_that_is_gone(self):
        with self.assertRaises(ToolError):
            self.call("go", deck="bible-99999")

    def test_a_translation_named_in_the_reference(self):
        deck = self.call("lookup", reference="John 3:16 WEB")["deck"]
        self.assertEqual(deck["translation"], "web")
        self.assertIn("only born Son", deck["slides"][0]["text"])

    def test_song_library_and_deck(self):
        with open(os.path.join(SAMPLES, "holy-holy-holy.xml"), encoding="utf-8") as f:
            saved = self.call("song_import", name="holy-holy-holy.xml", content=f.read())["song"]
        self.assertEqual(saved["id"], "holy-holy-holy")
        listed = self.call("songs", query="trinity")["songs"]
        self.assertEqual([s["id"] for s in listed], ["holy-holy-holy"])
        deck = self.call("song_deck", id="holy-holy-holy")["deck"]
        self.assertEqual([s["section"] for s in deck["slides"]], ["V1", "V2", "V1"])
        self.assertIn("CCLI Licence # 7654321", deck["slides"][0]["ref"])
        other = self.call("song_deck", id="holy-holy-holy", order="V2")["deck"]
        self.assertEqual([s["section"] for s in other["slides"]], ["V2"])
        text = self.call("song_get", id="holy-holy-holy")["text"]
        edited = text.replace("Order: V1 V2 V1", "Order: V1 V2")
        again = self.call("song_save", id="holy-holy-holy", text=edited)["song"]
        self.assertEqual(again["order"], ["V1", "V2"])
        self.call("song_delete", id="holy-holy-holy")
        self.assertEqual(self.call("songs")["songs"], [])

    def test_a_new_song_with_the_same_title_gets_its_own_id(self):
        text = "Title: Same\n[Verse 1]\nOne line\n"
        a = self.call("song_save", text=text)["song"]["id"]
        b = self.call("song_save", text=text)["song"]["id"]
        self.assertNotEqual(a, b)

    def test_style_change_recuts_the_live_deck(self):
        deck = self.call("lookup", reference="Ps 23")["deck"]
        self.call("go", deck=deck["id"], index=0)
        before = len(deck["slides"])
        out = self.call("style_set", kind="bible", id="full-screen")
        self.assertEqual(out["current_style"]["bible"]["id"], "full-screen")
        self.assertLess(len(out["decks"][deck["id"]]["slides"]), before)
        self.assertEqual(out["layers"][0]["rect"], {"x": 0, "y": 0, "w": 1280, "h": 720})
        with self.assertRaises(Exception):
            self.call("style_set", kind="bible", id="sparkles")
        self.assertEqual(self.svc.style["bible"]["id"], "full-screen")

    def test_import_a_translation_in_pieces(self):
        with open(os.path.join(SAMPLES, "sample.zefania.xml"), "rb") as f:
            data = f.read()
        uid = None
        for seq, at in enumerate(range(0, len(data), 300)):
            uid = self.call("upload", upload=uid, seq=seq, name="z.xml",
                            data_base64=base64.b64encode(data[at:at + 300]).decode())["upload"]
        done = self.call("bible_import", upload=uid, abbreviation="ZEF", licence="Test text, no rights needed")
        self.assertEqual(done["imported"]["id"], "zef")
        self.assertEqual(done["imported"]["verses"], 3)
        self.assertIn("zef", [t["id"] for t in self.call("translations")["translations"]])
        deck = self.call("lookup", reference="1 John 4:8", translation="zef")["deck"]
        self.assertIn("God is love", deck["slides"][0]["text"])
        self.assertTrue(deck["slides"][0]["ref"].endswith("ZEF"))
        with self.assertRaises(refparse.RefError) as caught:
            self.call("lookup", reference="John 3:16", translation="zef")
        self.assertIn("has no John", str(caught.exception))
        self.call("bible_remove", id="zef")
        self.assertNotIn("zef", [t["id"] for t in self.call("translations")["translations"]])

    def test_import_needs_an_abbreviation_and_a_licence(self):
        with self.assertRaises(ToolError):
            self.call("bible_import", content="43,3,16,x", licence="mine")
        with self.assertRaises(ToolError):
            self.call("bible_import", content="43,3,16,x", abbreviation="MINE")

    def test_bundled_translations_cannot_be_replaced(self):
        with self.assertRaises(refparse.RefError):
            self.call("bible_import", content="43,3,16,x", abbreviation="KJV", licence="no")

    def test_pieces_out_of_order_are_refused(self):
        uid = self.call("upload", seq=0, data_base64=base64.b64encode(b"abc").decode())["upload"]
        with self.assertRaises(ToolError):
            self.call("upload", upload=uid, seq=2, data_base64="")

    def test_stage_display_follows_the_live_slide(self):
        urls = self.call("stage")["urls"]
        self.assertTrue(urls[0].startswith("http://127.0.0.1:23098/"))
        page = urllib.request.urlopen(urls[0], timeout=5).read().decode("utf-8")
        self.assertIn("Stage display", page)
        deck = self.call("lookup", reference="Ps 23")["deck"]
        self.call("go", deck=deck["id"])
        state = json.loads(urllib.request.urlopen(urls[0] + "state?since=-1", timeout=5).read())
        self.assertTrue(state["on_air"])
        self.assertIn("shepherd", state["current"]["text"])
        self.assertIsNotNone(state["next"])
        # A waiting page is answered as soon as the slide changes.
        started = time.time()
        import threading
        threading.Timer(0.4, lambda: self.call("step", by=1)).start()
        moved = json.loads(urllib.request.urlopen(
            urls[0] + "state?since=%d" % state["version"], timeout=10).read())
        self.assertLess(time.time() - started, 5)
        self.assertEqual(moved["index"], 1)


class ApiBible(unittest.TestCase):
    def test_verse_numbers_split_and_cross_a_chapter(self):
        rows = apibible.split_verses(1, 1, "[30] And to every beast. [31] And God saw. [1] Thus the heavens.")
        self.assertEqual([(r[1], r[2]) for r in rows], [(1, 30), (1, 31), (2, 1)])

    def test_passage_ids(self):
        ref = refparse.parse("Gen 1:30-2:3")
        self.assertEqual(apibible.ApiBible._passage_id("GEN", ref.segments[0]), "GEN.1.30-GEN.2.3")
        ref = refparse.parse("Ps 23")
        self.assertEqual(apibible.ApiBible._passage_id("PSA", ref.segments[0]), "PSA.23")

    def test_a_passage_through_a_fake_server(self):
        class Answer:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(self.body).encode()

        seen = []

        def opener(request, timeout=0):
            seen.append((request.full_url, request.headers))
            return Answer({"data": {"content": "[16] Words of a licensed text. [17] More words.",
                                    "copyright": "Copyright line from the publisher"}})

        api = apibible.ApiBible("secret-key", opener=opener)
        rows, meta = api.passage("abc", refparse.parse("John 3:16-17"))
        self.assertEqual([r[2] for r in rows], [16, 17])
        self.assertEqual(meta["copyright"], "Copyright line from the publisher")
        self.assertIn("/bibles/abc/passages/JHN.3.16-JHN.3.17", seen[0][0])
        self.assertEqual(seen[0][1].get("Api-key"), "secret-key")

    def test_no_key_says_where_to_get_one(self):
        with self.assertRaises(refparse.RefError) as caught:
            apibible.ApiBible("").bibles()
        self.assertIn("scripture.api.bible", str(caught.exception))


class Protocol(unittest.TestCase):
    """main.py over stdin and stderr, as the core drives it."""

    def test_handshake_tools_and_shutdown(self):
        tmp = tempfile.TemporaryDirectory()
        lines = [
            {"jsonrpc": "2.0", "id": 0, "result": {"canvas": CANVAS, "params": {"data_dir": tmp.name},
                                                   "instance": "scripture-service", "provide": "service"}},
            {"jsonrpc": "2.0", "id": 1, "method": "health", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tool.call",
             "params": {"name": "scripture/find", "arguments": {"query": "jn 3 16"}}},
            {"jsonrpc": "2.0", "id": 3, "method": "tool.call",
             "params": {"name": "scripture/lookup", "arguments": {"reference": "John 22"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "teleport", "params": {}},
            {"jsonrpc": "2.0", "id": 5, "method": "configure", "params": {"params": {"verse_numbers": False}}},
            {"jsonrpc": "2.0", "id": 6, "method": "shutdown", "params": {"reason": "test"}},
        ]
        stdin = "".join(json.dumps(m) + "\n" for m in lines).encode("utf-8")
        out = subprocess.run([sys.executable, os.path.join(ROOT, "main.py")], input=stdin,
                             capture_output=True, timeout=60)
        self.assertEqual(out.stdout, b"", "stdout must stay empty: it is the media channel")
        got = [json.loads(l) for l in out.stderr.decode("utf-8").splitlines() if l.startswith("{")]
        by_id = {m["id"]: m for m in got if "id" in m and "method" not in m}
        self.assertEqual(got[0]["method"], "initialize")
        self.assertEqual(got[0]["params"]["plugin"], "scripture")
        self.assertTrue(any(m.get("method") == "initialized" for m in got))
        self.assertEqual(by_id[1]["result"]["state"], "ok")
        self.assertIn("John 3:16", by_id[2]["result"]["structuredContent"]["deck"]["title"])
        self.assertTrue(by_id[3]["result"]["isError"])
        self.assertIn("21 chapters", by_id[3]["result"]["content"][0]["text"])
        self.assertEqual(by_id[4]["error"]["code"], -32601)
        self.assertTrue(by_id[5]["result"]["applied"])
        self.assertEqual(by_id[6]["result"], {})
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
