# 0007. Data standins are `{{key}}` tokens plus a document-level `data` table

Status: accepted (Round 3). Requirements: R11.

**In the context of** showing "live" data (what a user would really see) versus
"debug" data (the name of the value, such as `cart.total`) in a wireframe,
**facing** where the sample text should live, **we decided for** writing
`{{key}}` tokens inside labels, placeholders, values and options, with an optional
document-level `data` table of sample text (a missing key gets an automatic standin
such as "Cart total"), **and neglected** (a) a per-block `sample` field next to
`label`, and (b) a separate sample-data file, **to achieve** one place per value
(two blocks showing the same total share one sample), a label that reads the same
way in the file as in debug mode, and old files that stay valid, **accepting** that
a label can now contain markup-like text that is replaced on display, and that
the coder spec has to keep tokens raw so a coder still sees the key.

## Consequences you can check yourself

- `python -m wireframe render FILE --data debug` shows `{{cart.total}}`; `--data live` shows the sample.
- A file with no `data` field is still valid (see [0006](0006-round-2-fields-are-optional.md)).
