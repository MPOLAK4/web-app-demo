# Handoff: end of Round 4

Read this, then `problem.md`, `spec.md`, `CLAUDE.md` and `docs/decisions/` (0001-0011)
before starting Round 5. Do not commit this file until the user has read it.

## Current state

- Round 4 (R12, R13) is implemented and committed on `master`. 409 tests pass
  (`python -m unittest discover -s tests -v`, about 21 s), including every earlier
  round. The suite was run three times in a row after the last fix and passed each time.
- Round 4 commits, oldest first: `7d88429` spec + problem, `303bec2` viewer (R13) +
  ADR 0010, `0f5f6a2` server lifetime and wiring (R12) + tests + ADR 0011, `8d9551b`
  Windows retry fix. Nothing has been pushed.
- Uncommitted on purpose: `CLAUDE.md` (the user edits it; I appended four standing rules
  this session, listed below) and this file.
- What exists:
  - R12: `server.make_server(..., idle_timeout=300)`; `dispatch` updates
    `httpd.last_request` on every request (even 404/405); `server.run(httpd)` starts a
    watcher thread that calls `httpd.shutdown()` after the idle timeout and closes the
    socket. Routes: `GET /api/ping`, `POST /api/shutdown` (JSON-only, local-Host-only).
    `server.py` flags: `--port` (0 = any free port), `--idle-timeout`, `--state-file`.
  - `wireframe/serverctl.py`: state file `.wireframe-server.json` (`pid, port, url, file`),
    written atomically by the server once listening and removed on exit. `start`, `stop`,
    `status`. `stop` asks the server to quit over HTTP; it never kills by pid.
  - CLI: `python -m wireframe start [FILE] [--port] [--idle-timeout] [--state-file]`,
    `stop`, `status`, and `viewer FILE [--out FILE]`.
  - Editor: sends `GET /api/ping` every 60 s (stops and shows a message if it fails);
    "Save viewer" link to `/api/viewer?download=1`.
  - R13: `wireframe/viewer.py` (`build_viewer(doc)`) + `wireframe/viewer_template.html`.
    Python precomputes per-screen SVG (both data modes), hotspots and every `play.step`
    answer; the page only looks them up. Root `viewer.html` is a built example.
  - Authoring guide (`wireframe/spec.py`) has a "Servers: prefer none" section.

## How to run

- Prefer no server. To edit in the browser: `python -m wireframe start` (prints the URL,
  runs in the background, edits `wireframe.json`), then `status`, then `stop` when done.
  Foreground still works: `python server.py [file] [--port N]`.
- Headless: `python -m wireframe new my.json --example`, then `validate`, `check`,
  `export --mode coder|image`, `guide`, `op FILE 'JSON'`, `walk`, `render`, `viewer`.
- Viewer: `python -m wireframe viewer my.json --out my-viewer.html`, then double-click it.
- Tests: `python -m unittest discover -s tests -v`. One file:
  `discover -s tests -p "test_x.py"` (not `-m unittest tests.test_x`).
- Python 3.12+, standard library only. Node is optional; if installed, tests run
  `node --check` on `static/app.js` and on the viewer's script.

## Decisions made this round, and why

Asked for by the user (answers to my questions): R13 = limited viewer only (view screens,
Play, Save SVG, no editing); any API request counts as a ping; start/stop as CLI commands.
Decisions I made on my own:

- Viewer is built by Python and only looks things up (ADR 0010), so it cannot disagree with
  the editor. Cost: it is a snapshot; rebuild after editing.
- Server lifetime = idle watcher + state file + HTTP shutdown (ADR 0011). `stop` never
  kills by pid because a stale pid could belong to another program.
- Viewer safety: Content-Security-Policy meta tag; data embedded with `ensure_ascii` and
  `<` escaped as `<`; pictures via `<img src="data:image/svg+xml...">`; no
  `innerHTML`, `fetch` or `eval` (a test checks).
- `start` defaults to any free port; `--idle-timeout` must be a positive number.
- Heartbeat is 60 s; `status` deletes a stale state file; `/api/viewer` and `/api/ping`
  added; `POST /api/shutdown` follows the same JSON-only/local-only rules as writes.
- Windows background start uses `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`; POSIX uses
  `start_new_session`.
- `remove_state` retries up to 20 times, 50 ms apart, on `PermissionError`.
- I skipped re-fetching the course instructions because the user said to use only the repo.
- Committed in two feature commits instead of three: `server.py` and `cli.py` mix R12 and
  R13, so splitting would have left an intermediate commit that fails its own tests.

## Unresolved

- **The viewer and the heartbeat were never run in a real browser by me or a test.** Unit
  tests check structure and `node --check`, not clicking. Ask the user to double-click
  `viewer.html` (hotspots, Back, Restart, data switch, Save SVG) and to open the editor
  and watch for the "Save viewer" download. Expect small bugs.
- `README.md` does not mention `start/stop/status/viewer`, `viewer.html` or the idle
  timeout. Update it (and commit) early in the next round.
- Carried over from Round 2, still open: some tests cite R9 letters that differ from
  `spec.md`; no op to delete a screen `background`; editor drag does not clamp at the
  right/bottom edge.
- R12 says the AI should close the server "when it's done using it". Nothing enforces that
  beyond the 5-minute idle timeout and the guide text. The guide is the only mechanism.
- A crash can leave `.wireframe-server.json` behind (it is gitignored); `status` and
  `start` clean it up.
- Line endings: git warns "LF will be replaced by CRLF". Harmless so far, but
  `viewer.html` is compared with LF normalised in its test; always write it with
  `newline="\n"` (the CLI's `--out` does).

## Warnings for the next session

- **Bash heredocs with large content containing quotes fail** ("unexpected EOF") in this
  environment. Use Write for files and Edit for changes. Small Python heredocs that use
  `<<'EOF'` worked this session.
- **Changing `render.py`, `play.py`, the example wireframe or the viewer template makes
  `test_R13_viewer_html_in_the_repository_is_up_to_date` fail** until `viewer.html` is
  rebuilt: `python -m wireframe new T.json --example`, then
  `python -m wireframe viewer T.json --out viewer.html`.
- A new server route must be added to the `known` set in `server.py`, or the wrong method
  returns 404 instead of 405.
- Subprocess tests in `tests/test_serverctl.py` start real servers. They clean up, but if
  a run is killed, check `python -m wireframe status` and stop strays.
- Earlier warnings still hold: test modules import each other as top-level modules and
  `tests/helpers.py` as `helpers`; new `checks.RULES` codes need `SPEC_CODES` in
  `tests/test_spec.py` and the example must stay free of findings; every `$("id")` in
  `app.js` must exist in `index.html`; every `op:` name must be in `ops.OPS`.
- Never push, amend or reset; commit after each feature; check `git status` and
  `git diff --staged` before committing; do not commit `CLAUDE.md` or handoff files
  until the user has read them.
- Standing rules I added to `CLAUDE.md` this session (the user should review them):
  rebuild `viewer.html` when its inputs change; register new routes in `known` and keep
  `dispatch` as the single entry; tests that start servers must stop them; retry file
  deletes on Windows `PermissionError`.
