# web-app-demo

A wireframe tool. You sketch screens and the flow between them in the browser (or
write the same wireframe headlessly, or have an AI write it), check the design for
problems, and export a spec sheet for a coding AI or an image-generating AI. The
problem it solves is in [problem.md](problem.md); what Round 1 builds and how it is
judged is in [spec.md](spec.md).

## How to run

Needs Python 3.12 or newer. No libraries to install.

    python server.py                 # edits wireframe.json, created if missing
    python server.py my.json --port 9000

Then open http://localhost:8000 in a browser. The server only listens on your own
machine (127.0.0.1). Stop it with Ctrl+C.

In the editor: click a screen on the left, add blocks from the palette, drag a block
to move it, drag its blue corner to resize it, and edit its details on the right. The
Problems panel updates after every edit. "Spec for coder" and "Spec for image AI" show
the exports; "AI guide" shows what to give an AI so it can write a wireframe, and
"Import JSON" checks and loads what the AI wrote.

Round 2 adds: named styles (panel under the screen list; "Use" gives a style to the
selected blocks), 23 block types and extra block fields in the inspector, a device
size and a background colour per screen, a snap grid, resizing from all four
corners, shift-click to select several blocks, Duplicate and stacking buttons, and
a **Play** button that lets you click through the flow (Back, Restart, path log;
it never changes the file).

## Headless use (no browser)

    python -m wireframe new my.json --example     # a 3-screen checkout example
    python -m wireframe validate my.json          # is the file well formed?
    python -m wireframe check my.json             # flow and duplicate-info problems
    python -m wireframe export my.json --mode coder    # or --mode image
    python -m wireframe guide                     # guide for an AI author
    python -m wireframe op my.json '{"op": "add_state", "title": "Receipt"}'

    python -m wireframe walk my.json go back      # follow events like a user; EVENT=ID picks a guarded option

The browser and these commands edit the same JSON file with the same code
([decision 0001](docs/decisions/0001-one-apply-op-for-every-edit.md)).

## How to run the tests

    python -m unittest discover -s tests -v

The tests cover the data model, the edit operations, the checks, the exports, the
command line, the HTTP server and the static editor files. Dragging and resizing in
the browser cannot be unit-tested this way; try them by hand.

## Project index

| Card | What it is |
| --- | --- |
| `problem.md` | The problem and the numbered requirements (R1, R2, ...). Written by me. |
| `spec.md` | What Round 1 builds: the agreed meaning of each requirement and lettered acceptance criteria that tests cite. |
| `README.md` | This file: how to run, how to test, and this index. |
| `CLAUDE.md` | Instructions the coding assistant follows in this project. |
| `.gitignore` | Files git must never track (transcripts, secrets, virtual environments, `wireframe.json`). |
| `.gitattributes` | Keeps `tests/` out of release archives (`git archive`). |
| `server.py` | The small local Python server (standard library only): JSON API plus the static files. |
| `static/` | The browser editor: `index.html`, `style.css`, `app.js`. |
| `wireframe/` | The Python package: `model.py` (data and validation), `ops.py` (edits), `checks.py` (R4/R5 checks), `spec.py` (exports and AI guide), `cli.py` (command line), `example.py`. |
| `docs/decisions/` | Decision records, one per choice that had real alternatives. |
| `tests/` | Unit tests; they name the requirement IDs they check. Not part of a release. |
