# Print and PDF

Two different PDFs exist, for two different jobs.

| | Engine | What it is for |
|---|---|---|
| **Reading edition print** | Chrome, from the HTML | The "Print / Save PDF" button; also how page numbers are measured |
| **Print edition** | Typst, from the markdown | The published PDF artifact, when a document declares `pdf = "typst"` |

## Why Typst

Chrome's print engine cannot do footnotes at the foot of a page, chapters
opening on a new page reliably, chapter titles in running heads, or numbered
cross-references. Typst does all of it natively, and localises captions from the
document language, which lines up with the profile model.

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

> **Limitation.** Page numbering and the pagination check both work by reading
> the PDF's text back. Chrome embeds some fonts — CJK body faces among them —
> without a usable `ToUnicode` map, so glyphs are drawn but cannot be read: the
> Chinese fixture returns 12% of its source. The pipeline measures that ratio and
> **declines both checks with a stated reason**, rather than reporting no page
> numbers and a document full of "empty" pages. Rendering, structure and
> publication are unaffected.

## Both editions are published

A document declaring `pdf = "typst"` gets its reading edition and its print
edition published as separate artifacts, each with its own URL and content type.
`status` lists both.

Because two independent emitters render the same source, `verify` compares them:
the same headings must open a page and both must carry the same figures. See
`verify.md`.

## Related

`diagrams.md` · `maths.md` · `citations.md` · `verify.md` · `layout.md` · `docx.md`
