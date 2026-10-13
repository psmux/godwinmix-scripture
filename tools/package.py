#!/usr/bin/env python3
"""Build the release archives, one per platform, into dist/.

    python tools/package.py            the version in gmx-plugin.toml
    python tools/package.py v1.0.0     refuse unless the manifest says 1.0.0

The plugin is Python with no compiled parts, so every archive holds the same
files. There is one per platform because `gmx plugin add owner/repo` picks the
asset whose name carries this machine's platform triple. Linux and macOS get a
.tar.gz, Windows a .zip; each holds one folder, scripture-<version>/, with
gmx-plugin.toml at its top.
"""
import io
import os
import sys
import tarfile
import tomllib
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIP = ["gmx-plugin.toml", "main.py", "README.md", "LICENSE", "BIBLE-TEXTS.md",
        "scripture", "ui", "schemas", "skills", "bibles"]
PLATFORMS = ["windows-x86_64", "linux-x86_64", "linux-aarch64", "macos-aarch64", "macos-x86_64"]
FIXED_TIME = 1767225600  # 2026-01-01, so the same files make the same archive


def files():
    out = []
    for item in SHIP:
        path = os.path.join(ROOT, item)
        if os.path.isfile(path):
            out.append(item)
            continue
        for dirpath, dirnames, names in os.walk(path):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for n in sorted(names):
                if n.endswith((".pyc", ".pyo")):
                    continue
                out.append(os.path.relpath(os.path.join(dirpath, n), ROOT).replace(os.sep, "/"))
    return out


def main():
    with open(os.path.join(ROOT, "gmx-plugin.toml"), "rb") as f:
        manifest = tomllib.load(f)
    name, version = manifest["plugin"]["name"], manifest["plugin"]["version"]
    if len(sys.argv) > 1 and sys.argv[1].lstrip("v") != version:
        sys.exit("the tag says %s but gmx-plugin.toml says %s. Change one of them." % (sys.argv[1], version))
    missing = [p for p in PLATFORMS if p not in manifest["plugin"]["platforms"]]
    if missing:
        sys.exit("gmx-plugin.toml does not list %s in platforms." % ", ".join(missing))
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    top = "%s-%s" % (name, version)
    listing = files()
    for platform in PLATFORMS:
        base = os.path.join(dist, "%s-%s-%s" % (name, version, platform))
        if platform.startswith("windows"):
            with zipfile.ZipFile(base + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
                for rel in listing:
                    info = zipfile.ZipInfo("%s/%s" % (top, rel), date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    with open(os.path.join(ROOT, rel), "rb") as f:
                        z.writestr(info, f.read())
            print(base + ".zip")
        else:
            with tarfile.open(base + ".tar.gz", "w:gz") as t:
                for rel in listing:
                    with open(os.path.join(ROOT, rel), "rb") as f:
                        data = f.read()
                    info = tarfile.TarInfo("%s/%s" % (top, rel))
                    info.size = len(data)
                    info.mtime = FIXED_TIME
                    info.mode = 0o755 if rel == "main.py" else 0o644
                    t.addfile(info, io.BytesIO(data))
            print(base + ".tar.gz")


if __name__ == "__main__":
    main()
