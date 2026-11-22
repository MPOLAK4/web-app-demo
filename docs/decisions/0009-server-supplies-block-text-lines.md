# 0009. The server supplies each block's text lines; the browser keeps no copy of the rules

Status: accepted (Round 3). Requirements: R10, R11.

**In the context of** the editor and Play needing to show standins in live mode,
**facing** that the per-type text rules (a checkbox shows `[x] Label`, and so on)
existed in JavaScript while Round 3 needed them in Python for the files, **we
decided for** keeping them only in `render.content_lines` and serving the result
through `/api/lines` and `lines` in `/api/play`, **and neglected** keeping two
copies in sync, or porting the substitution rule to JavaScript, **to achieve** an
editor, Play and picture file that cannot disagree, **accepting** one extra
request when the screen or mode changes and that the editor shows stale text for a
moment while it refetches.

## Consequences you can check yourself

- `app.js` has no `contentLines` function (a test checks this).
