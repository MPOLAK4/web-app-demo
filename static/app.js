// Wireframe editor (R1(e), R7(e), R8, R9(g)). Plain JavaScript, no libraries.
//
// The one rule that keeps this file small: the browser never changes the
// wireframe itself. Every edit is sent to the server as an "op" message
// (POST /api/op); the server applies it with the same Python code the command
// line uses, saves the file, and replies with the new wireframe. We then just
// redraw. So the browser and the headless tools cannot disagree.
//
// How a block LOOKS is also decided by the server (GET /api/resolved gives the
// final style of every block), and how Play mode FOLLOWS the flow is decided by
// the server too (/api/play). The words inside a block, including data standins
// (GET /api/lines), come from the server as well. This file only draws what it is told.
//
// We only ever write text with .textContent (never innerHTML), so a label
// like "<script>" is shown as text and cannot run as code.
"use strict";

const BLOCK_TYPES = [
  "heading", "text", "button", "input", "image", "list", "nav", "container",
  "textarea", "checkbox", "radio", "toggle", "select", "slider", "tabs", "card",
  "table", "modal", "icon", "divider", "link", "badge", "avatar",
];
const PRESETS = ["phone", "tablet", "desktop"];

let doc = null;            // the wireframe, exactly as the server last sent it
let resolved = {};         // "stateId/blockId" -> full style, from /api/resolved
let current = null;        // id of the state (screen) being shown
let selected = null;       // id of the main selected block, or null
let picked = new Set();    // ids of all selected blocks (shift-click adds)
let playing = false;       // true while Play mode is on
let dataMode = "debug";    // "debug" shows {{tokens}} as written, "live" shows sample text (R11)
let lines = {};            // blockId -> text lines on the current screen, from /api/lines
let linesFor = null;       // the screen `lines` belongs to; null means "ask the server again"

const $ = (id) => document.getElementById(id);

// el("div", {className: "x", onclick: fn}, [child, "text"]) builds an element.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) node[key] = value;
  for (const child of [].concat(children)) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// ---------- talking to the server ----------

async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  const isJson = (response.headers.get("Content-Type") || "").includes("json");
  const data = isJson ? await response.json() : await response.text();
  return { ok: response.ok, data };
}

function showStatus(messages) {
  const box = $("status");
  box.textContent = [].concat(messages).join(" | ");
  box.className = messages.length ? "error" : "";
}

// Send one edit. Returns true if the server accepted it.
async function send(op) {
  const result = await api("POST", "/api/op", op);
  if (!result.ok) {
    showStatus(result.data.errors || ["the edit was rejected"]);
    await load();            // throw away anything we drew that the server refused
    return false;
  }
  showStatus([]);
  await adopt(result.data);
  return true;
}

async function adopt(newDoc) {
  doc = newDoc;
  const styled = await api("GET", "/api/resolved");
  resolved = styled.ok ? styled.data : {};
  linesFor = null;                  // the text may have changed; render() will refetch it
  if (!doc.states.some((s) => s.id === current)) current = doc.initial || (doc.states[0] || {}).id || null;
  const ids = new Set((currentState() || { blocks: [] }).blocks.map((b) => b.id));
  picked = new Set([...picked].filter((id) => ids.has(id)));
  if (!ids.has(selected)) selected = [...picked].at(-1) || null;
  render();
  refreshFindings();
}

async function refreshLines() {
  linesFor = current;               // set first so a failed request cannot loop forever
  if (!current) { lines = {}; return; }
  const result = await api("GET", `/api/lines?state=${encodeURIComponent(current)}&data=${dataMode}`);
  lines = result.ok ? result.data : {};
}

async function load() {
  const result = await api("GET", "/api/wireframe");
  if (result.ok) await adopt(result.data);
  else showStatus(["could not load the wireframe"]);
}

// ---------- small helpers ----------

const currentState = () => (doc && doc.states.find((s) => s.id === current)) || null;
const currentBlock = () => {
  const st = currentState();
  return st ? st.blocks.find((b) => b.id === selected) || null : null;
};
const gridSize = () => Math.max(1, Math.round(Number($("grid-size").value)) || 1);
const snap = (v) => Math.round(v / gridSize()) * gridSize();

// "fill=#2a6cf0, radius=8, shadow=true" <-> {fill: "#2a6cf0", radius: 8, shadow: true}
// The server checks the names and values; we only turn text into JSON types.
function parseFields(text) {
  const out = {};
  for (const part of text.split(",").map((s) => s.trim()).filter(Boolean)) {
    const at = part.indexOf("=");
    if (at < 1) { showStatus([`'${part}' should look like name=value`]); return null; }
    const key = part.slice(0, at).trim(), raw = part.slice(at + 1).trim();
    out[key] = raw === "true" ? true : raw === "false" ? false : /^-?\d+(\.\d+)?$/.test(raw) ? Number(raw) : raw;
  }
  return out;
}
const formatFields = (obj) => Object.entries(obj || {}).map(([k, v]) => `${k}=${v}`).join(", ");

// ---------- drawing ----------

function render() {
  // The text inside blocks comes from the server. If we do not have it for this
  // screen yet (or the document or data mode changed), ask, then draw.
  if (!playing && linesFor !== current) { refreshLines().then(render); return; }
  renderHeader();
  renderData();
  renderSaveLinks();
  renderStates();
  renderStyles();
  renderPalette();
  renderTools();
  renderCanvas();
  renderInspector();
  renderTransitions();
  $("play-panel").hidden = !playing;
  $("edit-panels").hidden = playing;
  $("palette").hidden = playing;
  $("block-tools").hidden = playing;
  $("btn-play").textContent = playing ? "Stop playing" : "Play";
  if (playing) drawPlay();
}

function renderHeader() {
  $("doc-name").value = doc.name;
  $("doc-width").value = doc.canvas.width;
  $("doc-height").value = doc.canvas.height;
  const preset = $("doc-preset");
  preset.replaceChildren(el("option", { value: "" }, "(choose a size)"),
    ...PRESETS.map((p) => el("option", { value: p }, p)));
  const st = currentState();
  $("state-bg").value = st ? st.background || "" : "";
}

function renderStates() {
  const list = $("state-list");
  list.replaceChildren();
  for (const st of doc.states) {
    const initial = el("input", { type: "radio", name: "initial", checked: doc.initial === st.id, title: "Start screen" });
    initial.onchange = () => send({ op: "update_wireframe", initial: st.id });
    const final = el("input", { type: "checkbox", checked: st.final, title: "Final screen (the flow may end here)" });
    final.onchange = () => send({ op: "update_state", id: st.id, final: final.checked });
    const title = el("span", { className: "title", title: "Click to open, double-click to rename" }, st.title);
    title.onclick = () => { if (playing) return; current = st.id; selected = null; picked = new Set(); render(); };
    title.ondblclick = () => {
      const name = prompt("New title for this screen", st.title);
      if (name) send({ op: "update_state", id: st.id, title: name });
    };
    const remove = el("button", { title: "Delete this screen and its transitions" }, "x");
    remove.onclick = () => {
      if (confirm(`Delete screen "${st.title}" and its transitions?`)) send({ op: "delete_state", id: st.id });
    };
    list.append(el("li", { className: st.id === current ? "selected" : "" }, [initial, final, title, remove]));
  }
}

// The style manager: one row per named style (R7(e)).
function renderStyles() {
  const box = $("style-list");
  box.replaceChildren();
  for (const [name, fields] of Object.entries(doc.styles || {})) {
    const input = el("input", { value: formatFields(fields), title: "Edit the fields, then press Enter or leave the box" });
    input.onchange = () => {
      const parsed = parseFields(input.value);
      if (parsed) send({ op: "update_style", name, style: parsed });
    };
    const apply = el("button", { title: "Give this style to the selected blocks" }, "Use");
    apply.onclick = () => {
      if (picked.size) send({ op: "set_style", state: current, ids: [...picked], style: name });
      else showStatus(["select one or more blocks first"]);
    };
    const remove = el("button", { title: "Delete the style; blocks keep how they look" }, "x");
    remove.onclick = () => send({ op: "delete_style", name });
    box.append(el("div", { className: "style-row" }, [el("strong", {}, name), input, el("span", {}, [apply, remove])]));
  }
}

function renderPalette() {
  const bar = $("palette");
  bar.replaceChildren(el("span", {}, "Add: "));
  for (const type of BLOCK_TYPES) {
    const button = el("button", { disabled: !current }, type);
    button.onclick = async () => {
      const st = currentState();
      const offset = (st.blocks.length % 10) * 12;   // so new blocks do not land exactly on top of each other
      const ok = await send({ op: "add_block", state: current, type, x: snap(20 + offset), y: snap(20 + offset), label: type });
      if (ok) { selected = currentState().blocks.at(-1).id; picked = new Set([selected]); render(); }
    };
    bar.append(button);
  }
}

// Duplicate and stacking-order buttons act on every selected block (R8(e)).
function renderTools() {
  const bar = $("block-tools");
  bar.replaceChildren(el("span", {}, "Selected: "));
  const none = picked.size === 0;
  const each = async (make) => {
    for (const id of [...picked]) if (!(await send(make(id)))) return;
  };
  const dup = el("button", { disabled: none, title: "Copy the selected blocks, 20 px down and right" }, "Duplicate");
  dup.onclick = async () => {
    const before = new Set(currentState().blocks.map((b) => b.id));
    await each((id) => ({ op: "duplicate_block", state: current, id }));
    const fresh = currentState().blocks.filter((b) => !before.has(b.id)).map((b) => b.id);
    picked = new Set(fresh); selected = fresh.at(-1) || null; render();
  };
  bar.append(dup);
  const order = [["front", "To front"], ["forward", "Forward"], ["backward", "Backward"], ["back", "To back"]];
  for (const [where, text] of order) {
    const button = el("button", { disabled: none, title: "Change which blocks are drawn on top" }, text);
    button.onclick = () => each((id) => ({ op: "reorder_block", state: current, id, where }));
    bar.append(button);
  }
}

// Turn a resolved style into CSS. Used by the editor and by Play, so both look the same.
function applyStyle(node, r) {
  const s = node.style;
  if (!r) return;
  if (r.fill) s.background = r.fill;
  if (r.text_color) s.color = r.text_color;
  if (r.border_width !== undefined || r.border_color) {
    s.border = `${r.border_width === undefined ? 1 : r.border_width}px solid ${r.border_color || "#667"}`;
  }
  if (r.radius !== undefined) s.borderRadius = r.radius + "px";
  if (r.padding !== undefined) s.padding = r.padding + "px";
  if (r.font_size !== undefined) s.fontSize = r.font_size + "px";
  if (r.font_weight) s.fontWeight = String(r.font_weight);
  if (r.align) s.textAlign = r.align;
  if (r.opacity !== undefined) s.opacity = String(r.opacity);
  if (r.shadow) s.boxShadow = "0 3px 8px rgba(0,0,0,.3)";
}

// What a block says on the page. The server works it out (render.content_lines)
// so the editor, Play and the saved picture files can never disagree.
const linesOf = (b) => b.lines || lines[b.id] || [b.label];

function fillContent(node, b, withKind) {
  if (withKind) node.append(el("span", { className: "kind" }, b.type));
  for (const line of linesOf(b)) node.append(el("div", { className: "line" }, line));
}

function renderCanvas() {
  const canvas = $("canvas");
  canvas.replaceChildren();
  canvas.style.width = doc.canvas.width + "px";
  canvas.style.height = doc.canvas.height + "px";
  const st = currentState();
  canvas.style.background = (st && st.background) || "#ffffff";
  canvas.onpointerdown = null;
  if (!st) return;
  if (playing) return;                          // Play draws its own canvas
  canvas.onpointerdown = (event) => {
    if (event.target === canvas) { selected = null; picked = new Set(); highlight(); renderInspector(); renderTools(); }
  };
  for (const b of st.blocks) canvas.append(blockNode(b));
}

function blockNode(b) {
  const cls = ["block", `t-${b.type}`];
  if (picked.has(b.id)) cls.push("selected");
  if (b.hidden) cls.push("is-hidden");
  const node = el("div", { className: cls.join(" "), title: `${b.type} ${b.id}${b.hidden ? " (hidden)" : ""}` });
  node.dataset.id = b.id;
  applyStyle(node, resolved[`${current}/${b.id}`]);
  fillContent(node, b, true);
  if (b.hidden) node.style.opacity = "0.35";    // so it can still be found and edited
  Object.assign(node.style, { left: b.x + "px", top: b.y + "px", width: b.w + "px", height: b.h + "px" });
  for (const corner of ["nw", "ne", "sw", "se"]) {
    const handle = el("div", { className: `handle ${corner}`, title: "Drag to resize" });
    handle.addEventListener("pointerdown", (event) => { event.stopPropagation(); beginDrag(event, b, node, corner); });
    node.append(handle);
  }
  node.addEventListener("pointerdown", (event) => beginDrag(event, b, node, "move"));
  return node;
}

function allBlockNodes() { return [...document.querySelectorAll("#canvas .block")]; }

// Dragging moves the <div> on screen while the mouse is down; only when the
// button is released do we send ONE op with the final numbers.
function beginDrag(event, b, node, mode) {
  event.preventDefault();
  if (mode === "move" && event.shiftKey) { select(b.id, true); return; }   // shift-click only changes the selection
  select(b.id, false);
  node.setPointerCapture(event.pointerId);
  const st = currentState();
  const group = mode === "move" && picked.size > 1 ? st.blocks.filter((o) => picked.has(o.id)) : [b];
  const start = { x: event.clientX, y: event.clientY, bx: b.x, by: b.y, bw: b.w, bh: b.h };
  let result = { x: b.x, y: b.y, w: b.w, h: b.h };
  let shift = { dx: 0, dy: 0 };
  let moved = false;

  const onMove = (e) => {
    let dx = Math.round(e.clientX - start.x), dy = Math.round(e.clientY - start.y);
    moved = moved || dx !== 0 || dy !== 0;
    if (mode === "move") {
      dx = snap(start.bx + dx) - start.bx; dy = snap(start.by + dy) - start.by;
      dx = Math.max(dx, -Math.min(...group.map((o) => o.x)));      // never push a block off the left edge
      dy = Math.max(dy, -Math.min(...group.map((o) => o.y)));
      shift = { dx, dy };
      for (const other of allBlockNodes()) {
        const o = group.find((g) => g.id === other.dataset.id);
        if (o) Object.assign(other.style, { left: o.x + dx + "px", top: o.y + dy + "px" });
      }
      return;
    }
    let { bx: x, by: y, bw: w, bh: h } = start;
    if (mode.includes("e")) w = start.bw + dx;
    if (mode.includes("w")) { w = start.bw - dx; x = start.bx + dx; }
    if (mode.includes("s")) h = start.bh + dy;
    if (mode.includes("n")) { h = start.bh - dy; y = start.by + dy; }
    x = snap(x); y = snap(y); w = snap(w); h = snap(h);
    if (w < 10) { if (mode.includes("w")) x -= 10 - w; w = 10; }
    if (h < 10) { if (mode.includes("n")) y -= 10 - h; h = 10; }
    if (x < 0) { if (mode.includes("w")) w += x; x = 0; }
    if (y < 0) { if (mode.includes("n")) h += y; y = 0; }
    result = { x, y, w: Math.max(10, w), h: Math.max(10, h) };
    Object.assign(node.style, { left: result.x + "px", top: result.y + "px", width: result.w + "px", height: result.h + "px" });
  };
  const onUp = () => {
    node.removeEventListener("pointermove", onMove);
    node.removeEventListener("pointerup", onUp);
    node.removeEventListener("pointercancel", onUp);
    if (!moved) return;
    if (mode === "move") {
      if (shift.dx === 0 && shift.dy === 0) return;
      if (group.length > 1) send({ op: "move_blocks", state: current, ids: group.map((o) => o.id), dx: shift.dx, dy: shift.dy });
      else send({ op: "update_block", state: current, id: b.id, x: b.x + shift.dx, y: b.y + shift.dy });
    } else {
      send({ op: "update_block", state: current, id: b.id, x: result.x, y: result.y, w: result.w, h: result.h });
    }
  };
  node.addEventListener("pointermove", onMove);
  node.addEventListener("pointerup", onUp);
  node.addEventListener("pointercancel", onUp);
}

function highlight() {
  for (const node of allBlockNodes()) node.classList.toggle("selected", picked.has(node.dataset.id));
}

// Selecting does not redraw the canvas (that would destroy the block mid-drag);
// it only moves the highlight and refreshes the side panels.
function select(id, additive) {
  if (additive) {
    if (picked.has(id)) { picked.delete(id); selected = [...picked].at(-1) || null; }
    else { picked.add(id); selected = id; }
  } else if (!picked.has(id)) {
    picked = new Set([id]); selected = id;
  } else {
    selected = id;
  }
  highlight();
  renderInspector();
  renderTools();
}

function renderInspector() {
  const box = $("inspector");
  const b = currentBlock();
  if (!b) {
    box.replaceChildren(el("p", { className: "hint" }, "Click a block to edit it. Shift-click to select several."));
    return;
  }
  const edit = (field, value) => send({ op: "update_block", state: current, id: b.id, [field]: value });
  const text = (label, field, value) => {
    const input = el("input", { value });
    input.onchange = () => edit(field, input.value);
    return el("label", {}, [label, input]);
  };
  const number = (label, field, value) => {
    const input = el("input", { type: "number", value, step: 1 });
    input.onchange = () => edit(field, Number(input.value));
    return el("label", {}, [label, input]);
  };
  const flag = (label, field) => {
    const input = el("input", { type: "checkbox", checked: Boolean(b[field]) });
    input.onchange = () => edit(field, input.checked);
    return el("label", { className: "inline" }, [input, " " + label]);
  };

  const type = el("select", {}, BLOCK_TYPES.map((t) => el("option", { value: t, selected: t === b.type }, t)));
  type.onchange = () => edit("type", type.value);

  const info = el("input", { value: b.info.join(", "), placeholder: "e.g. cart.total, user.name" });
  info.onchange = () => edit("info", info.value.split(",").map((s) => s.trim()).filter(Boolean));

  const options = el("input", { value: (b.options || []).join(", "), placeholder: "choices, comma-separated" });
  options.onchange = () => edit("options", options.value.split(",").map((s) => s.trim()).filter(Boolean));

  const note = el("textarea", { rows: 3, value: b.note });
  note.onchange = () => edit("note", note.value);

  // Style picker: applies to every selected block (R7(e)).
  const names = Object.keys(doc.styles || {});
  const style = el("select", {}, [el("option", { value: "" }, "(no named style)"),
    ...names.map((n) => el("option", { value: n, selected: n === b.style }, n))]);
  style.onchange = () => send({ op: "set_style", state: current, ids: [...picked], style: style.value });

  const look = el("input", { value: formatFields(b.look), placeholder: "fill=#fff, radius=6 (overrides the style)" });
  look.onchange = () => {
    const parsed = parseFields(look.value);
    if (parsed) edit("look", parsed);
  };

  const duplicate = el("button", {}, "Duplicate");
  duplicate.onclick = async () => {
    if (await send({ op: "duplicate_block", state: current, id: b.id })) {
      selected = currentState().blocks.at(-1).id; picked = new Set([selected]); render();
    }
  };
  const remove = el("button", {}, "Delete block");
  remove.onclick = () => send({ op: "delete_block", state: current, id: b.id });

  const count = picked.size > 1 ? el("p", { className: "hint" }, `${picked.size} blocks selected: drag to move them together; the style picker applies to all.`) : "";

  box.replaceChildren(
    count,
    el("label", {}, ["Type", type]),
    text("Label (text shown)", "label", b.label),
    el("label", {}, ["Information it shows or collects (comma-separated keys)", info]),
    text("Event (what happens when it is used)", "event", b.event),
    el("label", {}, ["Note for the coder", note]),
    el("label", {}, ["Named style", style]),
    el("label", {}, ["This block's own look", look]),
    text("Placeholder", "placeholder", b.placeholder || ""),
    text("Value", "value", b.value === undefined ? "" : String(b.value)),
    el("label", {}, ["Choices", options]),
    el("div", { className: "row" }, [flag("disabled", "disabled"), flag("hidden", "hidden"), flag("required", "required")]),
    number("x", "x", b.x), number("y", "y", b.y), number("width", "w", b.w), number("height", "h", b.h),
    el("div", { className: "row" }, [duplicate, remove]),
  );
}

function renderTransitions() {
  const box = $("transitions");
  box.replaceChildren();
  const st = currentState();
  if (!st) return;
  const titleOf = (id) => (doc.states.find((s) => s.id === id) || { title: `? ${id}` }).title;

  for (const t of doc.transitions.filter((t) => t.source === current || t.target === current)) {
    const event = el("input", { value: t.event, title: "Event (a button's event, or sys:something)" });
    event.onchange = () => send({ op: "update_transition", id: t.id, event: event.value });
    const guard = el("input", { value: t.guard, placeholder: "guard (optional condition, text only)" });
    guard.onchange = () => send({ op: "update_transition", id: t.id, guard: guard.value });
    const remove = el("button", {}, "Delete");
    remove.onclick = () => send({ op: "delete_transition", id: t.id });
    box.append(el("div", { className: "tr" }, [`${titleOf(t.source)} → ${titleOf(t.target)}`, event, guard, remove]));
  }

  const target = el("select", {}, doc.states.map((s) => el("option", { value: s.id }, s.title)));
  const event = el("input", { placeholder: "event, e.g. click-pay", required: true });
  const guard = el("input", { placeholder: "guard (optional)" });
  const form = el("form", { className: "tr" }, [el("strong", {}, "Add transition from this screen"), target, event, guard, el("button", {}, "Add")]);
  form.onsubmit = async (e) => {
    e.preventDefault();
    if (await send({ op: "add_transition", source: current, target: target.value, event: event.value, guard: guard.value })) {
      event.value = ""; guard.value = "";
    }
  };
  box.append(form);
}

// ---------- problems (R4, R5) ----------

async function refreshFindings() {
  const result = await api("GET", "/api/check");
  const list = $("findings");
  list.replaceChildren();
  if (!result.ok) return;
  const { findings } = result.data;
  $("findings-count").textContent = findings.length ? `(${findings.length})` : "";
  if (!findings.length) list.append(el("li", {}, "No problems found."));
  for (const f of findings) {
    const item = el("li", { className: f.severity }, [el("code", {}, f.code), " ", f.message]);
    item.onclick = () => {
      if (playing) return;
      if (f.state && doc.states.some((s) => s.id === f.state)) {
        current = f.state;
        selected = (f.blocks || [])[0] || null;
        picked = new Set(selected ? [selected] : []);
        render();
      }
    };
    list.append(item);
  }
}

// ---------- sample data and picture files (R10, R11) ----------

// One row per key of doc.data. Edits go through the set_data / delete_data ops.
function renderData() {
  const box = $("data-list");
  box.replaceChildren();
  for (const [key, value] of Object.entries(doc.data || {})) {
    const input = el("input", { value, title: "Sample text shown in live mode" });
    input.onchange = () => send({ op: "set_data", key, value: input.value });
    const remove = el("button", { title: "Delete this sample" }, "x");
    remove.onclick = () => send({ op: "delete_data", key });
    box.append(el("div", { className: "style-row" }, [el("strong", {}, key), input, el("span", {}, [remove])]));
  }
  if (!Object.keys(doc.data || {}).length) box.append(el("p", { className: "hint" }, "No samples yet. A {{key}} with no sample shows a standin made from its name."));
  $("data-mode").value = dataMode;
}

// The links ask the server for the screen being shown, in the mode being shown.
function renderSaveLinks() {
  for (const format of ["html", "svg"]) {
    const link = $("save-" + format);
    link.hidden = !current;
    if (current) link.href = `/api/render?state=${encodeURIComponent(current)}&format=${format}&data=${dataMode}&download=1`;
  }
}

$("data-mode").onchange = () => {
  dataMode = $("data-mode").value;
  linesFor = null;
  if (playing && playScreen) playGoto(playScreen.state); else render();
};

$("add-data-form").onsubmit = async (e) => {
  e.preventDefault();
  if (await send({ op: "set_data", key: $("new-data-key").value.trim(), value: $("new-data-value").value })) {
    $("new-data-key").value = "";
    $("new-data-value").value = "";
  }
};

// ---------- spec viewer, guide, import ----------

async function showText(title, url) {
  const result = await api("GET", url);
  if (!result.ok) { showStatus([typeof result.data === "string" ? result.data : "could not load"]); return; }
  $("viewer-title").textContent = title;
  $("viewer-text").value = result.data;
  $("viewer").showModal();
}

$("btn-spec-coder").onclick = () => showText("Spec sheet for a coding AI", "/api/spec?mode=coder");
$("btn-spec-image").onclick = () => showText("Spec sheet for an image-generating AI", `/api/spec?mode=image&data=${dataMode}`);
$("btn-guide").onclick = () => showText("Guide for an AI that writes a wireframe", "/api/guide");
$("viewer-close").onclick = () => $("viewer").close();
$("viewer-copy").onclick = async () => {
  const area = $("viewer-text");
  try { await navigator.clipboard.writeText(area.value); showStatus([]); }
  catch (err) { area.select(); }   // clipboard blocked: select the text so Ctrl+C works
};

$("btn-import").onclick = () => { $("import-errors").replaceChildren(); $("importer").showModal(); };
$("import-close").onclick = () => $("importer").close();
$("import-go").onclick = async () => {
  const errors = $("import-errors");
  errors.replaceChildren();
  let proposal;
  try { proposal = JSON.parse($("import-text").value); }
  catch (err) { errors.append(el("li", {}, "That is not valid JSON: " + err.message)); return; }
  const result = await api("PUT", "/api/wireframe", proposal);
  if (!result.ok) {
    for (const message of result.data.errors || ["rejected"]) errors.append(el("li", {}, message));
    return;
  }
  $("importer").close();
  $("import-text").value = "";
  current = null; selected = null; picked = new Set();
  await adopt(result.data);
};

// ---------- header fields ----------

$("doc-name").onchange = () => send({ op: "update_wireframe", name: $("doc-name").value });
$("doc-width").onchange = () => send({ op: "update_wireframe", width: Number($("doc-width").value) });
$("doc-height").onchange = () => send({ op: "update_wireframe", height: Number($("doc-height").value) });
$("doc-preset").onchange = () => {
  const preset = $("doc-preset").value;
  if (preset) send({ op: "update_wireframe", preset });
};
$("state-bg").onchange = () => {
  if (current) send({ op: "update_state", id: current, background: $("state-bg").value.trim() || "#ffffff" });
};

$("add-state-form").onsubmit = async (e) => {
  e.preventDefault();
  const title = $("new-state-title").value;
  if (await send({ op: "add_state", title })) {
    $("new-state-title").value = "";
    current = doc.states.at(-1).id;
    selected = null; picked = new Set();
    render();
  }
};

$("add-style-form").onsubmit = async (e) => {
  e.preventDefault();
  const fields = parseFields($("new-style-fields").value);
  if (!fields) return;
  if (await send({ op: "add_style", name: $("new-style-name").value.trim(), style: fields })) {
    $("new-style-name").value = ""; $("new-style-fields").value = "";
  }
};

// ---------- play mode (R9(g)) ----------
// Everything in this section only READS: it asks /api/play where a click leads
// and redraws. It never calls the edit function and never writes the file.

let playScreen = null;   // what the server said the user sees now
let playTrail = [];      // screens visited before this one, for Back
let playLog = [];        // lines for the path log

async function playGoto(stateId) {
  const result = await api("GET", `/api/play?state=${encodeURIComponent(stateId)}&data=${dataMode}`);
  if (!result.ok) { showStatus(result.data.errors || ["could not show that screen"]); return false; }
  playScreen = result.data;
  current = result.data.state;
  drawPlay();
  return true;
}

async function playStart() {
  playing = true;
  playTrail = [];
  playLog = [];
  selected = null; picked = new Set();
  render();
  if (!(await playGoto(doc.initial || (doc.states[0] || {}).id))) return;
  playLog.push(`Started on "${playScreen.title}"`);
  drawPlay();
}

function playStop() {
  playing = false;
  playScreen = null;
  render();
}

// Raise an event on the current screen. `choice` is a transition id when the
// server asked us to pick between guarded alternatives.
async function playEvent(event, choice) {
  const body = { state: playScreen.state, event };
  if (choice) body.choice = choice;
  const result = await api("POST", "/api/play", body);
  if (!result.ok) { showStatus(result.data.errors || ["play failed"]); return; }
  showStatus([]);
  const step = result.data;
  const chooser = $("play-chooser");
  chooser.replaceChildren();
  if (step.status === "moved") {
    playTrail.push(playScreen.state);
    const from = playScreen.title;
    if (await playGoto(step.state)) playLog.push(`${from} --${event}--> ${playScreen.title}`);
  } else if (step.status === "stuck") {
    playLog.push(`${event}: nothing happens (no transition handles it)`);
  } else {
    playLog.push(`${event}: several transitions could apply, choose one`);
    chooser.append(el("p", { className: "hint" }, "Which one applies?"));
    for (const option of step.options) {
      const target = (doc.states.find((s) => s.id === option.target) || { title: option.target }).title;
      const button = el("button", {}, `${option.guard ? "if " + option.guard : "(no condition)"} → ${target}`);
      button.onclick = () => playEvent(event, option.transition);
      chooser.append(button);
    }
  }
  drawPlay();
}

async function playBack() {
  if (!playTrail.length) return;
  const previous = playTrail.pop();
  $("play-chooser").replaceChildren();
  if (await playGoto(previous)) playLog.push(`Back to "${playScreen.title}"`);
  drawPlay();
}

function drawPlay() {
  if (!playScreen) return;
  const canvas = $("canvas");
  canvas.replaceChildren();
  canvas.style.width = doc.canvas.width + "px";
  canvas.style.height = doc.canvas.height + "px";
  canvas.style.background = playScreen.background;
  for (const b of playScreen.blocks) {
    const live = b.event && !b.disabled;
    const node = el("div", { className: `block play t-${b.type}${live ? " live" : ""}${b.disabled ? " is-disabled" : ""}`,
                             title: live ? `Click: ${b.event}` : "" });
    applyStyle(node, b.resolved);
    fillContent(node, b, false);
    if (b.disabled) node.style.opacity = "0.45";
    Object.assign(node.style, { left: b.x + "px", top: b.y + "px", width: b.w + "px", height: b.h + "px" });
    if (live) node.onclick = () => playEvent(b.event);
    canvas.append(node);
  }
  const system = $("play-system");
  system.replaceChildren();
  for (const event of playScreen.system_events) {
    const button = el("button", { title: "Something the system does, not the user" }, event);
    button.onclick = () => playEvent(event);
    system.append(button);
  }
  const final = $("play-final");
  final.hidden = !playScreen.final;
  final.textContent = playScreen.final ? `"${playScreen.title}" is a final screen: the flow may end here.` : "";
  $("play-back").disabled = playTrail.length === 0;
  $("play-log").replaceChildren(...playLog.map((line) => el("li", {}, line)));
  renderStates();
  renderSaveLinks();
}

$("btn-play").onclick = () => (playing ? playStop() : playStart());
$("play-back").onclick = () => playBack();
$("play-restart").onclick = () => { $("play-chooser").replaceChildren(); playStart(); };

// ---------- end play mode ----------

load();

// Heartbeat (R12): the server stops itself after 5 minutes with no requests, so while
// this page is open it asks for /api/ping once a minute. A closed tab stops the pings.
const heartbeat = () => api("GET", "/api/ping").catch(() => {
  clearInterval(heartbeatTimer);
  showStatus(["The server has stopped. Start it again with: python -m wireframe start"]);
});
const heartbeatTimer = setInterval(heartbeat, 60000);
