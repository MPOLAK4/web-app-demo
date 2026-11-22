# 0008. Picture files are SVG and HTML written by Python, not PNG

Status: accepted (Round 3). Requirements: R10.

**In the context of** producing a picture file of any screen or any state reached
after some events, **facing** which formats to support and where to draw them, **we
decided for** SVG, plus the same SVG inside an HTML page, produced by
`wireframe/render.py` from the same resolved styles Play uses, **and neglected** (a)
PNG, which needs a drawing library or a headless browser, and (b) drawing in
`app.js` and saving from the browser, which would have no command-line route,
**to achieve** the standard library only, a `render` command and `/api/render`
that work without a browser, and one drawing path, **accepting** that there is no
PNG (an image AI or a viewer can open the SVG) and that the look is a simple
approximation of the editor.

## Consequences you can check yourself

- `python -m wireframe render FILE --out screen.svg` works with no server running.
- Text is escaped, the file has no script, and `/api/render` sends a policy that forbids scripts.
