# Callouts

A blockquote whose first line is `[!KIND]`:

```markdown
> [!NOTE]
> Legal basis is Decision 21/2026/QĐ-TTg, in force from 1 July 2026.

> [!WARNING]
> Both page numbering and the pagination check read the PDF's text back.
```

`note`, `warning` and `tip` are the vocabulary that reads differently: amber,
red and green respectively, each as a rule down the left edge, a fill behind
and a hairline around. **Any other kind renders as a note** in every edition.
Nothing errors on an unknown kind — it simply looks like a note.

All three editions honour the kind. The print and Word emitters used to match
`[!WARNING]`, strip it and draw a note, so a warning was a warning only on
screen; that was a limitation of those emitters, one line above the block that
needed it, and not of Typst or Word. The nine colours come from
`palette.CALLOUTS`, so a project that brands `red` brands its warnings
everywhere.

Word cannot draw the fill without fighting its own `Intense Quote` style, so it
says the same thing in the text colour instead.

A blockquote with no `[!KIND]` marker is still rendered as a callout, not as a
quotation. There is no separate blockquote style.

Callout bodies take the full block grammar: paragraphs, lists, tables, inline
maths and citations all work inside one.

In print, callouts set `break-inside: avoid` — a callout never splits across a
page.

## Related

`tables.md` · `branding.md` (the nine callout tokens) · `print.md`
