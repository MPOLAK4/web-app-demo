# 0003. The screen flow is a state machine, and flow problems are findings, not save errors

Status: accepted (Round 1). Requirements: R3, R4, R5.

**In the context of** finding conflicts in the flow between screens (R4) while
an AI or a person is still drafting the wireframe, **facing** two linked
choices (how rich the flow model is, and when a flow problem should stop you),
**we decided for** a full state machine stored in the JSON file (screens are
states, transitions have a source, target, event and an optional guard; events
starting with `sys:` are raised by the system rather than by a block), and for
splitting the checks in two: `validate` rejects only a malformed *shape*
(wrong types, unknown fields, bad numbers), while `check` reports flow and
duplication problems as findings with a severity, **and neglected** (a) a plain
list of "screen A links to screen B", and (b) refusing to save a wireframe
whose flow is broken, **to achieve** checks that a plain link list cannot
express (unreachable screens, dead ends, two transitions on the same event,
buttons that trigger nothing, transitions no control can fire) and the ability
to save and keep editing a half-finished wireframe, **accepting** more concepts
for the user to learn, and that guards are opaque text that is never
evaluated, so two guarded transitions on one event can only be flagged as a
possible overlap, not proven to conflict.

## Consequences you can check yourself

- `python -m wireframe validate FILE` can pass while `python -m wireframe check
  FILE` exits 1: valid shape, broken flow.
- Warnings alone never make `check` fail; only errors set exit code 1.
- The authoring guide an AI reads is generated from the same rule table
  (`wireframe/checks.py: RULES`) the checker uses, so they cannot drift apart.
