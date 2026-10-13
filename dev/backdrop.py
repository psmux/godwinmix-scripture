#!/usr/bin/env python3
"""Draw a still that stands in for a camera on a church stage, for the real
check and the gallery pictures. A still, so the programme only changes when
the words do, which is what the check measures.

    python dev/backdrop.py out.png [width height]

Needs Pillow. Nothing here ships in the plugin.
"""
import random
import sys

from PIL import Image, ImageDraw, ImageFilter


def draw(width=1280, height=720, seed=7):
    rnd = random.Random(seed)
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        t = y / float(height)
        top, bottom = (24, 28, 58), (70, 38, 60)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(width):
            px[x, y] = row
    glow = Image.new("RGB", (width, height), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    # Stage lights: soft discs of warm and cool colour.
    for _ in range(26):
        r = rnd.randint(height // 30, height // 9)
        x, y = rnd.randint(0, width), rnd.randint(0, int(height * 0.6))
        colour = rnd.choice([(255, 196, 120), (120, 160, 255), (255, 120, 170), (255, 236, 200)])
        g.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * rnd.uniform(0.35, 0.8)) for c in colour))
    glow = glow.filter(ImageFilter.GaussianBlur(height // 40))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.85)
    d = ImageDraw.Draw(img)
    # A stage edge and a cross of light at the back.
    d.rectangle([0, int(height * 0.78), width, height], fill=(18, 14, 22))
    cx = width // 2
    d.rectangle([cx - width // 160, int(height * 0.12), cx + width // 160, int(height * 0.62)], fill=(250, 232, 190))
    d.rectangle([cx - width // 18, int(height * 0.24), cx + width // 18, int(height * 0.24) + width // 80],
                fill=(250, 232, 190))
    return img.filter(ImageFilter.GaussianBlur(1))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "backdrop.png"
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 720
    draw(w, h).save(out)
