// The two forms the panel opens over itself: a song editor and the import of
// a licensed translation. Loaded the first time one is wanted.

const NEW_SONG = `Title: New song
Author:
CCLI:
Order: V1 C V2 C

[Verse 1]
First line of the verse
Second line of the verse

[Chorus]
First line of the chorus
`;

function overlay(host, title, body) {
  const wrap = document.createElement("div");
  wrap.className = "scr-dialog";
  wrap.innerHTML = `<div class="scr-dialog-box"><div class="row"><strong class="grow">${title}</strong>
    <button class="btn" data-act="close" title="Close">Close</button></div>${body}
    <div class="scr-dialog-msg sm dim"></div></div>`;
  host.appendChild(wrap);
  const close = () => wrap.remove();
  wrap.querySelector('[data-act="close"]').onclick = close;
  wrap.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Escape") close();
  });
  const msg = (text, bad) => {
    const m = wrap.querySelector(".scr-dialog-msg");
    m.textContent = text;
    m.classList.toggle("scr-bad", !!bad);
  };
  return { wrap, close, msg, $: (s) => wrap.querySelector(s) };
}

export function openSongEditor(panel, song) {
  const d = overlay(panel.root, song ? "Edit song" : "New song", `
    <p class="sm dim">Headers first (Title, Author, CCLI, Order), then each section under a heading
    such as [Verse 1], [Chorus] or [Bridge]. A section too long for one slide is split by itself, at
    the end of a line.</p>
    <textarea class="scr-editor" spellcheck="true"></textarea>
    <div class="row"><button class="btn primary" data-act="save">Save</button>
    ${song ? '<button class="btn" data-act="delete">Delete</button>' : ""}<span class="grow"></span></div>`);
  const area = d.$("textarea");
  area.value = song ? song.text : NEW_SONG;
  area.focus();
  d.$('[data-act="save"]').onclick = async () => {
    try {
      const r = await panel.tool("song_save", { text: area.value, id: song ? song.song.id : undefined });
      d.close();
      await panel.loadSongs();
      await panel.openSong(r.song.id);
    } catch (e) {
      d.msg(e.message, true);
    }
  };
  const del = d.$('[data-act="delete"]');
  if (del) {
    del.onclick = async () => {
      if (!confirm(`Delete "${song.song.title}" from the song library?`)) return;
      try {
        await panel.tool("song_delete", { id: song.song.id });
        d.close();
        await panel.loadSongs();
      } catch (e) {
        d.msg(e.message, true);
      }
    };
  }
}

function base64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// Send a file in pieces small enough for one call each, and answer the upload id.
export async function sendFile(panel, file, progress) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const piece = 256 * 1024;
  let upload;
  for (let seq = 0, at = 0; at < bytes.length || seq === 0; seq++, at += piece) {
    const r = await panel.tool("upload", { upload, seq, name: file.name, data_base64: base64(bytes.subarray(at, at + piece)) });
    upload = r.upload;
    if (progress) progress(Math.min(1, (at + piece) / Math.max(1, bytes.length)));
  }
  return upload;
}

export function openBibleImport(panel) {
  const d = overlay(panel.root, "Import a translation", `
    <p class="sm dim">For a translation this church has the right to show. USFM (one file per book, or
    the zip of them), OSIS XML, Zefania XML, or a table of book,chapter,verse,text. It is stored on the
    mixer and never sent anywhere.</p>
    <label class="scr-field">File <input type="file" data-f="file"
      accept=".zip,.usfm,.sfm,.xml,.osis,.csv,.tsv,.txt" multiple></label>
    <label class="scr-field">Abbreviation <input data-f="abbreviation" placeholder="NIV" maxlength="16"></label>
    <label class="scr-field">Name <input data-f="title" placeholder="New International Version"></label>
    <label class="scr-field">Format <select data-f="format"><option value="">Work it out</option>
      <option value="usfm">USFM</option><option value="osis">OSIS XML</option>
      <option value="zefania">Zefania XML</option><option value="csv">book,chapter,verse,text</option></select></label>
    <label class="scr-field">Your right to show it <input data-f="licence"
      placeholder="Licensed to Grace Church by the publisher, 2026"></label>
    <div class="row"><button class="btn primary" data-act="go">Import</button><span class="grow"></span></div>`);
  d.$('[data-act="go"]').onclick = async () => {
    const files = [...d.$('[data-f="file"]').files];
    if (!files.length) return d.msg("Pick the file first.", true);
    if (files.length > 1) return d.msg("Pick one file: a zip holds many USFM books in one.", true);
    try {
      const upload = await sendFile(panel, files[0], (f) => d.msg(`Sending ${Math.round(f * 100)}%`));
      d.msg("Reading the text...");
      const r = await panel.tool("bible_import", {
        upload, name: files[0].name,
        abbreviation: d.$('[data-f="abbreviation"]').value,
        title: d.$('[data-f="title"]').value,
        format: d.$('[data-f="format"]').value || undefined,
        licence: d.$('[data-f="licence"]').value,
      });
      d.msg(`Imported ${r.imported.name}: ${r.imported.verses} verses in ${r.imported.books} books.`);
      await panel.loadTranslations(r.imported.id);
    } catch (e) {
      d.msg(e.message, true);
    }
  };
}

export async function importSongs(panel, files) {
  const done = [];
  for (const file of files) {
    const content = await file.text();
    const r = await panel.tool("song_import", { name: file.name, content });
    done.push(r.song);
  }
  return done;
}
