# Review copies

Most journals want two artefacts from one manuscript: the submission, and a
blind copy that is line-numbered, anonymised and double-spaced. Two documents
may share one source, so both come from the same markdown:

```toml
  [[collection.document]]
  id = "submission"
  source = "paper.md"
  pdf = "typst"
  docx = true
  publish = true

  [[collection.document]]
  id = "review"
  source = "paper.md"           # the same source
  output = "paper-review.html"
  review = true
  pdf = "typst"
  docx = true
  publish = false
```

## What `review = true` does

**Anonymises the front matter.** The byline, affiliations and corresponding
address are removed, and so is the funding statement — a funder identifies a
group as reliably as a name does, and so does an acknowledgements list. The
abstract, keywords and the remaining declarations stay, because a reviewer
needs them. A localised notice takes their place: *"Author details removed for
blind review."*

This is not a redaction of the rendered page. The identifying fields never
reach an emitter, so there is nothing left in the file to recover.

**Numbers the lines**, so a reviewer can write "line 214".

**Doubles the leading**, by long convention.

## One difference between the editions, stated rather than hidden

CSS counts elements, not wrapped lines, so the reading edition **numbers
paragraphs**. True line numbers are in the print and Word editions — Typst
numbers lines natively, and Word has section line numbering.

A reviewer quoting "line 214" must therefore be reading the PDF or the Word
file, not the HTML. Send one of those.

## Related

`front-matter.md` · `manifest.md` · `docx.md` · `print.md`
