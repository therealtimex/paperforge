# Branding and design tokens

The stylesheet is `paperforge/theme/paperforge.css` in the pipeline package;
the page shell beside it is `document.html`. Both are shared by every document, so a change made once
applies across the corpus.

This is a **document** design system — typography, print and page furniture for
long-form research documents. It is deliberately not a component library.

## The whole brand surface is seven tokens

The stylesheet ships neutral defaults; a project declares its own palette in the
manifest. The other ~290 lines of the stylesheet are structure and print
behaviour, not brand.

```toml
[defaults.brand]
navy = "#0b2545"        # carries structure
"navy-2" = "#13315c"
"navy-3" = "#1c4a80"
amber = "#c2761a"       # emphasis and annex material
"amber-soft" = "#fdf3e3"
```

`--red` is reserved for warnings; body text is `--ink` on `--paper`, page `--bg`.

Report parts (`h2.part`) get a navy banner; annex sections (`h2.annex-part`) get
amber, so a reader can tell at a glance whether they are in the report or the
annex. The same tokens apply to the print edition and to decks, so the palette
and the script-safe font stack are consistent across all three.

## Fonts are declared per language, not per brand

The serif and sans stacks come from the **profile**, because glyph coverage is a
correctness constraint rather than a preference — Georgia carries no CJK or
Arabic glyphs, and three common serifs drop Vietnamese tone marks. See
`languages.md` before changing a font.

## Components

Cover (badge, title, optional lede, metadata grid) · sticky contents sidebar
with scroll-spy · part and annex banners · callouts · table frame with
horizontal-scroll affordance · diagram figure with numbered caption · printed
contents with measured page numbers.

## Related

`languages.md` · `layout.md` · `print.md` · `manifest.md`
