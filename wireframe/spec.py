"""Turn a wireframe into text for other tools.

export_spec()      R2: a Markdown spec sheet for a coding AI ("coder") or an
                   image generator ("image").
authoring_guide()  R3: Markdown that teaches an AI how to write a wireframe
                   JSON of its own, with a worked example.

Both are pure functions: same input, same output text, no side effects.
"""

import json

from . import data as datamod
from .checks import RULES
from .example import example_wireframe
from .model import BLOCK_TYPES, DEVICE_PRESETS, WireframeError
from .styles import STYLE_FIELDS, resolve_style

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
    "textarea": "a multi-line text field the user types into",
    "checkbox": "a box the user ticks on or off (label says what it means)",
    "radio": "one choice among several; give each choice its own radio block",
    "toggle": "an on/off switch",
    "select": "a dropdown; put the choices in `options`",
    "slider": "a control for picking a value in a range",
    "tabs": "a row of tabs; put the tab names in `options`",
    "card": "a framed panel that groups related blocks; it conveys nothing itself",
    "table": "rows and columns of data",
    "modal": "a dialog panel that sits over the screen; it conveys nothing itself",
    "icon": "a small symbol",
    "divider": "a thin line separating areas; it conveys nothing",
    "link": "text the user presses to go elsewhere; should raise an event",
    "badge": "a small label such as a count or status",
    "avatar": "a round picture of a person or account",
}

# How an image generator should call each type.
_VISUAL_KIND = {
    "heading": "heading text", "text": "text", "button": "button", "input": "text input field",
    "image": "image placeholder", "list": "list", "nav": "navigation bar", "container": "panel",
    "textarea": "multi-line text input", "checkbox": "checkbox", "radio": "radio button",
    "toggle": "on/off switch", "select": "dropdown menu", "slider": "slider", "tabs": "row of tabs",
    "card": "card panel", "table": "table", "modal": "dialog box", "icon": "icon",
    "divider": "thin divider line", "link": "text link", "badge": "small badge", "avatar": "round avatar",
}


def _sorted_blocks(state):
    return sorted(state["blocks"], key=lambda b: (b["y"], b["x"], b["id"]))


def _cell(text):
    """Make text safe inside one Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


# ---- styles in the exports (R6, R7) ----------------------------------------

_STYLE_COLUMNS = list(STYLE_FIELDS)          # fixed order -> deterministic output
DEFAULT_BACKGROUND = "#ffffff"


def _background(state):
    return state.get("background") or DEFAULT_BACKGROUND


def _properties(block):
    """The optional block properties that are set, as short `name=value` words."""
    out = []
    for key in ("placeholder", "value"):
        if block.get(key):
            out.append(f'{key}="{block[key]}"')
    if block.get("options"):
        out.append("options=" + " / ".join(block["options"]))
    for key in ("disabled", "hidden", "required"):
        if block.get(key):
            out.append(key)
    return ", ".join(out)


def _style_users(doc):
    """style name -> list of (state, block), in document order."""
    users = {}
    for s in doc["states"]:
        for b in s["blocks"]:
            if b.get("style"):
                users.setdefault(b["style"], []).append((s, b))
    return users


def _look_words(r):
    """A resolved style in plain visual words, for an image generator."""
    parts = [f"fill {r['fill']}", f"text {r['text_color']} {r['font_size']}px {r['font_weight']}",
             f"{r['align']}-aligned text"]
    parts.append(f"{r['border_width']}px {r['border_color']} border" if r["border_width"] else "no border")
    parts.append(f"corners rounded {r['radius']}px" if r["radius"] else "square corners")
    if r["padding"]:
        parts.append(f"{r['padding']}px inner padding")
    if r["shadow"]:
        parts.append("soft drop shadow")
    if r["opacity"] < 1:
        parts.append(f"{round(r['opacity'] * 100)}% opacity")
    return ", ".join(parts)


# ---- R2 --------------------------------------------------------------------

def _coder_spec(doc):
    w, h = doc["canvas"]["width"], doc["canvas"]["height"]
    lines = [
        f"# Spec sheet: {doc['name']} (for a coding AI)",
        "",
        f"Each screen is {w} x {h} px. The first screen is `{doc['initial']}`.",
        "Positions are the top-left corner of each block, in pixels.",
        "A block's `event` is what it raises when the user uses it; transitions below say what happens next.",
        "Every block also has a resolved style (built-in default for its type, then its named style, "
        "then its own overrides); see the table under each screen and the Styles section.",
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
        lines += [f"Background: `{_background(s)}`", "",
                  "Resolved style and properties of each block:", "",
                  "| id | style | " + " | ".join(_STYLE_COLUMNS) + " | properties |",
                  "| --- | --- | " + " | ".join("---" for _ in _STYLE_COLUMNS) + " | --- |"]
        for b in _sorted_blocks(s):
            r = resolve_style(doc, b)
            cells = [str(r[f]).lower() if isinstance(r[f], bool) else str(r[f]) for f in _STYLE_COLUMNS]
            lines.append("| " + " | ".join([f"`{b['id']}`", _cell(b.get("style") or "-")] + cells
                                           + [_cell(_properties(b) or "-")]) + " |")
        lines.append("")
    lines += ["## Styles", ""]
    named = doc.get("styles", {})
    if not named:
        lines += ["(none)", ""]
    users = _style_users(doc)
    for name in sorted(named):
        fields = ", ".join(f"{k}={named[name][k]}" for k in _STYLE_COLUMNS if k in named[name]) or "(defaults only)"
        used = ", ".join(f"`{s['id']}.{b['id']}`" for s, b in users.get(name, [])) or "(nobody)"
        lines.append(f"- **{name}**: {fields}. Used by: {used}")
    if named:
        lines.append("")
    if doc.get("data"):
        lines += ["## Sample data", "",
                  "Text such as `{{key}}` stands for a value; these are the sample values (live mode):", ""]
        lines += [f"- `{k}`: {_cell(v)}" for k, v in sorted(doc["data"].items())]
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


def _image_spec(doc, mode="debug"):
    def fill(text):
        return datamod.fill(doc, text, mode)

    w, h = doc["canvas"]["width"], doc["canvas"]["height"]
    lines = [
        f"# Image brief: {doc['name']}",
        "",
        f"Draw one wireframe-style UI mockup per screen below, each {w} x {h} px.",
        "Use the exact label text. Sizes are given as a share of the screen.",
        "",
    ]
    for i, s in enumerate(doc["states"], 1):
        lines += [f"## Screen {i}: {s['title']}", "", f"Screen background {_background(s)}.", ""]
        shown = [b for b in _sorted_blocks(s) if not b.get("hidden")]
        if not shown:
            lines += ["An empty screen.", ""]
            continue
        for b in shown:
            label = f' labelled "{fill(b["label"])}"' if b["label"].strip() else ""
            size = f"about {round(100 * b['w'] / w)}% wide and {round(100 * b['h'] / h)}% tall"
            extra = ""
            if b.get("placeholder"):
                extra += f', placeholder text "{fill(b["placeholder"])}"'
            if b.get("options"):
                extra += ", choices: " + ", ".join(fill(o) for o in b["options"])
            if b.get("value"):
                extra += f', showing "{fill(b["value"])}"'
            if b.get("disabled"):
                extra += ", greyed out"
            look = _look_words(resolve_style(doc, b))
            lines.append(f"- {_place(b, w, h)}: {_VISUAL_KIND[b['type']]}{label}, {size}{extra}; {look}")
        lines.append("")
    drawn = {name: [(s, b) for s, b in users if not b.get("hidden")]
             for name, users in _style_users(doc).items()}
    groups = [(n, u) for n, u in sorted(drawn.items()) if len(u) > 1]
    if groups:
        lines += ["## Blocks that must look identical", ""]
        for name, users in groups:
            names = []
            for s, b in users:
                n = doc["states"].index(s) + 1
                what = f'"{fill(b["label"])}" {_VISUAL_KIND[b["type"]]}' if b["label"].strip() else _VISUAL_KIND[b["type"]]
                names.append(f"{what} on screen {n}")
            lines.append("- " + "; ".join(names))
        lines.append("")
    return "\n".join(lines)


def export_spec(doc, mode, data="debug"):
    """Markdown spec sheet. mode is 'coder' or 'image'.

    `data` is the standin mode (R11): the image brief shows sample text when it is
    'live'. The coder spec always keeps tokens as written, because code needs the key."""
    datamod.check_mode(data)
    if mode == "coder":
        return _coder_spec(doc)
    if mode == "image":
        return _image_spec(doc, data)
    raise WireframeError(f"unknown mode '{mode}'; use one of: {', '.join(MODES)}")


# ---- R3 --------------------------------------------------------------------

def authoring_guide():
    """Markdown an AI can follow to propose a valid wireframe of its own."""
    types = "\n".join(f"- `{t}`: {TYPE_MEANING[t]}" for t in BLOCK_TYPES)
    rules = "\n".join(f"- `{code}` ({sev}): {text}" for code, (sev, text) in RULES.items())
    example = json.dumps(example_wireframe(), indent=2)
    sizes = {k: f"{w}x{h}" for k, (w, h) in DEVICE_PRESETS.items()}
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

The fields above are required. Unknown fields are rejected, so spell them exactly.

## Optional design fields

All of these may be left out; leave them out unless you mean them.

- Document: `styles`, an object of style name -> style, for design shared by many blocks.
- Block: `style` (the name of one of `styles`), `look` (a style that overrides single
  fields for this block only), `placeholder`, `value` (text), `options` (a list of
  non-empty strings, for `select`, `tabs`, `radio`), and the true/false flags
  `disabled`, `hidden` and `required`.
- State: `background`, a colour.
- Sample data: text in a block's `label`, `placeholder`, `value` or `options` may hold a
  token such as `{{{{cart.total}}}}`. The document's optional `data` is an object of key ->
  sample text (`{{"cart.total": "$42.00"}}`). In *debug* mode a picture or brief shows the
  token as written; in *live* mode it shows the sample, or a readable standin made from
  the key (`cart.total` becomes "Cart total") when `data` has no entry. A key starts with
  a letter or `_`, then letters, digits, `_`, `.` or `-`.
- A *style* may use only these fields: `fill`, `text_color`, `border_color` (hex colours
  such as `#fff` or `#2a6cf0`), `border_width`, `radius`, `padding` (whole numbers, 0 or
  more), `font_size` (whole number above 0), `font_weight` (`normal` or `bold`), `align`
  (`left`, `center` or `right`), `opacity` (0 to 1) and `shadow` (true or false).
- A block's final look is the default for its type, then its named style, then its `look`.
  Give blocks that should look the same one shared style rather than copying fields.
- Screen sizes: phone {sizes['phone']}, tablet {sizes['tablet']}, desktop {sizes['desktop']}.

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

## Servers: prefer none

Everything above works from the command line with **no server**: `validate`, `check`,
`export`, `render`, `walk`, `op` and `viewer` (a clickable `.html` of the wireframe).
Use those first. Only start the editor server when a person needs the browser editor:

- `python -m wireframe start FILE` runs it in the background and prints its URL.
- `python -m wireframe stop` shuts it down. **Always stop a server you started.**
- `python -m wireframe status` says whether one is running.

A server also stops itself after 5 minutes with no requests, but do not rely on that.

## Complete example

```json
{example}
```
"""
