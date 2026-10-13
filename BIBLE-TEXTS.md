# The Bible texts in this plugin

Two translations ship with the plugin. Both are public domain. They are kept
in `bibles/` as gzipped tables of book, chapter, verse and text, one verse a
line, made from the files below by `tools/build_bibles.py` through the
plugin's own USFM importer. `bibles/sources.json` records the same details in
a form the plugin reads.

## King James Version (`kjv`)

* Edition: the King James (Authorized) Version, standardized text of 1769,
  protocanon only (the 66 books), as published by eBible.org from the
  Crosswire Bible Society's text.
* Source: https://ebible.org/Scriptures/eng-kjv2006_usfm.zip
* SHA-256 of that download: `77bbe9c78f4f588b1465e49ddad986293a09e7f4b140abe7248232c8c5ae2a5b`
* Verses: 31,102.
* Licence: public domain outside the United Kingdom. In the United Kingdom
  the text is under Crown letters patent held by the Queen's (now King's)
  Printers, which govern printing it and importing printed copies there.
  eBible.org's page for this edition says so; showing it on a screen or a
  stream is not printing, but a church in the UK that wants certainty should
  read the details at https://en.wikipedia.org/wiki/King_James_Version#Copyright_status.

## World English Bible (`web`)

* Edition: the World English Bible, 66 book protocanon edition (`engwebp`),
  as published by eBible.org.
* Source: https://ebible.org/Scriptures/engwebp_usfm.zip
* SHA-256 of that download: `6b47e6553ce0bd71902fe4b4ba71a5d7d862928e2ce47936acdda345bc6c5dd0`
* Verses: 31,098. The WEB leaves out a few verses that the oldest manuscripts
  do not have, and gives them in footnotes, which this plugin does not show.
* Licence: public domain. "World English Bible" is a trademark of eBible.org,
  which asks that a changed text not be called the World English Bible. The
  plugin shows the text as published, with Strong's numbers, footnotes,
  cross references and section headings left out.

## What was taken out

From both: footnotes, cross references, section headings, psalm titles
(`\d`), Strong's numbers and other word level markup, and the paragraph sign
some verses begin with. The words of the verses themselves are as published.

eBible.org rebuilds its files from time to time. `tools/build_bibles.py`
refuses a download whose checksum differs from the one recorded here until it
is run with `--update`, so a change upstream is noticed and looked at rather
than taken in silently.

## Translations you import

A translation an operator imports is stored in the plugin's data folder on
the mixer's computer with the licence line the operator gave. It is never
added to this repository or sent anywhere.
