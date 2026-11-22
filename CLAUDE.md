# CSC299 portfolio: shared instructions

These rules apply to every project in this portfolio: `web-app-demo`,
`webapp-game`, and `cmd-line-ending`. Each project is its own git repo;
this repo only holds the README that links to them.

## Always write unit tests

- Whenever you create or change application code, write unit tests for it in the
  same step. Do not hand over an app without tests.
- Keep all tests in a top-level `tests/` folder, separate from the app code, so
  they are easy to leave out of a release.
- Use the standard test tool for the language (for Python, the standard-library
  `unittest`; run `python -m unittest discover -s tests -v`). Run the
  tests before saying a change is done, and show me the result.
- Explain what each test checks and why, so I can learn to write them myself.

## Tests are for development, not for releases

- Tests stay in git (never put `tests/` in `.gitignore`), but they must not be
  shipped in a release version of the program.
- Keep them out of release builds/packages, for example with
  `tests/ export-ignore` in `.gitattributes` (affects `git archive`) or by
  excluding `tests/` in the packaging config.
- Release code must not import from `tests/` or depend on test-only packages.

## General

- Follow the root `CLAUDE.md` for how to teach, explain, and commit.
- Keep each project small and readable; I should be able to understand all of it.

## What never goes in a repository

From the project spec sheet: "No transcripts (.jsonl files), no API keys or
passwords, no .venv or node_modules folders, and no personal information you
would not put on a public web page. These repositories are public."

- Never create, copy, or commit any of those things, in any project repo.
- Give every project a `.gitignore` that covers `*.jsonl`, `.env` and other secret
  files, `.venv/`, and `node_modules/`.
- Read keys and passwords from environment variables, never from source files.
- Before each commit, check what is staged (`git status`, `git diff --staged`) and
  stop if anything on this list is in it.

## Commits

- Whenever you fix, add, or modify a feature, make a commit right after, with a
  short message saying what changed. Do not batch unrelated changes together.
- Never push. I decide what gets pushed and when. Do not run `git push`, add
  remotes, or create GitHub repos unless I ask.
- Never undo or amend a commit (no `git commit --amend`, `reset`, or rebase that
  rewrites history). Fix a mistake with a new commit.

## Conventions for this project

- Python 3.12+, standard library only. No packages to install, for the app or the
  tests.
- Run the tests with `python -m unittest discover -s tests -v`. Running a module
  by name (`python -m unittest tests.test_x`) fails because the tests import
  `tests/helpers.py` as `helpers`; for one file use
  `discover -s tests -p "test_x.py"`.
- Name each test `test_R<n>_<what>` after the requirement it checks (IDs are in
  `problem.md`), and cite the lettered acceptance criterion from `spec.md` in its
  docstring.
- `spec.md` says what each round builds. Update it, and commit it, before writing
  code for a round.
- Every edit to a wireframe goes through `apply_op` in `wireframe/ops.py` (CLI,
  HTTP API and browser alike). To add an editing feature, add an op and register
  it in `OPS`; do not put editing rules in `static/app.js`. The browser writes text
  with `textContent`, never `innerHTML`.
- New wireframe fields are optional and only written when used, so older files stay
  valid (ADR 0006). Run a test against an old-shape document when you add one.
- How a block looks comes from `styles.resolve_style` (served at `/api/resolved`);
  how Play follows the flow comes from `wireframe/play.py` (served at `/api/play`).
  The browser draws those answers and never re-implements either rule.
- In `server.py`, call `drain_body()` before replying with any error to a request that
  has a body. On Windows, answering without reading the body can reset the connection
  (WinError 10053) and make server tests flaky.
- Play mode code in `static/app.js` (between the `play mode` marker comments) must never
  call `send(`; a test enforces it.
- When a test passes `test_static*` but you changed the editor, still try it by hand in a
  browser: unit tests cannot click or drag.
- A choice with real alternatives gets a Y-statement record in
  `docs/decisions/`, numbered `0001`, `0002`, ... in order.
- Write a handoff file (`handoff-round-<N>.md`) only when I ask for one, and leave
  it uncommitted until I have read it.
- The repo-root `viewer.html` is a built file (`python -m wireframe viewer FILE --out viewer.html`
  from `example_wireframe()`). Rebuild it whenever `render.py`, `play.py`, `viewer.py`,
  `viewer_template.html` or the example wireframe changes; a test fails if it is stale.
- A new route in `server.py` must also be added to the `known` set that produces 405 for the
  wrong method. Any request resets the idle clock, so do not add a route that skips `dispatch`.
- Tests that start a real server (`serverctl`, `server.py` subprocesses) must stop it in
  cleanup, use `--state-file` in a temp dir, and short `--idle-timeout`s. Never leave a server
  running when you finish. When you need one yourself, use `python -m wireframe start` / `stop`,
  not a bare `python server.py &`.
- On Windows, deleting or replacing a file another process may touch can raise
  `PermissionError` for a moment; retry briefly (see `serverctl.remove_state`).
