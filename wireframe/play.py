"""Play mode logic (R9): use a wireframe as if it were a real app.

The wireframe is a state machine, so "playing" it is just two questions:

    screen(doc, state)            what does the user see on this screen?
    step(doc, state, event, ...)  they used something that raises `event`: where next?

Both functions only READ the document. The browser's Play mode and the
`walk` command both call these, so they cannot disagree about the rules.

Guards are conditions written in words ("card is valid"), which a program
cannot evaluate. When several transitions on the same event could apply, step()
answers "choose" and lists them; the person walking decides.
"""

from .model import WireframeError
from .styles import resolve_style


def _state(doc, state_id):
    for s in doc["states"]:
        if s["id"] == state_id:
            return s
    raise WireframeError(f"no state with id '{state_id}'")


def screen(doc, state_id):
    """What a user sees: visible blocks with their resolved style, and what they can do."""
    s = _state(doc, state_id)
    blocks, events = [], []
    for b in s["blocks"]:
        if b.get("hidden"):
            continue
        blocks.append({**b, "resolved": resolve_style(doc, b)})
        event = b["event"].strip()
        if event and not b.get("disabled") and event not in events:
            events.append(event)
    system = []
    for t in doc["transitions"]:
        event = t["event"].strip()
        if t["source"] == state_id and event.startswith("sys:") and event not in system:
            system.append(event)
    return {"state": s["id"], "title": s["title"], "final": s["final"],
            "background": s.get("background") or "#ffffff",
            "blocks": blocks, "events": events, "system_events": system}


def step(doc, state_id, event, choice=None):
    """Raise `event` on a screen. Returns a dict whose `status` is:

    moved  -> `state` is the new screen, `transition` the one taken
    stuck  -> no transition handles the event; `state` is unchanged
    choose -> several could apply; `options` lists them, call again with `choice`
    """
    _state(doc, state_id)
    event = event.strip()
    matches = [t for t in doc["transitions"]
               if t["source"] == state_id and t["event"].strip() == event]
    if choice is not None:
        picked = [t for t in matches if t["id"] == choice]
        if not picked:
            raise WireframeError(f"'{choice}' is not a transition for event '{event}' on '{state_id}'")
        matches = picked
    if not matches:
        return {"status": "stuck", "state": state_id, "event": event}
    if len(matches) > 1:
        return {"status": "choose", "state": state_id, "event": event,
                "options": [{"transition": t["id"], "guard": t["guard"], "target": t["target"]}
                            for t in matches]}
    t = matches[0]
    return {"status": "moved", "state": t["target"], "event": event, "transition": t["id"]}
