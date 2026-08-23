# Tables

Standard pipe tables. The alignment row may use `:---`, `---:` and `:---:`.

```markdown
| Instrument | Issued | Status |
|---|---|---|
| Decision 21 | 2026-04-30 | **In force** |
```

A table needs its alignment row: a line starting with `|` is only read as a
table when the next line matches `^\|[\s:*|-]+\|?$`.

## Line breaks inside a cell

A cell cannot contain a list or a paragraph break. Use `<br>` — the one HTML tag
the renderer lets through:

```markdown
| - First provision.<br>- Second provision.<br>- Third. | **VERIFIED**<br>*(Political mandate)* |
```

Both editions render this as a line break, and the dashes stay literal text in
both. Do not expect a bullet: a cell beginning `- ` is *not* a list.

> This is where the two editions drifted. The Typst emitter escaped `<` and `>`
> before it tried to convert the tag, so the replace could never match and
> `<br>` was set as visible text — and because `TRỊ<br>(Verified` is one
> unbreakable token it overflowed its column and printed on top of the next one.
> `verify` now reports raw markup that reached either rendered page.

## Wide tables

**Wide tables scroll; they are never restructured.** These are comparison
matrices, where reading across the row *is* the content, so stacking them into
cards on mobile would destroy the comparison to avoid a swipe. The reading
edition puts a measured edge fade and a swipe hint only where content really is
cut off; in print the table lays flat and scales to fit.

Six columns on A4 leave roughly 25mm each, too narrow to justify — tables set
ragged right for that reason while body text stays justified.

## Density

`build` reports a deck table beyond 7 rows or 5 columns: it will not read from
the back of a room. Reports carry no such limit.

## Not supported

A caption line — `: Table caption {#tbl-x}` — is **not rendered**; it would
print as a stray paragraph, so lint blocks it. See `unsupported-syntax.md`.

## Related

`unsupported-syntax.md` · `print.md` · `layout.md` (scroll affordance)
