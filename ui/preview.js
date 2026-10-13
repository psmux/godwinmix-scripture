// A picture of a slide in its style, drawn in the panel with HTML and CSS
// from the same layers the programme gets. It costs the mixer nothing: no
// source, no encode. A still of the programme sits behind it when the panel
// has one, fetched only when the preview is drawn and at most every 5 seconds.

function rgba(hex) {
  if (!hex) return "transparent";
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const r = parseInt(full.slice(0, 2), 16), g = parseInt(full.slice(2, 4), 16), b = parseInt(full.slice(4, 6), 16);
  const a = full.length === 8 ? parseInt(full.slice(6, 8), 16) / 255 : 1;
  return `rgba(${r},${g},${b},${a.toFixed(3)})`;
}

const JUSTIFY = { top: "flex-start", middle: "center", bottom: "flex-end" };

export function drawPreview(box, layers, canvas, backdrop) {
  const width = box.clientWidth || 320;
  const scale = width / canvas.width;
  box.style.height = `${Math.round(canvas.height * scale)}px`;
  box.innerHTML = "";
  if (backdrop) {
    const img = document.createElement("img");
    img.src = backdrop;
    img.alt = "";
    img.className = "scr-backdrop";
    box.appendChild(img);
  }
  for (const layer of layers || []) {
    if (!layer.visible) continue;
    const p = layer.params;
    const el = document.createElement("div");
    el.className = "scr-layer";
    Object.assign(el.style, {
      left: `${layer.rect.x * scale}px`,
      top: `${layer.rect.y * scale}px`,
      width: `${layer.rect.w * scale}px`,
      height: `${layer.rect.h * scale}px`,
      padding: `${p.padding * scale}px`,
      borderRadius: `${p.radius * scale}px`,
      background: rgba(p.background),
      color: rgba(p.color),
      fontFamily: p.font,
      fontSize: `${p.size * scale}px`,
      fontWeight: String(p.weight),
      fontStyle: p.italic ? "italic" : "normal",
      textAlign: p.align,
      justifyContent: JUSTIFY[p.valign] || "center",
      textShadow: p.shadow ? `0 ${2 * scale}px ${6 * scale}px rgba(0,0,0,.85)` : "none",
      webkitTextStroke: p.outline ? `${Math.max(0.5, 1.5 * scale)}px ${rgba(p.outline)}` : "",
    });
    const span = document.createElement("span");
    span.textContent = p.text;
    el.appendChild(span);
    box.appendChild(el);
  }
}
