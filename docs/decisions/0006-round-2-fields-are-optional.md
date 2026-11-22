# 0006. Every Round 2 field is optional, so Round 1 files stay valid

Status: accepted (Round 2). Requirements: R6, R7, R8.

**In the context of** adding styles, block properties, backgrounds and 15 block
types to a file format that Round 1 wireframes already use, **facing** whether old
files should keep working, **we decided for** making every new field optional (a
document's `styles`, a screen's `background`, a block's `style`, `look`,
`placeholder`, `options`, `value`, `disabled`, `hidden`, `required`) and only writing
a field when it is used, **and neglected** (a) making the new fields required and
migrating old files, and (b) a version number with a separate loader per version,
**to achieve** files that need no migration and a validator that stays one list of
allowed fields, **accepting** that code reading a block must always handle a missing
field, and that an old file gets `missing-style` warnings until it is styled.

## Consequences you can check yourself

- A Round 1 file passes `python -m wireframe validate FILE` unchanged.
- The same file fails nothing in `check`; it only gains `missing-style` warnings.
