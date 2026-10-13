// The real check: a running GodwinMix with this plugin installed, driven
// through its own web page in headless Chrome.
//
//   node dev/e2e.mjs --base http://127.0.0.1:23010 --cdp 23011 --out ./e2e-out
//
// It loads the page, opens the Bible and lyrics panel, puts John 3:16 on air,
// adds a public domain hymn through the song editor, puts its first slide on
// air, steps to the next with the Right arrow key, blanks and clears. While it
// runs the programme is recorded with the mixer's own recorder, and the
// moments that matter are written to timeline.json so dev/frames.py can cut
// those frames out of the recording and check the words are there.
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { Browser, sleep } from "./cdp.mjs";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const BASE = arg("base", "http://127.0.0.1:23010");
const PORT = Number(arg("cdp", "23011"));
const OUT = resolve(arg("out", "e2e-out"));
const CHROME = arg("chrome", [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((p) => existsSync(p)));
const WIDTH = Number(arg("width", "1600"));
const HEIGHT = Number(arg("height", "1000"));
mkdirSync(OUT, { recursive: true });

const HYMN = `Title: Amazing Grace
Author: John Newton
Copyright: Public domain
Order: V1 V2 V3

[Verse 1]
Amazing grace! How sweet the sound
That saved a wretch like me!
I once was lost, but now am found;
Was blind, but now I see.

[Verse 2]
'Twas grace that taught my heart to fear,
And grace my fears relieved;
How precious did that grace appear
The hour I first believed.

[Verse 3]
Through many dangers, toils and snares,
I have already come;
'Tis grace hath brought me safe thus far,
And grace will lead me home.
`;

async function rest(method, path, body) {
  const r = await fetch(BASE + path, {
    method, headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  try { return JSON.parse(text); } catch { return text; }
}
const tool = async (name, args = {}) => (await rest("POST", "/api/v1/tool/call", { name: `scripture/${name}`, arguments: args })).structuredContent;

const P = "document.querySelector('gmx-scripture-panel')";
const timeline = { started: null, marks: [] };
let recStart = 0;
const steps = [];
function ok(name, pass, detail = "") {
  steps.push({ name, pass, detail });
  console.log(`${pass ? "ok  " : "FAIL"} ${name}${detail ? "  (" + detail + ")" : ""}`);
}
// Note the moment for the recording, and keep what the mixer says is on air
// now as a still: program.thumbnail is the programme itself, not a monitor.
async function mark(name, expect) {
  const at = (Date.now() - recStart) / 1000;
  const thumb = await rest("GET", "/api/v1/program/thumbnail?width=320");
  let still = null;
  if (thumb && thumb.jpeg) {
    still = `thumb-${name}.jpg`;
    writeFileSync(resolve(OUT, still), Buffer.from(thumb.jpeg, "base64"));
  }
  timeline.marks.push({ name, at, expect, still });
}

const recDir = resolve(OUT, "recording");
mkdirSync(recDir, { recursive: true });
await rest("DELETE", "/api/v1/outputs/scripture-check");
const rec = await rest("POST", "/api/v1/outputs", {
  id: "scripture-check", uri: "record://programme", type: "record/output",
  params: { format: "mkv", directory: recDir },
});
recStart = Date.now();
ok("recorder started", !rec.error, rec.error ? rec.error.message : "");

const b = await Browser.launch({ chrome: CHROME, port: PORT, profile: resolve(OUT, "chrome"), width: WIDTH, height: HEIGHT });
let n = 0;
const shot = async (name) => b.shot(resolve(OUT, `${String(++n).padStart(2, "0")}-${name}.png`));
try {
  await b.goto(BASE + "/");
  await b.until("(window.godwinmixPanels || []).some((p) => p.panel && p.panel.id === 'scripture/panel')", 30000);
  ok("panel registered by the page", true);
  if (arg("layout", "wide") === "wide") {
    // The operator's own Panels and layout, Move panel: the Bible and lyrics
    // panel beside the programme, where it has room for two columns.
    await b.eval(`import('/shell/dock-model.js').then((m) => {
      const s = m.load();
      s.tree = m.dock(s.tree, 'scripture/panel', 'core/program', 'right');
      m.save(s);
    })`);
    await b.goto(BASE + "/");
    await b.until("(window.godwinmixPanels || []).some((p) => p.panel && p.panel.id === 'scripture/panel')", 30000);
  }
  await b.until("[...document.querySelectorAll('.dock-tab')].some((t) => t.textContent.trim() === 'Bible and lyrics')", 15000);
  await b.eval("[...document.querySelectorAll('.dock-tab')].find((t) => t.textContent.trim() === 'Bible and lyrics').click()");
  await b.until(`${P} && ${P}.querySelector('[data-el=translation] option')`, 15000);
  ok("panel loaded with translations", true, await b.eval(`[...${P}.querySelectorAll('[data-el=translation] option')].map((o) => o.value).join(',')`));
  await mark("before", "nothing");
  await sleep(1500);

  // Bible: John 3:16 typed the short way.
  await b.eval(`(() => { const q = ${P}.querySelector('[data-el=query]'); q.value = 'jn 3 16-17'; q.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); })()`);
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent.startsWith('John 3:16')`, 10000);
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await b.until(`${P}.querySelector('[data-el=pill]').textContent === 'ON AIR'`, 15000);
  await sleep(3500);
  let st = await tool("state");
  ok("John 3:16 on air", st.on_air && /For God so loved the world/.test(st.current.text), st.current && st.current.ref);
  await mark("john-3-16", "For God so loved");
  await shot("bible-john-3-16");

  // The next slide of the verse, with the arrow key, as an operator would.
  await b.eval(`${P}.querySelector('.scr').focus()`);
  await b.key("ArrowRight", "ArrowRight", 39);
  await b.until(`${P}.querySelector('.scr-slide.live') && ${P}.querySelector('.scr-slide.live').dataset.i !== '0'`, 10000).catch(() => {});
  await sleep(2000);
  st = await tool("state");
  ok("Right arrow steps the verse on", st.index === 1, `slide ${st.index + 1} of ${st.deck.count}`);
  await mark("john-3-16-part-2", st.current.text.slice(0, 20));

  // A full screen style for a psalm.
  await b.eval(`(() => { const q = ${P}.querySelector('[data-el=query]'); q.value = 'Ps 23'; q.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); })()`);
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent.startsWith('Psalm 23')`, 10000);
  await b.eval(`(() => { const s = ${P}.querySelector('[data-el=style]'); s.value = 'full-screen'; s.dispatchEvent(new Event('change')); })()`);
  await sleep(1500);
  const t0 = Date.now();
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await b.until(`${P}.querySelector('.scr-slide.live') && ${P}.deck.title.startsWith('Psalm 23')`, 15000).catch(() => {});
  console.log(`     Go live answered in ${Date.now() - t0} ms; panel says: ${await b.eval(`${P}.querySelector('[data-el=msg]').textContent`)}`);
  await sleep(2500);
  st = await tool("state");
  ok("Psalm 23 full screen on air", st.on_air && st.deck.title.startsWith("Psalm 23") && st.style.bible.id === "full-screen");
  await mark("psalm-23-full", "The LORD is my shepherd");
  await shot("bible-psalm-23-full-screen");

  // Centred verse style.
  await b.eval(`(() => { const s = ${P}.querySelector('[data-el=style]'); s.value = 'centred-verse'; s.dispatchEvent(new Event('change')); })()`);
  await sleep(3000);
  await mark("psalm-23-centred", "The LORD is my shepherd");
  await shot("bible-centred-verse");

  // Songs: a public domain hymn through the editor.
  const existing = await tool("songs", { query: "Amazing Grace" });
  for (const s of existing.songs) await tool("song_delete", { id: s.id });
  await b.eval(`${P}.querySelector('[data-tab=songs]').click()`);
  await sleep(800);
  await b.eval(`${P}.querySelector('[data-act=new-song]').click()`);
  await b.until(`${P}.querySelector('.scr-editor')`, 10000);
  await b.eval(`${P}.querySelector('.scr-editor').value = ${JSON.stringify(HYMN)}`);
  await shot("song-editor");
  await b.eval(`${P}.querySelector('.scr-dialog [data-act=save]').click()`);
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent === 'Amazing Grace'`, 10000);
  ok("hymn saved through the editor", true);
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await sleep(3000);
  st = await tool("state");
  ok("first lyric slide on air", st.on_air && /Amazing grace/.test(st.current.text), st.current.label);
  await mark("hymn-v1", "Amazing grace");
  await shot("song-verse-1");
  await b.eval(`${P}.querySelector('.scr').focus()`);
  await b.key(" ", "Space", 32);
  await sleep(3000);
  st = await tool("state");
  ok("Space steps to the next lyric slide", st.index === 1 && /taught my heart/.test(st.current.text), st.current.label);
  await mark("hymn-v2", "taught my heart");
  await shot("song-verse-2");

  // Blank, then show again, then clear.
  await b.key("b", "KeyB", 66);
  await sleep(2000);
  st = await tool("state");
  ok("B blanks", st.blank === true);
  await mark("blank", "nothing");
  await b.key("b", "KeyB", 66);
  await sleep(2000);
  await b.key("Escape", "Escape", 27);
  await sleep(2000);
  st = await tool("state");
  ok("Escape clears", st.on_air === false);
  await mark("cleared", "nothing");
  const stage = await tool("stage");
  ok("stage display started", Array.isArray(stage.urls) && stage.urls.length > 0, stage.urls.join(" "));
  console.log(b.logs.filter((l) => /scripture|EXCEPTION/i.test(l)).slice(-10).join("\n"));
} catch (e) {
  ok("drive", false, e.message);
  await shot("error");
  console.log(b.logs.slice(-20).join("\n"));
} finally {
  await b.close();
  await sleep(1500);
  timeline.stopped_at = (Date.now() - recStart) / 1000;
  await rest("POST", "/api/v1/outputs/scripture-check/stop");
  await sleep(4000);
  await rest("DELETE", "/api/v1/outputs/scripture-check");
  writeFileSync(resolve(OUT, "timeline.json"), JSON.stringify({ ...timeline, steps }, null, 2));
}
const failed = steps.filter((s) => !s.pass);
console.log(failed.length ? `${failed.length} step(s) failed` : "every step passed");
process.exit(failed.length ? 1 : 0);
