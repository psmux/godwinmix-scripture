---
name: scripture
description: Look up Bible verses (KJV and WEB bundled, plus any translation the church imported), search the Bible by words, and prepare song lyrics from the church's library as slides for the GodwinMix programme. Use when someone asks to show, find or prepare a verse, a passage or a song's words in a service, or asks what is on screen now.
---

# Bible verses and lyrics

The `scripture` plugin keeps the Bible texts and the song library and cuts
them into slides that fit the chosen style. The operator's panel puts the live
slide on the programme. As an agent you prepare and inspect; the panel does
the showing.

## Finding verses

* `find {query}` takes anything a person types. "jn 3 16", "1 Cor 13:4-7",
  "Ps 23", "Gen 1:1-2:3" are references; "love one another" is a search.
* `lookup {reference, translation}` when you know it is a reference.
* `search {query, translation}` for verses holding every word.
* `translations {}` lists what is installed. `kjv` and `web` always are.

A lookup answers a deck: `{id, title, slides: [{text, ref, label}]}`. Read the
`title` back to the person to confirm it is the passage they meant.

## Songs

* `songs {query}` to find one, `song_get {id}` to read it.
* `song_deck {id, order}` prepares it. `order` is like `V1 C V2 C B C`.
* `song_save {text}` adds one from plain text:

```
Title: Doxology
Author: Thomas Ken
Order: V1

[Verse 1]
Praise God from whom all blessings flow
```

Song words are shown under the church's own CCLI licence; reporting use is
the church's job, not yours and not the plugin's.

## What is live

`state {}` says whether words are on air, which slide, and the next one.
`go`, `step`, `blank` and `clear` change what the plugin counts as live and
what the stage display shows, but only the panel changes the programme, so
tell the operator to press Go live rather than claiming you did.
