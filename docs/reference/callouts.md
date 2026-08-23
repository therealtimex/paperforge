# Callouts

A blockquote whose first line is `[!KIND]`:

```markdown
> [!NOTE]
> Legal basis is Decision 21/2026/QĐ-TTg, in force from 1 July 2026.

> [!WARNING]
> Both page numbering and the pagination check read the PDF's text back.
```

The kind becomes a CSS class, lower-cased. The stylesheet gives `warning` a red
left rule on a pale red ground and `tip` a green one; **any other kind, including
`note`, renders as the default amber-ruled callout**. Nothing errors on an
unknown kind — it simply looks like a note — so treat `note`, `warning` and `tip`
as the vocabulary that actually reads differently.

A blockquote with no `[!KIND]` marker is still rendered as a callout, not as a
quotation. There is no separate blockquote style.

Callout bodies take the full block grammar: paragraphs, lists, tables, inline
maths and citations all work inside one.

In print, callouts set `break-inside: avoid` — a callout never splits across a
page.

## Related

`tables.md` · `branding.md` (the `--amber` and `--red` tokens) · `print.md`
