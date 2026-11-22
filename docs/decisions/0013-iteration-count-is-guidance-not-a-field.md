# 0013. The iteration count is guidance in the guide and exports, not a stored field

Status: accepted (Round 5). Requirement: R15.

**In the context of** an AI that should decide, or ask, how many times to rework one UI
piece, **facing** that the tool never sees the AI's conversation and cannot tell whether
a pass really changed anything, **we decided for** text only: an "Iterating on one UI
piece" section in the authoring guide (ask the user for the count; if you cannot ask,
use `DEFAULT_ITERATIONS`, which is 2, and say so; change a named thing each pass; log
`Pass k of N: ...`), plus a short `## Iterations` section at the end of both exports,
with the default kept in one constant, **and neglected** an `iterations` field on each
screen (every older file and every op would need to know about it, and nothing could
enforce it anyway), an `iterate` command that counts passes (the tool would be pretending
to supervise something it cannot see), and putting the guidance only in the guide (an AI
that was handed just the spec sheet would never read it), **to achieve** a rule the
AI reads wherever it starts, with no change to the file format, **accepting** that the
count is not enforced: the AI is responsible for it, and the user can only check it by
reading the pass log.

## Consequences you can check yourself

- `python -m wireframe guide` contains the section; `export FILE --mode image` ends with
  `## Iterations` and uses only visual words (no event names, guards or info keys).
- Adding `"iterations": 3` to a wireframe file makes `validate` fail: there is no such
  field.
- Change `DEFAULT_ITERATIONS` in `wireframe/spec.py` and the number changes in the
  guide and both exports.
