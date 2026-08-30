# Images

A diagram is written in the document and drawn at build time. An image is the
other kind of figure — a photograph, a chart exported from an analysis, a
scanned instrument trace — and it is a *reference to a file*.

```markdown
![Refining share by country, 2024](figures/refining-share.svg)

: Refining share by country, 2024 {#fig-refining}

Refining is where the concentration is: see @fig-refining.
```

An image on a line of its own, at the left margin, is a **figure**. It is numbered with the
diagrams, in source order, takes the caption written under it, and carries that
caption's label — so `@fig-refining` resolves to *Figure 1* the same way a
diagram's does. An image inside a sentence is left in the sentence.

An indented image is content of whatever contains it — a list item, most
often — and stays inline, because the four emitters do not agree about where an
indented block belongs and a figure they disagree about takes a number in two
editions and not the others.

The path is relative **to the document's own source file**, which is where an
author is looking when they type it. An included chapter is a fragment of that
document rather than a document of its own — see `assembling.md` — so a path
written in one resolves from the same place, and lint and the four emitters
cannot disagree about where that is.

## The file travels with the document

The picture is inlined as a data URI in the reading edition, rasterised into
the print edition, and placed in the `.docx`. Nothing in a published document
loads over the network — see `layout.md` — and a relative `src=` is not an
exception to that rule, only a slower way to break it: a linked image survives
`verify`, which refuses `http(s)://`, and then fails the first time the file
travels on its own.

An SVG is rasterised for print and for Word rather than placed as vector art.
Word cannot place one at all, and Typst draws it as vector operations, which is
invisible to the gate that compares the editions.

## What is refused

| Rule | Severity | Fires on |
|:---|:---|:---|
| `missing-image` | block | no file at that path, relative to the document |
| `remote-image` | block | an `http(s)://` or protocol-relative src |
| `stray-caption` | block | a caption under something that carries none |

A missing file is the one failure in a document that is true when it is written
and false when it is built: nothing in the prose changed, so nothing in the
prose looks wrong, and the paper still says "see Figure 1". There is no reading
under which it is correct, so it blocks rather than warns.

`stray-caption` is not only about images. A caption belongs to the block above
it, and every emitter takes it by looking back from a figure, a table or an
equation. Written under a paragraph or a list, nothing consumes it and it
prints to the reader as prose — colon, text and `{#fig-x}` braces — while
`@fig-x` still resolves to a number for a float that is not on the page.
Neither the dangling-reference check nor the orphan-label check can see that:
the label exists, and it is referred to.

In a draft build a missing image leaves a **visible gap** naming the path,
rather than being passed over silently.

## Related

`diagrams.md` (the other kind of figure) · `cross-references.md` ·
`figures.md` (the numeric-consistency gate — a different thing) ·
`layout.md` · `lint.md`
