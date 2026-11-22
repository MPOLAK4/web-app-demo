# Handoff: end of Round 1 (for the session that does Round 2)

Written 2026-11-21. Repo state: branch `master`, last commit `851118f`, working
tree clean (apart from the git-excluded `NEXT-SESSION.md`, see warning 2).
159 tests, all passing.

This file is a briefing, not a spec. The rules every session follows are in
`CLAUDE.md`; what each requirement means is in `spec.md`; the reasons behind big
choices are in `docs/decisions/`. Read those three, then this.

## 0. Read these warnings first

1. **Deadline.** `NEXT-SESSION.md` says the final project is due
   **Sun Nov 22, 2026, 11:59 PM**. Round 1 was written on Nov 21, so time may be
   short. Ask the user how much time is left before planning anything big.
2. **`NEXT-SESSION.md` is stale. Do not follow it.** It is a start prompt written
   before any code existed. It says "only the scaffold exists", plans R1, R2 and
   R5 only (R3, R4 as stretch), says `CLAUDE.md` mentions `pytest`, and asks you to
   edit `problem.md`. All of that is out of date: R1 to R5 are built, the test tool
   is `unittest`, and `problem.md` was deliberately not edited (see section 5). It is
   listed in `.git/info/exclude`, so it never shows in `git status`.
3. **Round 2's requirements are not in the repo.** `problem.md` has R1 to R5 and
   all five are implemented. Wait for the user's Round 2 prompt; do not invent
   scope.
4. **Run tests with `discover`, never by module name.**
   `python -m unittest tests.test_server` fails with
   `ModuleNotFoundError: No module named 'helpers'`. The tests import
   `from helpers import ...`, which only works when `discover -s tests` puts
   `tests/` on the path. For one file use
   `python -m unittest discover -s tests -p "test_server.py"`.
5. **Git: never undo or amend a commit; never push.** The user has said so in
   every round prompt. Fix a mistake with a new commit.
6. **This repo is public.** No `.jsonl`, keys, passwords, `.venv`, `node_modules`
   or personal details in any file, including this one. This repo sits inside a
   bigger course repo; run git from inside `web-app-demo/` (check with
   `git rev-parse --show-toplevel`). The outer repo has unrelated uncommitted
   changes that are not yours.

## 1. What the project is, and what exists

A wireframe tool. A wireframe is one JSON file: screens (states) holding blocks,
plus transitions between screens. You can edit it in a browser, from the command
line, or by having an AI write it; check it for problems; and export a spec sheet
for a coding AI or an image-generating AI.

| Req | What it means (agreed with the user, see `spec.md`) | Where |
| --- | --- | --- |
| R1 | Both a browser editor and headless editing, sharing one JSON file | `wireframe/ops.py`, `wireframe/cli.py`, `server.py`, `static/` |
| R2 | One Markdown spec, two modes: `coder` (everything) and `image` (visual only) | `wireframe/spec.py` |
| R3 | An authoring guide plus a validator, so an AI can write a wireframe and have it accepted or rejected with readable errors | `spec.authoring_guide()`, `model.validate`, `PUT /api/wireframe`, "Import JSON" |
| R4 | The screen flow is a full state machine; the checker finds flow conflicts | `wireframe/checks.py` |
| R5 | Blocks carry `info` keys (what data they show) and a `note`; the checker finds duplicates | `wireframe/checks.py` |

Data shape: `{name, canvas{width,height}, initial, states[{id,title,final,blocks[{id,type,x,y,w,h,label,info[],note,event}]}], transitions[{id,source,target,event,guard}]}`.
Block types: heading, text, button, input, image, list, nav, container.
`wireframe/example.py` has a valid 3-screen checkout (cart, payment, done).

### How data flows (important to keep)

```
browser (static/app.js) --POST /api/op--> server.py --apply_op--> wireframe/ops.py
CLI: python -m wireframe op FILE '<json>' ------------apply_op--^
                                   every op: copy doc -> change -> validate -> save atomically
```

The browser never edits the wireframe itself; it sends an op and redraws from the
reply (decision 0001). `ops.OPS` is the one list of ops; `tests/test_static.py`
fails if `app.js` sends an op that is not in it.

### Checker rules (`checks.RULES`, 14 codes)

Errors (make `check` exit 1): `no-initial`, `unknown-state`, `dead-end`,
`nondeterministic`, `dead-control`, `no-trigger`.
Warnings: `unreachable-state`, `unguarded-overlap`, `button-without-event`,
`overlap`, `out-of-canvas`, `duplicate-info`, `duplicate-label`, `missing-info`.
Findings are dicts `{severity, code, state, blocks, message}`. The guide an AI
reads is generated from `RULES`, so a new rule belongs in `RULES` and shows up in
the guide automatically.

## 2. How to run it

Needs Python 3.12+; nothing to install.

    python server.py                    # http://localhost:8000, edits ./wireframe.json
    python server.py my.json --port 9000
    python -m wireframe new my.json --example
    python -m wireframe validate my.json    # shape only
    python -m wireframe check my.json       # flow + duplicates; exit 1 on errors
    python -m wireframe export my.json --mode coder    # or image
    python -m wireframe guide
    python -m wireframe op my.json '{"op": "add_state", "title": "Receipt"}'

`wireframe.json` is git-ignored (it is the user's working file). Stop the server
with Ctrl+C.

## 3. How to run the tests

    python -m unittest discover -s tests -v
    python -W error::ResourceWarning -m unittest discover -s tests   # also catches unclosed files

Expected: `Ran 159 tests ... OK` in about 1 second. Per file: test_ops 31,
test_checks_flow 26, test_server 25, test_model 20, test_spec 20, test_cli 16,
test_checks_info 14, test_static 7. Test methods are `test_R<n>_<what>` and the
docstring cites the lettered criterion from `spec.md`, for example `R4(c)`.

What the tests cannot do: click and drag. Dragging and resizing blocks has only
been checked by a headless smoke test (the page loads, blocks and the Problems
panel render), not by a person. Headless recipe if Edge is installed:
start the server on a spare port, then
`msedge.exe --headless --disable-gpu --virtual-time-budget=4000 --dump-dom http://127.0.0.1:PORT/`
and look for `class="block` in the output.

## 4. Decisions made in Round 1, and why

The user asked for the first three in effect (the answers to my questions); the
rest are mine and the user was told. Decision records exist for 0001 to 0003.

| Decision | Why |
| --- | --- |
| R1 means both UI and headless, sharing one JSON file | The requirement contradicts itself; the user picked "both". |
| Single `apply_op` for every edit (ADR 0001) | One source of truth for rules; CLI, API and browser cannot disagree. Cost: a round trip per edit (a drag sends one op on release). |
| `unittest`, not `pytest` (ADR 0002) | "No libraries to install"; user chose it. Cost: more typing, no parametrize (use `subTest`). |
| Flow is a state machine; `validate` checks shape only, `check` reports flow problems as findings (ADR 0003) | Allows richer checks and saving half-finished work. Cost: guards are opaque text, never evaluated. |
| Transitions use `source`/`target` | `from` is a Python keyword. |
| Events starting `sys:` need no block | Timeouts and similar system events have no button. |
| `info` (keys) and `note` (free text) on blocks; keys compared casefolded and stripped | R5 needs something comparable; labels alone are too loose. |
| Duplicate checks are per screen, labels normalised (lowercase, punctuation to spaces) | The same data on different screens is normal; same screen is the bug. |
| A container may fully hold other blocks without an `overlap` warning | Otherwise every container would be flagged. |
| Severity per rule (see list above); only errors fail `check` | Warnings are advice; the exit code should mean "broken". |
| Ids are fixed; a state's `id` cannot be renamed (change `title`) | Renaming would have to rewrite every transition; out of scope in `spec.md`. |
| Deleting a state deletes its transitions; `initial` moves to the first remaining state or `""` | Avoids dangling references. |
| Auto ids `s1..`, `b1..`, `t1..` | Simple, readable in JSON. |
| `new` refuses to overwrite; saves are atomic (temp file then rename) | Never destroy or half-write the user's file. |
| Extra CLI commands `op` and `new --example` | `op` is how R1(c) is satisfied headlessly; the example gives a known-good file. |
| Server: 127.0.0.1 only, local Host header only, JSON-only writes, 1 MB body cap, drains oversized bodies before replying 413, serves only inside `static/` | No login exists, so the safe default is local-only. Draining fixes a Windows connection-reset race. |
| Explicit mimetype map in `server.py` | Windows can map `.js` to the wrong type via the registry. |
| Browser writes text with `textContent` only; a test bans `innerHTML` etc. | A label like `<script>` must show as text, not run. |
| `wireframe.json` git-ignored | User data, and the repo is public. |
| `problem.md` was not edited | The user did not ask; `spec.md` records my reading instead. |
| Mutation check of the checker in a scratch copy | I wrote tests and checks in the same step, so I proved the tests can fail. Three deliberate bugs were caught. |

## 5. Unresolved

1. **`problem.md` still says "Headless / User interface"** (self-contradictory).
   `spec.md` records the agreed reading ("both"). Ask the user whether to update
   `problem.md`.
2. **Hand test of the editor is pending.** The user was asked to open
   http://localhost:8000 and try add, drag, resize, delete. No result yet. Offer to
   fix anything they find.
3. **`NEXT-SESSION.md`**: delete, update or keep? User's call (warning 2).
4. **Root `CLAUDE.md` session-start duties were not done in Round 1** (re-fetching
   the course instructions and applying migrations, the one-line reminder about
   recording questions, quizzing on earlier topics). The Round 1 prompt said to use
   only what is in the repo. Ask the user whether to resume them. The files
   `course-instructions/`, `topics/` and the coaching notes live in the outer
   repo and I did not touch them.
5. **Tutor check not answered.** At the end of Round 1 I asked the user to explain
   in their own words why a drag sends one op on release and why the browser does
   not change the wireframe itself. Follow up per the root `CLAUDE.md`.
6. **Open design questions, not decided:** should `duplicate-info` also look across
   screens (today per screen only)? Should guards ever be evaluated (today never)?

## 6. Known limitations (not bugs, but the next round may hit them)

- The browser does not poll. An edit made by the CLI or another tab appears only
  after a reload or after the next edit in that tab.
- The lock in `server.py` is in-process. The CLI does not take it, so a CLI edit
  and a browser edit at the same instant can race (last write wins; the file is
  never corrupted because saves are atomic).
- Editor gaps: no undo/redo, no multi-select, no copy/paste, no snap-to-grid,
  no zoom (a big canvas scrolls), resize only from the bottom-right corner, info
  keys cannot contain commas (the field splits on them), rename and delete use
  the browser's `prompt()` and `confirm()`, findings are listed but not
  highlighted on the canvas (clicking one selects the screen and block).
- Text fields send their edit on `change` (leave the field or press Enter).

## 7. Gotchas for the machine

- Windows. Git prints "LF will be replaced by CRLF" warnings; harmless.
- The course shell is Git Bash, but the harness may route you to PowerShell; both
  work for the commands above.
- **Port 8765 may still have a smoke-test server from Round 1** (started on a
  scratch wireframe file). The permission system blocked my broad kill command,
  so I left it. It does not affect the tests (they use a free port) or the default
  port 8000. If something answers on 8765, find the exact process id for that port
  and stop only that one.
- `-W error::ResourceWarning` is a useful flag: it caught unclosed files in tests
  once.
- Tests start real servers on port 0 with `poll_interval=0.01`; the default
  0.5 s would add half a second per test.

## 8. Round 1 commits (oldest first, after the scaffold)

Data model with validation, headless ops, design checker, spec export and AI
guide, command line, then in this order: `6016bb2` server and API, `11a25a2`
browser editor, `15d0ce9` `.gitignore` for `wireframe.json`, `5d9c5d8` decision
records 0001 to 0003, `851118f` README. Use `git log --oneline` for the full list.

## 9. How to start Round 2

1. Read `CLAUDE.md`, `spec.md`, `docs/decisions/`, then this file.
2. Run the test suite and confirm 159 passing before changing anything.
3. Wait for the user's Round 2 prompt. Expect the same shape as Round 1: update
   `spec.md` and commit it, write tests naming requirement IDs, implement, commit
   in small steps, write at least one new decision record (next number is 0004),
   and finish with a list of every decision the user did not ask for.
4. Do not write the next handoff file unless asked.
