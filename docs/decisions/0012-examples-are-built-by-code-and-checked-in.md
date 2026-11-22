# 0012. Examples are built by code, and their expected output is checked in and tested

Status: accepted (Round 5). Requirement: R14.

**In the context of** showing a user or an AI example layouts together with the output
the tool gives for them, **facing** that an "expected output" file silently goes wrong
the day the exports, checker or renderer change, **we decided for** writing each example
as a small builder function in `wireframe/examples.py` (using the same `model` rules as
any wireframe), generating every expected output (coder spec, image brief, check result,
SVGs, viewer) with the real functions, saving them into the repo folder `examples/`
with `python -m wireframe examples --build examples`, and adding a test that fails when
the saved files differ from a fresh build, **and neglected** hand-written JSON files
plus hand-written expected output (they drift and nothing notices), producing examples
only on demand with no files in the repo (an AI or a reader without Python could not
look at them), and a "golden file" folder that tests overwrite themselves (a failing
test should tell you to rebuild on purpose, not fix itself), **to achieve** examples
whose expected output is always true and can be read without running anything,
**accepting** that a change to an export means rebuilding `examples/` and committing the
new files, and that the folder holds about 40 generated files.

## Consequences you can check yourself

- Change a word in `spec.py`'s coder export, run the tests: the stale-folder test fails
  and tells you to run `python -m wireframe examples --build examples`.
- `python -m wireframe examples login --part coder` prints the same text as
  `examples/login/coder.md`.
- `examples/flawed/check.txt` lists the seven findings that `flawed` is built to cause.
