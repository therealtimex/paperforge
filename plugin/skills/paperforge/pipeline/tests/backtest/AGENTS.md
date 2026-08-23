# Phát triển các công nghệ chiến lược đến năm 2030

Research project. Markdown is the source; every rendered artefact is **built**
from it and must never be hand-edited.

## Working here

```bash
pf status      # what is built, linked, published
pf all         # figures -> lint -> build -> verify -> publish
pf all --only <source.md>
```

- `documents.toml` decides what may be published. Process records — peer review,
  editorial notes, approvals — belong under `[internal]` and never ship.
- `figures.toml` holds values the documents must agree on. Add a figure the
  moment it appears in more than one place.
- A document becomes publishable by a deliberate edit to `publish`, which is
  also the moment someone decides it is ready.
- If lint blocks, fix the markdown. Do not bypass the gate.

Skeleton sections are marked `{.part}` so structure is explicit and does not
depend on matching a heading pattern. Keep the marker when you rewrite them.
