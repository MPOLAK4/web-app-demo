# Handoff: Round 7 (R17, changes R12)

Date: 2026-11-22. Requirement: R17 (idle timeout 10 minutes instead of 5; changes R12).

## What changed
- `wireframe/serverctl.py`: `DEFAULT_IDLE_TIMEOUT = 600` (still the only definition).
- Help text and docs: `server.py`, `wireframe/cli.py`, `wireframe/spec.py` (AI guide),
  `static/app.js` comment, `README.md`.
- `spec.md`: new "Round 7" section, which replaces the 5-minute wording of Round 4.
- Tests: `tests/test_round7.py` (new), and the 300 -> 600 numbers in
  `tests/test_server_round4.py` and `tests/test_refactor_round6.py`.
- `docs/decisions/0015-idle-timeout-ten-minutes.md`: the decision record.

## Not changed on purpose
- The Round 4 history text in `spec.md`, older handoff files and ADR 0011 still say
  5 minutes or 300 seconds: they record what was true in that round.
- The editor heartbeat (one ping a minute).

## Check it yourself
- `python -m unittest discover -s tests` -> 475 tests, OK, 0 skipped.
- `python -m wireframe start`, then `status`, then `stop`.

## What remains
- Round 8+ requirements are yours to give.
