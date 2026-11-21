# Spec: wireframe tool

Status: **Round 1** (all of R1-R5 from `problem.md`).

The requirement IDs below are the ones in `problem.md`. Each one is followed by
acceptance criteria, lettered (a), (b), ... Tests cite the ID and, in their
docstring, the letter, e.g. `R4(c)`.

## How I read the unclear parts of problem.md

These readings were agreed with the author before writing code.

- **R1 "Headless / User interface"** means both. The wireframe is one JSON file.
  A browser editor and a headless interface (Python functions and a command
  line) read and write that same file. Neither is the "real" one.
- **R2 output** is one Markdown spec sheet with two modes: `coder` (for a coding
  AI) and `image` (for an image generator).
- **R3** means: the app gives an AI an authoring guide (the format, the rules, a
  valid example) and a validator that checks an AI-written wireframe and returns
  readable errors. The app does not call any AI service itself.
- **R4 "states/flow"** means a full state machine: named states, events, and
  transitions with optional guards. The checker analyses that machine against
  the blocks drawn in each state.
- **R5 "representation of information"** means both: a list of short info keys
  per block (used for matching) and a free-text note (for humans and AIs).

## Data model

One JSON document (see `wireframe/model.py`):

```
{
  "name": "Checkout",
  "canvas": {"width": 800, "height": 600},
  "initial": "cart",
  "states": [
    {"id": "cart", "title": "Cart", "final": false, "blocks": [
      {"id": "b1", "type": "button", "x": 20, "y": 500, "w": 160, "h": 40,
       "label": "Pay", "info": ["action.pay"], "note": "", "event": "pay"}
    ]}
  ],
  "transitions": [
    {"id": "t1", "source": "cart", "target": "done", "event": "pay", "guard": ""}
  ]
}
```

- A **state** is one screen. `final: true` marks a legitimate end of the flow.
- A **block** is a rectangle on a screen. `type` is one of: `heading`, `text`,
  `button`, `input`, `image`, `list`, `nav`, `container`. `x`, `y`, `w`, `h` are
  whole pixels. `info` is a list of dotted keys such as `cart.total`. `note` is
  free text. `event` is the event the block raises when the user uses it.
- A **transition** moves the app from `source` to `target` when `event` happens,
  optionally only if `guard` (free text, never evaluated) holds.
- An event starting with `sys:` (for example `sys:timeout`) is raised by the
  system, not by any block.

Unknown fields are rejected, so a typo like `lable` is an error, not silently
ignored.

## Requirements

### R1. Edit a wireframe through a UI and headlessly

- (a) A wireframe can be created, loaded from, and saved to a JSON file. Loading
  rejects malformed files with a list of readable errors; saving never writes an
  invalid document.
- (b) Headless editing: Python functions (`wireframe/ops.py`) add, change
  (move, resize, rename, retype, edit info) and delete blocks, states and
  transitions. Each returns a new document and leaves the old one untouched. An
  invalid edit raises an error and changes nothing.
- (c) The same edits are available as one JSON "op" message
  (`{"op": "add_block", ...}`), through the command line
  (`python -m wireframe op FILE '<json>'`) and through the HTTP API.
- (d) Deleting a state also deletes the transitions that start or end there.
- (e) A browser editor (served by `server.py` from `static/`) lets the user pick
  a state, add blocks from a palette, drag to move, drag a corner to resize,
  edit label/type/info/note/event in a side panel, delete blocks, and manage
  states and transitions. Every edit goes through the op API, so the browser
  and the headless interface cannot disagree.
- (f) The server listens on `127.0.0.1` only and serves only files inside
  `static/`.

### R2. Blocks become a spec sheet

- (a) `export_spec(doc, "coder")` returns Markdown listing, per state, every
  block with type, position, size, label, info keys, note and event, plus the
  transitions (source, event, guard, target).
- (b) `export_spec(doc, "image")` returns Markdown describing each screen in
  visual terms only: element kind, label, and rough position (for example
  "top-left"). It contains no event names, guards, or info keys.
- (c) Output is deterministic: same document, same text. Blocks are listed top
  to bottom, then left to right.
- (d) An unknown mode is an error.
- (e) Available as `python -m wireframe export FILE --mode coder|image` and
  `GET /api/spec?mode=`, and from the browser editor.

### R3. An AI can propose its own wireframe

- (a) `authoring_guide()` returns Markdown that states the JSON format, every
  allowed block type, the event conventions, and the rules the checker
  enforces, and includes a complete example.
- (b) The example inside the guide is generated from a real, valid wireframe
  and passes validation with no check errors (so the guide cannot go stale).
- (c) `validate(doc)` returns a list of human-readable errors, each saying where
  the problem is (for example `states[1].blocks[0].w: must be a positive
  integer`). It reports all errors it finds, not just the first.
- (d) An AI-written wireframe can be submitted with `PUT /api/wireframe`; an
  invalid one gets HTTP 400 with the error list and the stored file does not
  change. A valid one replaces the stored file and then shows up in the
  browser editor for the user to inspect.
- (e) Available as `python -m wireframe guide`, `python -m wireframe validate
  FILE`, and `GET /api/guide`.

### R4. Check the state machine against the UI

`check(doc)` returns a list of findings. Each has a `severity` (`error` or
`warning`), a `code`, an optional `state`, the involved block ids, and a
message. Flow findings:

- (a) `no-initial` (error): `initial` is empty or not a state.
- (b) `unknown-state` (error): a transition's source or target is not a state.
- (c) `unreachable-state` (warning): no path from the initial state reaches it.
- (d) `dead-end` (error): a non-final state has no outgoing transition.
- (e) `nondeterministic` (error): two transitions from one state on one event
  have the same guard (including both empty). If only one of them has an empty
  guard the finding is `unguarded-overlap` (warning).
- (f) `dead-control` (error): a block raises an event but no transition from
  that state handles it (the UI promises something the flow does not do).
- (g) `no-trigger` (error): a transition on a non-`sys:` event has no block in
  its source state that raises that event (the flow has a path the user
  cannot take).
- (h) `button-without-event` (warning): a `button` block has no event.
- (i) Layout findings, because overlapping or off-screen blocks conflict with
  the intended UI: `overlap` (warning) for two blocks in one state that
  intersect, except where one is a `container` that fully holds the other;
  `out-of-canvas` (warning) for a block not fully inside the canvas.
- (j) A well-formed wireframe with a sound flow produces no error findings.
- (k) Available as `python -m wireframe check FILE` (exit code 1 if any error)
  and `GET /api/check`. The browser editor shows the findings and refreshes
  them after every edit.

### R5. Blocks carry information so duplicates can be found

- (a) Every block has `info` (list of keys) and `note` (free text); both are
  validated and exported (R2) and visible in the editor.
- (b) `duplicate-info` (warning): two or more blocks in one state share an info
  key. The message names the key and the blocks.
- (c) `duplicate-label` (warning): two or more blocks in one state have the
  same label after lower-casing and collapsing whitespace and punctuation.
  Empty labels are ignored.
- (d) `missing-info` (warning): a block other than a `container` has neither
  info keys nor a note, so a reader cannot tell what it conveys.
- (e) The same info key on blocks in *different* states is not a finding,
  because those screens are not visible together.
- (f) Info-key comparison ignores case and surrounding whitespace.

## Out of scope for this round

- Evaluating guards, simulating user sessions, or checking data values.
- Calling an AI service, image generation, or generating UI code.
- Undo/redo, multi-user editing, authentication (the server is local only).
- Renaming a state's `id` after creation (change its `title` instead).

## Files

| Path | Purpose |
| --- | --- |
| `wireframe/model.py` | data model, `validate`, `load`, `save`, `new_wireframe` |
| `wireframe/ops.py` | headless edit functions and `apply_op` |
| `wireframe/checks.py` | `check` (R4, R5) |
| `wireframe/spec.py` | `export_spec`, `authoring_guide` (R2, R3) |
| `wireframe/example.py` | a valid example wireframe |
| `wireframe/cli.py`, `wireframe/__main__.py` | command line |
| `server.py` | local HTTP server and API |
| `static/` | browser editor (HTML, CSS, JS) |
| `tests/` | `unittest` tests, not part of a release |

Python 3.12+, standard library only. Tests run with
`python -m unittest discover -s tests -v`.
