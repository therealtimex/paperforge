# Word editions

```toml
docx = true
```

Builds `<name>.docx` beside the reading edition, and publishes it when the
document is publishable.

## What it is for

A ministry receives a report and then **works on** it: lifts a section into a
submission, comments in the margin, routes it through three offices with tracked
changes. HTML and PDF are read-only to that reader, so the document stops being
usable at exactly the point it becomes useful.

This is a **working document, not a rendition of the print edition.** Structure,
tables, diagrams and the source annex come across intact and land on real Word
styles — `Heading 1..4`, `List Bullet`, `Table Grid`, `Intense Quote` — so an
official can apply a house template without unpicking direct formatting.

Wide tables get their own landscape section, the same rule the print edition
uses, for the same reason: an eight-column source ledger is unreadable in
portrait and its right-hand column is where the citations live.

## What it deliberately does not carry

- **Banners, gradients and the colour system.** A part heading takes the brand's
  navy and nothing else. A colour ramp is not what survives being pasted into
  someone else's template.
- **Measured page numbers.** Word paginates the document when it opens it. The
  pipeline's page numbers describe an A4 print at fixed margins and would be
  wrong the moment the reader changes a font.
- **The contents sidebar and scroll affordances**, which are reading-edition
  furniture.

## It is the third emitter

`markdown.py` renders HTML, `typst.py` the print edition, and this one Word.
The first two drifted apart within a day of the second existing. **This one
drifted on its first build**: it carried the embedded annex's own title,
subtitle and contents, which the reading edition drops because the annex is
folded into its parent.

So `verify` compares them — headings as *sets*, not counts, because the totals
were close enough that counting alone would have hidden it — along with figure
and table counts:

```
docx: 40 headings, 7 figures, 9 tables agree with the reading edition
```

Pages are not compared. There is nothing in a `.docx` to hold a measured page
number against.

## Requires

`python-docx`. Diagrams are reused from the raster the print edition already
produces, so a document with diagrams also needs headless Chrome.

## Related

`manifest.md` · `print.md` · `tables.md` · `verify.md`
