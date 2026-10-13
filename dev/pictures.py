#!/usr/bin/env python3
"""Turn what dev/gallery.mjs and dev/e2e.mjs captured into gallery/.

    python dev/pictures.py <gallery-raw> <e2e-out>

Writes gallery/icon.png (drawn here), gallery/thumbnail.png (the programme
itself, 1280 by 720, from the real run's recording), gallery/screenshot-N.png
and gallery/demo.gif (the programme and the panel as an operator steps
through a verse and a hymn), kept under 3 MB. Needs Pillow.
"""
import glob
import os
import shutil
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "gallery")
GOLD = (242, 193, 78)
NAVY = (14, 23, 38)


def icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 6, fill=NAVY)
    s = size / 256.0
    # An open book.
    left = [(36 * s, 92 * s), (124 * s, 104 * s), (124 * s, 206 * s), (36 * s, 194 * s)]
    right = [(132 * s, 104 * s), (220 * s, 92 * s), (220 * s, 194 * s), (132 * s, 206 * s)]
    d.polygon(left, fill=(251, 247, 238))
    d.polygon(right, fill=(251, 247, 238))
    for i in range(5):
        y = (122 + i * 15) * s
        d.line([(50 * s, y - 2 * s), (112 * s, y + 6 * s)], fill=(150, 160, 180), width=max(1, int(3 * s)))
        d.line([(144 * s, y + 6 * s), (206 * s, y - 2 * s)], fill=(150, 160, 180), width=max(1, int(3 * s)))
    # A cross of light above it.
    d.rectangle([122 * s, 22 * s, 134 * s, 86 * s], fill=GOLD)
    d.rectangle([104 * s, 38 * s, 152 * s, 50 * s], fill=GOLD)
    # The lower third bar, gold, under the book.
    d.rounded_rectangle([36 * s, 214 * s, 220 * s, 232 * s], radius=int(6 * s), fill=GOLD)
    return img


def demo_gif(frames_dir, dest, width=1200, ms=650):
    files = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    frames = []
    for f in files:
        im = Image.open(f).convert("RGB")
        h = int(im.height * width / im.width)
        frames.append(im.resize((width, h), Image.LANCZOS))
    palette_src = Image.new("RGB", (width, frames[0].height * min(4, len(frames))))
    for i, f in enumerate(frames[::max(1, len(frames) // 4)][:4]):
        palette_src.paste(f, (0, i * f.height))
    palette = palette_src.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    quant = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    durations = [ms] * len(quant)
    durations[-1] = 2000
    quant[0].save(dest, save_all=True, append_images=quant[1:], duration=durations, loop=0, optimize=True)
    return os.path.getsize(dest)


def main(raw, e2e):
    os.makedirs(OUT, exist_ok=True)
    icon().save(os.path.join(OUT, "icon.png"))
    frame = os.path.join(e2e, "frame-john-3-16.png")
    Image.open(frame).convert("RGB").resize((1280, 720)).save(os.path.join(OUT, "thumbnail.png"))
    for f in sorted(glob.glob(os.path.join(raw, "screenshot-*.png"))):
        shutil.copyfile(f, os.path.join(OUT, os.path.basename(f)))
    size = demo_gif(os.path.join(raw, "gif"), os.path.join(OUT, "demo.gif"))
    width = 1200
    while size > 3 * 1024 * 1024 and width > 600:
        width -= 200
        size = demo_gif(os.path.join(raw, "gif"), os.path.join(OUT, "demo.gif"), width=width)
    print("demo.gif %d KB at %d wide" % (size // 1024, width))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
