// Putting words on the programme, through the mixer's public methods only.
//
// Two text sources, scripture-body and scripture-ref, drawn by the mixer's
// own text source (text/source). They are added once and then changed in
// place with source.set, which swaps the words on the next frame: no source
// is rebuilt and the programme does not skip. Each is an item in whatever
// scene is on the programme; showing and hiding them is scene.item.set with
// visible, which plays a short fade.
//
// When the programme is a bare source rather than a scene, Go live wraps it
// in a scene called "<source> with words" holding that source full frame,
// and takes it. The picture is the same; the words can now sit on it.

const IDS = ["scripture-body", "scripture-ref"];
const FADE = { type: "fade", duration_ms: 200 };

export class OnAir {
  constructor(client) {
    this.client = client;
    this.placed = new Map(); // scene name -> {id: "x,y,w,h"} of what is placed there
    this.added = new Set(); // source ids known to exist
    this.scene = null;
    this.shown = false;
  }

  call(method, params) {
    return this.client.call(method, params || {});
  }

  async programmeScene() {
    const p = await this.call("program.get");
    if (p.scene) return p.scene;
    const source = p.program || "";
    const name = source ? `${source} with words` : "Words";
    const list = await this.call("scene.list");
    if (!(list.scenes || []).some((s) => s.name === name)) {
      if (source) await this.call("scene.create_from", { sources: [source], name });
      else await this.call("scene.add", { name });
    }
    await this.call("program.take", { scene: name });
    return name;
  }

  async ensureSource(layer) {
    if (this.added.has(layer.id)) {
      try {
        await this.call("source.set", { id: layer.id, params: layer.params });
        return;
      } catch (e) {
        if (e.code !== -32004) throw e;
        this.added.delete(layer.id);
      }
    }
    try {
      await this.call("source.set", { id: layer.id, params: layer.params });
    } catch (e) {
      if (e.code !== -32004 && !/no source|not found|unknown source/i.test(e.message || "")) throw e;
      await this.call("source.add", {
        id: layer.id,
        name: layer.id === "scripture-body" ? "Scripture words" : "Scripture reference",
        uri: "text: ",
        type: "text/source",
        params: layer.params,
      });
    }
    this.added.add(layer.id);
  }

  async itemsIn(scene) {
    const doc = await this.call("scene.get", { scene });
    const have = new Set();
    for (const r of doc.records || []) {
      if (r.kind === "item" && IDS.includes(r.name)) have.add(r.name);
    }
    return have;
  }

  // Put one slide's layers on the programme. blank keeps them hidden.
  async show(layers, { blank = false } = {}) {
    const scene = await this.programmeScene();
    if (scene !== this.scene) {
      this.scene = scene;
      this.placed.set(scene, await this.placedIn(scene));
    }
    const placed = this.placed.get(scene);
    for (const layer of layers) await this.ensureSource(layer);
    for (const layer of layers) {
      const visible = layer.visible && !blank;
      const box = `${layer.rect.x},${layer.rect.y},${layer.rect.w},${layer.rect.h}`;
      const transform = {
        position: { x: layer.rect.x, y: layer.rect.y },
        frame: { w: layer.rect.w, h: layer.rect.h },
      };
      if (!(layer.id in placed)) {
        await this.call("scene.item.add", {
          scene, content: { source: layer.id }, name: layer.id, transform, visible,
          enter: FADE, exit: FADE,
        });
      } else if (placed[layer.id].box !== box || placed[layer.id].visible !== visible) {
        const props = { visible };
        if (placed[layer.id].box !== box) props.transform = transform;
        await this.call("scene.item.set", { scene, item: layer.id, props });
      }
      placed[layer.id] = { box, visible };
    }
    this.shown = !blank;
    return scene;
  }

  async placedIn(scene) {
    const have = await this.itemsIn(scene);
    const placed = {};
    for (const id of have) placed[id] = { box: "", visible: null };
    return placed;
  }

  // Take the words off: hide the items, keep the sources for next time.
  async hide() {
    const p = await this.call("program.get");
    const scene = p.scene;
    if (!scene) return;
    const have = await this.itemsIn(scene);
    const placed = this.placed.get(scene) || {};
    for (const id of have) {
      await this.call("scene.item.set", { scene, item: id, props: { visible: false } });
      if (placed[id]) placed[id].visible = false;
    }
    this.placed.set(scene, placed);
    this.shown = false;
  }

  // The operator took another scene while words were up: follow them there.
  async follow(sceneName, layers, blank) {
    if (!sceneName || sceneName === this.scene) return;
    await this.show(layers, { blank });
  }
}
