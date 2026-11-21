# 0002. `unittest` instead of `pytest`

Status: accepted (Round 1). Requirement: the project rule "always write unit
tests".

**In the context of** needing a test tool for a project whose README promises
"no libraries to install", **facing** a choice between Python's built-in
`unittest` and the third-party `pytest`, **we decided for** `unittest`, run
with `python -m unittest discover -s tests -v`, **and neglected** `pytest`,
**to achieve** a project that anyone with Python 3.12 can test straight after
cloning it, with nothing to install and no test-only dependency to keep out of
a release, **accepting** more typing per test (classes, `self.assertEqual`),
no fixtures or `parametrize`, so repeated cases use `subTest` loops and a small
helper module (`tests/helpers.py`).

## Consequences you can check yourself

- `pip list` does not need to show `pytest` for the suite to run.
- Test files are named `test_*.py` and test methods `test_R<n>_...`, so a
  failure message names the requirement it protects.
