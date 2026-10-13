"""How words look on the programme.

A style is two text layers, the words and a reference line, each a box on the
canvas and the params the mixer's own text source takes (font, size, colour,
shadow, box and so on). Styles are drawn on a 1920 by 1080 grid and scaled to
the canvas, so the same style fits 720p and 1080p. Every word sits inside
title safe (96 to 1824 across, 54 to 1026 down) unless the operator moves the
margin.

The mixer draws the text itself, with no browser and no template, so a
change of words is a param change on a source that is already there: the new
words replace the old on the next frame.
"""
import copy
import re

BASE_W, BASE_H = 1920, 1080
SERIF = "Georgia, DejaVu Serif, Serif"
SANS = "Segoe UI, Noto Sans, DejaVu Sans, Sans"

STYLES = {
    "lower-third": {
        "title": "Lower third",
        "description": "A dark band across the bottom with the reference on a gold tab. Sits over a camera.",
        "for": ["bible", "song"],
        "body": {"rect": [96, 770, 1728, 240], "font": SANS, "size": 42, "weight": 500,
                 "color": "#ffffff", "background": "#0e1726e8", "padding": 30, "radius": 10,
                 "align": "left", "valign": "middle", "shadow": False, "outline": ""},
        "ref": {"rect": [96, 708, 0, 56], "font": SANS, "size": 30, "weight": 700,
                "color": "#1d1607", "background": "#f2c14eff", "padding": 12, "radius": 8,
                "align": "left", "valign": "middle", "shadow": False, "outline": "", "fit": "text"},
    },
    "full-screen": {
        "title": "Full screen",
        "description": "Words centred on a deep blue page with the reference beneath. Covers the camera.",
        "for": ["bible", "song"],
        "body": {"rect": [0, 0, 1920, 1080], "font": SERIF, "size": 62, "weight": 400,
                 "color": "#fbf7ee", "background": "#0b1a2cf7", "padding": 150, "radius": 0,
                 "align": "center", "valign": "middle", "shadow": False, "outline": "",
                 "reserve": 150},
        "ref": {"rect": [96, 900, 1728, 80], "font": SANS, "size": 34, "weight": 600,
                "color": "#f2c14e", "background": "", "padding": 0, "radius": 0,
                "align": "center", "valign": "middle", "shadow": False, "outline": ""},
    },
    "centred-verse": {
        "title": "Centred verse",
        "description": "Large words in the middle of the picture with a soft shadow and no box.",
        "for": ["bible"],
        "body": {"rect": [192, 180, 1536, 600], "font": SERIF, "size": 60, "weight": 600,
                 "color": "#ffffff", "background": "", "padding": 0, "radius": 0,
                 "align": "center", "valign": "bottom", "shadow": True, "outline": "#00000080"},
        "ref": {"rect": [192, 800, 1536, 70], "font": SERIF, "size": 38, "weight": 600, "italic": True,
                "color": "#f2c14e", "background": "", "padding": 0, "radius": 0,
                "align": "center", "valign": "top", "shadow": True, "outline": "#00000080"},
    },
    "lyrics-lower": {
        "title": "Lyrics, lower",
        "description": "Bold centred words at the bottom with an outline, no box. The usual look over a band.",
        "for": ["song", "bible"],
        "body": {"rect": [96, 700, 1728, 300], "font": SANS, "size": 56, "weight": 700,
                 "color": "#ffffff", "background": "", "padding": 0, "radius": 0,
                 "align": "center", "valign": "bottom", "shadow": True, "outline": "#000000c0"},
        "ref": {"rect": [96, 1004, 1728, 34], "font": SANS, "size": 22, "weight": 500,
                "color": "#ffffffd0", "background": "", "padding": 0, "radius": 0,
                "align": "center", "valign": "middle", "shadow": True, "outline": ""},
    },
    "lyrics-full": {
        "title": "Lyrics, full screen",
        "description": "Large centred words on a dark page, for a screen in the room or a stream with no camera.",
        "for": ["song"],
        "body": {"rect": [0, 0, 1920, 1080], "font": SANS, "size": 70, "weight": 700,
                 "color": "#ffffff", "background": "#111111f5", "padding": 140, "radius": 0,
                 "align": "center", "valign": "middle", "shadow": False, "outline": "",
                 "reserve": 90},
        "ref": {"rect": [96, 990, 1728, 40], "font": SANS, "size": 24, "weight": 500,
                "color": "#bbbbbb", "background": "", "padding": 0, "radius": 0,
                "align": "center", "valign": "middle", "shadow": False, "outline": ""},
    },
}

DEFAULTS = {"bible": "lower-third", "song": "lyrics-lower"}
COLOUR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

# How wide an average letter is, and how tall a line is, as a share of the
# letter size. Measured against the mixer's text source with Segoe UI, Georgia
# and DejaVu Sans; a little generous so a slide never runs out of its box.
CHAR_WIDTH = 0.53
LINE_HEIGHT = 1.30

OVERRIDES = {
    "font": "a font family installed on the mixer, or a list ending in Sans or Serif",
    "scale": "letter size as a multiple of the style's own, 0.6 to 1.6",
    "color": "colour of the words, #rrggbb",
    "accent": "colour of the reference, or of its tab in the lower third, #rrggbb",
    "box": "colour of the box behind the words with opacity, #rrggbbaa, or empty for none",
    "shadow": "true for a soft shadow under the words",
    "align": "left, center or right",
    "margin": "extra space inside the safe area, in percent of the canvas, 0 to 15",
}


class StyleError(ValueError):
    pass


def listing():
    return [{"id": sid, "title": s["title"], "description": s["description"], "for": s["for"]}
            for sid, s in STYLES.items()]


def check_overrides(over):
    """Keep only the overrides that mean something, refusing ones that are wrong."""
    clean = {}
    for key, value in (over or {}).items():
        if value is None or value == "" and key not in ("box",):
            continue
        if key == "font":
            clean[key] = str(value)[:120]
        elif key == "scale":
            clean[key] = max(0.6, min(1.6, float(value)))
        elif key in ("color", "accent", "box"):
            if value and not COLOUR.match(str(value)):
                raise StyleError("'%s' is not a colour. Use #rrggbb or #rrggbbaa." % value)
            clean[key] = str(value)
        elif key == "shadow":
            clean[key] = bool(value)
        elif key == "align":
            if value not in ("left", "center", "right"):
                raise StyleError("align is left, center or right, not '%s'." % value)
            clean[key] = value
        elif key == "margin":
            clean[key] = max(0.0, min(15.0, float(value)))
        else:
            raise StyleError("'%s' is not a style setting. These are: %s." % (key, ", ".join(OVERRIDES)))
    return clean


def resolve(style_id, overrides=None):
    """The style with the operator's overrides applied, still on the 1920 grid."""
    if style_id not in STYLES:
        raise StyleError("there is no style '%s'. Pick one of: %s." % (style_id, ", ".join(STYLES)))
    style = copy.deepcopy(STYLES[style_id])
    over = check_overrides(overrides)
    body, ref = style["body"], style["ref"]
    if "font" in over:
        body["font"] = ref["font"] = over["font"]
    if "scale" in over:
        body["size"] = round(body["size"] * over["scale"])
        ref["size"] = round(ref["size"] * (1 + (over["scale"] - 1) / 2))
    if "color" in over:
        body["color"] = over["color"]
    if "accent" in over:
        if ref.get("background"):
            ref["background"] = over["accent"]
        else:
            ref["color"] = over["accent"]
    if "box" in over:
        body["background"] = over["box"]
        if not over["box"] and not body["shadow"]:
            body["shadow"] = True
    if "shadow" in over:
        body["shadow"] = ref["shadow"] = over["shadow"]
    if "align" in over:
        body["align"] = over["align"]
        if not ref.get("background"):
            ref["align"] = over["align"]
    if over.get("margin"):
        _inset(style, over["margin"])
    return style


def _inset(style, percent):
    """Pull every box in from the edges by a share of the canvas."""
    dx, dy = BASE_W * percent / 100.0, BASE_H * percent / 100.0
    for layer in (style["body"], style["ref"]):
        x, y, w, h = layer["rect"]
        if w >= BASE_W - 1:  # a full page keeps its edges and gains padding
            layer["padding"] = layer["padding"] + max(dx, dy)
            continue
        cx = x + w / 2.0
        new_w = max(200, w - 2 * dx) if w else 0
        x = cx - new_w / 2.0 if layer.get("align") == "center" or w > BASE_W / 2 else x + dx
        y = y - dy if y + h / 2 > BASE_H / 2 else y + dy
        layer["rect"] = [x, y, new_w, h]


def capacity(style):
    """(characters a line, lines a slide) for the words box of a resolved style."""
    body = style["body"]
    _, _, w, h = body["rect"]
    pad = body["padding"]
    usable_h = h - 2 * pad - body.get("reserve", 0)
    per_line = int((w - 2 * pad) / (body["size"] * CHAR_WIDTH))
    lines = int(usable_h / (body["size"] * LINE_HEIGHT))
    return max(12, per_line), max(1, lines)


def _scale_rect(rect, canvas):
    sx = canvas["width"] / float(BASE_W)
    sy = canvas["height"] / float(BASE_H)
    x, y, w, h = rect
    return {"x": int(round(x * sx)), "y": int(round(y * sy)),
            "w": int(round(w * sx)), "h": int(round(h * sy))}


def _params(layer, text, rect, scale):
    params = {
        "text": text,
        "font": layer["font"],
        "size": max(8, int(round(layer["size"] * scale))),
        "weight": layer["weight"],
        "italic": bool(layer.get("italic")),
        "color": layer["color"],
        "outline": layer.get("outline", ""),
        "shadow": bool(layer.get("shadow")),
        "background": layer.get("background", ""),
        "padding": int(round(layer["padding"] * scale)),
        "radius": int(round(layer["radius"] * scale)),
        "align": layer["align"],
        "valign": layer["valign"],
        "width": rect["w"],
        "height": rect["h"],
    }
    return params


def layers(style, slide, canvas):
    """The two text layers that put one slide on the programme.

    Each is {id, visible, rect, params}: a source id, whether it shows, where
    it goes in canvas pixels and the text source params. An empty reference
    hides its layer rather than showing an empty tab.
    """
    scale = min(canvas["width"] / float(BASE_W), canvas["height"] / float(BASE_H))
    out = []
    for key, sid, text in (("body", "scripture-body", slide.get("text", "")),
                           ("ref", "scripture-ref", slide.get("ref", ""))):
        layer = style[key]
        x, y, w, h = layer["rect"]
        if layer.get("fit") == "text":
            w = min(BASE_W - 2 * 96, len(text) * layer["size"] * 0.6 + 2 * layer["padding"] + 8)
        rect = _scale_rect([x, y, w, h], canvas)
        out.append({"id": sid, "visible": bool(text.strip()), "rect": rect,
                    "params": _params(layer, text or " ", rect, scale)})
    return out
