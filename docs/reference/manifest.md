# The manifest: documents.toml

The manifest is the publication allowlist and the per-document settings. A
document ships only if it appears here with `publish = true`.

Located via `--config`, `$PAPERFORGE_CONFIG`, or the nearest `documents.toml`
walking up from the working directory.

```toml
[defaults]
workspace = "editor"          # RealTimeX workspace whose artifacts/ dir is served
profile = "vi"                # language and document conventions
organisation = "Paperforge"  # short form, shown in the top bar
publisher = "…"               # full line, shown on the cover
footer_note = "…"
paper = "A4"

[defaults.brand]              # see branding.md — seven tokens, the whole surface
navy = "#0b2545"

[[collection]]
slug = "vn-strategic-tech-2030"
root = "vietnam/vn-strategic-tech-2030"
profile = "vi"
figures = "figures.toml"

  [[collection.document]]
  id = "report"
  type = "report"
  page_numbers = true
  pdf = "typst"               # also build and publish a print edition

    [collection.document.vi]
    source = "bao-cao.md"
    annex  = "annex.vi.md"
    publish = true

    [collection.document.en]
    source = "report.md"
    publish = false           # translation in progress

[lint]
packs = ["realtimex-loops"]

[internal]
files = ["PEER_REVIEW_EVALUATION.md", "EDITORIAL_REPORT.md"]
reason = "process records: review, editorial notes, approvals"
```

## One work, several language editions

Language belongs to an **edition** of a work, not to a separate collection. A
sub-table carrying its own `source` is an edition; anything else is a plain
setting, so shared keys are declared once. The edition key selects the profile.

A document with `source` at the top level is the flat, single-language form and
keeps working unchanged.

This is also what makes the figures gate correct across languages — Vietnamese
writes `50.000` where English writes `50,000`. See `figures.md`.

## Document keys

| Key | Effect |
|---|---|
| `type` | Layout and defaults — see `document-types.md` |
| `source`, `output` | Input markdown, output HTML (defaults to the source's name) |
| `annex` | Embedded inline, never published alone |
| `annex_label` | Sidebar entry for the annex |
| `title_kind` | Badge text when the source has no `# ` line |
| `contents_heading` | Usually from the profile; enables sidebar and page numbers |
| `page_numbers` | Measured printed page numbers on the contents |
| `pdf = "typst"` | Print edition typeset by Typst — footnotes at the foot of the page, running heads |
| `pdf = "chrome"` | Print edition from the reading edition's own layout, including landscape wide tables |
| `docx = true` | Word edition — a working document the reader can edit; see `docx.md` |
| `bibliography`, `citation_style` | See `citations.md` |
| `publish` | The allowlist flag |
| `request` | The request this work answers; snapshotted with every run |

A print edition **publishes only if it is declared**. Before that was true, any
`.pdf` sitting beside the HTML was shipped, so a file appearing on disk could
reach a public URL without anyone deciding — which is the one thing the manifest
exists to prevent. A stray PDF is now reported and left alone.

Choose `typst` when the document needs real footnotes and running heads;
`chrome` when what you want published is exactly what a reader sees on screen.
`chrome` is also the only one that handles wide tables today — see `print.md`.

## `[internal]`

Process records — peer review, editorial notes, approvals. Listed explicitly so
the intent is on the record, and so adding one to the allowlist has to be a
deliberate edit. These can never be published by accident.

## Related

`document-types.md` · `languages.md` · `branding.md` · `lint.md` · `publishing.md`
