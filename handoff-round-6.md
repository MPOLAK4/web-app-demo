# Handoff: Round 6 (R16, codebase cleanup)

Date: 2026-11-22. Requirement: R16 (cleanup/refactor, no behaviour change).

## What changed
- `server.py`: a `ROUTES` table (16 entries) replaces the 147-line if-chain; each route is a
  small Handler method; 404/405 come from the table (`KNOWN_PATHS`). One `drain_body()`,
  one `download_name()`, idle-timeout default imported from `serverctl`.
- `wireframe/cli.py`: `_render` reuses `_write_or_print`.
- `wireframe/data.py`: removed an unused `is_data_key` import.
- `tests/test_refactor_round6.py`: 9 tests for R16(a)-(g).
- `docs/decisions/0014-server-routes-in-one-table.md`: the decision record.
- `README.md` index updated; `CLAUDE.md` route rule updated (uncommitted, please read).

## Not changed on purpose
- `static/app.js` (754 lines): unit tests cannot click or drag, so a refactor there is not
  safe to verify here.

## Check it yourself
- `python -m unittest discover -s tests` -> 472 tests, OK, 0 skipped.
- `git status` stays clean after `python -m wireframe examples --build examples`.
- Open the editor in a browser once and click through; unit tests cannot do that.

## What remains
- Round 7+ requirements: yours to give, including which earlier requirement ID is changed
  or removed. Commit them on 2026-11-23 or later.
