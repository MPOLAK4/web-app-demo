# 0010. The clickable viewer is built by Python and only looks answers up

Status: accepted (Round 4). Requirement: R13.

**In the context of** needing one `.html` file you can double-click, with no server,
**facing** that a file opened from disk cannot run Python and the rules for Play and
for drawing a screen live in Python (ADR 0005, 0008), **we decided for** a build
step: `viewer.build_viewer` precomputes every picture (both data modes), every click
area and every `play.step` answer, and the page just looks them up, **and neglected**
porting `play` and `render` to JavaScript, running Python in the browser (Pyodide,
which needs a download), and a launcher page that secretly starts a server (which
breaks R12), **to achieve** a viewer that cannot disagree with the editor and works
offline, **accepting** that the viewer is a snapshot (rebuild it after editing, with
`python -m wireframe viewer`), that it cannot edit or load another wireframe, and a
larger file because each screen is stored twice.

## Consequences you can check yourself

- `viewer.html` in the repo root is a built example; a test fails if it is out of date.
- The page has no `innerHTML`, `fetch` or `eval` and carries a Content-Security-Policy
  (a test checks this); data is embedded with `<` escaped so wireframe text cannot
  end the script block.
- Double-click `viewer.html`: click a block, use Back, Restart, the data switch and
  Save SVG. Unit tests cannot click, so try it yourself.
