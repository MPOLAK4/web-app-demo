# Handoff: end of Round 3

Read this, then `problem.md`, `spec.md`, `CLAUDE.md` and `docs/decisions/` (0001-0009)
before starting Round 4. Do not commit this file until the user has read it.

**Written after the fact.** No handoff was requested at the end of Round 3, so this one
was reconstructed later from the Round 3 session transcript and the git history, and the
test count below was re-run on the last Round 3 commit. It describes the repo as of
`3b86582`. Round 4 (R12, R13) was built on top of it; see `handoff-round-4.md` for what
changed since.

## Current state

- Round 3 (R10, R11) is implemented and committed on `master`. 360 tests pass
  (`python -m unittest discover -s tests -v`), including every Round 1 and Round 2 test.
  Baseline before the round was 286. Re-checked at `3b86582` in a throwaway worktree.
- Round 3 commits, oldest first:
  - `b204dfc` problem.md update (R10, R11 added)
  - `89e6970` spec for Round 3
  - `74b9362` data standins: `{{key}}` tokens, `data` table, `set_data` / `delete_data` ops
  - `3bb1425` `render_screen` (SVG/HTML) and `play.follow`
  - `1fb167f` spec export honours data mode; guide and example use tokens
  - `860abcd` CLI: `render` command and `export --data`
  - `1dfe444` server: `/api/render`, `/api/lines`, `data` param on play and spec
  - `c6abbdd` editor: debug/live mode, sample-data panel, Save HTML/SVG
  - `3b86582` decision records 0007-0009 and README
- Nothing was pushed. Uncommitted on purpose: `CLAUDE.md` (the user edits it) and
  `handoff-round-2.md` at the time; this file now.
- What exists:
  - R11, data standins: `wireframe/data.py` (`MODES`, `check_mode`, `find_tokens`,
    `standin`, `fill`). A token is `{{key}}`, key format `[A-Za-z_][A-Za-z0-9_.\-]*`.
    Optional document field `data` (key -> sample text). Debug mode shows the text as
    written; live mode replaces each token with `data[key]`, or an automatic standin
    (`cart.total` -> `Cart total`). `re.sub` scans once, so a sample is never
    re-expanded. Validation is in `model.py`; `KEY_PATTERN` and `is_data_key` live there
    to avoid a circular import.
  - R10, picture files: `wireframe/render.py` (`content_lines`, `render_screen(doc,
    state_id, fmt, data="debug")`, `FORMATS = ("svg", "html")`). HTML is the same SVG
    wrapped in a small page. One nested `<svg>` per block for clipping. Output is
    deterministic.
  - `play.follow(doc, tokens)` returns the screen reached after events (`EVENT` or
    `EVENT=ID`, same syntax as `walk`). It errors on a stuck event or an unresolved
    choice, naming the event.
  - CLI: `python -m wireframe render FILE [--state ID | --after EVENT[=ID] ...]
    [--format svg|html] [--data debug|live] [--out PATH]`, and `export --data`.
  - Server: `GET /api/render?state=&after=...&format=&data=&download=1` (repeated
    `after=`), `GET /api/lines?state=&data=`, `data` param on `/api/spec` and
    `/api/play` (400 on a bad value), `lines` on each `/api/play` block.
  - Editor: debug/live select (`#data-mode`), sample-data panel (add/delete through the
    `set_data` / `delete_data` ops), "Save HTML" and "Save SVG" links, block text taken
    from the server. The JavaScript `contentLines` function was deleted.
  - Spec export: the image spec follows the mode; the coder spec stays raw and gains a
    `## Sample data` section when `data` is non-empty. The authoring guide explains
    tokens and data. The example wireframe now has `Total: {{cart.total}}`,
    `Order {{done.order_number}}` and `"data": {"cart.total": "$42.00"}`.

## How to run

- Editor: `python server.py` (edits `wireframe.json`), open http://localhost:8000.
  `python server.py my.json --port 9000` for another file or port.
- Headless: `python -m wireframe new my.json --example`, then `validate`, `check`,
  `export --mode coder|image [--data live]`, `guide`, `op FILE 'JSON'`, `walk`, `render`.
- Picture of a screen, no server needed:
  `python -m wireframe render my.json --state <id> --data live --out screen.svg`.
- Tests: `python -m unittest discover -s tests -v`. One file:
  `discover -s tests -p "test_x.py"` (not `-m unittest tests.test_x`).
- Python 3.12+, standard library only. Node is optional; if installed, a test runs
  `node --check static/app.js`.

## Decisions made this round, and why

Asked for by the user (answers to my questions): HTML + SVG only (no PNG); "state" means
any screen, or the screen after an events list; tokens in labels plus a sample-data
table; the mode applies to renders and Play (and, as I applied it, the image spec).
Decisions I made on my own:

- Default mode is `debug` everywhere, so old callers get old output.
- Automatic standin wording: dots, underscores and dashes become spaces and the first
  letter is capitalised (`cart.total` -> `Cart total`).
- Tokens apply only in `label`, `placeholder`, `value` and `options`.
- Sample values must be text. When `data` becomes empty the field is removed (ADR 0006
  style: new fields only exist when used).
- No new `checks.RULES` codes for data, so an unknown token is not a finding.
- `walk` is unchanged. `render --out` overwrites an existing file.
- `/api/render` sends `Content-Security-Policy: default-src 'none'; style-src
  'unsafe-inline'; img-src data:` and `X-Content-Type-Options: nosniff`. Rendered text is
  escaped and the file has no script.
- Download filename is slugged from the app name and screen, e.g. `My-App-b.html`.
- Files draw disabled blocks at half opacity and skip hidden blocks. `/api/lines` still
  lists hidden blocks because the editor draws them. File order is z-order.
- `/api/lines` replaced the JS `contentLines`, and the editor refetches lines lazily
  (only when the screen or mode changes), so text can be stale for a moment.
- The coder spec stays raw so a coder still sees the key.
- Decision records: 0007 (tokens + data table), 0008 (SVG/HTML from Python, no PNG),
  0009 (server supplies block text lines).

## Unresolved

- **The editor changes were never run in a real browser by me or a test.** Check by
  hand: the debug/live switch changes canvas text; add and delete a sample-data key;
  Save HTML and Save SVG download files that open; Play in live mode shows samples; the
  inspector still shows the raw `{{...}}` text after switching back to debug. Also still
  unverified from Round 2: drag, four-corner resize, shift-click, snap grid, style panel
  and Play. Expect small bugs.
- Carried over from Round 2, still open: some tests cite R9 letters that differ from
  `spec.md`; there is no op to delete a screen `background` (the editor sends `#ffffff`);
  editor drag does not clamp at the right/bottom edge.
- Unknown tokens are silently replaced by an automatic standin. Whether a check should
  warn about them was not decided.
- The user was asked to explain, in their own words, why live mode never saves standins
  back into the file. The session ended before an answer.
- Line endings: git warns "LF will be replaced by CRLF". The CLI writes output with
  `newline="\n"`; keep doing that.

## Warnings for the next session

- **Python heredoc patch scripts mangle escapes.** In this session a patch script written
  inside a Bash heredoc turned `"\n"` in the target code into a real newline, which broke
  `cli.py` and `tests/test_static.py` until I fixed them with Edit. Prefer Write and Edit
  for code; check any scripted patch with `git diff` before running tests.
  (Earlier warning still holds: large Bash heredocs containing quotes fail with
  "unexpected EOF".)
- **Do not subclass an existing `TestCase` just to share setup.** `CliRenderTests` first
  inherited `CliTests` and re-ran every old test against an existing file; it is now a
  standalone class with its own `setUp`.
- Block text rules live only in `render.content_lines`. Do not re-add them in
  `static/app.js`; a test checks `contentLines` is gone.
- New server routes must be added to the `known` list in `server.py` (wrong method gives
  405 instead of 404). `send_bytes` takes `extra_headers`.
- New optional document fields must be tested against an old-shape document (ADR 0006).
- Earlier warnings still hold: test modules import each other as top-level modules and
  `tests/helpers.py` as `helpers`; new `checks.RULES` codes need `SPEC_CODES` in
  `tests/test_spec.py` and the example must stay free of findings; every `$("id")` in
  `app.js` must exist in `index.html`; every `op:` name must be in `ops.OPS`; never use
  `innerHTML`; Play code must not call `send(`; call `drain_body()` before error replies.
- Never push, amend or reset; commit after each feature; check `git status` and
  `git diff --staged` before committing; do not commit `CLAUDE.md` or handoff files
  until the user has read them.
- The session hit a usage limit and was compacted twice. If a long round is planned,
  commit small and early (this round did).
