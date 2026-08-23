# Citations and bibliography

```markdown
The mandate is explicit [@nq57], and the targets follow [@qd21; @qd1493].
```

Declare the BibTeX file per document in the manifest:

```toml
bibliography = "references.bib"
citation_style = "apa"        # any style Typst ships
```

The reference list is appended automatically, under the profile's `references`
label, and is omitted entirely if the document cites nothing.

## One formatter, two editions

Typst formats both the in-text markers and the reference list from the `.bib`,
for **both** editions — so no citation style is reimplemented and the two
editions cannot disagree. The reading edition gets this through Typst's HTML
export, which is explicitly experimental, so it is used for nothing but the
citations and the list, and the parser **raises rather than guessing** if that
output changes shape.

The language is passed through, so month names and the list heading are
localised rather than defaulting to English.

## Back-tested

Against a real Vietnamese reference list: 14 entries, mostly legal instruments
with institutional authors and no DOIs. Diacritics survive, corporate authors
are handled, and same-author disambiguation is automatic (`2026a`, `2026b`).

## A known upstream behaviour

APA formats `@legislation` and `@misc` as "(year, month day)", so an entry
carrying only a year renders `(2026,).` — with a stray comma. `@report` has no
such template.

The build **reports** affected entries rather than correcting them:

```
bibliography: 'nq57' is @legislation with a year but no month; APA emits a
stray comma. Use @report, or give a full date.
```

Whether to add a full date or change the entry type is the author's call.

## Related

`maths.md` (the other Typst-backed feature) · `manifest.md` · `print.md`
