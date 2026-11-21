"""Turn a wireframe into text for other tools.

export_spec()      R2: a Markdown spec sheet for a coding AI ("coder") or an
                   image generator ("image").
authoring_guide()  R3: Markdown that teaches an AI how to write a wireframe
                   JSON of its own, with a worked example.

Both are pure functions: same input, same output text, no side effects.
"""

import json

from .checks import RULES
from .example import example_wireframe
from .model import BLOCK_TYPES, WireframeError

MODES = ("coder", "image")

# What each block type means, for the AI authoring guide.
TYPE_MEANING = {
    "heading": "a title for the screen or a section",
    "text": "a read-only piece of text or a value (for example a total)",
    "button": "something the user presses; should raise an event",
    "input": "a field the user types into",
    "image": "a picture or icon",
    "list": "a repeated set of rows or cards",
    "nav": "a navigation bar or menu",
    "container": "an empty panel that groups other blocks; it conveys nothing itself",
}

# How an image generator should call each type.
_VISUAL_KIND = {
    "heading": "heading text", "text": "text", "button": "button", "input": "text input field",
    "image": "image placeholder", "list": "list", "nav": "navigation bar", "container": "panel",
}


def _sorted_blocks(state):
    return sorted(state["blocks"], key=lambda b: (b["y"], b["x"], b["id"]))


def _cell(text):
    """Make text safe inside one Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


# ---- R2 --------------------------------------------------------------------

def _coder_spec(doc):
    w, h = doc["canvas"]["width"], doc["canvas"]["height"]
    lines = [
        f"# Spec sheet: {doc['name']} (for a coding AI)",
        "",
        f"Each screen is {w} x {h} px. The first screen is `{doc['initial']}`.",
        "Positions are the top-left corner of each block, in pixels.",
        "A block's `event` is what it raises when the user uses it; transitions below say what happens next.",
        "",
    ]
    for s in doc["states"]:
        lines.append(f"## Screen `{s['id']}`: {s['title']}" + (" (final)" if s["final"] else ""))
        lines.append("")
        if not s["blocks"]:
            lines += ["(no blocks)", ""]
            continue
        lines += ["| id | type | x | y | w | h | label | info | event | note |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for b in _sorted_blocks(s):
            lines.append("| " + " | ".join([
                f"`{b['id']}`", b["type"], str(b["x"]), str(b["y"]), str(b["w"]), str(b["h"]),
                _cell(b["label"]), _cell(", ".join(b["info"])), _cell(b["event"]), _cell(b["note"]),
            ]) + " |")
        lines.append("")
    lines += ["## Transitions", ""]
    if not doc["transitions"]:
        lines.append("(none)")
    for t in doc["transitions"]:
        guard = f" if {t['guard']}" if t["guard"].strip() else ""
        lines.append(f"- `{t['source']}` --`{t['event']}`{guard}--> `{t['target']}`")
    return "\n".join(lines) + "\n"


def _place(block, width, height):
    """Rough position word from the block's centre, using a 3x3 grid."""
    cx = (block["x"] + block["w"] / 2) / width
    cy = (block["y"] + block["h"] / 2) / height
    col = "left" if cx < 1 / 3 else "center" if cx < 2 / 3 else "right"
    row = "top" if cy < 1 / 3 else "middle" if cy < 2 / 3 else "bottom"
    if row == "middle" and col == "center":
        return "center"
    return col if row == "middle" else row if col == "center" else f"{row}-{col}"


def _image_spec(doc):
    w, h = doc["canvas"]["width"], doc["canvas"]["height"]
    lines = [
        f"# Image brief: {doc['name']}",
        "",
        f"Draw one wireframe-style UI mockup per screen below, each {w} x {h} px.",
        "Use the exact label text. Sizes are given as a share of the screen.",
        "",
    ]
    for i, s in enumerate(doc["states"], 1):
        lines += [f"## Screen {i}: {s['title']}", ""]
        if not s["blocks"]:
            lines += ["An empty screen.", ""]
            continue
        for b in _sorted_blocks(s):
            label = f' labelled "{b["label"]}"' if b["label"].strip() else ""
            size = f"about {round(100 * b['w'] / w)}% wide and {round(100 * b['h'] / h)}% tall"
            lines.append(f"- {_place(b, w, h)}: {_VISUAL_KIND[b['type']]}{label}, {size}")
        lines.append("")
    return "\n".join(lines)


def export_spec(doc, mode):
    """Markdown spec sheet. mode is 'coder' or 'image'."""
    if mode == "coder":
        return _coder_spec(doc)
    if mode == "image":
        return _image_spec(doc)
    raise WireframeError(f"unknown mode '{mode}'; use one of: {', '.join(MODES)}")


# ---- R3 --------------------------------------------------------------------

def authoring_guide():
    """Markdown an AI can follow to propose a valid wireframe of its own."""
    types = "\n".join(f"- `{t}`: {TYPE_MEANING[t]}" for t in BLOCK_TYPES)
    rules = "\n".join(f"- `{code}` ({sev}): {text}" for code, (sev, text) in RULES.items())
    example = json.dumps(example_wireframe(), indent=2)
    return f"""# How to write a wireframe

A wireframe is one JSON object describing an app as a **state machine**: each
**state** is a screen, drawn as rectangular **blocks**, and **transitions** say
which user action moves the app from one screen to another.

## Format

- `name`: a title.
- `canvas`: `{{"width": W, "height": H}}`, the size of every screen in pixels.
- `initial`: the `id` of the first screen.
- `states`: a list of screens. Each has `id` (unique, short, no spaces), `title`,
  `final` (true if the flow may end here) and `blocks`.
- `blocks`: rectangles on a screen. Each has `id` (unique on that screen), `type`,
  `x`, `y` (top-left corner) and `w`, `h` (size), all whole pixels with `w`, `h`
  above zero. It also has `label` (the text shown), `info`, `note` and `event`.
- `transitions`: a list. Each has `id`, `source` and `target` (state ids), `event`
  and `guard` (a condition in words, or an empty string).

Every field is required. Unknown fields are rejected, so spell them exactly.

## Block types

{types}

## What a block conveys: `info` and `note`

- `info` is a list of short dotted keys naming the *information* a block shows or
  asks for, such as `cart.total` or `user.email`. Use the same key for the same
  information everywhere, and never put one key on two blocks of the same screen:
  that would show the user the same thing twice.
- `note` is one plain sentence about what the block conveys. It may be empty if
  `info` is enough.

## Events and flow

- A block that the user can act on has an `event` (for example `checkout`).
  Leave `event` as an empty string for blocks that are only displayed.
- A transition fires when its `event` happens on its `source` screen. A transition
  must have a block on its source screen that raises that event, unless the event
  starts with `sys:` (for example `sys:timeout`), which means the system raises it.
- Every screen needs a way out unless `final` is true.

## Rules the checker enforces

Errors mean the design contradicts itself. Warnings are probably mistakes.

{rules}

## How to submit

Check your file with `python -m wireframe validate FILE` (the format) and
`python -m wireframe check FILE` (the rules above), or send it with
`PUT /api/wireframe` to a running server. A malformed wireframe is rejected with
a list of errors that each say where the problem is.

## Complete example

```json
{example}
```
"""
