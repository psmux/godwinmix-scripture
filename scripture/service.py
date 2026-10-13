"""The plugin's state and every tool it answers.

The service holds the libraries, the decks that have been prepared, and what
is live: which deck, which slide, whether the screen is blanked. It does not
talk to the mixer itself. The panel asks it for the layers of a slide and
puts them on the programme with the mixer's public methods, then the service
knows what is on air and the stage display can show it.
"""
import base64
import os
import threading

from . import apibible, bible, decks, songs, styles

DEFAULT_SETTINGS = {
    "default_translation": "kjv",
    "verse_numbers": True,
    "ccli_licence": "",
    "ccli_footer": "first",
    "bible_style": "lower-third",
    "song_style": "lyrics-lower",
    "api_bible_key": "",
    "stage_bind": "0.0.0.0",
    "stage_port": 8091,
    "data_dir": "",
}

UPLOAD_LIMIT = 64 * 1024 * 1024
KEEP_DECKS = 30


class ToolError(Exception):
    """A refusal to show the caller, with data they can act on."""

    def __init__(self, message, **data):
        super().__init__(message)
        self.data = data


class Service:
    def __init__(self, root, canvas, settings=None):
        self.root = root
        self.canvas = canvas or {"width": 1920, "height": 1080, "fps": 30}
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings.update({k: v for k, v in (settings or {}).items() if v is not None})
        self.data_dir = self.settings["data_dir"] or default_data_dir(root)
        os.makedirs(self.data_dir, exist_ok=True)
        self.bibles = bible.Library(os.path.join(root, "bibles"), self.data_dir)
        self.songs = songs.Library(self.data_dir)
        self.style = {"bible": {"id": self.settings["bible_style"], "overrides": {}},
                      "song": {"id": self.settings["song_style"], "overrides": {}}}
        self.decks = {}
        self.live = {"deck": None, "index": 0, "blank": False, "on_air": False}
        self.uploads = {}
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.version = 0
        self.stage = None
        self._api = None

    # --- settings -----------------------------------------------------------

    def configure(self, params):
        with self.lock:
            restart = []
            for key, value in (params or {}).items():
                if key not in DEFAULT_SETTINGS:
                    continue
                if key in ("data_dir", "stage_bind", "stage_port") and value != self.settings[key]:
                    restart.append(key)
                self.settings[key] = value
            if "api_bible_key" in (params or {}):
                self._api = None
            for kind in ("bible", "song"):
                wanted = self.settings[kind + "_style"]
                if wanted in styles.STYLES and wanted != self.style[kind]["id"]:
                    self.style[kind] = {"id": wanted, "overrides": {}}
        if restart:
            return {"applied": False, "restart_required": True,
                    "reason": "%s take effect when the plugin starts again: call plugin.reload "
                              "for scripture." % ", ".join(restart)}
        return {"applied": True}

    def translation_ids(self):
        ids = self.bibles.ids()
        if self._api is not None and self._api._bibles:
            ids += [b["id"] for b in self._api._bibles]
        return ids

    def api_bible(self):
        if self._api is None:
            self._api = apibible.ApiBible(self.settings.get("api_bible_key"))
        return self._api

    # --- state --------------------------------------------------------------

    def _touch(self):
        self.version += 1
        self.changed.notify_all()

    def _keep(self, deck):
        self.decks[deck["id"]] = deck
        while len(self.decks) > KEEP_DECKS:
            oldest = next(iter(self.decks))
            if self.live["deck"] is self.decks[oldest]:
                self.decks[oldest] = self.decks.pop(oldest)  # keep the live one, move it last
                continue
            del self.decks[oldest]
        return decks.public(deck)

    def state(self, full=True):
        with self.lock:
            deck = self.live["deck"]
            index = self.live["index"]
            current = deck["slides"][index] if deck else None
            following = deck["slides"][index + 1] if deck and index + 1 < len(deck["slides"]) else None
            out = {
                "version": self.version,
                "on_air": self.live["on_air"],
                "blank": self.live["blank"],
                "index": index,
                "deck": decks.public(deck) if (deck and full) else (
                    {"id": deck["id"], "title": deck["title"], "kind": deck["kind"],
                     "count": len(deck["slides"])} if deck else None),
                "current": current,
                "next": following,
                "style": self.style,
                "canvas": self.canvas,
                "stage": self.stage.urls() if self.stage else None,
            }
            return out

    def _go(self, deck, index):
        if not deck["slides"]:
            raise ToolError("that deck has no slides.")
        index = max(0, min(int(index), len(deck["slides"]) - 1))
        self.live.update(deck=deck, index=index, blank=False, on_air=True)
        self._touch()
        return self._answer()

    def _answer(self):
        st = self.state(full=False)
        current = st["current"]
        st["layers"] = current["layers"] if current else []
        return st

    def _deck(self, deck_id):
        deck = self.decks.get(deck_id)
        if deck is None:
            if self.live["deck"] and self.live["deck"]["id"] == deck_id:
                return self.live["deck"]
            raise ToolError("there is no prepared deck '%s'. Look the passage or song up again "
                            "with lookup or song_deck." % deck_id, deck=deck_id)
        return deck


def default_data_dir(root):
    """Beside the installed versions, so an update keeps the songs and imports.

    The mixer installs a plugin into <plugins>/<name>/<version>/. One level up
    is the plugin's own folder, which no other plugin writes to.
    """
    parent = os.path.dirname(os.path.abspath(root))
    if os.path.basename(parent) == "scripture":
        return os.path.join(parent, "data")
    return os.path.join(os.path.abspath(root), "data")


def decode_upload(arguments):
    if "content" in arguments and arguments["content"] is not None:
        return arguments["content"]
    if arguments.get("data_base64"):
        return base64.b64decode(arguments["data_base64"])
    return None

