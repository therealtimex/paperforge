# Document structure

How a source file is divided, and how the renderer learns where the divisions
are. This is the one authoring decision that changes every edition: a part opens
a new page in print, gets a banner in the reading edition, and becomes a
top-level contents entry.

## The head

Everything above the contents heading is the head, and it is set as a cover
rather than as body text.

```markdown
# POLICY RESEARCH REPORT          <- the kind, shown as a badge
## Strategic technologies to 2030 <- the title
**Publisher:** Ministry of X      <- metadata, rendered as a two-column grid
**Date:** August 2026

## CONTENTS                       <- the head ends here
```

`# ` is the kind, `## ` is the title, and any `**Key:** value` line becomes a
metadata row. A bare `**LABEL:**` line above the title is treated as a label
introducing it and dropped. Anything else in the head survives as a lede.

The head ends at the profile's `contents_heading` (`CONTENTS`, `MỤC LỤC`, …).
If the document has none, it ends at the first `---` rule. Both editions split
at the same place — a mismatch here once put the whole metadata block into the
body of the PDF.

## Parts

A `##` heading may open a **part**: new page in print, banner in HTML, top-level
contents entry. Three ways to mark one, explicit first:

```markdown
## PART III: International experience {.part}   mark this heading as a part
## Background {#context}                        fix the anchor id
## Appendix {.no-part}                          suppress a pattern that matched
```

Without an attribute, the profile's `part_banner` pattern decides
(`^(PART|CONCLUSION|CONTENTS|\d+\.\s*EXECUTIVE)` in `en`). Explicit always wins,
in both directions, so a project can carry structure no profile knows about.

A profile that matches nothing is **reported at build time** — "no part headings
detected in 8 top-level headings" — because silently producing a document with
no structure is the failure this pipeline exists to prevent. Scaffolded projects
mark parts explicitly for exactly this reason.

## Anchors

Heading ids are generated from the text, diacritics folded when the profile
allows it (`PHẦN III` → `phan-iii`). Fix one with `{#id}` when a cross-reference
has to survive an edit to the heading. `verify` fails on any `href="#…"` with no
matching id.

## The annex

An annex is a separate markdown file, embedded into its parent at build time:

```toml
annex = "GAPS_AND_SOURCES_ANNEX.md"
annex_label = "Annex: sources and benchmarks"   # sidebar entry
```

Its `##` sections all open pages, its figures number separately (`Figure A1`),
its banners are amber rather than navy, and every `./FILE.md` link in the parent
is rewritten to an in-document anchor — see `cross-references.md`. The annex is
embedded, never published on its own.

## Related

`document-types.md` (what a type implies) · `cross-references.md` ·
`languages.md` (where `part_banner` comes from) · `print.md` (page breaks)
