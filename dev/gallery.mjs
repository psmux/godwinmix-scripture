// The gallery pictures, taken from a real mixer with this plugin installed.
//
//   node dev/gallery.mjs --base http://127.0.0.1:23010 --cdp 23011 --out ./gallery-raw --still stage.png
//
// Writes screenshot-N.png of the page at 1920 by 1080 and gif/NNN.png, the
// frames dev/gif.py turns into demo.gif. Song words are a public domain hymn.
import { mkdirSync, existsSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { Browser, sleep } from "./cdp.mjs";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const BASE = arg("base", "http://127.0.0.1:23010");
const OUT = resolve(arg("out", "gallery-raw"));
const CHROME = arg("chrome", ["C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/google-chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find((p) => existsSync(p)));
mkdirSync(resolve(OUT, "gif"), { recursive: true });

const HYMN = `Title: Be Thou My Vision
Author: Irish hymn, translated by Mary Byrne and Eleanor Hull
Copyright: Public domain
Order: V1 V2 V3

[Verse 1]
Be Thou my Vision, O Lord of my heart;
Naught be all else to me, save that Thou art.
Thou my best Thought, by day or by night,
Waking or sleeping, Thy presence my light.

[Verse 2]
Be Thou my Wisdom, and Thou my true Word;
I ever with Thee and Thou with me, Lord;
Thou my great Father, I Thy true son;
Thou in me dwelling, and I with Thee one.

[Verse 3]
High King of Heaven, my victory won,
May I reach Heaven's joys, O bright Heaven's Sun!
Heart of my own heart, whatever befall,
Still be my Vision, O Ruler of all.
`;

async function rest(method, path, body) {
  const r = await fetch(BASE + path, { method, headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined });
  const t = await r.text();
  try { return JSON.parse(t); } catch { return t; }
}
const tool = async (name, args = {}) => (await rest("POST", "/api/v1/tool/call", { name: `scripture/${name}`, arguments: args })).structuredContent;

async function settled() {
  let last = null, same = 0;
  for (let i = 0; i < 30; i++) {
    const t = await rest("GET", "/api/v1/program/thumbnail?width=320");
    if (t && t.jpeg && t.jpeg === last) same++; else same = 0;
    last = (t && t.jpeg) || last;
    if (same >= 2) break;
    await sleep(1000);
  }
  await sleep(1500); // the page's own monitor follows a moment later
}

const STILL = arg("still", "");
if (STILL) {
  await rest("DELETE", "/api/v1/sources/stage-cam");
  await rest("POST", "/api/v1/sources", { id: "stage-cam", name: "Stage camera", uri: STILL });
  await sleep(3000);
  await rest("POST", "/api/v1/program/take", { source: "stage-cam" });
  await sleep(2000);
}
for (const s of (await tool("songs", { query: "Be Thou" })).songs) await tool("song_delete", { id: s.id });
await tool("clear");
await tool("style_set", { kind: "bible", id: "lower-third", overrides: {} });
await tool("style_set", { kind: "song", id: "lyrics-lower", overrides: {} });

const b = await Browser.launch({ chrome: CHROME, port: Number(arg("cdp", "23011")), profile: resolve(OUT, "chrome"), width: 1920, height: 1080 });
const P = "document.querySelector('gmx-scripture-panel')";
let frame = 0;
// The top of the page: the programme and the panel beside it.
const gifShot = async (repeat = 1) => {
  for (let i = 0; i < repeat; i++) {
    await b.shot(resolve(OUT, "gif", `${String(frame++).padStart(3, "0")}.png`), { x: 0, y: 92, width: 1920, height: 560 });
  }
};
const type = (q) => b.eval(`(() => { const e = ${P}.querySelector('[data-el=query]'); e.value = ${JSON.stringify(q)};
  e.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); })()`);
try {
  await b.goto(BASE + "/");
  await b.until("(window.godwinmixPanels || []).some((p) => p.panel && p.panel.id === 'scripture/panel')", 30000);
  await b.eval(`import('/shell/dock-model.js').then((m) => { const s = m.load(); s.tree = m.dock(s.tree, 'scripture/panel', 'core/program', 'right'); m.save(s); })`);
  await b.goto(BASE + "/");
  await b.until(`${P} && ${P}.querySelector('[data-el=translation] option')`, 30000);
  await sleep(2000);
  await gifShot(2);

  await type("jn 3 16-17");
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent.startsWith('John 3:16')`, 15000);
  await gifShot(2);
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await settled();
  await gifShot(3);
  await b.shot(resolve(OUT, "screenshot-1.png"));
  await b.eval(`${P}.querySelector('.scr').focus()`);
  await b.key("ArrowRight", "ArrowRight", 39);
  await settled();
  await gifShot(3);

  await type("Ps 23");
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent.startsWith('Psalm 23')`, 15000);
  await b.eval(`(() => { const s = ${P}.querySelector('[data-el=style]'); s.value = 'full-screen'; s.dispatchEvent(new Event('change')); })()`);
  await sleep(1500);
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await settled();
  await gifShot(3);
  await b.shot(resolve(OUT, "screenshot-2.png"));

  await b.eval(`${P}.querySelector('[data-tab=songs]').click()`);
  await b.eval(`${P}.querySelector('[data-act=new-song]').click()`);
  await b.until(`${P}.querySelector('.scr-editor')`, 10000);
  await b.eval(`${P}.querySelector('.scr-editor').value = ${JSON.stringify(HYMN)}`);
  await gifShot(2);
  await b.shot(resolve(OUT, "screenshot-4.png"));
  await b.eval(`${P}.querySelector('.scr-dialog [data-act=save]').click()`);
  await b.until(`${P}.querySelector('[data-el=deck-title]').textContent === 'Be Thou My Vision'`, 10000);
  await b.eval(`${P}.querySelector('[data-act=go]').click()`);
  await settled();
  await gifShot(3);
  await b.shot(resolve(OUT, "screenshot-3.png"));
  await b.eval(`${P}.querySelector('.scr').focus()`);
  await b.key(" ", "Space", 32);
  await settled();
  await gifShot(3);
  await b.key("b", "KeyB", 66);
  await settled();
  await gifShot(2);
  await b.key("b", "KeyB", 66);
  await settled();
  await gifShot(2);

  const stage = await tool("stage");
  await b.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  await b.goto(stage.urls[0]);
  await sleep(2500);
  await b.shot(resolve(OUT, "screenshot-5.png"));
  writeFileSync(resolve(OUT, "done.txt"), "ok\n");
} catch (e) {
  console.log("ERR", e.message);
  await b.shot(resolve(OUT, "error.png"));
} finally {
  await b.close();
}
process.exit(0);
