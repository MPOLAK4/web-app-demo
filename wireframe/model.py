"""The wireframe data model: shape checking, loading and saving.

A wireframe is a plain dict (see spec.md, "Data model"). We keep it as a dict,
not a class, so it is exactly the JSON that is stored, sent over HTTP, and
written by an AI.

validate() checks the SHAPE only: field names, types, unique ids. It does not
judge the design. A transition that points at a missing state is a *design*
problem, reported by checks.check() (R4), so it must still be saveable here.
"""

import json
import os
import tempfile

from . import styles as _styles

BLOCK_TYPES = (
    "heading", "text", "button", "input", "image", "list", "nav", "container",
    # Round 2 (R8)
    "textarea", "checkbox", "radio", "toggle", "select", "slider", "tabs", "card",
    "table", "modal", "icon", "divider", "link", "badge", "avatar",
)

# Canvas sizes (width, height) for update_wireframe(preset=...) (R8(c)).
DEVICE_PRESETS = {"phone": (390, 844), "tablet": (820, 1180), "desktop": (1280, 800)}

# Required fields, then the optional ones added in Round 2. Optional means a
# Round 1 file (without them) is still valid.
_DOC_FIELDS = {"name", "canvas", "initial", "states", "transitions"}
_DOC_OPTIONAL = {"styles"}
_STATE_FIELDS = {"id", "title", "final", "blocks"}
_STATE_OPTIONAL = {"background"}
_BLOCK_FIELDS = {"id", "type", "x", "y", "w", "h", "label", "info", "note", "event"}
_BLOCK_OPTIONAL = {"style", "look", "placeholder", "options", "value", "disabled", "hidden", "required"}
_TRANSITION_FIELDS = {"id", "source", "target", "event", "guard"}


class WireframeError(Exception):
    """Raised when a document or an edit is invalid. `errors` lists every problem."""

    def __init__(self, errors):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def new_wireframe(name="Untitled"):
    """A blank wireframe: one empty starting screen."""
    return {
        "name": name,
        "canvas": {"width": 800, "height": 600},
        "initial": "home",
        "states": [{"id": "home", "title": "Home", "final": False, "blocks": []}],
        "transitions": [],
    }


def _is_int(value):
    # bool is a subclass of int in Python (True == 1), so exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def _check_fields(obj, required, path, errors, optional=()):
    for key in obj:
        if key not in required and key not in optional:
            errors.append(f"{path}: unknown field '{key}'")
    for key in required:
        if key not in obj:
            errors.append(f"{path}: missing field '{key}'")


def _check_str(obj, key, path, errors, nonempty=False):
    value = obj.get(key)
    if key in obj and (not isinstance(value, str) or (nonempty and not value.strip())):
        kind = "a non-empty string" if nonempty else "a string"
        errors.append(f"{path}.{key}: must be {kind}")


def _check_unique_id(obj, seen, path, errors):
    ident = obj.get("id")
    if isinstance(ident, str) and ident.strip():
        if ident in seen:
            errors.append(f"{path}.id: duplicate id '{ident}'")
        seen.add(ident)


def _validate_block(block, path, errors):
    if not isinstance(block, dict):
        errors.append(f"{path}: must be an object")
        return
    _check_fields(block, _BLOCK_FIELDS, path, errors, _BLOCK_OPTIONAL)
    _check_str(block, "id", path, errors, nonempty=True)
    if "type" in block and block["type"] not in BLOCK_TYPES:
        errors.append(f"{path}.type: must be one of {', '.join(BLOCK_TYPES)}")
    for key in ("x", "y"):
        if key in block and not _is_int(block[key]):
            errors.append(f"{path}.{key}: must be an integer")
    for key in ("w", "h"):
        if key in block and not (_is_int(block[key]) and block[key] > 0):
            errors.append(f"{path}.{key}: must be a positive integer")
    for key in ("label", "note", "event"):
        _check_str(block, key, path, errors)
    if "info" in block:
        info = block["info"]
        if not isinstance(info, list) or not all(isinstance(k, str) and k.strip() for k in info):
            errors.append(f"{path}.info: must be a list of non-empty strings")
    # Round 2 optional fields (R6, R7, R8)
    for key in ("style", "placeholder", "value"):
        _check_str(block, key, path, errors)
    if "look" in block:
        _styles.validate_style(block["look"], f"{path}.look", errors)
    if "options" in block:
        options = block["options"]
        if not isinstance(options, list) or not all(isinstance(o, str) and o.strip() for o in options):
            errors.append(f"{path}.options: must be a list of non-empty strings")
    for key in ("disabled", "hidden", "required"):
        if key in block and not isinstance(block[key], bool):
            errors.append(f"{path}.{key}: must be true or false")


def validate(doc):
    """Return a list of readable error strings; an empty list means valid."""
    if not isinstance(doc, dict):
        return ["document: must be a JSON object"]
    errors = []
    _check_fields(doc, _DOC_FIELDS, "document", errors, _DOC_OPTIONAL)
    _check_str(doc, "name", "document", errors)
    _check_str(doc, "initial", "document", errors)

    canvas = doc.get("canvas")
    if "canvas" in doc:
        if not isinstance(canvas, dict) or set(canvas) != {"width", "height"}:
            errors.append("canvas: must be an object with exactly 'width' and 'height'")
        else:
            for key in ("width", "height"):
                if not (_is_int(canvas[key]) and canvas[key] > 0):
                    errors.append(f"canvas.{key}: must be a positive integer")

    if "styles" in doc:
        table = doc["styles"]
        if not isinstance(table, dict):
            errors.append("styles: must be an object of name -> style")
        else:
            for name, style in table.items():
                if not isinstance(name, str) or not name.strip():
                    errors.append("styles: every style name must be a non-empty string")
                else:
                    _styles.validate_style(style, f"styles.{name}", errors)

    states = doc.get("states")
    if "states" in doc:
        if not isinstance(states, list):
            errors.append("states: must be a list")
        else:
            seen_states = set()
            for i, st in enumerate(states):
                path = f"states[{i}]"
                if not isinstance(st, dict):
                    errors.append(f"{path}: must be an object")
                    continue
                _check_fields(st, _STATE_FIELDS, path, errors, _STATE_OPTIONAL)
                if "background" in st and not _styles.is_colour(st["background"]):
                    errors.append(f"{path}.background: {_styles.COLOUR_MESSAGE}")
                _check_str(st, "id", path, errors, nonempty=True)
                _check_str(st, "title", path, errors)
                _check_unique_id(st, seen_states, path, errors)
                if "final" in st and not isinstance(st["final"], bool):
                    errors.append(f"{path}.final: must be true or false")
                blocks = st.get("blocks")
                if "blocks" in st:
                    if not isinstance(blocks, list):
                        errors.append(f"{path}.blocks: must be a list")
                    else:
                        seen_blocks = set()
                        for j, blk in enumerate(blocks):
                            _validate_block(blk, f"{path}.blocks[{j}]", errors)
                            if isinstance(blk, dict):
                                _check_unique_id(blk, seen_blocks, f"{path}.blocks[{j}]", errors)

    transitions = doc.get("transitions")
    if "transitions" in doc:
        if not isinstance(transitions, list):
            errors.append("transitions: must be a list")
        else:
            seen_ids = set()
            for i, tr in enumerate(transitions):
                path = f"transitions[{i}]"
                if not isinstance(tr, dict):
                    errors.append(f"{path}: must be an object")
                    continue
                _check_fields(tr, _TRANSITION_FIELDS, path, errors)
                for key in ("id", "source", "target", "event"):
                    _check_str(tr, key, path, errors, nonempty=True)
                _check_str(tr, "guard", path, errors)
                _check_unique_id(tr, seen_ids, path, errors)
    return errors


def require_valid(doc):
    """Raise WireframeError if the document has any shape errors."""
    errors = validate(doc)
    if errors:
        raise WireframeError(errors)


def load(path):
    """Read and validate a wireframe file."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as exc:
        raise WireframeError(f"{path}: not valid JSON ({exc})") from exc
    except OSError as exc:
        raise WireframeError(f"{path}: cannot read ({exc.strerror})") from exc
    require_valid(doc)
    return doc


def save(doc, path):
    """Validate, then write atomically (temp file + rename), so a crash or a
    refused save can never leave a half-written or invalid file behind."""
    require_valid(doc)
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def load_or_create(path):
    """Load the file, or create a blank wireframe there if it does not exist."""
    if not os.path.exists(path):
        save(new_wireframe(), path)
    return load(path)
