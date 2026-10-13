// Bible verses and song lyrics: the panel in the mixer's page.
//
// The scripture service (main.py) holds the Bible, the song library and what
// is live, and answers tool calls. This panel asks it for slides, shows them,
// and puts the live one on the programme through the mixer's own methods
// (onair.js). Keys, while the panel has focus: Right, Down, Space or Page Down
// for the next slide; Left, Up or Page Up for the one before; Enter to go
// live with the selected slide; B to blank; Escape to clear.
import { OnAir } from "./onair.js";
import { drawPreview } from "./preview.js";

const BASE = new URL(".", import.meta.url).href;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

class ScripturePanel extends HTMLElement {
  static get panel() {
    return { id: "scripture/panel", title: "Bible and lyrics", slots: ["sidebar", "main"] };
  }

  setClient(client) { this.client = client; }
  setConfig(config) { this.config = config || {}; }

  connectedCallback() {
    if (!document.getElementById("scr-css")) {
      const link = document.createElement("link");
      link.id = "scr-css";
      link.rel = "stylesheet";
      link.href = BASE + "panel.css";
      document.head.appendChild(link);
    }
    this.tab = "bible";
    this.deck = null;
    this.selected = 0;
    this.live = { on_air: false, blank: false, deck: null, index: 0 };
    this.canvas = { width: 1920, height: 1080 };
    this.busy = Promise.resolve();
    this.air = new OnAir(this.client);
    this.build();
    this.resize = new ResizeObserver(() => {
      this.root.classList.toggle("wide", this.root.clientWidth >= 720);
      this.drawPreview();
    });
    this.resize.observe(this.root);
    this.off = this.client.onRender ? this.client.onRender((s) => this.onMixer(s)) : null;
    this.start().catch((e) => this.say(e.message, true));
  }

  disconnectedCallback() {
    if (this.off) this.off();
    if (this.resize) this.resize.disconnect();
  }

  // --- talking to the service --------------------------------------------

  async tool(name, args = {}) {
    const r = await this.client.call("tool.call", { name: `scripture/${name}`, arguments: args });
    if (r && r.isError) {
      const e = new Error((r.structuredContent && r.structuredContent.error) || r.content?.[0]?.text || "refused");
      e.data = r.structuredContent?.data;
      throw e;
    }
    return r ? r.structuredContent : {};
  }

  // One thing at a time, in the order pressed: four presses of Next are four slides.
  run(fn) {
    this.busy = this.busy.then(fn).catch((e) => this.say(e.message || String(e), true));
    return this.busy;
  }

  say(text, bad) {
    this.msg.textContent = text || "";
    this.msg.classList.toggle("scr-bad", !!bad);
  }

  // --- building ------------------------------------------------------------

  build() {
    this.innerHTML = `
<div class="scr" tabindex="0">
  <div class="scr-top">
    <button class="scr-tab on" data-tab="bible">Bible</button>
    <button class="scr-tab" data-tab="songs">Songs</button>
    <span class="grow" style="flex:1"></span>
    <span class="scr-pill" data-el="pill">OFF AIR</span>
    <button class="btn sm" data-act="stage" title="A page for the band and the preacher: this slide and the next">Stage display</button>
  </div>
  <div class="scr-body">
    <div class="scr-col" data-el="left">
      <div data-pane="bible" class="scr-col" style="padding:0">
        <div class="scr-row"><input class="grow" data-el="query" placeholder="John 3:16, Ps 23, or words to find">
          <button class="btn primary" data-act="find">Find</button></div>
        <div class="scr-row"><select class="grow" data-el="translation" title="Translation"></select>
          <button class="btn sm" data-act="import-bible" title="Add a translation this church has the right to show">Import...</button></div>
        <div class="scr-list" data-el="results"><div class="scr-empty">Type a reference and press Enter. Words with no
          numbers search the whole Bible.</div></div>
      </div>
      <div data-pane="songs" class="scr-col" style="padding:0" hidden>
        <div class="scr-row"><input class="grow" data-el="songq" placeholder="Find a song by title, words or CCLI number">
          <button class="btn sm" data-act="new-song">New</button>
          <label class="btn sm" title="Plain text, OpenLyrics XML or ChordPro">Import...<input type="file" data-el="songfile"
            accept=".txt,.xml,.cho,.chopro,.chordpro,.pro,.crd" multiple hidden></label></div>
        <div class="scr-list" data-el="songs"></div>
      </div>
    </div>
    <div class="scr-col" data-el="right">
      <div class="scr-row"><span class="scr-title grow" data-el="deck-title">Nothing prepared</span>
        <button class="btn sm" data-act="edit-song" hidden>Edit song</button></div>
      <div class="scr-row" data-el="order-row" hidden><span class="sm dim">Order</span>
        <input class="grow" data-el="order" placeholder="V1 C V2 C B C"><button class="btn sm" data-act="order">Apply</button></div>
      <div class="scr-chips" data-el="chips"></div>
      <div class="scr-slides" data-el="slides"></div>
      <div class="scr-controls">
        <button class="btn golive" data-act="go" title="Enter">Go live</button>
        <button class="btn" data-act="prev" title="Left, Up or Page Up">Previous</button>
        <button class="btn" data-act="next" title="Right, Down, Space or Page Down">Next</button>
        <button class="btn" data-act="blank" title="B">Blank</button>
        <button class="btn" data-act="clear" title="Escape">Clear</button>
      </div>
      <div class="scr-keys"><kbd>Enter</kbd> go live <kbd>Space</kbd> <kbd>Right</kbd> next <kbd>Left</kbd> previous
        <kbd>B</kbd> blank <kbd>Esc</kbd> clear</div>
      <div class="scr-row"><span class="sm dim">Style</span><select class="grow" data-el="style"></select>
        <button class="btn sm" data-act="look" title="Font, size, colours, box and margins">Adjust</button></div>
      <div class="scr-look" data-el="look" hidden>
        <span>Size</span><input type="range" min="0.6" max="1.6" step="0.05" value="1" data-o="scale">
        <span>Align</span><select data-o="align"><option value="">Style's own</option><option>left</option><option>center</option><option>right</option></select>
        <span>Words</span><input type="color" value="#ffffff" data-o="color">
        <span>Accent</span><input type="color" value="#f2c14e" data-o="accent">
        <span>Box</span><select data-o="box"><option value="">Style's own</option><option value="#0e1726e8">Dark blue</option>
          <option value="#000000b3">Black, see through</option><option value="#000000f2">Black</option><option value="#ffffffe6">White</option><option value="none">No box</option></select>
        <span>Shadow</span><select data-o="shadow"><option value="">Style's own</option><option value="1">On</option><option value="0">Off</option></select>
        <span>Margin</span><input type="range" min="0" max="15" step="1" value="0" data-o="margin">
        <span>Font</span><input data-o="font" placeholder="Style's own">
        <span></span><span></span><button class="btn sm" data-act="look-reset">Reset</button><button class="btn sm primary" data-act="look-apply">Apply</button>
      </div>
      <div class="scr-preview" data-el="preview"></div>
    </div>
  </div>
  <div class="scr-msg" data-el="msg"></div>
</div>`;
    this.root = this.querySelector(".scr");
    this.el = {};
    for (const n of this.querySelectorAll("[data-el]")) this.el[n.dataset.el] = n;
    this.msg = this.el.msg;
    for (const b of this.querySelectorAll("[data-tab]")) b.onclick = () => this.showTab(b.dataset.tab);
    const acts = {
      find: () => this.run(() => this.find()),
      "import-bible": () => import("./dialogs.js").then((m) => m.openBibleImport(this)),
      "new-song": () => import("./dialogs.js").then((m) => m.openSongEditor(this, null)),
      "edit-song": () => this.run(async () => {
        const s = await this.tool("song_get", { id: this.deck.song });
        (await import("./dialogs.js")).openSongEditor(this, s);
      }),
      order: () => this.run(() => this.openSong(this.deck.song, this.el.order.value)),
      go: () => this.run(() => this.goLive(this.selected)),
      next: () => this.run(() => this.step(1)),
      prev: () => this.run(() => this.step(-1)),
      blank: () => this.run(() => this.blank()),
      clear: () => this.run(() => this.clear()),
      stage: () => this.run(() => this.stage()),
      look: () => { this.el.look.hidden = !this.el.look.hidden; },
      "look-apply": () => this.run(() => this.applyLook()),
      "look-reset": () => this.run(() => this.applyLook(true)),
    };
    for (const b of this.querySelectorAll("[data-act]")) b.onclick = () => acts[b.dataset.act]();
    this.el.query.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); this.run(() => this.find()); }
    });
    let timer;
    this.el.songq.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => this.run(() => this.loadSongs()), 200); });
    this.el.songfile.addEventListener("change", () => this.run(async () => {
      const files = [...this.el.songfile.files];
      const done = await (await import("./dialogs.js")).importSongs(this, files);
      this.el.songfile.value = "";
      await this.loadSongs();
      if (done.length) await this.openSong(done[done.length - 1].id);
      this.say(`Imported ${done.map((s) => s.title).join(", ")}.`);
    }));
    this.el.translation.onchange = () => this.el.query.value && this.run(() => this.find());
    this.el.style.onchange = () => this.run(() => this.setStyle(this.el.style.value));
    this.root.addEventListener("keydown", (e) => this.onKey(e));
  }

  showTab(tab) {
    this.tab = tab;
    for (const b of this.querySelectorAll("[data-tab]")) b.classList.toggle("on", b.dataset.tab === tab);
    for (const p of this.querySelectorAll("[data-pane]")) p.hidden = p.dataset.pane !== tab;
    this.fillStyles();
    if (tab === "songs") this.run(() => this.loadSongs());
  }

  // --- loading ---------------------------------------------------------------

  async start() {
    await this.loadTranslations();
    const st = await this.tool("styles");
    this.styles = st.styles;
    this.current = st.current;
    this.fillStyles();
    const state = await this.tool("state");
    this.canvas = state.canvas || this.canvas;
    this.takeState(state);
    if (state.deck) {
      this.deck = state.deck;
      this.selected = state.index;
    }
    this.render();
    this.say("Ready. The words go on whatever scene is on the programme.");
  }

  async loadTranslations(pick) {
    const r = await this.tool("translations");
    const keep = pick || this.el.translation.value || r.default;
    this.el.translation.innerHTML = r.translations.map((t) =>
      `<option value="${esc(t.id)}" title="${esc(t.licence)}">${esc(t.abbreviation || t.id.toUpperCase())}, ${esc(t.name)}</option>`).join("");
    this.el.translation.value = keep;
  }

  fillStyles() {
    if (!this.styles) return;
    const kind = this.kindNow();
    const mine = this.styles.filter((s) => s.for.includes(kind));
    this.el.style.innerHTML = mine.map((s) => `<option value="${s.id}" title="${esc(s.description)}">${esc(s.title)}</option>`).join("");
    this.el.style.value = this.current[kind].id;
  }

  kindNow() {
    if (this.deck) return this.deck.kind === "song" ? "song" : "bible";
    return this.tab === "songs" ? "song" : "bible";
  }

  async loadSongs() {
    const r = await this.tool("songs", { query: this.el.songq.value });
    this.el.songs.innerHTML = r.songs.length ? r.songs.map((s) => `
      <button class="scr-item" data-song="${esc(s.id)}"><span class="ref">${esc(s.title)}</span>
      <span class="sm">${esc(s.author)}${s.ccli ? " &middot; CCLI " + esc(s.ccli) : ""}</span><br>
      <span class="sm">${esc(s.first_line)}</span></button>`).join("")
      : `<div class="scr-empty">No songs yet. Press New to type one, or Import for a text, OpenLyrics or ChordPro file.</div>`;
    for (const b of this.el.songs.querySelectorAll("[data-song]")) b.onclick = () => this.run(() => this.openSong(b.dataset.song));
  }

  async find() {
    const query = this.el.query.value.trim();
    if (!query) return;
    const r = await this.tool("find", { query, translation: this.el.translation.value });
    if (r.kind === "reference") {
      this.useDeck(r.deck);
      this.el.results.innerHTML = `<div class="scr-empty">${esc(r.deck.title)}: ${r.deck.slides.length} slide${r.deck.slides.length === 1 ? "" : "s"}.
        Press Enter or Go live.</div>`;
      this.root.focus();
      return;
    }
    this.el.results.innerHTML = r.results.length ? r.results.map((h) => `
      <button class="scr-item" data-ref="${esc(h.reference)}"><span class="ref">${esc(h.reference)}</span>${esc(h.text)}</button>`).join("")
      : `<div class="scr-empty">Nothing in ${esc(r.translation.toUpperCase())} has all of those words.</div>`;
    for (const b of this.el.results.querySelectorAll("[data-ref]")) {
      b.onclick = () => this.run(async () => {
        const d = await this.tool("lookup", { reference: b.dataset.ref, translation: this.el.translation.value });
        this.useDeck(d.deck);
        this.root.focus();
      });
    }
    this.say(`${r.results.length} verse${r.results.length === 1 ? "" : "s"} found.`);
  }

  async openSong(id, order) {
    const r = await this.tool("song_deck", { id, order: order || undefined });
    this.useDeck(r.deck);
    this.root.focus();
  }

  useDeck(deck) {
    this.deck = deck;
    this.selected = this.live.deck && this.live.deck.id === deck.id ? this.live.index : 0;
    this.fillStyles();
    this.render();
  }

  // --- live ----------------------------------------------------------------

  takeState(r) {
    this.live = { on_air: r.on_air, blank: r.blank, index: r.index, deck: r.deck, version: r.version };
    this.layers = r.layers || (r.current && r.current.layers) || [];
  }

  async goLive(index) {
    if (!this.deck) return this.say("Find a passage or pick a song first.", true);
    const r = await this.tool("go", { deck: this.deck.id, index });
    this.takeState(r);
    this.selected = r.index;
    this.render();
    await this.air.show(r.layers, { blank: false });
    this.say(`On air: ${r.current.ref || r.current.label}`);
  }

  async step(by) {
    if (!this.live.on_air) {
      // Nothing live: the arrows move the selection, ready for Go live.
      if (!this.deck) return;
      this.selected = Math.max(0, Math.min(this.deck.slides.length - 1, this.selected + by));
      return this.render();
    }
    const r = await this.tool("step", { by });
    const moved = r.index !== this.live.index;
    this.takeState(r);
    if (this.deck && this.deck.id === r.deck.id) this.selected = r.index;
    this.render();
    if (moved || r.blank) await this.air.show(r.layers, { blank: r.blank });
    if (!moved) this.say(by > 0 ? "That is the last slide." : "That is the first slide.");
  }

  async blank() {
    const r = await this.tool("blank", {});
    this.takeState(r);
    this.render();
    if (r.blank) await this.air.hide();
    else await this.air.show(r.layers, { blank: false });
  }

  async clear() {
    const r = await this.tool("clear", {});
    this.takeState(r);
    this.render();
    await this.air.hide();
    this.say("Cleared. Nothing of ours is on the programme.");
  }

  async stage() {
    const r = await this.tool("stage", {});
    this.say(`Stage display: ${r.urls.join("  or  ")}`);
    window.open(r.urls[0], "_blank", "noopener");
  }

  async setStyle(id) {
    const kind = this.kindNow();
    await this.restyle({ kind, id });
  }

  async applyLook(reset) {
    const over = {};
    if (!reset) {
      for (const el of this.querySelectorAll("[data-o]")) {
        const k = el.dataset.o, v = el.value;
        if (k === "scale" && Number(v) !== 1) over.scale = Number(v);
        else if (k === "margin" && Number(v) > 0) over.margin = Number(v);
        else if (k === "box" && v) over.box = v === "none" ? "" : v;
        else if (k === "shadow" && v) over.shadow = v === "1";
        else if ((k === "align" || k === "font") && v) over[k] = v;
        else if ((k === "color" || k === "accent") && el.dataset.touched) over[k] = v;
      }
    } else {
      for (const el of this.querySelectorAll("[data-o]")) {
        el.value = { scale: "1", margin: "0", color: "#ffffff", accent: "#f2c14e" }[el.dataset.o] ?? "";
        delete el.dataset.touched;
      }
    }
    await this.restyle({ kind: this.kindNow(), overrides: over });
  }

  async restyle(args) {
    const r = await this.tool("style_set", args);
    this.current = r.current_style;
    if (this.deck && r.decks[this.deck.id]) {
      this.deck = r.decks[this.deck.id];
      this.selected = Math.min(this.selected, this.deck.slides.length - 1);
    }
    const wasLive = r.on_air;
    this.takeState(r);
    this.fillStyles();
    this.render();
    if (wasLive && r.deck && r.deck.kind === (args.kind === "song" ? "song" : "bible")) {
      await this.air.show(r.layers, { blank: r.blank });
    }
  }

  // The mixer changed: if the operator took another scene while words are up,
  // put them on that scene too.
  onMixer(state) {
    if (!state || !this.live.on_air || this.live.blank || !this.layers?.length) return;
    const scene = state.scene;
    if (scene && this.air.scene && scene !== this.air.scene) {
      this.run(() => this.air.follow(scene, this.layers, false));
    }
  }

  onKey(e) {
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
    const map = {
      ArrowRight: () => this.step(1), ArrowDown: () => this.step(1), PageDown: () => this.step(1), " ": () => this.step(1),
      ArrowLeft: () => this.step(-1), ArrowUp: () => this.step(-1), PageUp: () => this.step(-1),
      Enter: () => this.goLive(this.selected), b: () => this.blank(), B: () => this.blank(), Escape: () => this.clear(),
    };
    const fn = map[e.key];
    if (!fn) return;
    e.preventDefault();
    e.stopPropagation();
    this.run(fn);
  }

  // --- drawing ---------------------------------------------------------------

  render() {
    const pill = this.el.pill;
    pill.className = "scr-pill" + (this.live.on_air ? (this.live.blank ? " blank" : " live") : "");
    pill.textContent = this.live.on_air ? (this.live.blank ? "BLANK" : "ON AIR") : "OFF AIR";
    const deck = this.deck;
    const isSong = deck && deck.kind === "song";
    this.querySelector('[data-act="edit-song"]').hidden = !isSong;
    this.el["order-row"].hidden = !isSong;
    if (isSong) this.el.order.value = deck.order.join(" ");
    this.el["deck-title"].textContent = deck ? deck.title : "Nothing prepared";
    const liveHere = deck && this.live.on_air && this.live.deck && this.live.deck.id === deck.id;
    this.el.slides.innerHTML = deck ? deck.slides.map((s, i) => {
      const cls = ["scr-slide"];
      if (i === this.selected) cls.push("sel");
      if (liveHere && i === this.live.index && !this.live.blank) cls.push("live");
      if (liveHere && i === this.live.index + 1) cls.push("next");
      return `<button class="${cls.join(" ")}" data-i="${i}"><span class="lab">${esc(s.label)}</span>${esc(s.text)}</button>`;
    }).join("") : `<div class="scr-empty">Find a passage or open a song. Its slides appear here.</div>`;
    for (const b of this.el.slides.querySelectorAll("[data-i]")) {
      b.onclick = () => this.run(async () => {
        const i = Number(b.dataset.i);
        if (liveHere) return this.goLive(i);
        this.selected = i;
        this.render();
      });
      b.ondblclick = () => this.run(() => this.goLive(Number(b.dataset.i)));
    }
    const sel = this.el.slides.querySelector(".scr-slide.sel");
    if (sel) sel.scrollIntoView({ block: "nearest" });
    this.el.chips.innerHTML = isSong ? [...new Set(deck.slides.map((s) => s.section))].map((sec) =>
      `<button class="scr-chip" data-sec="${esc(sec)}" title="Jump to the next ${esc(sec)}">${esc(sec)}</button>`).join("") : "";
    for (const c of this.el.chips.querySelectorAll("[data-sec]")) {
      c.onclick = () => this.run(() => this.jumpTo(c.dataset.sec));
    }
    this.drawPreview();
  }

  async jumpTo(section) {
    const slides = this.deck.slides;
    const from = this.selected;
    let at = slides.findIndex((s, i) => i > from && s.section === section && slides[i - 1]?.section !== section);
    if (at < 0) at = slides.findIndex((s) => s.section === section);
    if (at < 0) return;
    const liveHere = this.live.on_air && this.live.deck && this.live.deck.id === this.deck.id;
    if (liveHere) return this.goLive(at);
    this.selected = at;
    this.render();
  }

  drawPreview() {
    if (!this.el || !this.el.preview) return;
    const slide = this.deck && this.deck.slides[this.selected];
    const now = Date.now();
    if (!this.backdrop || now - (this.backdropAt || 0) > 5000) {
      try {
        this.backdrop = this.client.snapshotUrl ? this.client.snapshotUrl("program", 640) : null;
        this.backdropAt = now;
      } catch { this.backdrop = null; }
    }
    drawPreview(this.el.preview, slide ? slide.layers : [], this.canvas, this.backdrop);
  }
}

for (const el of ["color", "accent"]) {
  document.addEventListener("input", (e) => {
    if (e.target && e.target.dataset && e.target.dataset.o === el) e.target.dataset.touched = "1";
  });
}

if (!customElements.get("gmx-scripture-panel")) {
  customElements.define("gmx-scripture-panel", ScripturePanel);
  (window.godwinmixPanels = window.godwinmixPanels || []).push(ScripturePanel);
}
