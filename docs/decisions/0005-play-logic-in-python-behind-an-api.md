# 0005. Play mode logic lives in Python and the browser asks over the API

Status: accepted (Round 2). Requirements: R9.

**In the context of** letting a person navigate the wireframe like a real UI, in the
browser and from the command line (R9), **facing** where the "which screen comes
next?" rule should live, **we decided for** a small Python module (`wireframe/play.py`
with `screen` and `step`) used by both the `walk` command and `POST /api/play`, with
the browser only drawing the answers, and for answering `choose` (listing the
options) when several transitions could apply, **and neglected** (a) writing the
rules again in `app.js`, and (b) trying to evaluate guards to pick automatically,
**to achieve** one rule set that the tests can check without a browser and that the
two interfaces cannot disagree on, **accepting** a server round trip for every click
and that a person must choose between guarded alternatives, because guards are plain
words that are never evaluated (decision 0003).

## Consequences you can check yourself

- `python -m wireframe walk FILE go back` and Play mode in the browser end on the
  same screen for the same events.
- Playing never changes the file: compare it before and after (tests do).
- The test `test_R9_play_mode_never_sends_an_edit` fails if the Play code in
  `app.js` ever calls the edit function.
