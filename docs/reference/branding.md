# Branding and design tokens

The tokens are declared in `paperforge/palette.py`, and every surface is filled
from that one table: the two stylesheets' `:root` blocks, the Typst emitter and
the Word emitter. The stylesheet itself is `paperforge/theme/paperforge.css` and
the page shell beside it is `document.html`. All of it is shared by every
document, so a change made once applies across the corpus.

This is a **document** design system — typography, print and page furniture for
long-form research documents. It is deliberately not a component library.

## The palette

Twenty colour tokens. The table ships neutral defaults; a project declares its
own in the manifest, and the build emits them *after* the theme so they win.
Every token the stylesheet consumes is overridable, and a token it does not know
is carried through rather than dropped:

> **Not yet the whole brand surface.** The stylesheets also paint with 56 colour
> literals across 33 distinct values that are not tokens, including the entire
> cover — a fourth palette, darker than the document's. This page used to claim
> the tokens *were* the whole surface, and that claim was wrong before the count
> in it was. See #25.

```toml
[defaults.brand]
navy   = "#5b2333"      # carries structure: parts, table headers, links
"navy-2" = "#7a3145"
"navy-3" = "#9a4058"
"navy-soft" = "#efe2e6"   # diagram node fills
amber  = "#2f6d5b"      # emphasis, annex material, note callouts
"amber-soft" = "#eaf3f0"
"amber-line" = "#bcd8cd"
red    = "#8c2f39"      # warning callouts
"red-soft" = "#f9ecee"
"red-line" = "#e3c3c7"
green  = "#3f6d2f"      # tip callouts
"green-soft" = "#eef5e9"
"green-line" = "#cfe0c4"
ink    = "#231f20"      # body text
"ink-soft" = "#4a5568"
muted  = "#7a736b"
bg     = "#f7f4ef"      # page behind the sheet
paper  = "#fffdf9"      # the sheet
line   = "#e3ddd4"
"line-soft" = "#eef1f6"
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
| Palette | 19 of 20 | 16 | 8 | 7 |
| Type | yes | yes | yes | first real family in the stack |
| Logo | yes | yes | title slide | yes, rasterised |

- **Reading** consumes every token but `navy-soft`, which only diagrams use.
- **Print** takes `navy` ×3, `ink`, `ink-soft`, `muted`, `line` and all nine
  callout colours.
- **Deck** has fewer surfaces to paint: no tables, no callouts, no captions.
- **Word** takes `navy`, `ink`, `ink-soft`, `muted` and the three callout rules.
  It cannot draw a callout's fill without fighting its own `Intense Quote`
  style, so it says the same thing in the text colour.

**Diagrams** take seven tokens across twelve Mermaid variables, and they take
them in every edition, because a diagram is rendered once and then placed.

Three colours are **screen-only**, and every one of them is about the sheet
rather than about anything printed on it:

- `bg` is the colour behind the sheet, and paper has no behind.
- `paper` is the sheet, which a printer supplies — and most cannot full-bleed.
- `shadow` is the lift under the sheet, the same absence.

> `red` and `line-soft` were listed here too, each justified by a feature that
> did not exist rather than by the paper: the print emitter could not tell a
> warning callout from a note, and drew no soft rules. A limitation attributed
> to the medium ages into a property of the medium. Both reach print now.

Word takes a single face rather than a fallback list, and CSS system keywords —
`-apple-system`, `system-ui` — are skipped, because naming one in a `.docx`
gives Word a font it cannot find and a document that renders differently on
every machine.

Diagrams take eleven tokens through `palette.MERMAID`, which writes the mapping
onto Mermaid's own vocabulary down once — see `diagrams.md`. They used to take
none of it and render in a private palette; the diagram cache now keys on the
palette as well as the sources, because it did not, and a rebuild after a brand
change served the old colours back while reporting success.

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

## Callouts

Three colours per variant — the rule down the edge, the fill behind, the
hairline around — and all nine are tokens:

| | Rule | Fill | Hairline |
|---|---|---|---|
| note | `amber` | `amber-soft` | `amber-line` |
| warning | `red` | `red-soft` | `red-line` |
| tip | `green` | `green-soft` | `green-line` |

`palette.CALLOUTS` is the one place this is written down, and all three editions
read it, so a warning is a warning everywhere. See `callouts.md`.

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
