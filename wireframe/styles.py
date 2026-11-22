"""Style fields, built-in defaults, and resolving a block's final look (R6, R7).

A *style* is a small dict that uses only the fields in STYLE_FIELDS, for example
{"fill": "#2a6cf0", "radius": 8}. Any field may be left out.

A block's final look (its "resolved style") is built in three layers, and a
later layer wins over an earlier one:

    1. the built-in default for the block's type        (default_style)
    2. the named style the block points at (`style`)    (document["styles"])
    3. the block's own overrides (`look`)

So every block always has all eleven fields when we write a spec sheet, even if
the author never chose any of them.
"""

import re

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _is_int(value):
    # bool is a subclass of int in Python (True == 1), so exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


COLOUR_MESSAGE = "must be a colour like #fff or #2a6cf0"

# field name -> (is the value acceptable?, the message when it is not)
STYLE_FIELDS = {
    "fill": (lambda v: isinstance(v, str) and bool(_HEX.match(v)), COLOUR_MESSAGE),
    "text_color": (lambda v: isinstance(v, str) and bool(_HEX.match(v)), COLOUR_MESSAGE),
    "border_color": (lambda v: isinstance(v, str) and bool(_HEX.match(v)), COLOUR_MESSAGE),
    "border_width": (lambda v: _is_int(v) and v >= 0, "must be a whole number, 0 or more"),
    "radius": (lambda v: _is_int(v) and v >= 0, "must be a whole number, 0 or more"),
    "padding": (lambda v: _is_int(v) and v >= 0, "must be a whole number, 0 or more"),
    "font_size": (lambda v: _is_int(v) and v > 0, "must be a whole number above 0"),
    "font_weight": (lambda v: v in ("normal", "bold"), "must be 'normal' or 'bold'"),
    "align": (lambda v: v in ("left", "center", "right"), "must be 'left', 'center' or 'right'"),
    "opacity": (lambda v: _is_number(v) and 0 <= v <= 1, "must be a number from 0 to 1"),
    "shadow": (lambda v: isinstance(v, bool), "must be true or false"),
}


def is_colour(value):
    return isinstance(value, str) and bool(_HEX.match(value))


def validate_style(style, path, errors):
    """Append a readable error for every problem in one style dict."""
    if not isinstance(style, dict):
        errors.append(f"{path}: must be an object")
        return
    for key, value in style.items():
        if key not in STYLE_FIELDS:
            errors.append(f"{path}: unknown field '{key}'")
        elif not STYLE_FIELDS[key][0](value):
            errors.append(f"{path}.{key}: {STYLE_FIELDS[key][1]}")


# ---- defaults ------------------------------------------------------------------

BASE_STYLE = {
    "fill": "#ffffff", "text_color": "#222222", "border_color": "#667788",
    "border_width": 1, "radius": 0, "padding": 4,
    "font_size": 14, "font_weight": "normal", "align": "left",
    "opacity": 1, "shadow": False,
}

# Only what differs from BASE_STYLE, per block type.
_TYPE_DEFAULTS = {
    "heading": {"font_size": 24, "font_weight": "bold", "border_width": 0},
    "text": {"border_width": 0},
    "button": {"fill": "#dfe9ff", "radius": 6, "align": "center", "font_weight": "bold"},
    "input": {"border_color": "#99a0aa"},
    "textarea": {"border_color": "#99a0aa"},
    "select": {"border_color": "#99a0aa", "radius": 4},
    "checkbox": {"border_width": 0},
    "radio": {"border_width": 0},
    "toggle": {"fill": "#dfe9ff", "radius": 16, "border_width": 0},
    "slider": {"border_width": 0, "fill": "#dfe9ff"},
    "image": {"fill": "#eeeeee"},
    "icon": {"border_width": 0, "align": "center", "fill": "#ffffff"},
    "avatar": {"fill": "#eeeeee", "radius": 999, "align": "center"},
    "badge": {"fill": "#ffe9b8", "radius": 10, "font_size": 12, "align": "center", "border_width": 0},
    "list": {"fill": "#fafafa"},
    "table": {"fill": "#fafafa"},
    "nav": {"fill": "#f0f2f7", "font_weight": "bold"},
    "tabs": {"fill": "#f0f2f7", "font_weight": "bold"},
    "container": {"fill": "#f4f6fb", "border_color": "#aab3cc"},
    "card": {"fill": "#ffffff", "radius": 8, "shadow": True, "border_color": "#d8dce6", "padding": 12},
    "modal": {"fill": "#ffffff", "radius": 10, "shadow": True, "border_color": "#aab3cc", "padding": 16},
    "divider": {"fill": "#cccccc", "border_width": 0, "padding": 0},
    "link": {"text_color": "#2a6cf0", "border_width": 0},
}


def default_style(block_type):
    """A fresh, complete style for a block type (a copy: safe to change)."""
    return {**BASE_STYLE, **_TYPE_DEFAULTS.get(block_type, {})}


def resolve_style(doc, block):
    """The complete style for one block: defaults, then named style, then `look`."""
    resolved = default_style(block.get("type"))
    named = doc.get("styles", {}).get(block.get("style") or "")
    if isinstance(named, dict):
        resolved.update(named)
    look = block.get("look")
    if isinstance(look, dict):
        resolved.update(look)
    return resolved
