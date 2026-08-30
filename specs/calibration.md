# Calibration

Numbers in this pipeline that were **measured against a corpus**, not chosen.

Every one of them decides what the pipeline refuses. Changing one without
repeating the measurement changes what ships, silently, and the corpus they
were measured against is not in this repository — it was a set of real project
documents. A new maintainer cannot re-derive them by reading the code, which is
why they are listed in one place instead of only at their definitions.

**This file is gated.** `tests/unit_calibration.py` imports each constant and
fails if its value here and its value in the code disagree. The prose is not
gated, and could in principle drift from the docstring that holds the full
reasoning; the number cannot. Where the two differ, the docstring at the
definition is the record — this table is the index.

## Measured

| Constant | Value | What was measured |
|---|---|---|
| `verify.SCRIPT_FLOOR['latin']` | `80` | Stranded headings ran 22–74 characters; a genuinely short but complete section ran 91+. The floor sits in the gap, so brevity is not reported as a defect. |
| `verify.SCRIPT_FLOOR['cjk']` | `30` | The same two measurements repeated on CJK documents, where a page carries far fewer characters for the same content. A Latin floor applied to CJK reported whole correct pages as near-empty. |
| `pages.FLOOR` | `0.45` | Across every fixture, documents whose print checks work score 0.75–0.97 on word correspondence and those whose do not score 0.00–0.08. The floor sits in that gap. |
| `pages.SAMPLE` | `60` | Distinctive words taken from the source. Enough to separate the two populations above without making the check quadratic on a book. |
| `pages.WORD` | `4` | Shortest word distinctive enough to look for. Below this, common function words match by accident in any language. |
| `markdown.WIDE_DIAGRAM` | `900` | Natural width in px above which a diagram is allowed to scroll horizontally rather than shrink to fit. |
| `markdown.DIAGRAM_FLOOR` | `0.7` | Of natural width. Below ~70%, Mermaid node labels stop being legible; the figure scrolls instead. |
| `typst.RASTER_SCALE` | `3` | Of natural size, rasterising diagrams for print. Mermaid draws labels in `<foreignObject>`, which Typst does not render, so diagrams go to PNG; below 3× the type is visibly soft on paper. |

## Adding a script to `SCRIPT_FLOOR`

Measure it the way Latin was measured: what a stranded heading runs, what a
short but complete section runs, and a floor between the two. **A number fitted
to one document is not that.** A script with no measured floor is `skip`ped
with the reason rather than borrowed against another script's number — see
[0001](0001-measure-not-compose.md): a check that fires on a correct page is
worse than one that admits it has nothing to say.

## Not calibrated

These are heuristics that have never been measured against a corpus. They are
listed so nobody treats them as though they had been:

- `verify.coverage`: the 12-character minimum for a line worth probing, and the
  3-character minimum for a word worth matching. Both are inherited from the
  first version of the check. #44 and #46 were caused by arithmetic around
  them, not by the values.
- `matching.quorum`'s floors — 2 in `verify`, 3 in `pages`. The *rule* is
  gated (`min(pool, max(floor, pool - 1))`, after the same off-by-one shipped
  in three files); the floors themselves were chosen.
- `docx`: 160mm figure width, 11pt inline image height, 425 twips column
  gutter. Typographic defaults, not measurements.
- The print caps in `paperforge.css` (198mm diagram height, 470px on a deck
  slide) came from observed overflow in one corpus and are recorded in
  `docs/reference/diagrams.md`. They are in the stylesheet, so this test cannot
  reach them.
