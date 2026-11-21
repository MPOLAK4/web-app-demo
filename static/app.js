// Wireframe editor (R1(e)). Plain JavaScript, no libraries.
//
// The one rule that keeps this file small: the browser never changes the
// wireframe itself. Every edit is sent to the server as an "op" message
// (POST /api/op); the server applies it with the same Python code the command
// line uses, saves the file, and replies with the new wireframe. We then just
// redraw. So the browser and the headless tools cannot disagree.
//
// We only ever write text with .textContent (never innerHTML), so a label
// like "<script>" is shown as text and cannot run as code.
"use strict";

const BLOCK_TYPES = ["heading", "text", "button", "input", "image", "list", "nav", "container"];

let doc = null;        // the wireframe, exactly as the server last sent it
let current = null;    // id of the state (screen) being shown
let selected = null;   // id of the selected block, or null

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
  adopt(result.data);
  return true;
}

function adopt(newDoc) {
  doc = newDoc;
  if (!doc.states.some((s) => s.id === current)) current = doc.initial || (doc.states[0] || {}).id || null;
  if (!currentBlock()) selected = null;
  render();
  refreshFindings();
}

async function load() {
  const result = await api("GET", "/api/wireframe");
  if (result.ok) adopt(result.data);
  else showStatus(["could not load the wireframe"]);
}

// ---------- small helpers ----------

const currentState = () => (doc && doc.states.find((s) => s.id === current)) || null;
const currentBlock = () => {
  const st = currentState();
  return st ? st.blocks.find((b) => b.id === selected) || null : null;
};

// ---------- drawing ----------

function render() {
  renderHeader();
  renderStates();
  renderPalette();
  renderCanvas();
  renderInspector();
  renderTransitions();
}

function renderHeader() {
  $("doc-name").value = doc.name;
  $("doc-width").value = doc.canvas.width;
  $("doc-height").value = doc.canvas.height;
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
    title.onclick = () => { current = st.id; selected = null; render(); };
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

function renderPalette() {
  const bar = $("palette");
  bar.replaceChildren(el("span", {}, "Add: "));
  for (const type of BLOCK_TYPES) {
    const button = el("button", { disabled: !current }, type);
    button.onclick = async () => {
      const st = currentState();
      const offset = (st.blocks.length % 10) * 12;   // so new blocks do not land exactly on top of each other
      const ok = await send({ op: "add_block", state: current, type, x: 20 + offset, y: 20 + offset, label: type });
      if (ok) { selected = currentState().blocks.at(-1).id; render(); }
    };
    bar.append(button);
  }
}

function renderCanvas() {
  const canvas = $("canvas");
  canvas.replaceChildren();
  canvas.style.width = doc.canvas.width + "px";
  canvas.style.height = doc.canvas.height + "px";
  const st = currentState();
  if (!st) return;
  for (const b of st.blocks) canvas.append(blockNode(b));
}

function blockNode(b) {
  const node = el("div", { className: `block t-${b.type}${b.id === selected ? " selected" : ""}`, title: `${b.type} ${b.id}` },
    [el("span", { className: "kind" }, b.type), b.label]);
  node.dataset.id = b.id;
  Object.assign(node.style, { left: b.x + "px", top: b.y + "px", width: b.w + "px", height: b.h + "px" });
  const handle = el("div", { className: "handle", title: "Drag to resize" });
  node.append(handle);
  node.addEventListener("pointerdown", (event) => beginDrag(event, b, node, "move"));
  handle.addEventListener("pointerdown", (event) => { event.stopPropagation(); beginDrag(event, b, node, "resize"); });
  return node;
}

// Dragging moves the <div> on screen while the mouse is down; only when the
// button is released do we send ONE op with the final numbers.
function beginDrag(event, b, node, mode) {
  event.preventDefault();
  select(b.id);
  node.setPointerCapture(event.pointerId);
  const start = { x: event.clientX, y: event.clientY, bx: b.x, by: b.y, bw: b.w, bh: b.h };
  let result = { x: b.x, y: b.y, w: b.w, h: b.h };
  let moved = false;

  const onMove = (e) => {
    const dx = Math.round(e.clientX - start.x), dy = Math.round(e.clientY - start.y);
    moved = moved || dx !== 0 || dy !== 0;
    if (mode === "move") {
      result = { ...result, x: Math.max(0, start.bx + dx), y: Math.max(0, start.by + dy) };
      Object.assign(node.style, { left: result.x + "px", top: result.y + "px" });
    } else {
      result = { ...result, w: Math.max(10, start.bw + dx), h: Math.max(10, start.bh + dy) };
      Object.assign(node.style, { width: result.w + "px", height: result.h + "px" });
    }
  };
  const onUp = () => {
    node.removeEventListener("pointermove", onMove);
    node.removeEventListener("pointerup", onUp);
    node.removeEventListener("pointercancel", onUp);
    if (!moved) return;
    const fields = mode === "move" ? { x: result.x, y: result.y } : { w: result.w, h: result.h };
    send({ op: "update_block", state: current, id: b.id, ...fields });
  };
  node.addEventListener("pointermove", onMove);
  node.addEventListener("pointerup", onUp);
  node.addEventListener("pointercancel", onUp);
}

// Selecting does not redraw the canvas (that would destroy the block mid-drag);
// it only moves the highlight and refreshes the side panel.
function select(id) {
  selected = id;
  for (const node of document.querySelectorAll(".block")) node.classList.toggle("selected", node.dataset.id === id);
  renderInspector();
}

function renderInspector() {
  const box = $("inspector");
  const b = currentBlock();
  if (!b) {
    box.replaceChildren(el("p", { className: "hint" }, "Click a block to edit it."));
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

  const type = el("select", {}, BLOCK_TYPES.map((t) => el("option", { value: t, selected: t === b.type }, t)));
  type.onchange = () => edit("type", type.value);

  const info = el("input", { value: b.info.join(", "), placeholder: "e.g. cart.total, user.name" });
  info.onchange = () => edit("info", info.value.split(",").map((s) => s.trim()).filter(Boolean));

  const note = el("textarea", { rows: 3, value: b.note });
  note.onchange = () => edit("note", note.value);

  const remove = el("button", {}, "Delete block");
  remove.onclick = () => send({ op: "delete_block", state: current, id: b.id });

  box.replaceChildren(
    el("label", {}, ["Type", type]),
    text("Label (text shown)", "label", b.label),
    el("label", {}, ["Information it shows or collects (comma-separated keys)", info]),
    text("Event (what happens when it is used)", "event", b.event),
    el("label", {}, ["Note for the coder", note]),
    number("x", "x", b.x), number("y", "y", b.y), number("width", "w", b.w), number("height", "h", b.h),
    remove,
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
      if (f.state && doc.states.some((s) => s.id === f.state)) {
        current = f.state;
        selected = (f.blocks || [])[0] || null;
        render();
      }
    };
    list.append(item);
  }
}

// ---------- spec viewer, guide, import ----------

async function showText(title, url) {
  const result = await api("GET", url);
  if (!result.ok) { showStatus([typeof result.data === "string" ? result.data : "could not load"]); return; }
  $("viewer-title").textContent = title;
  $("viewer-text").value = result.data;
  $("viewer").showModal();
}

$("btn-spec-coder").onclick = () => showText("Spec sheet for a coding AI", "/api/spec?mode=coder");
$("btn-spec-image").onclick = () => showText("Spec sheet for an image-generating AI", "/api/spec?mode=image");
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
  current = null; selected = null;
  adopt(result.data);
};

// ---------- header fields ----------

$("doc-name").onchange = () => send({ op: "update_wireframe", name: $("doc-name").value });
$("doc-width").onchange = () => send({ op: "update_wireframe", width: Number($("doc-width").value) });
$("doc-height").onchange = () => send({ op: "update_wireframe", height: Number($("doc-height").value) });

$("add-state-form").onsubmit = async (e) => {
  e.preventDefault();
  const title = $("new-state-title").value;
  if (await send({ op: "add_state", title })) {
    $("new-state-title").value = "";
    current = doc.states.at(-1).id;
    selected = null;
    render();
  }
};

load();
