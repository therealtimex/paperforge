# Document types

A document declares its `type`; the type implies how it is rendered, so the
manifest names the kind of thing rather than repeating layout mechanics.

| Type | What it means |
|---|---|
| `report` | Title page, contents, sidebar, printed page numbers, embedded annex |
| `brief` | Masthead, tighter scale, no contents |
| `note` | A brief without page numbers |
| `deck` | reveal.js slides, speaker notes, landscape PDF |

## Scale is not cosmetic

Rendered as a report, a 1,470-word brief ran to **ten A4 pages** — for a document
whose title says *2 pages*. As a brief it is five. Getting to two would need
editorial cuts, not CSS. Choosing the type wrongly is a content problem
disguised as a formatting one.

## A project declares its own

The set of things research teams publish is not ours to enumerate:

```toml
[types.case-study]
extends = "report"
page_numbers = true

[types.board-pack]
layout = "brief"
```

`extends` inherits from a built-in or an earlier declared type; the remaining
keys override. An **undeclared type is an error**, not silence — a mistyped
`case-stdy` used to render quietly as a report.

## Related

`manifest.md` · `decks.md` · `layout.md` · `print.md`
