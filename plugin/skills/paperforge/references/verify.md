# The verify gate

What `paperforge verify` checks, and why each check exists. Most were added
after a real defect got past everything else.

## Within one document

- **Markup balance** — no unclosed or crossed tags.
- **Coverage** — every substantive markdown line survives into the output.
- **Anchors** — every internal `href="#…"` resolves.
- **Self-containment** — no `http(s)://` reference in the built file.
- **Layout** — no horizontal overflow at 1440 / 1024 / 768 / 390px, nothing
  clipped in print.
- **Raw markup leaks** — HTML tags, real HTML entities, `**`, or Typst escapes
  that reached the rendered page in *either* edition.
- **Near-empty printed pages** — a stranded heading or an orphaned frame.
- **Page-number audit** — re-checks each measured number against the PDF
  *without reusing the build's matching*; a number is accepted only if the
  entry's own wording is found where it claims to be.

## Between the two editions

Two independent emitters render the same source, and they drifted within a day
of the second being added: parts opened a page in the HTML and ran on mid-page
in the PDF, the annex likewise, and figure captions gained a duplicate label.
None of it was caught, **because every other gate looks at one edition at a time
and each was individually valid.**

So `verify` also compares them: the same headings must open a page, and both
must carry the same figures.

```
editions: 18 page-opening headings agree, 10 figures in both
```

The contents repeats every heading, so pages carrying several candidates are
excluded outright — the same trap that caught the page-number measurement.

## Reading the output

A clean run states what it confirmed, not just that it passed:

```
      editions: 18 page-opening headings agree, 10 figures in both
      page numbers: 46 confirmed, 1 untestable, 0 wrong
  report.html                            ok
```

"untestable" is not "passed": it means the check declined, with a reason. See
the `ToUnicode` limitation in `print.md`.

## Related

`print.md` · `layout.md` · `lint.md` · `unsupported-syntax.md`
