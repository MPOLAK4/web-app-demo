# web-app-demo

A small web app: a Python server that sends HTML/JavaScript to the browser. The
problem it solves is in [problem.md](problem.md).

## How to run

Needs Python 3.12 or newer. No libraries to install.

    python server.py

Then open http://localhost:8000 in a browser.
(`server.py` does not exist yet; this works once the first code is added.)

## How to run the tests

    python -m unittest discover -s tests -v

## Project index

| Card | What it is |
| --- | --- |
| `problem.md` | The problem and the numbered requirements (R1, R2, ...). Written by me. |
| `README.md` | This file: how to run, how to test, and this index. |
| `CLAUDE.md` | Instructions the coding assistant follows in this project. |
| `.gitignore` | Files git must never track (transcripts, secrets, virtual environments). |
| `server.py` *(coming)* | The small Python server (standard library only). |
| `static/` *(coming)* | The HTML, CSS and JavaScript the browser loads. |
| `tests/` *(coming)* | Unit tests; they name the requirement IDs they check. Not part of a release. |
