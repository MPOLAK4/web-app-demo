# 0001. One `apply_op` function for every edit

Status: accepted (Round 1). Requirements: R1(b), R1(c), R1(e).

**In the context of** letting a wireframe be edited both from a browser and
headlessly (command line, scripts, an AI), **facing** the risk that two copies
of the editing and validation rules would slowly disagree, **we decided for**
one Python function, `apply_op(doc, {"op": ..., ...})`, that the command line
(`python -m wireframe op`), the HTTP API (`POST /api/op`) and the browser all
use, with the browser sending small op messages and redrawing from the
server's reply, **and neglected** (a) keeping the wireframe in browser
JavaScript and saving the whole document with `PUT`, and (b) writing the edit
rules twice, once in Python and once in JavaScript, **to achieve** a single
source of truth: a move, resize or delete behaves identically everywhere, and
invalid edits are refused by the same validator whichever door they use,
**accepting** a network round trip per edit (a drag sends only one op, when the
mouse is released), and that the editor does not work without the server
running.

## Consequences you can check yourself

- `static/app.js` contains no editing rules; `tests/test_static.py` checks that
  every op name it sends exists in `wireframe.ops.OPS`.
- Run `python -m wireframe op FILE '{"op": "delete_block", ...}'`, then
  reload the browser: the change is there.
