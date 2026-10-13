"""Put the panel where GodwinMix 0.3.9's page looks for it.

`gmx plugin add` installs a plugin into <plugins>/<name>/<version>/, but the
page lists panels from <plugins>/<name>/ui/ (crates/godwinmix/src/ui.rs,
plugin_index), one level up. Until the mixer reads the versioned folder, the
service copies its own ui/ folder up one level when it starts. It writes only
inside <plugins>/scripture/, the folder the mixer gave this plugin, and
`gmx plugin remove scripture` deletes that whole folder.

On a mixer that already finds the panel, the copy is the same files in a
second place and does no harm.
"""
import filecmp
import os
import re
import shutil


def panel(root, name):
    """Copy root/ui to ../ui when root is a versioned install. Returns where, or None."""
    root = os.path.abspath(root)
    parent = os.path.dirname(root)
    if os.path.basename(parent) != name or not re.fullmatch(r"\d+\.\d+\.\d+[\w.+-]*", os.path.basename(root)):
        return None
    source = os.path.join(root, "ui")
    target = os.path.join(parent, "ui")
    if not os.path.isdir(source):
        return None
    changed = False
    for dirpath, _, files in os.walk(source):
        rel = os.path.relpath(dirpath, source)
        dest_dir = os.path.join(target, rel) if rel != "." else target
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            src, dst = os.path.join(dirpath, f), os.path.join(dest_dir, f)
            if not os.path.exists(dst) or not filecmp.cmp(src, dst, shallow=False):
                shutil.copyfile(src, dst)
                changed = True
    return target if changed else None
