"""Every tool the plugin answers, by name.

Each takes the Service and the arguments object and returns a JSON-able
result. A refusal raises ToolError (or RefError, SongError, StyleError,
ImportError_) with a message that says what is wrong and what to do.
"""
import os
import secrets

from . import bible, decks, importers, lyrics, refparse, songs, styles
from .service import UPLOAD_LIMIT, ToolError, decode_upload

TOOLS = {}
SLOW = set()  # run on a thread of their own so Next is never kept waiting


def tool(name, slow=False):
    def register(fn):
        TOOLS[name] = fn
        if slow:
            SLOW.add(name)
        return fn
    return register


# --- Bible ------------------------------------------------------------------

@tool("translations")
def translations(svc, args):
    return {"translations": svc.bibles.list(), "default": svc.settings["default_translation"]}


@tool("lookup")
def lookup(svc, args):
    reference = (args.get("reference") or "").strip()
    with svc.lock:
        deck = decks.bible_deck(svc, reference, args.get("translation"))
        return {"deck": svc._keep(deck)}


@tool("search")
def search(svc, args):
    tid = (args.get("translation") or svc.settings["default_translation"]).lower()
    trans = svc.bibles.get(tid)
    limit = max(1, min(200, int(args.get("limit") or 50)))
    rows = trans.search(args.get("query") or "", limit)
    results = [{"reference": bible.label([r]), "text": r[3], "translation": tid} for r in rows]
    return {"query": args.get("query") or "", "translation": tid, "results": results}


@tool("find")
def find(svc, args):
    """A reference if the words read as one, a word search if they do not."""
    query = (args.get("query") or "").strip()
    if not query:
        raise ToolError("type a reference such as John 3:16, or some words to search for.")
    if refparse.try_parse(query, svc.translation_ids()):
        out = lookup(svc, {"reference": query, "translation": args.get("translation")})
        out["kind"] = "reference"
        return out
    out = search(svc, args)
    out["kind"] = "search"
    return out


@tool("bible_import", slow=True)
def bible_import(svc, args):
    abbreviation = (args.get("abbreviation") or "").strip()
    if not abbreviation:
        raise ToolError("give the translation an abbreviation, such as NIV, so it can be "
                        "picked and shown on air.")
    licence = (args.get("licence") or "").strip()
    if not licence:
        raise ToolError("say under what right this church shows the translation, for example "
                        "'Licensed to Grace Church by the publisher, 2026'. It is kept with the text.")
    name, data = _payload(svc, args)
    fmt, rows, title = importers.parse(name, data, args.get("format"))
    meta = {"id": abbreviation, "abbreviation": abbreviation.upper(),
            "name": (args.get("title") or title or abbreviation).strip(),
            "licence": licence, "source": "imported by the operator from %s (%s)" % (
                os.path.basename(name), fmt), "language": args.get("language") or ""}
    result = svc.bibles.add(meta, rows)
    return {"imported": result}


@tool("bible_remove")
def bible_remove(svc, args):
    return svc.bibles.remove(args.get("id"))


@tool("api_bibles", slow=True)
def api_bibles(svc, args):
    return {"bibles": svc.api_bible().bibles(args.get("language") or "eng")}


# --- Songs ------------------------------------------------------------------

@tool("songs")
def song_list(svc, args):
    return {"songs": svc.songs.list(args.get("query") or "")}


@tool("song_get")
def song_get(svc, args):
    song = svc.songs.get(args.get("id"))
    return {"song": song, "text": songs.to_text(song)}


@tool("song_save")
def song_save(svc, args):
    if args.get("text"):
        _, song = lyrics.parse(args["text"], "", "text")
    elif isinstance(args.get("song"), dict):
        song = args["song"]
    else:
        raise ToolError("send the song as text (Title:, then [Verse 1] and its lines) or as a "
                        "song object.")
    if args.get("id"):
        song["id"] = args["id"]
    saved = svc.songs.save(song, replace=bool(args.get("id")))
    return {"song": saved}


@tool("song_delete")
def song_delete(svc, args):
    return svc.songs.delete(args.get("id"))


@tool("song_import", slow=True)
def song_import(svc, args):
    name, data = _payload(svc, args)
    text = importers.decode(data)
    fmt, song = lyrics.parse(text, name, args.get("format"))
    saved = svc.songs.save(song, replace=False)
    return {"format": fmt, "song": saved}


@tool("song_deck")
def song_deck(svc, args):
    with svc.lock:
        deck = decks.song_deck(svc, args.get("id"), args.get("order"))
        return {"deck": svc._keep(deck)}


# --- Styles -----------------------------------------------------------------

@tool("styles")
def style_list(svc, args):
    return {"styles": styles.listing(), "current": svc.style, "overrides": styles.OVERRIDES}


@tool("style_set")
def style_set(svc, args):
    kind = args.get("kind") or "bible"
    if kind not in ("bible", "song"):
        raise ToolError("kind is bible or song, not '%s'." % kind)
    with svc.lock:
        chosen = dict(svc.style[kind])
        if args.get("id"):
            chosen["id"] = args["id"]
        if "overrides" in args:
            chosen["overrides"] = styles.check_overrides(args.get("overrides"))
        styles.resolve(chosen["id"], chosen["overrides"])  # refuses a bad one before it sticks
        svc.style[kind] = chosen
        for deck in list(svc.decks.values()):
            if deck["kind"] == kind:
                decks.cut(svc, deck)
        live = svc.live["deck"]
        if live is not None and live["kind"] == kind:
            if live["id"] not in svc.decks:
                decks.cut(svc, live)
            svc.live["index"] = min(svc.live["index"], len(live["slides"]) - 1)
            svc._touch()
        out = svc._answer()
        out["current_style"] = svc.style
        out["decks"] = {d["id"]: decks.public(d) for d in svc.decks.values() if d["kind"] == kind}
        return out


# --- Live -------------------------------------------------------------------

@tool("go")
def go(svc, args):
    with svc.lock:
        return svc._go(svc._deck(args.get("deck")), args.get("index") or 0)


@tool("step")
def step(svc, args):
    with svc.lock:
        deck = svc.live["deck"]
        if deck is None:
            raise ToolError("nothing is live to step through. Pick a passage or a song and press "
                            "Go live first.")
        by = int(args.get("by", 1))
        return svc._go(deck, svc.live["index"] + by)


@tool("blank")
def blank(svc, args):
    with svc.lock:
        if svc.live["deck"] is None:
            raise ToolError("nothing is live to blank.")
        on = args.get("on")
        svc.live["blank"] = (not svc.live["blank"]) if on is None else bool(on)
        svc._touch()
        return svc._answer()


@tool("clear")
def clear(svc, args):
    with svc.lock:
        svc.live.update(on_air=False, blank=False)
        svc._touch()
        return svc._answer()


@tool("state")
def state(svc, args):
    return svc.state(full=True)


@tool("stage")
def stage(svc, args):
    from .stage import StageServer
    with svc.lock:
        if svc.stage is None:
            svc.stage = StageServer(svc)
            svc.stage.start()
        return {"urls": svc.stage.urls()}


# --- Uploads ----------------------------------------------------------------

@tool("upload")
def upload(svc, args):
    """One piece of a file too big for one call. Send them in order, then name
    the upload id in bible_import or song_import."""
    import base64
    uid = args.get("upload") or secrets.token_hex(6)
    seq = int(args.get("seq", 0))
    with svc.lock:
        entry = svc.uploads.setdefault(uid, {"parts": [], "bytes": 0, "name": args.get("name", "")})
        if seq != len(entry["parts"]):
            raise ToolError("upload %s expected piece %d and got %d. Start again with a new upload."
                            % (uid, len(entry["parts"]), seq), expected=len(entry["parts"]))
        piece = base64.b64decode(args.get("data_base64") or "")
        entry["bytes"] += len(piece)
        if entry["bytes"] > UPLOAD_LIMIT:
            svc.uploads.pop(uid, None)
            raise ToolError("that file is over 64 MB, which is bigger than any Bible.")
        entry["parts"].append(piece)
        return {"upload": uid, "seq": seq, "bytes": entry["bytes"]}


def _payload(svc, args):
    """(file name, bytes or text) from an upload id, a path on the mixer, or inline content."""
    name = args.get("name") or ""
    if args.get("upload"):
        entry = svc.uploads.pop(args["upload"], None)
        if entry is None:
            raise ToolError("there is no upload '%s'. Send the file with upload first." % args["upload"])
        return name or entry["name"] or "upload", b"".join(entry["parts"])
    if args.get("path"):
        path = os.path.expanduser(args["path"])
        if not os.path.isfile(path):
            raise ToolError("there is no file at %s on the mixer's machine." % path, path=path)
        with open(path, "rb") as f:
            return name or path, f.read()
    data = decode_upload(args)
    if data is None:
        raise ToolError("send the file as content (text), data_base64, an upload id or a path "
                        "on the mixer's machine.")
    return name or "upload", data


def summarise(name, result):
    """One line a person or a model can read without parsing the JSON."""
    if not isinstance(result, dict):
        return str(result)
    deck = result.get("deck")
    if isinstance(deck, dict) and deck.get("slides"):
        first = deck["slides"][0]["text"].replace("\n", " / ")
        return "%s: %d slide%s. %s" % (deck["title"], len(deck["slides"]),
                                       "" if len(deck["slides"]) == 1 else "s", first[:300])
    if "results" in result:
        hits = result["results"]
        return "%d verse%s for '%s'. %s" % (len(hits), "" if len(hits) == 1 else "s", result["query"],
                                           " | ".join("%s: %s" % (h["reference"], h["text"][:80])
                                                      for h in hits[:5]))
    if "songs" in result:
        return "%d song%s: %s" % (len(result["songs"]), "" if len(result["songs"]) == 1 else "s",
                                  ", ".join(s["title"] for s in result["songs"][:20]))
    if "layers" in result:
        cur = result.get("current")
        if not result.get("on_air"):
            return "off air"
        if result.get("blank"):
            return "blanked"
        return "on air: %s" % (cur["text"].replace("\n", " / ")[:200] if cur else "nothing")
    if "translations" in result:
        return "translations: " + ", ".join("%s (%s)" % (t["id"], t.get("name", ""))
                                            for t in result["translations"])
    return None
