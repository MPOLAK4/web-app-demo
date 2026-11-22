"""Design checks on a wireframe: the state machine (R4) and information (R5).

check(doc) returns a list of "findings". A finding is a dict:

    {"severity": "error" | "warning", "code": "dead-end", "state": "cart" or None,
     "blocks": ["b1", ...], "message": "human readable sentence"}

Errors are things that make the design contradict itself (a button that does
nothing, a screen you cannot leave). Warnings are things that are probably
mistakes (two blocks showing the same information).

check() only reads the document; it never changes it.
"""

import re


# Every code check() can emit, with its severity and a one-line rule. The
# authoring guide (spec.py) is generated from this table, and a test makes sure
# check() never emits a code that is missing here.
RULES = {
    "no-initial": ("error", "'initial' must name one of the states."),
    "unknown-state": ("error", "every transition's source and target must be an existing state."),
    "unreachable-state": ("warning", "every state should be reachable from the initial state."),
    "dead-end": ("error", "a state with no outgoing transition must be marked final."),
    "nondeterministic": ("error", "two transitions from one state on one event need different guards."),
    "unguarded-overlap": ("warning", "if two transitions share a source and event, give both a guard."),
    "dead-control": ("error", "a block that raises an event needs a transition from its state for it."),
    "no-trigger": ("error", "a transition's event (unless it starts with 'sys:') must be raised by "
                            "a block in its source state."),
    "button-without-event": ("warning", "a button or link must raise an event."),
    "overlap": ("warning", "visible blocks on one screen must not overlap (a container, card or modal may fully hold others)."),
    "out-of-canvas": ("warning", "blocks must lie fully inside the canvas."),
    "duplicate-info": ("warning", "no two blocks on one screen may carry the same info key."),
    "duplicate-label": ("warning", "no two blocks on one screen may have the same label."),
    "missing-info": ("warning", "every block except container, card, modal and divider needs info keys or a note."),
    "missing-style": ("warning", "every block needs a named style or a look of its own."),
    "unknown-style": ("error", "a block's style must name a style in 'styles'."),
    "unused-style": ("warning", "every named style should be used by at least one block."),
}


def _finding(severity, code, message, state=None, blocks=()):
    return {"severity": severity, "code": code, "state": state,
            "blocks": list(blocks), "message": message}


def has_errors(findings):
    return any(f["severity"] == "error" for f in findings)


def format_findings(findings):
    if not findings:
        return "No problems found."
    lines = []
    for f in findings:
        where = f" [{f['state']}]" if f["state"] else ""
        lines.append(f"{f['severity'].upper():7} {f['code']}{where}: {f['message']}")
    errors = sum(1 for f in findings if f["severity"] == "error")
    lines.append(f"{errors} error(s), {len(findings) - errors} warning(s).")
    return "\n".join(lines)


# ---- R4: flow ------------------------------------------------------------

def _flow_findings(doc):
    out = []
    states = {s["id"]: s for s in doc["states"]}
    transitions = doc["transitions"]

    if doc["initial"] not in states:
        out.append(_finding("error", "no-initial",
                            f"the initial state '{doc['initial']}' is not one of the states"))

    good_transitions = []
    for t in transitions:
        missing = [name for name in (t["source"], t["target"]) if name not in states]
        if missing:
            out.append(_finding(
                "error", "unknown-state",
                f"transition '{t['id']}' ({t['source']} -> {t['target']}) refers to "
                f"unknown state(s): {', '.join(missing)}",
                state=t["source"] if t["source"] in states else None))
        else:
            good_transitions.append(t)

    # Reachability: walk outward from the initial state.
    if doc["initial"] in states:
        reached, todo = {doc["initial"]}, [doc["initial"]]
        while todo:
            here = todo.pop()
            for t in good_transitions:
                if t["source"] == here and t["target"] not in reached:
                    reached.add(t["target"])
                    todo.append(t["target"])
        for s in doc["states"]:
            if s["id"] not in reached:
                out.append(_finding("warning", "unreachable-state",
                                    f"state '{s['id']}' cannot be reached from '{doc['initial']}'",
                                    state=s["id"]))

    for s in doc["states"]:
        leaving = [t for t in transitions if t["source"] == s["id"]]
        if not leaving and not s["final"]:
            out.append(_finding("error", "dead-end",
                                f"state '{s['id']}' has no way out and is not marked final",
                                state=s["id"]))

        # Same event leaving one state more than once.
        by_event = {}
        for t in leaving:
            by_event.setdefault(t["event"].strip(), []).append(t)
        for event, group in by_event.items():
            if len(group) < 2:
                continue
            guards = [t["guard"].strip() for t in group]
            ids = ", ".join(t["id"] for t in group)
            if len(set(guards)) < len(guards):
                out.append(_finding("error", "nondeterministic",
                                    f"event '{event}' leaves '{s['id']}' more than once with the "
                                    f"same guard (transitions {ids}); the app cannot choose",
                                    state=s["id"]))
            elif "" in guards:
                out.append(_finding("warning", "unguarded-overlap",
                                    f"event '{event}' leaves '{s['id']}' with and without a guard "
                                    f"(transitions {ids}); the unguarded one always also applies",
                                    state=s["id"]))

        # UI against flow, in both directions.
        handled = {t["event"].strip() for t in leaving}
        raised = {}
        for b in s["blocks"]:
            event = b["event"].strip()
            if event:
                raised.setdefault(event, []).append(b["id"])
                if event not in handled:
                    out.append(_finding("error", "dead-control",
                                        f"block '{b['id']}' raises '{event}' but no transition "
                                        f"from '{s['id']}' handles it",
                                        state=s["id"], blocks=[b["id"]]))
            elif b["type"] in ("button", "link"):
                out.append(_finding("warning", "button-without-event",
                                    f"{b['type']} '{b['id']}' raises no event, so it can do nothing",
                                    state=s["id"], blocks=[b["id"]]))
        for t in leaving:
            event = t["event"].strip()
            if not event.startswith("sys:") and event not in raised:
                out.append(_finding("error", "no-trigger",
                                    f"transition '{t['id']}' needs event '{event}' but no block in "
                                    f"'{s['id']}' raises it, so the user cannot take it",
                                    state=s["id"]))
    return out


# ---- layout ----------------------------------------------------------------

_HOLDERS = ("container", "card", "modal")
_STRUCTURE = ("container", "card", "modal", "divider")     # need no info keys


def _overlaps(a, b):
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] \
        and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _holds(outer, inner):
    return outer["type"] in _HOLDERS \
        and outer["x"] <= inner["x"] and outer["y"] <= inner["y"] \
        and inner["x"] + inner["w"] <= outer["x"] + outer["w"] \
        and inner["y"] + inner["h"] <= outer["y"] + outer["h"]


def _layout_findings(doc):
    out = []
    width, height = doc["canvas"]["width"], doc["canvas"]["height"]
    for s in doc["states"]:
        blocks = s["blocks"]
        visible = [b for b in blocks if not b.get("hidden")]
        for b in blocks:
            if b["x"] < 0 or b["y"] < 0 or b["x"] + b["w"] > width or b["y"] + b["h"] > height:
                out.append(_finding("warning", "out-of-canvas",
                                    f"block '{b['id']}' is not fully inside the {width}x{height} canvas",
                                    state=s["id"], blocks=[b["id"]]))
        for i, a in enumerate(visible):
            for b in visible[i + 1:]:
                if _overlaps(a, b) and not _holds(a, b) and not _holds(b, a):
                    out.append(_finding("warning", "overlap",
                                        f"blocks '{a['id']}' and '{b['id']}' overlap",
                                        state=s["id"], blocks=[a["id"], b["id"]]))
    return out


# ---- R5: information -------------------------------------------------------

def _normalise_label(text):
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())


def _info_findings(doc):
    out = []
    for s in doc["states"]:
        by_key, by_label = {}, {}
        for b in s["blocks"]:
            for key in {k.strip().casefold() for k in b["info"]}:
                by_key.setdefault(key, []).append(b["id"])
            label = _normalise_label(b["label"])
            if label:
                by_label.setdefault(label, []).append(b["id"])
            if b["type"] not in _STRUCTURE and not b["info"] and not b["note"].strip():
                out.append(_finding("warning", "missing-info",
                                    f"block '{b['id']}' has no info keys and no note, so a reader "
                                    f"cannot tell what it conveys",
                                    state=s["id"], blocks=[b["id"]]))
        for key, ids in by_key.items():
            if len(ids) > 1:
                out.append(_finding("warning", "duplicate-info",
                                    f"information '{key}' is shown by {len(ids)} blocks on this "
                                    f"screen: {', '.join(ids)}", state=s["id"], blocks=ids))
        for label, ids in by_label.items():
            if len(ids) > 1:
                out.append(_finding("warning", "duplicate-label",
                                    f"the label '{label}' appears on {len(ids)} blocks on this "
                                    f"screen: {', '.join(ids)}", state=s["id"], blocks=ids))
    return out


def _style_findings(doc):
    out = []
    named = doc.get("styles", {})
    used = set()
    for s in doc["states"]:
        for b in s["blocks"]:
            name = b.get("style") or ""
            if name:
                used.add(name)
                if name not in named:
                    out.append(_finding("error", "unknown-style",
                                        f"block '{b['id']}' uses style '{name}', which does not exist",
                                        state=s["id"], blocks=[b["id"]]))
            elif not b.get("look"):
                out.append(_finding("warning", "missing-style",
                                    f"block '{b['id']}' has no style and no look, so its design "
                                    f"is only a default", state=s["id"], blocks=[b["id"]]))
    for name in named:
        if name not in used:
            out.append(_finding("warning", "unused-style", f"style '{name}' is used by no block"))
    return out


def check(doc):
    """All findings for a (shape-valid) wireframe, errors first."""
    findings = _flow_findings(doc) + _layout_findings(doc) + _info_findings(doc) \
        + _style_findings(doc)
    return sorted(findings, key=lambda f: (f["severity"] != "error", f["code"], f["state"] or "", f["message"]))
