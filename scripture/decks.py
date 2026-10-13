"""A deck: the slides for one passage or one song, in one style, ready to show.

A deck remembers what it was made from, so when the operator picks another
style it is cut again for the new box rather than squeezed into it.
"""
import itertools

from . import bible, refparse, slides, styles

_ids = itertools.count(1)


def new_id(kind):
    return "%s-%d" % (kind, next(_ids))


def bible_deck(service, reference, translation=None):
    tid = translation or service.settings["default_translation"]
    ref = refparse.parse(reference, service.translation_ids())
    if ref.translation:
        tid = ref.translation
    if tid.startswith("api:"):
        rows, meta = service.api_bible().passage(tid[4:], ref)
    else:
        trans = service.bibles.get(tid)
        rows, meta = trans.passage(ref), trans.meta
    abbreviation = meta.get("abbreviation") or tid.upper()
    deck = {
        "id": new_id("bible"),
        "kind": "bible",
        "title": "%s %s" % (bible.label(rows, ref.book), abbreviation),
        "reference": ref.display(),
        "translation": tid,
        "copyright": meta.get("copyright", ""),
        "source": {"reference": reference, "translation": tid},
        "_rows": rows,
        "_abbreviation": abbreviation,
    }
    return cut(service, deck)


def song_deck(service, song_id, order=None):
    song = service.songs.get(song_id)
    if isinstance(order, str) and order.strip():
        from .songs import parse_order
        order = parse_order(order, song["sections"])
    deck = {
        "id": new_id("song"),
        "kind": "song",
        "title": song["title"],
        "song": song["id"],
        "order": order or song["order"],
        "source": {"song": song["id"], "order": order},
        "_song": song,
    }
    return cut(service, deck)


def cut(service, deck):
    """(Re)make a deck's slides and layers for the style now chosen for its kind."""
    chosen = service.style[deck["kind"]]
    style = styles.resolve(chosen["id"], chosen.get("overrides"))
    cap = styles.capacity(style)
    if deck["kind"] == "bible":
        made = slides.bible_slides(deck["_rows"], deck["_abbreviation"], cap,
                                   numbers=service.settings["verse_numbers"])
        if deck.get("copyright"):
            for s in made:
                s["ref"] = "%s. %s" % (s["ref"], deck["copyright"])
    else:
        made = slides.song_slides(deck["_song"], cap, deck["order"],
                                  licence=service.settings["ccli_licence"],
                                  footer=service.settings["ccli_footer"])
    for s in made:
        s["layers"] = styles.layers(style, s, service.canvas)
    deck["slides"] = made
    deck["style"] = chosen["id"]
    deck["capacity"] = {"chars_per_line": cap[0], "lines": cap[1]}
    return deck


def public(deck):
    """A deck as a caller sees it: no private working fields."""
    if deck is None:
        return None
    return {k: v for k, v in deck.items() if not k.startswith("_")}
