# Two columns

A journal asks for a two-column manuscript. One key sets it:

```toml
  [[collection.document]]
  source  = "paper.md"
  columns = 2
  pdf     = "typst"
  docx    = true
```

Only `1` and `2` are accepted. No journal asks for three, and a third column on
A4 is 55mm wide — it cannot hold a table, a source URL, or a Vietnamese compound
noun. A deck is refused outright: a slide is not a page and has no measure to
divide.

## It is a print instruction

| Edition | What `columns = 2` does |
|---|---|
| `pdf = "typst"` | Two columns, from the body down |
| `docx` | A two-column body section, after a one-column title section |
| HTML on screen | **Nothing.** One column, as before |
| HTML in print, including `pdf = "chrome"` | Two columns |

The reading edition stays one column on screen deliberately. A two-column
article in a scrolling window means reading to the foot of the window and
scrolling back to the top for every screenful — the layout only works when the
column has a bottom, which is what a page gives it and a browser does not.

## What crosses the gutter

Three things span the full measure, because none of them is legible inside an
88mm column:

- **The title block** — kind, title, byline, affiliations, corresponding
  address, abstract, keywords. A byline broken over a gutter is not a byline.
- **Part banners**, which open a page anyway.
- **Diagrams**, set as a top-of-page float. A Mermaid flowchart at 88mm is a
  picture of a flowchart, not a flowchart.

**A wide table leaves the columns entirely.** Six columns or more already needs
the long edge of the paper at 8pt; half of that is not a smaller version of the
problem. In the Typst edition it takes a landscape page to itself and the body
returns to two columns after it.

## One thing Chrome will not do

In the HTML print edition a wide table spans the measure on a **portrait** page
rather than taking a landscape one, because named pages do not work inside a
multi-column container in Chrome. Measured four ways on one probe:

| Tried | Result |
|---|---|
| `column-span: all` + `page: wide` | Takes the landscape page and never hands it back — the references and declarations were set in two columns of a 297mm measure |
| ...plus `break-after: page` on the table | No change |
| ...plus `page: auto; break-before: page` on the element after it | No change |
| `page: wide` without `column-span: all` | The page name is ignored outright |

The full portrait measure is 180mm either way — exactly what the table has in a
one-column document — so nothing is lost that a one-column document keeps. But
**a two-column manuscript with wide tables should use `pdf = "typst"`**, which
does turn the page and return from it.

If a fifth approach works, the line to change is `body.doc-columns main
.table-frame.wide` in `paperforge.css`.

## The check that had to learn about columns

Both columns share one leading, so their baselines coincide, and reading a
printed page a line at a time reads straight across the gutter. Measured on a
two-column A4 of body text, 55 of 55 lines came back merged:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit, utramque
Menandri legam? A quibus tantum dissentio, ut,
```

— two sentences from two different columns. `verify` reads a two-column page
per word instead: a line with a word straddling a column edge is a spanning
line and is kept whole, everything else goes to the column it sits in. A
landscape page is read as it is, being one column by construction.

Stated precisely, because it matters: the page-opening comparison passes on a
two-column document either way *today*, because every heading it looks for
spans the gutter and therefore forms its own line. That is a property of the
current candidate set, not of the check. Reading the page a line at a time was
producing text that was not what the page said, and the first fix — cropping
the page into strips — cut the spanning blocks in half and reported two of
three part banners as missing.

## Related

`review-copy.md` · `front-matter.md` · `print.md` · `tables.md` · `manifest.md`
