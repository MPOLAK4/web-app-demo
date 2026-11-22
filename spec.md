# Spec: wireframe tool

Status: **Round 3** (R1-R5 built in Round 1; R6-R9 in Round 2; R10-R11 specified below).

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

## Round 2: styles, more UI options, play mode (R6-R9)

How I read the unclear parts (agreed with the author before writing code):

- **R6** means fixed, validated style fields on every block (not free text).
- **R7** means *named styles*: the wireframe holds a table of named styles, a
  block points at one by name and may override single fields.
- **R8** means all four: more block types, more block properties, screen/canvas
  options, and more editor features.
- **R9** means a Play mode in the browser plus a headless `walk` command.

**Compatibility rule.** Every field added in Round 2 is *optional*. A Round 1
file (no `styles`, no `style`, ...) is still valid and still means what it did.
Missing values fall back to defaults (see R6(b)).

### Data model additions

```
document:  "styles": {"primary": {"fill": "#2a6cf0", "text_color": "#ffffff"}}
state:     "background": "#f4f4f6"
block:     "style": "primary", "look": {"radius": 12},
           "placeholder": "", "options": [], "value": "",
           "disabled": false, "hidden": false, "required": false
```

Style fields (all optional inside a style or a `look`): `fill`, `text_color`,
`border_color` (hex colours `#rgb` or `#rrggbb`), `border_width`, `radius`,
`padding` (whole numbers, 0 or more), `font_size` (whole number above 0),
`font_weight` (`normal` or `bold`), `align` (`left`, `center`, `right`),
`opacity` (number from 0 to 1), `shadow` (true or false).

New block types (added to the Round 1 eight): `textarea`, `checkbox`, `radio`,
`toggle`, `select`, `slider`, `tabs`, `card`, `table`, `modal`, `icon`,
`divider`, `link`, `badge`, `avatar`.

### R6. Detailed specs: a spec sheet's worth of style per block

- (a) A style (the table entries and a block's `look`) may only use the style
  fields above, with the stated value types; `validate` reports each bad value
  with its path, e.g. `states[0].blocks[1].look.opacity: must be a number from 0 to 1`.
- (b) Every block has a *resolved style* with all eleven fields. It is built from
  the built-in defaults for the block's type, then the named style, then the
  block's own `look`, later layers winning. A block with no style fields still
  resolves, so a Round 1 file exports fully.
- (c) `export_spec(doc, "coder")` lists, for every block, the full resolved
  style, its style name (if any) and its properties (placeholder, options,
  value, disabled, hidden, required), and the screen's background.
- (d) `export_spec(doc, "image")` describes every block's resolved style in
  visual words (colours, text size and weight, corner rounding, border,
  shadow, alignment, opacity) and the screen background. Still no event names,
  guards or info keys.
- (e) Both outputs stay deterministic (R2(c)).
- (f) `missing-style` (warning): a block with neither a named style nor a `look`
  has no deliberate design choice.

### R7. Blocks can share a style

- (a) `styles` maps a style name to a style. A block's `style` names one (empty
  or missing means none). `look` overrides single fields for that block only.
- (b) Ops: `add_style`, `update_style` (replaces the style's fields),
  `delete_style`, `set_style` (marks several blocks of one screen at once).
  Changing a style changes every block that uses it. `delete_style` keeps the
  look of its blocks by copying the style's fields into their `look` first.
- (c) `unknown-style` (error): a block names a style that does not exist.
  `unused-style` (warning): a style no block uses.
- (d) The coder spec has a `Styles` section listing each style, its fields and
  the blocks using it, and each block row shows its style name. The image spec
  says which blocks must look identical.
- (e) The editor has a style picker per block and a panel to create, edit and
  delete styles.

### R8. More UI options

- (a) The new block types above are valid, offered in the editor palette, drawn
  by the editor, described in the authoring guide and in the image spec.
- (b) The new block properties are validated, editable through `update_block`,
  shown in the inspector and exported (R6(c)).
- (c) Screens may have a `background` colour (`update_state`). The canvas size
  may be set from a device preset with `update_wireframe(preset=...)`: `phone`
  390x844, `tablet` 820x1180, `desktop` 1280x800. An unknown preset is an error.
- (d) Ops: `duplicate_block` (copy placed 20 px down and right, new id, same
  style), `reorder_block` (`front`, `back`, `forward`, `backward`; the order in
  the file is the stacking order), `move_blocks` (move several by dx, dy).
- (e) Editor: snap-to-grid (grid size field), resize from all four corners,
  shift-click multi-select and drag together, duplicate and z-order buttons.
- (f) Checker changes: `hidden` blocks are ignored by `overlap`; a `card` or
  `modal` may fully hold other blocks like a `container`; `link` must raise an
  event like a `button`; `card`, `modal` and `divider` need no info keys.

### R9. Navigate the wireframe like a real UI (Play mode)

- (a) `play.step(doc, state, event, choice=None)` follows a transition and
  returns `{"status": "moved", "state", "transition"}`.
- (b) If more than one transition leaves the screen on that event, it returns
  `{"status": "choose", "options": [...]}` listing them, unless `choice` names
  one of them (a transition id); a bad `choice` is an error.
- (c) If no transition handles the event, it returns `{"status": "stuck"}`
  with a message; it never raises for a design problem.
- (d) `play.screen(doc, state)` lists the events the user can raise on a screen:
  block events plus `sys:` events (the "system" buttons), and whether it is final.
- (e) `python -m wireframe walk FILE [EVENT[=TRANSITION_ID] ...]` starts at the
  initial screen, applies each event in order, prints each move, and exits 1
  if an event is stuck or needs a choice. With no events it prints the screen
  and its available events.
- (f) `POST /api/play` with `{"state": ..., "event": ...[, "choice": ...]}`
  runs `step` (an empty event just describes the screen); `GET /api/resolved`
  returns every block's resolved style so the browser draws what the exports say.
- (g) Browser: a Play button hides all editing handles and draws blocks with
  their styles; clicking a block that raises an event follows the flow, with
  Back, Restart, a path log, a chooser for ambiguous events, buttons for
  `sys:` events, and a notice on reaching a final screen. Play mode never
  changes the wireframe file.

## Round 3: picture files, data standins (R10, R11)

How I read the unclear parts (agreed with the author before writing code):

- **R10** means **HTML and SVG** files of one screen (no PNG: the project is
  standard-library-only and has no way to draw text into a PNG). "Any state of
  the UI" means any screen, or the screen reached after a list of events (the
  same events `walk` takes).
- **R11** means *tokens plus a sample-data table*: text such as `{{cart.total}}`
  inside a block's text, and an optional `data` table in the document that says
  what to show in its place. A key with no table entry gets a standin made from
  its name.
- **Debug and live.** *debug* shows the text exactly as written (`{{cart.total}}`);
  *live* shows the standins. The mode applies to the R10 files, to the browser
  editor and Play, and to the image spec. The coder spec always keeps the raw tokens.

### Data model additions (all optional, like Round 2)

```
document:  "data": {"cart.total": "$42.00", "user.name": "Sam Rivera"}
block text that may hold {{key}}:  label, placeholder, value, options (each entry)
```

A *key* starts with a letter or `_` and then uses letters, digits, `_`, `.` or `-`
(for example `file.value`). A token is `{{key}}`, spaces inside the braces allowed.

### R10. Output a picture file of any screen

- (a) `render.render_screen(doc, state_id, fmt, data="debug")` returns the file
  text for one screen. `fmt` is `svg` or `html`. An unknown format, screen or
  data mode is an error.
- (b) The file is self-contained: no `<script>`, no external links or images.
  Every piece of user text is escaped, so a label like `<script>` shows as text.
- (c) The file has the canvas size and the screen background, and draws every
  visible block at its x, y, w, h with its resolved style (fill, border,
  radius, text colour, font size and weight, alignment, opacity, shadow).
  Hidden blocks are not drawn; disabled blocks are drawn faded. Blocks are drawn
  in file order, so later blocks are on top.
- (d) What a block says (its label, placeholder, choices, value, with the
  per-type decoration such as `[x]` for a ticked checkbox) comes from
  `render.content_lines`. The browser gets the same lines from `GET /api/lines`
  instead of working them out again.
- (e) Output is deterministic: same document, screen, format and mode, same text.
- (f) `play.follow(doc, tokens)` starts at the initial screen, takes events like
  `walk` (`EVENT` or `EVENT=TRANSITION_ID`) and returns the screen reached. A
  stuck event or an unresolved choice is an error that names the event.
- (g) Command line: `python -m wireframe render FILE [--state ID | --after
  EVENT[=ID] ...] [--format svg|html] [--data debug|live] [--out PATH]`. With no
  `--out` the file text is printed. `--state` and `--after` together, or an
  unknown screen, give exit code 1 and write nothing.
- (h) `GET /api/render?state=ID&after=EVENT...&format=&data=&download=1` returns
  the file (`image/svg+xml` or `text/html`), read-only. It sends a
  `Content-Security-Policy` that forbids scripts. `download=1` adds a
  `Content-Disposition: attachment` filename. Bad input is HTTP 400.
- (i) Browser: "Save HTML" and "Save SVG" links download the screen being shown,
  in the data mode being shown, in the editor and in Play.

### R11. Data standins (live mode and debug mode)

- (a) `data` is validated: an object of key to text, each key in the key format
  above. Errors name the path, for example `data.cart total: ...`. A Round 1 or
  Round 2 file without `data` is still valid.
- (b) `data.find_tokens(text)` lists the keys in a text. A `{{` with no closing
  `}}`, or braces around something that is not a key, is plain text.
- (c) `data.fill(doc, text, mode)`: in `debug` mode the text is returned
  unchanged. In `live` mode each token is replaced by the table's text for its
  key; a key not in the table gets a standin made from the key (`cart.total`
  becomes `Cart total`). Replaced text is never searched for tokens again.
  An unknown mode is an error.
- (d) Ops `set_data` (add or replace one key) and `delete_data` (remove one key;
  an unknown key is an error). The `data` field is removed again when the last
  key is deleted, so an unused file keeps its old shape.
- (e) `render.content_lines` applies the mode to label, placeholder, value and
  options. The image spec honours it (`export_spec(doc, "image", data="live")`,
  `export --data live`, `GET /api/spec?data=live`); the coder spec ignores the
  mode, keeps tokens as written, and gains a `## Sample data` section when `data`
  is not empty.
- (f) `GET /api/play` and `GET /api/lines` take `data=debug|live`. An unknown
  value is HTTP 400.
- (g) Browser: a debug/live choice, and a panel to add, change and delete sample
  data. The canvas and Play show the chosen mode; the inspector always shows the
  raw text so editing never saves a standin.
- (h) The authoring guide explains tokens and `data`, and its example uses them.

## Out of scope for this round

- Evaluating guards, simulating user sessions, or checking data values.
- Calling an AI service, image generation, or generating UI code.
- PNG output, and a file holding every screen at once.
- Standins for anything but a block's visible text (not `note`, not `info`).
- Undo/redo, multi-user editing, authentication (the server is local only).
- Renaming a state's `id` after creation (change its `title` instead).

## Files

| Path | Purpose |
| --- | --- |
| `wireframe/model.py` | data model, `validate`, `load`, `save`, `new_wireframe` |
| `wireframe/ops.py` | headless edit functions and `apply_op` |
| `wireframe/checks.py` | `check` (R4, R5, R6-R8 findings) |
| `wireframe/styles.py` | style fields, defaults, `resolve_style` (R6, R7) |
| `wireframe/play.py` | `screen`, `step` (R9) |
| `wireframe/data.py` | `find_tokens`, `fill`, standins (R11) |
| `wireframe/render.py` | `content_lines`, `render_screen` to SVG or HTML (R10) |
| `wireframe/spec.py` | `export_spec`, `authoring_guide` (R2, R3) |
| `wireframe/example.py` | a valid example wireframe |
| `wireframe/cli.py`, `wireframe/__main__.py` | command line |
| `server.py` | local HTTP server and API |
| `static/` | browser editor (HTML, CSS, JS) |
| `tests/` | `unittest` tests, not part of a release |

Python 3.12+, standard library only. Tests run with
`python -m unittest discover -s tests -v`.
