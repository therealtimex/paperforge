# Print and PDF

Two different PDFs exist, for two different jobs.

| | Engine | What it is for |
|---|---|---|
| `pdf = "chrome"` | Chrome, from the built HTML | The reading edition's own layout, printed. Also how page numbers are measured, whether or not you publish it |
| `pdf = "typst"` | Typst, from the markdown | Typeset independently: footnotes at the foot of the page, running heads, denser setting |

## Choosing between them

Measured on the document both were built from — a 56-page policy report whose
annex carries an eight-column source ledger:

| | Chrome | Typst |
|---|---:|---:|
| Pages | 56 | **42** |
| Source URLs surviving whole | 23 of 26 | **26 of 26** |
| Wide tables | landscape | landscape |
| Footnotes at the foot of the page | no | yes |
| Running heads carrying the chapter | no | yes |
| Identical to what a reader sees on screen | yes | no |

Typst is the better print edition for a document with wide tables, and the gap
is not stylistic: a table row taller than a Chrome page splits across the
break, and a URL cut in half at that break is a citation a reader cannot
follow. A flipped Typst page keeps each wide table whole, so the question never
arises — which is also why it is shorter.

Choose `chrome` when what must be published is exactly what a reader sees in
the browser, or when the document has no wide tables and the reading edition's
layout is the deliverable.

## Why Typst exists here

Chrome's print engine cannot do footnotes at the foot of a page, chapters
opening on a new page reliably, or chapter titles in running heads. Typst does
all of it natively, and localises captions from the document language, which
lines up with the profile model.

Requires `typst` on `PATH` (`brew install typst`).

## Page breaks

Every part opens a new page, in both editions. So does the annex, and every
annex section. Headings avoid breaking from their content *and from splitting
internally* — a two-line part banner was once found split across two pages, each
holding one line and nothing else. Tables, figures and callouts avoid internal
breaks.

Printed diagrams are capped at **198mm** — see `diagrams.md` for why.

## Wide tables turn landscape

A table of six or more columns prints on a **landscape A4 page**, at a smaller
face, with a fixed layout and long tokens allowed to break. Portrait cannot hold
seven columns of prose plus a source URL at any legible size: shrinking until it
fits gives one word per line and *still* loses the right-hand column off the
page. In an evidence annex that column holds the citations, so the printed copy
becomes unverifiable while every gate stays green.

Both print paths do this. Chrome uses a named landscape `@page`; Typst places
the table on a flipped page and returns to portrait after it. On the report
this was found on — an eight-column source ledger — the Typst edition carries
**all 26 source URLs whole**, and does it in 42 pages against Chrome's 56,
because a flipped page keeps each wide table intact instead of splitting it
across a break.

`verify` reports source URLs it cannot find whole in the print edition. It is a
finding, not a failure — a table row taller than the page continues onto the
next one and nothing rejoins a URL split across that break, so some reported
URLs are in fact intact. Read it as "look at these pages".

## Printed page numbers are measured, never estimated

The build prints the document, reads back which page each contents entry landed
on, bakes the numbers in, and reprints until the mapping stops changing.

Because they are baked, print pins `@page size A4` with margins `16mm 15mm 18mm`.
That is what makes them trustworthy and equally what limits them: they describe
an A4 print at those margins.

`--no-measure` skips the whole loop when iterating on content.

### An entry that gets no number is reported

A contents entry is numbered by matching it to the heading it names, and then
finding that heading in the printed pages. Two things make that impossible, and
both end the same way — the match is **refused rather than guessed** and the
entry is left blank, because a wrong page number in a contents is worse than
none:

- **Two headings answer to the same words.** A report section and an annex
  section worded alike; case and punctuation are normalised away, so
  `## Domain 1. Downstream industrial cluster` and
  `### Domain 1: Downstream Industrial Cluster` are the same identity.
- **The heading was not located in the printed pages.** A part or annex
  section is required to *open* a page, which is what stops a number being
  aimed at a summary list of the same words. An annex section sharing a page
  with the annex title cannot pass that test, so the measurement never places
  it and the entry has no page to carry. `en-sample` has one: page 10 opens
  with the annex title and *Section 1. Source appraisal* sits below it.

Both are decided while the page numbers are being **measured**, before anything
is written into the contents. The check that reads the built document afterwards
sees only a blank entry, and reports it without claiming which cause it was.

Refusing quietly was the defect. Everything else in this check validates the
numbers that are present, which has no denominator, so a 49-page report with
five of its six entries blank reported `1 confirmed, 0 untestable, 0 wrong`.
`verify` now names them:

```
page numbers: 1 confirmed, 0 untestable, 0 wrong
warn  5 contents entries could not be numbered - no unambiguous heading in the printed pages; see print.md
    warn  domain 1. downstream industrial and chemical cluster
```

A **warning, not a refusal**: the document is correct and publishable, its
contents is only less useful than it looks. The fix is in the source — word the
two headings differently, and the entry finds its own.

> **Limitation.** Page numbering and the pagination check both work by reading
> the PDF's text back. Chrome embeds some fonts — CJK body faces among them —
> without a usable `ToUnicode` map, so glyphs are drawn but cannot be read: the
> Chinese fixture returns 12% of its source. The pipeline measures that ratio and
> **declines both checks with a stated reason**, rather than reporting no page
> numbers and a document full of "empty" pages. Rendering, structure and
> publication are unaffected.

## A bound edition

`type = "book"` sets the print edition for binding: a trim that is not A4,
mirrored margins, chapters opening on a recto with the skipped leaf left bare,
verso/recto running heads, and roman front matter restarting at arabic one. It
is the one type that refuses `pdf = "chrome"`, because Chrome honours the trim
and the mirrored margins and then gets the other three wrong — which is worse
than getting all five wrong, since the result looks bound. See `books.md`.

## Both editions are published

A document declaring `pdf = "typst"` gets its reading edition and its print
edition published as separate artifacts, each with its own URL and content type.
`status` lists both.

Because two independent emitters render the same source, `verify` compares them:
the same headings must open a page and both must carry the same figures. See
`verify.md`.

## Related

`diagrams.md` · `maths.md` · `citations.md` · `verify.md` · `layout.md` · `docx.md` · `columns.md` · `books.md`
