"""Small builders so tests can write a wireframe in a few readable lines.

Each builder returns plain dicts in exactly the shape described in spec.md.
"""


def block(id="b1", type="text", x=0, y=0, w=100, h=40, label="", info=("k.x",), note="", event=""):
    return {"id": id, "type": type, "x": x, "y": y, "w": w, "h": h,
            "label": label, "info": list(info), "note": note, "event": event}


def state(id, blocks=(), final=False, title=None):
    return {"id": id, "title": title or id.title(), "final": final, "blocks": list(blocks)}


def transition(id, source, target, event, guard=""):
    return {"id": id, "source": source, "target": target, "event": event, "guard": guard}


def doc(states, transitions=(), initial=None, name="Test", width=800, height=600):
    states = list(states)
    if initial is None:
        initial = states[0]["id"] if states else ""
    return {"name": name, "canvas": {"width": width, "height": height},
            "initial": initial, "states": states, "transitions": list(transitions)}


def codes(findings):
    """The set of finding codes in a check() result, for compact assertions."""
    return {f["code"] for f in findings}
