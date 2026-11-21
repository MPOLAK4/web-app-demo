"""Headless editing (R1): small functions that change a wireframe.

Rules every function follows:
  * It never changes the document you pass in. It works on a deep copy and
    returns the new document, so a failed edit leaves nothing half-done.
  * It validates the result. A bad edit raises WireframeError.
  * It does NOT check design rules (that is checks.py). You can create a
    transition to a missing state here, so the R4 checker has something to find.

The browser editor, the command line and the HTTP API all go through
apply_op(), so they cannot disagree about what an edit means.
"""

import copy
import inspect

from .model import WireframeError, require_valid

_BLOCK_EDITABLE = {"type", "x", "y", "w", "h", "label", "info", "note", "event"}
_STATE_EDITABLE = {"title", "final"}
_TRANSITION_EDITABLE = {"source", "target", "event", "guard"}


def _finish(doc):
    require_valid(doc)
    return doc


def _find(items, ident, what):
    for item in items:
        if item["id"] == ident:
            return item
    raise WireframeError(f"no {what} with id '{ident}'")


def _state(doc, state_id):
    return _find(doc["states"], state_id, "state")


def _fresh_id(prefix, taken):
    n = 1
    while f"{prefix}{n}" in taken:
        n += 1
    return f"{prefix}{n}"


def _apply_fields(target, fields, editable, what):
    for key, value in fields.items():
        if key not in editable:
            raise WireframeError(f"cannot change {what} field '{key}'")
        target[key] = value


# ---- wireframe ---------------------------------------------------------

def update_wireframe(doc, name=None, initial=None, width=None, height=None):
    new = copy.deepcopy(doc)
    if name is not None:
        new["name"] = name
    if initial is not None:
        new["initial"] = initial
    if width is not None:
        new["canvas"]["width"] = width
    if height is not None:
        new["canvas"]["height"] = height
    return _finish(new)


# ---- states ------------------------------------------------------------

def add_state(doc, title, id=None, final=False):
    new = copy.deepcopy(doc)
    if id is None:
        id = _fresh_id("s", {s["id"] for s in new["states"]})
    new["states"].append({"id": id, "title": title, "final": final, "blocks": []})
    return _finish(new)


def update_state(doc, id, **fields):
    new = copy.deepcopy(doc)
    _apply_fields(_state(new, id), fields, _STATE_EDITABLE, "state")
    return _finish(new)


def delete_state(doc, id):
    """Also removes transitions into or out of the state (R1(d))."""
    new = copy.deepcopy(doc)
    _state(new, id)
    new["states"] = [s for s in new["states"] if s["id"] != id]
    new["transitions"] = [t for t in new["transitions"] if id not in (t["source"], t["target"])]
    if new["initial"] == id:
        new["initial"] = new["states"][0]["id"] if new["states"] else ""
    return _finish(new)


# ---- blocks ------------------------------------------------------------

def add_block(doc, state, type, x=20, y=20, w=160, h=40, label="", info=None, note="", event="", id=None):
    new = copy.deepcopy(doc)
    st = _state(new, state)
    if id is None:
        id = _fresh_id("b", {b["id"] for b in st["blocks"]})
    st["blocks"].append({"id": id, "type": type, "x": x, "y": y, "w": w, "h": h,
                         "label": label, "info": list(info or []), "note": note, "event": event})
    return _finish(new)


def update_block(doc, state, id, **fields):
    """Move (x, y), resize (w, h), rename (label), retype, or edit info/note/event."""
    new = copy.deepcopy(doc)
    _apply_fields(_find(_state(new, state)["blocks"], id, "block"), fields, _BLOCK_EDITABLE, "block")
    return _finish(new)


def delete_block(doc, state, id):
    new = copy.deepcopy(doc)
    st = _state(new, state)
    _find(st["blocks"], id, "block")
    st["blocks"] = [b for b in st["blocks"] if b["id"] != id]
    return _finish(new)


# ---- transitions -------------------------------------------------------

def add_transition(doc, source, target, event, guard="", id=None):
    new = copy.deepcopy(doc)
    if id is None:
        id = _fresh_id("t", {t["id"] for t in new["transitions"]})
    new["transitions"].append({"id": id, "source": source, "target": target,
                               "event": event, "guard": guard})
    return _finish(new)


def update_transition(doc, id, **fields):
    new = copy.deepcopy(doc)
    _apply_fields(_find(new["transitions"], id, "transition"), fields, _TRANSITION_EDITABLE, "transition")
    return _finish(new)


def delete_transition(doc, id):
    new = copy.deepcopy(doc)
    _find(new["transitions"], id, "transition")
    new["transitions"] = [t for t in new["transitions"] if t["id"] != id]
    return _finish(new)


# ---- one entry point for CLI, HTTP and the browser ----------------------

OPS = {fn.__name__: fn for fn in (
    update_wireframe, add_state, update_state, delete_state,
    add_block, update_block, delete_block,
    add_transition, update_transition, delete_transition,
)}


def apply_op(doc, op):
    """Run one edit described as a dict, e.g.
    {"op": "update_block", "state": "cart", "id": "b1", "x": 40}."""
    if not isinstance(op, dict) or "op" not in op:
        raise WireframeError("an op must be an object with an 'op' field")
    args = {k: v for k, v in op.items() if k != "op"}
    fn = OPS.get(op["op"])
    if fn is None:
        raise WireframeError(f"unknown op '{op['op']}'; known ops: {', '.join(sorted(OPS))}")
    try:
        inspect.signature(fn).bind(doc, **args)
    except TypeError as exc:
        raise WireframeError(f"op '{op['op']}': {exc}") from exc
    return fn(doc, **args)
