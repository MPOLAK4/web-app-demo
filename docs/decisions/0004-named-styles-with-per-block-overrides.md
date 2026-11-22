# 0004. Blocks share a look through named styles, with a per-block override

Status: accepted (Round 2). Requirements: R6, R7.

**In the context of** making blocks look consistent (R7) and giving the coder and
image specs a precise look for every block (R6), **facing** the choice of how blocks
share a look, **we decided for** a document-level `styles` table of named styles (a
style is a set of up to 11 fixed fields such as `fill` and `radius`), a block's
optional `style` name, and a block's optional `look` that overrides single fields;
the resolved look of a block is the type default, then the named style, then the
`look`, **and neglected** (a) a free "group" tag that only says blocks belong
together, and (b) copying the style fields into every block, **to achieve** one
place to change a colour for every block that uses it, and a spec that can say
"these blocks must look identical", **accepting** one more concept to learn, a
rule to resolve in three layers, and new findings (`missing-style`,
`unknown-style`, `unused-style`) to keep the table honest.

## Consequences you can check yourself

- Change `styles.primary.fill` in the JSON and every block using `primary` changes
  in `python -m wireframe export FILE --mode coder`.
- `delete_style` does not leave blocks pointing at nothing: it copies the style's
  fields into each user's `look` first, so they keep how they look.
- `GET /api/resolved` gives the final style of every block; the editor draws from
  it instead of keeping its own copy of the rules.
