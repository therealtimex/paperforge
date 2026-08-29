---
name: paperforge
description: Prepare, render, check and publish research documents — reports, policy briefs, annexes and presentations — from markdown. Use when starting a research project, authoring or rebuilding a report, brief or deck, or when a publication gate blocks a document. Renders and gates only; it does not write content and does not decide what a document should say.
allowed-tools: Read, Write, Edit, Bash
license: UNLICENSED
metadata:
  version: "3.8.0"
---

# Paperforge documents

Markdown is the source. Every rendered artefact — HTML, PDF, slides — is
**built** from it. The pipeline ships beside this file in `pipeline/`. A project
that uses Paperforge carries no pipeline of its own: it holds the markdown, a
`documents.toml` and a `figures.toml`, and the pipeline is pointed at it.

## Never hand-write the rendered output

A hand-built HTML edition of a report once drifted out of step with its markdown
and nobody noticed: the published document contradicted its own source. If a
rendered file needs to change, change the markdown and rebuild. If the
*rendering* needs to change, change the theme — never the output.

## When to use what

| Task | Read |
|---|---|
| Start a new research project | [references/starting-a-project.md](references/starting-a-project.md) |
| Brief a research team on a project's rules | [references/brief.md](references/brief.md) |
| Run or debug a pipeline stage | [references/commands.md](references/commands.md) |
| Configure a project, or add a language edition | [references/manifest.md](references/manifest.md) |
| Choose report vs brief vs deck, or declare a new type | [references/document-types.md](references/document-types.md) |
| Divide a document into parts, or embed an annex | [references/structure.md](references/structure.md) |
| Split a long document into chapters | [references/assembling.md](references/assembling.md) |
| Set a book: recto chapters, running heads, a trim | [references/books.md](references/books.md) |
| Write a manuscript: authors, abstract, declarations | [references/front-matter.md](references/front-matter.md) |
| Send a paper out for blind review | [references/review-copy.md](references/review-copy.md) |
| Set a manuscript in two columns | [references/columns.md](references/columns.md) |
| Write a table, or a table cell with line breaks | [references/tables.md](references/tables.md) |
| Add a diagram | [references/diagrams.md](references/diagrams.md) |
| Add a callout or an aside | [references/callouts.md](references/callouts.md) |
| Add citations and a bibliography | [references/citations.md](references/citations.md) |
| Write maths | [references/maths.md](references/maths.md) |
| Link between documents, or refer to a figure | [references/cross-references.md](references/cross-references.md) |
| Build a presentation | [references/decks.md](references/decks.md) |
| Work in a new language or script | [references/languages.md](references/languages.md) |
| Change the palette, fonts or page furniture | [references/branding.md](references/branding.md) |
| Fix responsiveness or the contents sidebar | [references/layout.md](references/layout.md) |
| Fix page breaks, page numbers or the PDF | [references/print.md](references/print.md) |
| Deliver something the reader can edit | [references/docx.md](references/docx.md) |
| Keep a number consistent across documents | [references/figures.md](references/figures.md) |
| Say what a paragraph is for, and keep it true | [references/claims.md](references/claims.md) |
| See a document's structure and argument at a glance | [references/papermap.md](references/papermap.md) |
| Understand why lint blocked a document | [references/lint.md](references/lint.md) |
| Understand a verify failure | [references/verify.md](references/verify.md) |
| Publish, or fix a stale artifact link | [references/publishing.md](references/publishing.md) |
| Compare two runs, or recover an overwritten draft | [references/provenance.md](references/provenance.md) |
| A construct printed literally instead of rendering | [references/unsupported-syntax.md](references/unsupported-syntax.md) |

## Running it

**The command is not on `PATH`.** It ships at `pipeline/bin/paperforge`, and a
Paperforge checkout has it at `bin/paperforge`. Invoke it by path with
`--config <project>/documents.toml`, or ask the user to alias it. It is deliberately not abbreviated to `pf`, which is the
BSD/macOS packet filter.

```bash
paperforge all       # figures -> lint -> build -> verify -> publish
paperforge status    # what is built, linked and published
```

Scope with `--only <source|output|collection>`; point at a project with
`--config path/to/documents.toml`.

## Essentials

Enough to write a document without opening a reference file:

````markdown
# POLICY RESEARCH REPORT             the kind (badge)
## Strategic technologies to 2030    the title
**Publisher:** Ministry of X         metadata row

## CONTENTS                          the head ends here

## PART I: Context {.part}           a part: new page, banner, contents entry

> [!WARNING]                         a callout
> Targets are political, not forecast.

| Instrument | Status |                a table needs its alignment row
|---|---|
| Decision 21 | In force<br>*(2026)* | <br> is the only HTML tag allowed

Maths is **Typst syntax**: $a/b$, not $\frac{a}{b}$.
Citations are [@key].

```mermaid
flowchart LR
  A --> B
```
````

Footnotes (`[^1]`) and caption lines (`: Caption {#fig-1}`) are **not rendered**
and are blocked by lint — they would print as body text. There is no `@fig-1`
cross-reference.

## Three things not to work around

**The pipeline renders and gates; it does not author.** A brief or a deck derived
from a report must be *written*. Slicing a long report into slides produces
noise — someone has to choose the narrative.

**When lint blocks, fix the markdown.** It blocks on internal machinery reaching
a reader. A document is publishable only if declared in `documents.toml` with
`publish = true`; process records belong under `[internal]`. If a document
genuinely should ship, that is a manifest edit and a deliberate decision, not a
lint waiver.

**When verify fails, it found a defect, not a nit.** "missing lines" means
content never reached the output; "external refs" means the document will not
open offline; a cross-edition disagreement means the HTML and the PDF say
different things. Confirm with the user before publishing anything
outward-facing for the first time.

## Requirements

`python3`, headless Chrome (diagrams, page measurement, layout checks),
`pdfplumber`, `typst` (print editions, maths, citations), and `realtimex-pp-cli`
for the default publish target. Chrome and the Mermaid CDN are **build-time
only** — published documents carry no scripts or network dependencies.
