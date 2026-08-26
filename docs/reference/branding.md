# Branding and design tokens

The tokens are declared in `paperforge/palette.py`, and every surface is filled
from that one table: the two stylesheets' `:root` blocks, the Typst emitter and
the Word emitter. The stylesheet itself is `paperforge/theme/paperforge.css` and
the page shell beside it is `document.html`. All of it is shared by every
document, so a change made once applies across the corpus.

This is a **document** design system — typography, print and page furniture for
long-form research documents. It is deliberately not a component library.

## The palette

Thirteen colour tokens, and they are the whole brand surface — the remaining
~290 lines of the stylesheet are structure and print behaviour. The table ships
neutral defaults; a project declares its own in the manifest, and the build
emits them *after* the theme so they win. Every token the stylesheet consumes is
overridable, and a token it does not know is carried through rather than
dropped:

```toml
[defaults.brand]
navy   = "#5b2333"      # carries structure: parts, table headers, links
"navy-2" = "#7a3145"
"navy-3" = "#9a4058"
amber  = "#2f6d5b"      # emphasis and annex material
"amber-soft" = "#eaf3f0"
ink    = "#231f20"      # body text
"ink-soft" = "#4a5568"
muted  = "#7a736b"
bg     = "#f7f4ef"      # page behind the sheet
paper  = "#fffdf9"      # the sheet
line   = "#e3ddd4"
"line-soft" = "#eef1f6"
red    = "#8c2f39"      # reserved for warnings
shadow = "0 1px 3px rgba(0,0,0,.06)"
```

## Type

A profile supplies `serif` and `sans` because glyph coverage is a correctness
constraint — Georgia carries no CJK or Arabic, and three common serifs drop
Vietnamese tone marks. A project may override either from the manifest:

```toml
[defaults.brand]
serif = "Palatino, Georgia, serif"
```

**Naming your own face makes coverage your problem.** Render the test string in
`languages.md` before shipping one.

## A project mark

```toml
[defaults]
logo = "brand/mark.svg"
```

Placed on the cover of the reading and print editions, on the deck's title
slide, and at the head of the Word file. An SVG is inlined as markup and any
other format as a data URI, so the document still opens offline — a mark
fetched from a URL would be the one network dependency in a document whose
whole claim is that it has none. Word cannot place an SVG, so one is rasterised
the same way diagrams are; a project keeps one copy of its own mark.

## What reaches which edition

| | Reading | Print (Typst) | Deck | Word |
|---|---|---|---|---|
| Palette | all thirteen | nine | all thirteen | five |
| Type | yes | yes | yes | first real family in the stack |
| Logo | yes | yes | title slide | yes, rasterised |

Print takes `navy` ×3, `amber`, `amber-soft`, `ink`, `ink-soft`, `muted` and
`line`. Word takes `navy`, `ink`, `amber`, `muted` and `ink-soft`.

Four colours are **screen-only**, and the reason is the paper rather than the
emitter:

- `bg` is the colour behind the sheet, and paper has no behind.
- `paper` is the sheet, which a printer supplies — and most cannot full-bleed.
- `shadow` is the lift under the sheet, the same absence.
- `line-soft` is consumed only by rules the print edition does not draw.

`red` is the exception, and it is ours: it colours the rule beside a warning
callout, and the print emitter does not distinguish a warning from a note
(#21). It is listed as screen-only pointing at that issue rather than described
as a screen colour, which it is not.

Word takes a single face rather than a fallback list, and CSS system keywords —
`-apple-system`, `system-ui` — are skipped, because naming one in a `.docx`
gives Word a font it cannot find and a document that renders differently on
every machine.

Diagrams take none of it: `diagrams.py` renders Mermaid in a third palette
that no project can change (#22).

> The deck used to receive **none** of this. `deck.css` shipped one project's
> brand colours in its own `:root`, so every other project's slides came out
> wearing them and nothing said so — the report stylesheet was neutralised
> during the extraction and the deck was missed.
>
> That was fixed by appending the project's palette after the theme, which left
> the copy in place. The copy is the defect: both `:root` blocks are now filled
> from `palette.py` at build time and there is nothing left to keep in step.

Until the same treatment reached the emitters, a branded document printed
mostly in Paperforge's colours. Measured on the English fixture with all
thirteen tokens declared, three reached the PDF and two reached the `.docx`;
the most frequent non-black colour on the printed page, at 818 occurrences, was
`#6b7789` — the shipped `muted`, in every running head and metadata label, on a
document that had overridden it. A colour written as a literal in an emitter is
correct by default and unbrandable forever, and it reads as finished code
either way, which is why `tests/unit_palette.py` fails on the *form* — any hex
literal in either emitter — rather than on a colour going missing.

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
