# Cross-references

## What works: links between documents

Write an ordinary markdown link to the source file:

```markdown
See the source review in [Annex Section 2](./GAPS_AND_SOURCES_ANNEX.md).
```

When that annex is embedded, **every `./FILE.md` target is rewritten to an
in-document anchor**, so the same markdown stays navigable in a repo and
resolves inside a single self-contained HTML file. `verify` fails on any
`href="#…"` with no matching id, so a rewrite that misses is a build failure,
not a dead link in a published document.

Link *targets* of `./NAME.md` are fine. A link *label* showing a filename is a
lint block (`filename-label`): the reader should see "Annex Section 2", never
`GAPS_AND_SOURCES_ANNEX.md`.

## What works: referring to annex sections in prose

The profile supplies the phrase — `annex_reference` (`Annex Section`, *Phụ lục
Mục*) — and the annex numbers its own sections `1..N`. Write the reference in
that form and the contents entries line up with it.

## Anchors you control

```markdown
## Background {#context}
```

Fix an id when a reference must survive an edit to the heading text. Otherwise
the id is generated from the heading, with diacritics folded when the profile
allows.

## Not supported: numbered cross-references

There is **no `@fig-1`, `@tbl-2`, `@eq-3`**. Figure numbers are generated from
position (see `diagrams.md`) and cannot be referred to symbolically; a `{#fig-x}`
attribute on a caption line is blocked by lint because the line would print as
body text.

To point at a figure today, name it in prose ("the flow in Figure 3") and accept
that renumbering is a manual check. This is the largest known gap in the
authoring surface.

## Related

`structure.md` · `diagrams.md` · `unsupported-syntax.md` · `lint.md`
