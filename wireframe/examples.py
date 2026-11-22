"""R14: a small library of example wireframes, and the output the tool gives for each.

An example's *input* is a wireframe. Its *expected I/O* is what the real commands
print for it: the coder spec, the image brief, the check report, a picture of every
screen and a clickable viewer. Those are produced by calling the real functions, never
written by hand, so an example cannot drift from the code (ADR 0012).

    list_examples()      [{name, title, summary}, ...] in a fixed order
    get_example(name)    a fresh copy of the wireframe
    example_io(name)     {wireframe, coder, image, check, svg, viewer}
    build_files()        {relative path: text} for the repository folder `examples/`
    write_files(dir)     write those files

Four examples are clean (the checker finds nothing); `flawed` is wrong on purpose.
"""

import json
import os

from . import checks, render, spec, viewer
from .example import example_wireframe
from .model import WireframeError


def _b(id, type, x, y, w, h, label, info, event="", note="", style="body", **extra):
    block = {"id": id, "type": type, "x": x, "y": y, "w": w, "h": h, "label": label,
             "info": info, "note": note, "event": event, "style": style}
    block.update(extra)
    return block


def _state(id, title, blocks, final=False):
    return {"id": id, "title": title, "final": final, "blocks": blocks}


def _t(id, source, target, event, guard=""):
    return {"id": id, "source": source, "target": target, "event": event, "guard": guard}


# ---- the examples ------------------------------------------------------------

def _login():
    return {
        "name": "Login",
        "canvas": {"width": 390, "height": 844},
        "initial": "login",
        "styles": {
            "heading": {"font_size": 28, "font_weight": "bold", "text_color": "#1a2b4c"},
            "field": {"fill": "#ffffff", "border_color": "#c9ced8", "border_width": 1, "radius": 6},
            "primary": {"fill": "#2a6cf0", "text_color": "#ffffff", "radius": 8, "align": "center"},
            "body": {"text_color": "#333333"},
        },
        "data": {"user.name": "Sam Rivera", "user.email": "sam@example.com",
                 "user.last_visit": "Nov 20"},
        "states": [
            _state("login", "Sign in", [
                _b("title", "heading", 20, 60, 350, 40, "Welcome", ["login.title"], style="heading"),
                _b("email", "input", 20, 140, 350, 44, "Email", ["login.email"], style="field",
                   placeholder="you@example.com"),
                _b("password", "input", 20, 200, 350, 44, "Password", ["login.password"], style="field"),
                _b("remember", "checkbox", 20, 260, 350, 32, "Keep me signed in", ["login.remember"],
                   style="field"),
                _b("submit", "button", 20, 320, 350, 48, "Sign in", ["action.submit"], event="submit",
                   style="primary", note="Two outcomes: see the two guarded transitions"),
            ]),
            _state("failed", "Sign-in failed", [
                _b("title", "heading", 20, 60, 350, 40, "Sign-in failed", ["failed.title"], style="heading"),
                _b("message", "text", 20, 120, 350, 60, "We could not sign {{user.email}} in.",
                   ["failed.message"]),
                _b("retry", "button", 20, 200, 350, 48, "Try again", ["action.retry"], event="retry",
                   style="primary"),
            ]),
            _state("home", "Home", [
                _b("title", "heading", 20, 60, 350, 40, "Welcome back, {{user.name}}", ["home.title"],
                   style="heading"),
                _b("visit", "text", 20, 120, 350, 40, "Last visit: {{user.last_visit}}", ["home.last_visit"]),
            ], final=True),
        ],
        "transitions": [
            _t("t1", "login", "home", "submit", "credentials accepted"),
            _t("t2", "login", "failed", "submit", "credentials rejected"),
            _t("t3", "failed", "login", "retry"),
        ],
    }


def _dashboard():
    return {
        "name": "Dashboard",
        "canvas": {"width": 1280, "height": 800},
        "initial": "overview",
        "styles": {
            "heading": {"font_size": 28, "font_weight": "bold", "text_color": "#1a2b4c"},
            "chrome": {"fill": "#1a2b4c", "text_color": "#ffffff"},
            "card": {"fill": "#f7f8fa", "border_color": "#c9ced8", "border_width": 1, "radius": 10,
                     "shadow": True},
            "primary": {"fill": "#2a6cf0", "text_color": "#ffffff", "radius": 8, "align": "center"},
            "body": {"text_color": "#333333"},
        },
        "data": {"stats.revenue": "$12,400", "stats.orders": "318", "stats.users": "1,092",
                 "report.month_revenue": "$48,900"},
        "states": [
            _state("overview", "Overview", [
                _b("menu", "nav", 0, 0, 200, 800, "Menu", ["nav.main"], style="chrome",
                   options=["Overview", "Orders", "Customers"]),
                _b("title", "heading", 230, 24, 500, 40, "Overview", ["overview.title"], style="heading"),
                _b("revenue", "card", 230, 90, 300, 120, "Revenue {{stats.revenue}}", ["stats.revenue"],
                   style="card"),
                _b("orders", "card", 550, 90, 300, 120, "Orders {{stats.orders}}", ["stats.orders"],
                   style="card"),
                _b("users", "card", 870, 90, 300, 120, "Active users {{stats.users}}", ["stats.users"],
                   style="card"),
                _b("recent", "table", 230, 240, 940, 420, "Recent orders", ["orders.recent"]),
                _b("report", "button", 1000, 700, 170, 48, "View report", ["action.open_report"],
                   event="open_report", style="primary"),
            ]),
            _state("report", "Report", [
                _b("title", "heading", 230, 24, 500, 40, "Monthly report", ["report.title"], style="heading"),
                _b("month", "text", 230, 90, 500, 40, "Revenue this month: {{report.month_revenue}}",
                   ["report.month_revenue"]),
                _b("back", "button", 230, 700, 200, 48, "Back to overview", ["action.back"], event="back",
                   style="primary"),
            ]),
        ],
        "transitions": [
            _t("t1", "overview", "report", "open_report"),
            _t("t2", "report", "overview", "back"),
        ],
    }


def _settings():
    return {
        "name": "Settings",
        "canvas": {"width": 800, "height": 600},
        "initial": "settings",
        "styles": {
            "heading": {"font_size": 28, "font_weight": "bold", "text_color": "#1a2b4c"},
            "field": {"fill": "#ffffff", "border_color": "#c9ced8", "border_width": 1, "radius": 6},
            "primary": {"fill": "#2a6cf0", "text_color": "#ffffff", "radius": 8, "align": "center"},
            "secondary": {"fill": "#ffffff", "text_color": "#2a6cf0", "border_color": "#2a6cf0",
                          "border_width": 1, "radius": 8, "align": "center"},
        },
        "data": {"user.name": "Sam Rivera"},
        "states": [
            _state("settings", "Settings", [
                _b("title", "heading", 20, 20, 400, 40, "Settings", ["settings.title"], style="heading"),
                _b("name", "input", 20, 90, 360, 44, "Display name", ["settings.name"], style="field",
                   value="{{user.name}}"),
                _b("notify", "toggle", 20, 160, 360, 40, "Email notifications", ["settings.notifications"],
                   style="field"),
                _b("language", "select", 20, 220, 360, 44, "Language", ["settings.language"], style="field",
                   options=["English", "Espanol", "Deutsch"]),
                _b("volume", "slider", 20, 290, 360, 40, "Volume", ["settings.volume"], style="field"),
                _b("cancel", "button", 20, 520, 160, 48, "Cancel", ["action.cancel"], event="cancel",
                   style="secondary"),
                _b("save", "button", 600, 520, 180, 48, "Save changes", ["action.save"], event="save",
                   style="primary"),
            ]),
            _state("saved", "Saved", [
                _b("title", "heading", 20, 20, 400, 40, "Settings saved", ["saved.title"], style="heading"),
            ], final=True),
            _state("closed", "Closed", [
                _b("title", "heading", 20, 20, 400, 40, "Closed without saving", ["closed.title"],
                   style="heading"),
            ], final=True),
        ],
        "transitions": [
            _t("t1", "settings", "saved", "save"),
            _t("t2", "settings", "closed", "cancel"),
        ],
    }


def _flawed():
    """Valid JSON, wrong design: each flaw carries a `FLAW:` note naming its finding."""
    return {
        "name": "Inbox (flawed on purpose)",
        "canvas": {"width": 800, "height": 600},
        "initial": "inbox",
        "styles": {
            "heading": {"font_size": 28, "font_weight": "bold", "text_color": "#1a2b4c"},
            "primary": {"fill": "#2a6cf0", "text_color": "#ffffff", "radius": 8, "align": "center"},
            "body": {"text_color": "#333333"},
        },
        "data": {"inbox.unread": "12"},
        "states": [
            _state("inbox", "Inbox", [
                _b("title", "heading", 20, 20, 300, 40, "Inbox", ["inbox.title"], style="heading"),
                _b("unread", "text", 20, 80, 300, 40, "Unread: {{inbox.unread}}", ["inbox.unread"]),
                _b("badge", "badge", 340, 80, 160, 40, "Unread: {{inbox.unread}}", ["inbox.unread"],
                   note="FLAW: shows the unread count a second time (duplicate-info, duplicate-label)"),
                _b("messages", "list", 20, 140, 500, 300, "Messages", ["inbox.messages"]),
                _b("promo", "text", 400, 380, 300, 100, "Upgrade now!", ["inbox.promo"],
                   note="FLAW: sits on top of the message list (overlap)"),
                _b("compose", "button", 20, 500, 160, 48, "Compose", ["action.compose"], event="compose",
                   style="primary",
                   note="FLAW: raises 'compose' but no transition handles it (dead-control)"),
                _b("settings", "button", 200, 500, 160, 48, "Settings", ["action.settings"],
                   style="primary", note="FLAW: a button that raises no event (button-without-event)"),
                _b("archive", "button", 380, 500, 160, 48, "Archive", ["action.archive"],
                   event="open_archive", style="primary"),
            ]),
            _state("archive", "Archive", [
                _b("title", "heading", 20, 20, 300, 40, "Archive", ["archive.title"], style="heading",
                   note="FLAW: this screen has no way out and is not final (dead-end)"),
            ]),
            _state("trash", "Trash", [
                _b("title", "heading", 20, 20, 300, 40, "Trash", ["trash.title"], style="heading",
                   note="FLAW: no transition leads here (unreachable-state)"),
            ], final=True),
        ],
        "transitions": [
            _t("t1", "inbox", "archive", "open_archive"),
        ],
    }


# name -> (title, summary, builder). Order matters: it is the order listed everywhere.
_EXAMPLES = {
    "checkout": ("Checkout (3 screens)",
                 "The worked example from the authoring guide: cart, payment, done.", example_wireframe),
    "login": ("Login (phone)",
              "A sign-in form with inputs and a checkbox; one button leads to two screens (guarded).", _login),
    "dashboard": ("Dashboard (desktop)",
                  "Side navigation, three stat cards and a table, plus a report screen.", _dashboard),
    "settings": ("Settings (form controls)",
                 "A toggle, a dropdown and a slider, with Save and Cancel leading to two end screens.", _settings),
    "flawed": ("Inbox (flawed on purpose)",
               "A valid file with a bad design, so you can see what the checker reports.", _flawed),
}


def list_examples():
    return [{"name": n, "title": t, "summary": s} for n, (t, s, _) in _EXAMPLES.items()]


def get_example(name):
    """A fresh copy: every call builds the wireframe again, so editing it is safe."""
    if name not in _EXAMPLES:
        raise WireframeError(f"unknown example '{name}'; use one of: {', '.join(_EXAMPLES)}")
    return _EXAMPLES[name][2]()


def example_io(name):
    doc = get_example(name)
    return {
        "wireframe": json.dumps(doc, indent=2, ensure_ascii=False) + "\n",   # as model.save writes it
        "coder": spec.export_spec(doc, "coder"),
        "image": spec.export_spec(doc, "image", data="live"),
        "check": checks.format_findings(checks.check(doc)) + "\n",           # as `check` prints it
        "svg": {s["id"]: render.render_screen(doc, s["id"], "svg", "live") for s in doc["states"]},
        "viewer": viewer.build_viewer(doc),
    }


# ---- the repository folder ----------------------------------------------------

_README = """# Examples

Each folder is one example wireframe and the output the tool gives for it, so you can
see the expected input and output side by side. **These files are built by code; do not
edit them.** Rebuild with `python -m wireframe examples --build examples`. A test fails if
they are out of date.

| Example | What it shows |
| --- | --- |
{rows}

## What is in each folder

| File | What it is |
| --- | --- |
| `wireframe.json` | The **input**: the wireframe itself. |
| `coder.md` | `python -m wireframe export wireframe.json --mode coder`: the spec sheet for a coding AI. |
| `image-live.md` | `export --mode image --data live`: the brief for an image generator, with sample text filled in. |
| `check.txt` | `python -m wireframe check wireframe.json`: the problems found (none for the clean examples). |
| `screens/<screen>.svg` | `render --state <screen> --data live`: a picture of each screen. |
| `viewer.html` | `viewer`: double-click it to look at the screens and click through the flow. |

## Using an example

- Look at one: `python -m wireframe examples login --part coder` (parts: wireframe, coder,
  image, check, svg, viewer).
- Start your own file from it: `python -m wireframe new my.json --example login`.
- Over HTTP (with a server running): `GET /api/examples` and `GET /api/example?name=login`.
"""


def build_files():
    """{path relative to examples/ (always with '/'): text}."""
    rows = "\n".join(f"| `{e['name']}` | {e['summary']} |" for e in list_examples())
    files = {"README.md": _README.format(rows=rows)}
    for name in _EXAMPLES:
        io = example_io(name)
        files[f"{name}/wireframe.json"] = io["wireframe"]
        files[f"{name}/coder.md"] = io["coder"]
        files[f"{name}/image-live.md"] = io["image"]
        files[f"{name}/check.txt"] = io["check"]
        files[f"{name}/viewer.html"] = io["viewer"]
        for state_id, svg in io["svg"].items():
            files[f"{name}/screens/{state_id}.svg"] = svg
    return files


def write_files(folder):
    """Write the built files under `folder` (LF line endings), replacing earlier copies."""
    for rel, text in build_files().items():
        path = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
