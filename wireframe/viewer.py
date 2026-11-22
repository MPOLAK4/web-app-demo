"""The clickable viewer file (R13): one .html that opens by double-click, no server.

    build_viewer(doc) -> the text of the file

The file cannot run Python, so Python does all the thinking *before* the file is
written. For every screen it stores:

    the picture (render.render_screen, in debug and live data mode),
    the click areas (visible, enabled blocks that raise an event),
    and, for each event, the answer play.step gives.

The page then only *looks things up*: it never decides where an event leads, how
a block looks, or what a block says. That keeps one copy of those rules (ADR 0010).

Safety: the data sits in a JSON block with every `<` escaped, so no wireframe text
can end the block or start a tag. Pictures are shown through <img> with SVG data,
and an image cannot run script. The page also carries a Content-Security-Policy.
"""

import json
import os
from html import escape

from . import data as datamod
from .play import screen, step
from .render import render_screen

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer_template.html")


def _screen_data(doc, state_id):
    scr = screen(doc, state_id)
    events = scr["events"] + scr["system_events"]
    hotspots = [{"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "event": b["event"].strip()}
                for b in scr["blocks"] if b["event"].strip() and not b.get("disabled")]
    return {"title": scr["title"], "final": scr["final"], "events": events, "hotspots": hotspots,
            "steps": {e: step(doc, state_id, e) for e in events},
            "svg": {mode: render_screen(doc, state_id, "svg", mode) for mode in datamod.MODES}}


def build_viewer(doc):
    """The viewer page for `doc`. Reads the document, never changes it."""
    payload = {"name": doc["name"], "initial": doc["initial"], "canvas": doc["canvas"],
               "order": [s["id"] for s in doc["states"]],
               "states": {s["id"]: _screen_data(doc, s["id"]) for s in doc["states"]}}
    # ensure_ascii writes every non-ASCII character as \uXXXX; escaping "<" as well means
    # the text can never contain "</script>" or the start of a tag.
    embedded = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
    with open(TEMPLATE, encoding="utf-8", newline="") as f:
        page = f.read().replace("\r\n", "\n")
    return page.replace("__TITLE__", escape(f'{doc["name"]} (viewer)')).replace("__DATA__", embedded)
