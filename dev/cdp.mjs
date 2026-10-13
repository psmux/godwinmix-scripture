// A small Chrome DevTools Protocol driver with no dependencies, for the real
// check in dev/e2e.mjs. Node 22 or newer has WebSocket built in.
//
//   const b = await Browser.launch({ chrome, port, profile, width, height });
//   await b.goto(url); await b.eval("1 + 1"); await b.shot("a.png"); await b.close();
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));

export class Browser {
  static async launch({ chrome, port, profile, width = 1600, height = 1000, headless = true }) {
    const args = [
      `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
      `--window-size=${width},${height}`, "--no-first-run", "--no-default-browser-check",
      "--disable-extensions", "--disable-background-networking", "--disable-gpu",
      "--force-device-scale-factor=1", "about:blank",
    ];
    if (headless) args.unshift("--headless=new");
    const proc = spawn(chrome, args, { stdio: "ignore" });
    let page;
    for (let i = 0; i < 100 && !page; i++) {
      await sleep(200);
      try {
        const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
        page = list.find((t) => t.type === "page");
      } catch { /* not up yet */ }
    }
    if (!page) throw new Error(`Chrome did not open its debugging port ${port}`);
    const b = new Browser(proc, page.webSocketDebuggerUrl);
    await b.open();
    await b.send("Page.enable");
    await b.send("Runtime.enable");
    await b.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    return b;
  }

  constructor(proc, url) {
    this.proc = proc;
    this.url = url;
    this.id = 0;
    this.waiting = new Map();
    this.logs = [];
  }

  open() {
    return new Promise((ok, bad) => {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => ok();
      this.ws.onerror = (e) => bad(e);
      this.ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.id && this.waiting.has(msg.id)) {
          const { ok: done, bad: fail } = this.waiting.get(msg.id);
          this.waiting.delete(msg.id);
          msg.error ? fail(new Error(JSON.stringify(msg.error))) : done(msg.result);
        } else if (msg.method === "Runtime.consoleAPICalled") {
          this.logs.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
        } else if (msg.method === "Runtime.exceptionThrown") {
          this.logs.push("EXCEPTION " + JSON.stringify(msg.params.exceptionDetails).slice(0, 600));
        }
      };
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((ok, bad) => this.waiting.set(id, { ok, bad }));
  }

  async goto(url) {
    await this.send("Page.navigate", { url });
    await sleep(500);
    await this.until("document.readyState === 'complete'", 20000);
  }

  async eval(expression) {
    const r = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 800));
    return r.result.value;
  }

  async until(expression, timeout = 15000) {
    const end = Date.now() + timeout;
    for (;;) {
      try {
        if (await this.eval(`!!(${expression})`)) return true;
      } catch { /* the page may be mid load */ }
      if (Date.now() > end) throw new Error(`timed out waiting for: ${expression}`);
      await sleep(250);
    }
  }

  async key(key, code = key, keyCode = 0) {
    for (const type of ["keyDown", "keyUp"]) {
      await this.send("Input.dispatchKeyEvent", {
        type, key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode,
        text: type === "keyDown" && key.length === 1 ? key : undefined,
      });
    }
  }

  async shot(path, clip) {
    const params = { format: "png" };
    if (clip) params.clip = { ...clip, scale: 1 };
    const r = await this.send("Page.captureScreenshot", params);
    writeFileSync(path, Buffer.from(r.data, "base64"));
  }

  async close() {
    try { await Promise.race([this.send("Browser.close"), sleep(2000)]); } catch { /* already gone */ }
    try { this.ws.close(); } catch { /* fine */ }
    await sleep(300);
    try { this.proc.kill(); } catch { /* fine */ }
  }
}

export { sleep };
