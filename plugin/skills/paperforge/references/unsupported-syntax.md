# Constructs the renderer does not interpret

These fail **quietly**: the syntax is printed literally, and a definition line
becomes a stray paragraph in the published document. A coverage check cannot
catch it, because the text *is* present — it is simply not rendered. So lint
blocks them at the gate instead.

| Construct | Lint rule | Instead |
|---|---|---|
| `[^1]` and `[^1]: note text` | `unsupported-footnote` | Put the aside in a callout, or in the sentence |
| `: Caption {#fig-1}` / `{#tbl-2}` | `unsupported-caption` | See `diagrams.md`; captions are generated |
| `TODO`, `TBD`, `FIXME`, `XXX`, `PLACEHOLDER` | `todo` | Finish the line |
| `lorem ipsum` | `lorem` | Write the text |
| `(SOME_FILE.md)` in prose | `source-filename` | Name the document, not the file |
| `[`file.md`](./file.md)` as link text | `filename-label` | Label the link for a reader |

## Footnotes are asymmetric — and that is why they are blocked

The Typst emitter *does* implement `[^id]`, and sets it properly at the foot of
the page. The HTML renderer does not implement it at all. Rather than ship two
editions that disagree — one with a footnote, one with `[^1]` printed in the
middle of a sentence — lint blocks the construct in both.

If footnotes are wanted, the work is in the HTML renderer, not in the source.

## Other HTML in markdown

Only `<br>` is let through, and only for line breaks inside table cells
(`tables.md`). Every other tag is escaped and printed as text. `verify` reports
raw markup that reached a rendered page, in either edition.

## Related

`lint.md` · `tables.md` · `diagrams.md` · `cross-references.md`
