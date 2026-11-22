# Handoff: end of Round 2

Read this, then `problem.md`, `spec.md`, `CLAUDE.md` and `docs/decisions/` before
starting Round 3. Do not commit this file until the user has read it.

## Current state

- Round 2 (R6-R9) is implemented and committed on `master`. 286 tests pass
  (`python -m unittest discover -s tests -v`), including every Round 1 test.
- Round 2 commits, oldest first: spec, data layer, ops, checks, spec export
  (+ `drain_body` fix), play + `walk`, `/api/play` + `/api/resolved`, editor
  (`c808c18`), decision records 0004-0006 (`8845a4f`). Nothing has been pushed.
- Uncommitted on purpose: `CLAUDE.md` (the user edits it; I appended standing rules
  this session) and this file. `handoff-round-1.md` is also still untracked.
- What exists:
  - R6: coder spec has a resolved-style table (11 fields per block), a per-screen
    background, and a `## Styles` section; the image spec describes styles in visual
    words and lists blocks that must look identical.
  - R7: named styles in the document's `styles`; ops `add_style`, `update_style`,
    `delete_style`, `set_style`; editor style panel and per-block picker.
  - R8: 23 block types, optional props (`style, look, placeholder, options, value,
    disabled, hidden, required`), device presets (phone 390x844, tablet 820x1180,
    desktop 1280x800), screen `background`, ops `duplicate_block`, `reorder_block`,
    `move_blocks`; editor snap grid, four-corner resize, shift-click multi-select.
  - R9: `wireframe/play.py` (`screen`, `step`), `python -m wireframe walk FILE
    [EVENT[=TRANSITION_ID] ...]`, `GET/POST /api/play`, `GET /api/resolved`, and a
    Play button in the editor.

## How to run

- Editor: `python server.py` (edits `wireframe.json`), open http://localhost:8000.
  `python server.py my.json --port 9000` for another file/port.
- Headless: `python -m wireframe new my.json --example`, then `validate`, `check`,
  `export --mode coder|image`, `guide`, `op FILE 'JSON'`, `walk`.
- Tests: `python -m unittest discover -s tests -v`. One file:
  `discover -s tests -p "test_x.py"` (not `-m unittest tests.test_x`).
- Python 3.12+, standard library only. Node is optional; if installed, a test runs
  `node --check static/app.js`.

## Decisions made this round, and why

Asked for by the user: fixed style fields (R6), named styles (R7), all four R8
areas, browser Play plus CLI `walk` (R9). Decisions I made on my own:

- Every Round 2 field is optional (ADR 0006): old files stay valid.
- Named styles + per-block `look` override; resolution is type default, then named
  style, then `look` (ADR 0004).
- Play rules live in Python behind an API; guards are never evaluated, so competing
  guarded transitions return `choose` (ADR 0005).
- Colours are hex only; exactly 11 style fields; a built-in default per block type.
- `missing-style` and `unused-style` are warnings, `unknown-style` an error.
- `delete_style` copies the style's fields into its users' `look` before removing it.
- Holder types (container, card, modal) may contain blocks; hidden blocks are ignored
  by `overlap` and the image brief; `link` needs an event; card/modal/divider/
  container need no info keys.
- Array order is z-order; duplicate offsets by 20 px; snap-to-grid is JS-only rounding.
- `walk` syntax is `EVENT[=ID]`; `/api/resolved` exists so the editor keeps no style
  table of its own; default background `#ffffff`; the example wireframe was restyled.
- Editor edits styles/looks as `name=value, name=value` text; the device dropdown
  always shows "(choose a size)" because the browser does not know preset sizes.

## Unresolved

- **Browser behaviour is unverified by a human or a test.** Drag, four-corner resize,
  shift-click, snap grid, style panel and Play were never run in a real browser.
  First thing to do next session, or ask the user to try them: expect small bugs.
- Some tests cite R9 letters that differ from the lettering in `spec.md` (for example
  "moved" cites R9(b) but spec has it under R9(a)). Reconcile one way or the other.
- Clearing a screen background in the editor sends `#ffffff` rather than removing the
  field (the op requires a valid colour). There is no op to delete `background`.
- Dragging in the editor does not clamp to the canvas on the right/bottom, only at 0.
- Line endings: git warns "LF will be replaced by CRLF". Harmless so far.

## Warnings for the next session

- **Bash heredocs with large content containing quotes fail** ("unexpected EOF") in
  this environment. Use the Write tool for files and Edit for changes.
- **Windows + http.server:** reply to a request only after reading its body
  (`drain_body()`); otherwise server tests flake with WinError 10053. Now in CLAUDE.md.
- Test modules import each other as top-level modules (`from test_play import flow`),
  and `tests/helpers.py` as `helpers`; keep running tests via `discover -s tests`.
- Adding a rule code to `checks.RULES` requires updating `SPEC_CODES` in
  `tests/test_spec.py`, and the example (`wireframe/example.py`) must stay free of
  findings (`check(example) == []`).
- Adding an editor control: every `$("id")` in `app.js` must exist in `index.html`,
  every `op: "name"` must be in `ops.OPS`, and never use `innerHTML`.
- Never push, amend or reset; commit after each feature; check `git status` and
  `git diff --staged` before committing; do not commit `CLAUDE.md` or handoff files
  until the user has read them.
- Standing rules I added to `CLAUDE.md` this session: optional new fields, no
  duplicated style/play rules in JS, `drain_body()`, Play never calls `send(`, and
  try editor changes by hand. The user should review these.
