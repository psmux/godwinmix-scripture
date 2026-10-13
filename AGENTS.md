# AGENTS.md

A GodwinMix plugin: Bible verses and song lyrics on the programme. Python,
standard library only. Read README.md first.

## Layout

| Path | What it is |
|---|---|
| `main.py` | the service process: JSON-RPC on stdin and stderr, never stdout |
| `scripture/` | the work: reference parsing, the Bible store, importers, songs, slides, styles, tools, the stage display |
| `ui/` | the panel (`panel.js`, a trusted custom element) and the stage display page |
| `bibles/` | the bundled public domain texts and `sources.json` with their checksums |
| `tests/` | unit tests and public domain sample files |
| `dev/` | the real check against a running mixer, and the gallery capture |
| `tools/` | rebuilding the bundled Bibles, packaging the release |

## Rules

* Standard library only in `main.py` and `scripture/`. Pillow and Chrome are
  for `dev/` and nothing else.
* Never write to stdout in the service.
* The panel changes the programme only through public mixer methods
  (`source.add`, `source.set`, `scene.item.add`, `scene.item.set`,
  `program.get`, `program.take`, `scene.create_from`).
* Song samples and pictures use public domain hymns or words written for
  the tests. Never add the words of a copyrighted song.
* `python -m unittest discover -s tests -t .` passes before every commit.
