# Diagrams

A fenced `mermaid` block becomes a numbered figure. Nothing else in a fenced
block is rendered — any other language is set as a code sample.

````markdown
```mermaid
flowchart LR
  A[Technology attaché] --> B[Transfer agreement]
```
````

## Captions

Without a caption line the caption is the profile's `figure` label with the
figure's position: `Figure 1`, `Sơ đồ 1`. Inside an annex it uses
`annex_figure` — `Figure A1`.

To write the caption yourself, and to be able to refer to the figure by number,
put a caption line after the block:

```markdown
: Robot density by country, 2025 {#fig-density}
```

which renders as *Figure 3. Robot density by country, 2025* and makes
`@fig-density` resolve to **Figure 3** anywhere in the document. See
`cross-references.md`.

## Rendering

Diagrams are **pre-rendered at build time** to inline SVG. Nothing is fetched
when the document is opened, so it works offline, and this avoids a real defect:
with `startOnLoad` the library reused one SVG id across diagrams and emitted
several without a `viewBox`, drawing them on top of each other.

For the print edition the same diagrams are **rasterised through Chrome at 3×**
rather than embedded as SVG. Mermaid puts every node label inside
`<foreignObject>`, which Typst does not draw: embedding the SVG directly
produced boxes and arrows with no text at all.

## Sizing

A wide diagram is never shrunk below ~70% of its natural width — it scrolls
horizontally instead of turning illegible. In print it scales to fit, capped at
**198mm tall**: A4 leaves ~249mm of printable height, and a diagram taller than
the page cannot honour `break-inside: avoid`, so it splits and strands an empty
frame on the page before. Three of ten diagrams in one report printed at
255–334mm before the cap.

Deck diagrams are capped at 470px so they fill a slide.

## Related

`figures.md` (the numeric-consistency gate — a different thing) ·
`unsupported-syntax.md` · `print.md` · `decks.md`
