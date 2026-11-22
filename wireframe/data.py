"""Data standins (R11): show sample text where a block says `{{some.key}}`.

A block's text may contain *tokens* such as `{{cart.total}}`. Two modes decide
what a reader sees:

    debug   the text exactly as written          "Total {{cart.total}}"
    live    each token replaced by sample text    "Total $42.00"

The sample text comes from the document's optional `data` table
({"cart.total": "$42.00"}). A key that is not in the table still gets a
readable standin made from its name ("cart.total" -> "Cart total"), so a
wireframe looks complete without the author typing every sample.

Everything here only reads; nothing writes a standin back into the document.
"""

import re

from .model import KEY_PATTERN, WireframeError

MODES = ("debug", "live")

# A token is {{key}} with optional spaces inside the braces. The key format
# itself lives in model.py because validation needs it too.
_TOKEN = re.compile(r"\{\{\s*(" + KEY_PATTERN + r")\s*\}\}")


def check_mode(mode):
    if mode not in MODES:
        raise WireframeError(f"unknown data mode '{mode}'; use one of: {', '.join(MODES)}")


def find_tokens(text):
    """The keys named in `text`, in order (a key used twice is listed twice)."""
    return _TOKEN.findall(text)


def standin(key):
    """Readable stand-in text made from a key: 'user.email_address' -> 'User email address'."""
    words = " ".join(re.split(r"[._\-]+", key)).strip()
    return words[:1].upper() + words[1:]


def fill(doc, text, mode):
    """`text` as it should be displayed in `mode`.

    re.sub scans the original text once, so a sample that itself contains a
    token is inserted as-is and never expanded (no loops)."""
    check_mode(mode)
    if mode == "debug":
        return text
    table = doc.get("data", {})
    return _TOKEN.sub(lambda m: table.get(m.group(1), standin(m.group(1))), text)
