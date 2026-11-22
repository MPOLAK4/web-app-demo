# 0014. Server routes live in one table, not an if-chain plus a second list

Status: accepted (Round 6). Requirement: R16.

**In the context of** the Round 6 cleanup of `server.py`, whose `dispatch` had grown to a
147-line chain of `if route == ...` blocks and kept a second, hand-written set of the same
paths to choose between 404 and 405, **facing** that a new route needed two edits in two
places and forgetting the second one silently gave 404 instead of 405 (CLAUDE.md even had
a rule warning about it), **we decided for** one module-level table,
`ROUTES = {(method, path): "handler_method_name"}`, with each handler a small method on the
request class and the 404/405 answer derived from the table, **and neglected** leaving the
chain and only moving the `known` set next to it (still two things to keep in step),
splitting the server into several files (more files to read for a 400-line module, against
the "keep it small and readable" rule), a decorator that registers routes as the methods are
defined (less to type, but the full list of routes is no longer visible in one place), and
leaving the server alone because it worked (the point of the round is to review and tidy),
**to achieve** a server where adding a route is one table line plus one method, and the
whole API surface can be read at a glance, **accepting** that handlers are named by string
(a typo shows up only when that route is called, so every route has a test that calls it)
and that the file got about thirty lines longer, because each handler is now its own
method.

## Consequences you can check yourself

- `python -c "import server; print(len(server.ROUTES))"` prints 16.
- Every path in `server.ROUTES` appears in the docstring at the top of `server.py`; a test
  checks it.
- `python -m unittest discover -s tests` still passes, and `examples/` and `viewer.html`
  are unchanged (`git status` stays clean after rebuilding them), because nothing the
  user can see changed.
