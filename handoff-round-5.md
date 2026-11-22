# Handoff: end of Round 5

Read this, then `problem.md`, `spec.md`, `CLAUDE.md` and `docs/decisions/` (0001-0013)
before starting Round 6. Do not commit this file or `CLAUDE.md` until the user has read them.

## Current state

- Round 5 (R14, R15) is implemented and committed on `master`. 463 tests pass
  (`python -m unittest discover -s tests -v`, about 35-45 s), including every earlier round.
  Nothing has been pushed.
- Round 5 commits, oldest first: `c39d6cd` spec, `1809577` R15 (guide + exports + tests),
  `44034fe` R14 example library + built `examples/` folder + guide Examples section,
  `f41755d` R14 CLI + server routes + tests, `c539ffb` ADRs 0012 and 0013, `ae0bd58` README.
- Uncommitted on purpose: `CLAUDE.md` (I appended three standing rules, below) and this file.
  `NEXT-SESSION.md` is an old start prompt (excluded by `.git/info/exclude`); it is out of date.
- What exists:
  - R14: `wireframe/examples.py`. `list_examples()` (order: checkout, login, dashboard,
    settings, flawed), `get_example(name)` (fresh copy; unknown name raises `WireframeError`
    listing the names), `example_io(name)` (keys wireframe, coder, image [live mode], check,
    svg {screen id: text}, viewer), `build_files()` / `write_files(folder)`.
    `checkout` is the Round 1 `example_wireframe()`. `flawed` produces 7 finding codes and
    carries `FLAW:` notes naming each. All others have zero findings.
  - Built folder `examples/`: `README.md`, and per example `wireframe.json`, `coder.md`,
    `image-live.md`, `check.txt`, `viewer.html`, `screens/<id>.svg` (40 files).
  - CLI: `python -m wireframe examples [NAME] [--part wireframe|coder|image|check|svg|viewer]
    [--state ID] [--build DIR]`; `new FILE --example [NAME]` (bare `--example` = checkout;
    unknown name exits 1 and writes nothing).
  - Server: `GET /api/examples` and `GET /api/example?name=` (read-only; no lock, never
    touches the server's wireframe file; 400 on missing/unknown name; both in `known`).
  - R15: `spec.DEFAULT_ITERATIONS = 2`; guide section "Iterating on one UI piece"; `## Iterations`
    as the last section of both exports (image brief uses visual words only); guide section
    "Examples".
  - Tests: `tests/test_examples.py`, `tests/test_server_round5.py`, `tests/test_spec_round5.py`.

## How to run

- Prefer no server. Browser editor: `python -m wireframe start`, then `status`, then `stop`.
- Headless: `examples`, `new`, `validate`, `check`, `export`, `guide`, `op`, `walk`, `render`,
  `viewer` (see README "Headless use").
- Tests: `python -m unittest discover -s tests -v`. One file:
  `discover -s tests -p "test_x.py"` (not `-m unittest tests.test_x`).
- Python 3.12+, standard library only.

## Decisions made this round, and why

Asked for by the user (answers to my questions): R14 = a library of examples plus expected I/O
pairs; R15 = guide text only (no new field, no judging whether a pass changed anything, only
record it); count rule = ask the user, else default 2.

My own decisions (the user did not ask for them):

- Examples are built by code, saved in `examples/`, and guarded by a stale test (ADR 0012),
  so expected output cannot drift from the real functions.
- Image I/O is stored in live mode (`image-live.md`) because it reads best as a picture brief.
- Example set: login, dashboard, settings, flawed, plus checkout reused from Round 1.
- `FLAW:` note convention for `flawed`; only `flawed` has such notes (a test checks).
- No editor picker for examples: they are reachable by CLI, API and each `viewer.html`.
- `examples --build DIR` exists so the folder is rebuilt by one command.
- Iteration guidance is also in both exports as `## Iterations` (ADR 0013), not only in the
  guide, because an AI may be handed only a spec sheet.
- "Record" in R15 = the AI writes a `Pass k of N: ...` line in its reply; the app stores nothing.
- Login heading renamed "Welcome" because the checker's `duplicate-label` warning caught
  "Sign in" twice. The settings example writes "Espanol" without an accent (ASCII only).
- Circular import avoided by importing `examples` inside `authoring_guide()`.
- I wrote the README update, including the missing Round 4 items.

## Unresolved

- **Not tried in a real browser.** Unit tests cannot click. Ask the user to open
  `examples/login/viewer.html` (the guarded button should offer two ways forward) and
  `dashboard`, and to run `python -m wireframe start` and `new --example` flows if wanted.
  Round 4's viewer and heartbeat were also never run in a browser.
- Nothing enforces the iteration count; it is guidance only. A later round could add a
  field or command if the user wants enforcement (ADR 0013 lists why not now).
- Carried over from Round 2: some tests cite R9 letters that differ from `spec.md`; no op to
  delete a screen `background`; editor drag does not clamp at the right/bottom edge.
- R12's "AI closes the server when done" is only enforced by the idle timeout and guide text.
- A crash can leave `.wireframe-server.json` behind (gitignored); `status`/`start` clean it up.
- Line endings: git warns "LF will be replaced by CRLF" for new files. Harmless; the stale
  tests compare with LF normalised. Always write built files with `newline="\n"`.

## Warnings for the next session

- **`examples/` and `viewer.html` go stale easily.** Changing a coder/image export, `checks.py`,
  `render.py`, `play.py`, the viewer, `viewer_template.html`, or `examples.py` makes tests fail
  until you run `python -m wireframe examples --build examples` and rebuild `viewer.html`
  (`python -m wireframe new T.json --example`, then `viewer T.json --out viewer.html`).
  Changing the iteration text or `DEFAULT_ITERATIONS` changes every `coder.md`.
- Adding a `checks.RULES` code needs `SPEC_CODES` in `tests/test_spec.py`; the checkout
  example and the four clean examples must stay free of findings.
- A new server route must be in the `known` set in `server.py`; call `drain_body()` before
  error replies to requests with a body.
- `spec.py` must not import `examples` at module level (circular).
- My intermediate commit `44034fe` has tests from `test_examples.py` not yet committed (they
  arrived in `f41755d`), so only the later commits are fully green. Do not bisect across it.
- **Bash heredocs with large quoted content fail** here; use Write/Edit for files.
- The tests dump the entire viewer HTML when an assertion on it fails; pipe test output
  through `tail` and `cut -c1-300`.
- Subprocess tests start real servers; if a run is killed, check `python -m wireframe status`.
- Earlier warnings still hold: test modules import each other as top-level modules and
  `tests/helpers.py` as `helpers`; every `$("id")` in `app.js` must exist in `index.html`;
  every `op:` name must be in `ops.OPS`.
- Never push, amend or reset; commit after each feature; check `git status` and
  `git diff --staged` first.
- Standing rules I added to `CLAUDE.md` (please review): rebuild `examples/` when its inputs
  change and never hand-edit it; `spec.py` imports `examples` only inside `authoring_guide()`;
  the default iteration count lives only in `spec.DEFAULT_ITERATIONS`.
