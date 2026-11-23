# 0015. The server idle timeout is 10 minutes, set in one place

Status: accepted (Round 7). Requirements: R17 (changes R12).

**In the context of** R17 changing R12's "shut down after 5 minutes of no requests" to
10 minutes, **facing** that the old number 300 was written in code, help text, the AI
guide, the README and several tests, **we decided for** changing the single constant
`serverctl.DEFAULT_IDLE_TIMEOUT` to 600 and updating every text that quotes it, with one
new test file (`tests/test_round7.py`) that checks the number and the texts, **and
neglected** adding a config file or environment variable for the default (more to
explain for one number), making the value depend on the editor heartbeat (the two have
different jobs), and leaving old texts saying 5 minutes (they would now be wrong),
**to achieve** a server that waits twice as long before stopping while `--idle-timeout`
still overrides it, **accepting** that a forgotten server now stays up 5 minutes longer.

## Consequences you can check yourself

- `python -c "from wireframe import serverctl; print(serverctl.DEFAULT_IDLE_TIMEOUT)"` prints 600.
- `python -m unittest discover -s tests` runs 475 tests, all passing, none skipped.
