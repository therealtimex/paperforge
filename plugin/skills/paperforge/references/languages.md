# Languages and scripts

**Nothing in the pipeline hard-codes a language.** A profile supplies the
interface strings, the labels, and the structural vocabulary the renderer
matches on.

`vi`, `en`, `zh` and `ar` ship today — starting points, not gatekeepers.

## Three ways to declare conventions, in order of independence

1. **Mark structure in the markdown.** `{.part}`, `{#id}`, `{.no-part}`.
   Explicit always wins, so a project can carry structure no profile knows
   about. See `structure.md`.
2. **Supply your own profile.** `profile_file = "profile.toml"` beside the
   sources, optionally layered over a shipped one (`profile = "none"` if none
   fits). Starting a new language needs no pipeline release — an Indonesian
   project was built this way with no `id` profile in the tool.
3. **Name a shipped profile.** `profile = "vi"`.

A declaration that matches nothing is reported at build time, because silently
producing a document with no structure is the failure this pipeline exists to
prevent.

## What a profile carries

```toml
lang = "en"
script = "latin"
direction = "ltr"
fold_diacritics = true        # PHẦN -> phan; false for Arabic, Thai, Devanagari

[fonts]
serif = 'Georgia,"Noto Serif","Times New Roman",Times,serif'
sans  = '-apple-system,…'

[labels]     # figure, annex_figure, annex_badge, references, document, deck …
[ui]         # contents_button, print_button, nav_title, scroll_hint, footer_note
[structure]  # contents_heading, part_banner, annex_word, annex_anchor, annex_reference
[scaffold]   # date_format and the skeleton vocabulary used by init
```

Structural words are written in **normalised form** (case-folded, diacritics
removed) because that is how they are matched. Numbering shape is part of it:
"PART III" and "第三部分" share no structure, so a profile supplies the pattern,
not just the word.

Facts about a *project* — publisher, footer note, annex sidebar label — live in
the manifest instead, because they change between projects that share a language.

## What stays with the pipeline

Diacritic folding, combining marks, font glyph coverage, direction and CJK word
counting. A research team should not have to know that Python's `\w` excludes
Thai vowel signs.

Right-to-left profiles mirror the sidebar, rules, banners, list markers, table
alignment and the scroll affordance.

## Typography can be a correctness constraint

Several common serif faces silently drop Vietnamese tone marks on `Ơ` and `Ư` at
display sizes: **Palatino, Iowan Old Style and Charter** render *TĂNG TRƯỞNG* as
*TĂNG TRƯƠNG*. Nothing errors; the words change meaning.

Verified safe: **Georgia, Noto Serif, Times New Roman**. Before changing a font,
render this at display size and confirm every mark survives:

```
TĂNG TRƯỞNG ĐỊNH HƯỚNG ĐỘT PHÁ CHỦ QUYỀN SỐ
```

Extraction of Vietnamese text from generated PDFs decomposes `Đ` to `Ð`, so any
tooling that matches document text must normalise both.

## Proof it stays language-neutral

`paperforge selftest` builds the English fixture end to end; Chinese,
Indonesian, bilingual and citation fixtures ship beside it. A second profile is
the only real proof that no assumption has crept back in — English already
caught one: a page-number audit demanding four matching words, so a short title
such as "PART I: CONTEXT" could never pass in any language.

## Related

`structure.md` · `manifest.md` · `figures.md` · `branding.md`
