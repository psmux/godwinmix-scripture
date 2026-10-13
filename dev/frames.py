#!/usr/bin/env python3
"""Cut the marked moments out of the recording dev/e2e.mjs made, and check them.

    python dev/frames.py e2e-out

Needs ffmpeg on PATH and Pillow (pip install pillow); neither is needed by
the plugin itself. For each mark in timeline.json it writes frame-<name>.png
at the programme's own size. The check itself reads the programme thumbnails
the run kept once the picture had settled: a mark that expects words must
differ from the one taken before anything was shown, a mark that expects
nothing must match it. contact.png puts the full size frames side by side.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageChops, ImageStat


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def frame(path, at, dest):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % max(0, at), "-i", path,
                    "-frames:v", "1", dest], check=True)
    return Image.open(dest).convert("RGB")


def difference(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3.0


def main(out):
    with open(os.path.join(out, "timeline.json"), encoding="utf-8") as f:
        timeline = json.load(f)
    rec_dir = os.path.join(out, "recording")
    files = sorted(os.path.join(rec_dir, n) for n in os.listdir(rec_dir) if n.endswith((".mkv", ".mp4")))
    video = files[-1]
    # The file starts when its first picture arrives, a moment after the
    # recorder was asked for; the gap is how much shorter the file is.
    offset = max(0.0, timeline["stopped_at"] - duration(video))
    frames = {}
    for m in timeline["marks"]:
        frames[m["name"]] = frame(video, m["at"] - offset - 0.5, os.path.join(out, "frame-%s.png" % m["name"]))
    stills = {m["name"]: Image.open(os.path.join(out, m["still"])).convert("RGB")
              for m in timeline["marks"] if m.get("still")}
    base = stills[timeline["marks"][0]["name"]]
    failed = 0
    for m in timeline["marks"][1:]:
        d = difference(stills[m["name"]], base)
        words = m["expect"] != "nothing"
        good = d > 3 if words else d < 1.5
        failed += not good
        print("%s %-18s differs from the programme before by %5.1f (%s)" % (
            "ok  " if good else "FAIL", m["name"], d, "words expected" if words else "nothing expected"))
    thumbs = [frames[m["name"]].resize((320, 180)) for m in timeline["marks"]]
    sheet = Image.new("RGB", (320 * 4, 180 * ((len(thumbs) + 3) // 4)), "black")
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % 4) * 320, (i // 4) * 180))
    sheet.save(os.path.join(out, "contact.png"))
    print("offset %.2f s; %d frame(s) failed" % (offset, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "e2e-out"))
