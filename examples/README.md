# Examples

Each folder is one example wireframe and the output the tool gives for it, so you can
see the expected input and output side by side. **These files are built by code; do not
edit them.** Rebuild with `python -m wireframe examples --build examples`. A test fails if
they are out of date.

| Example | What it shows |
| --- | --- |
| `checkout` | The worked example from the authoring guide: cart, payment, done. |
| `login` | A sign-in form with inputs and a checkbox; one button leads to two screens (guarded). |
| `dashboard` | Side navigation, three stat cards and a table, plus a report screen. |
| `settings` | A toggle, a dropdown and a slider, with Save and Cancel leading to two end screens. |
| `flawed` | A valid file with a bad design, so you can see what the checker reports. |

## What is in each folder

| File | What it is |
| --- | --- |
| `wireframe.json` | The **input**: the wireframe itself. |
| `coder.md` | `python -m wireframe export wireframe.json --mode coder`: the spec sheet for a coding AI. |
| `image-live.md` | `export --mode image --data live`: the brief for an image generator, with sample text filled in. |
| `check.txt` | `python -m wireframe check wireframe.json`: the problems found (none for the clean examples). |
| `screens/<screen>.svg` | `render --state <screen> --data live`: a picture of each screen. |
| `viewer.html` | `viewer`: double-click it to look at the screens and click through the flow. |

## Using an example

- Look at one: `python -m wireframe examples login --part coder` (parts: wireframe, coder,
  image, check, svg, viewer).
- Start your own file from it: `python -m wireframe new my.json --example login`.
- Over HTTP (with a server running): `GET /api/examples` and `GET /api/example?name=login`.
