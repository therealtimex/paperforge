# RESEARCH NOTE
## Publishing a document to a plain directory

---
**Publisher:** Paperforge Research
**Date:** August 2026

---

## CONTENTS

1. **Context**
2. **Markup**
3. **Conclusion**

---

## Context {.part}

A document reaches a reader only if it is declared publishable and then clears
the gate. This fixture exists so that path is exercised rather than assumed:
the manifest says what may ship, and lint says whether it is fit to.

The directory target copies the built artefact into a plain folder, which is
what a static host needs and what continuous integration can verify without a
RealTimeX workspace to serve from.

## Markup {.part}

This section exists so the Typst emitter renders the whole markdown grammar,
not just paragraphs. Only two fixtures declare a print edition, and both were
plain prose, so lists, tables, code blocks and callouts had never been set in
type at all — which is the exact shape of the defect that once put an
unrendered line-break tag on a printed page.

An ordered list:

1. The manifest says what may ship.
2. Lint says whether it is fit to.
3. The gate refuses anything blocking.

A bulleted list with a nested level:

- Reading edition
  - self-contained HTML
  - no network at view time
- Print edition
  - Typst, footnotes at the foot of the page

> [!NOTE]
> A callout must not split across a page, and must render in both editions.

| Stage | Refuses on |
|:---|:---|
| figures | a number disagreeing between documents |
| lint | internal machinery reaching a reader |
| verify | markup that never rendered |

The pipeline is drawn in @fig-stages, and what each gate refuses is set out in
@tbl-gates.

```mermaid
graph LR
  A[Markdown] --> B[Gates] --> C[Editions]
```

: How a document reaches a reader {#fig-stages}

A wide table — six columns or more — turns onto a landscape page in both the
print and Word editions, because the right-hand column is where sources live:

| Stage | Reads | Refuses on | Blocking | Since | Notes |
|:---|:---|:---|:---:|:---|:---|
| figures | `figures.toml` | a number disagreeing | yes | v1 | per-language forms |
| lint | the markdown | internal machinery | yes | v1 | packs are opt-in |
| verify | the built output | markup that never rendered | yes | v1 | and the editions |

: What each stage refuses {#tbl-gates}

A fenced block is set as a code sample, never executed:

```bash
paperforge all --config documents.toml
```

## Conclusion {.part}

Both editions are deliverables. A document that declares a Typst print edition
publishes the reading edition and the print edition as separate artefacts, and
this fixture declares one so that loop runs on every build rather than only on
the machine of whoever happens to be releasing.
