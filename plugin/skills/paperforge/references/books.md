# Setting a book

A book is a report that has been made into an object. It is bound, so it has an
inside edge; its leaves have two sides; and it is not A4.

```toml
[[collection.document]]
type    = "book"
source  = "book.md"                   # cover, contents
include = ["ch01.md", "ch02.md", "ch03.md"]
annex   = "appendix.md"
pdf     = "typst"
```

`type = "book"` carries the whole binding. Nothing else in the manifest repeats
any of it — that is what naming the type is for.

| It sets | Because |
|---|---|
| `binding = true` | the four conventions below |
| `trim = "royal"` | 156×234mm, the academic monograph |
| `page_numbers`, `layout = "report"` | a book on screen is a long report |

## Scaffolding one

```bash
paperforge init --into ~/research/monograph --slug monograph \
                --title "..." --languages en --publications book,annex
```

That writes the cover and contents as `monograph-book.md`, three chapters as
`monograph-ch01.md` … `ch03.md`, and the manifest wiring them together with
`include`. **Chapters are separate files from the start** — a scaffold is the
shape everyone copies, and one that put a book in a single markdown file would
teach the opposite of `assembling.md`.

`pdf = "typst"` is written into the manifest, because a book has no bound
edition without it.

A freshly scaffolded book comes out **mostly blank leaves** — five of twelve.
Each stub chapter is a page long and ends on a recto, so every opening skips
one. That is the convention working rather than a defect, and it disappears as
the chapters fill.

## The four conventions

**Mirrored margins.** A page bound at its inside edge loses part of that edge to
the gutter, so the inside margin is wider than the outside one — 22mm against
16mm. The inside edge alternates between left and right as the leaves turn,
which is why they are described as mirrored rather than as left and right.

**Chapters open recto.** A reader turning to a new chapter should find it under
their right hand. Whenever the previous chapter ends on a recto, that costs a
leaf.

**The skipped leaf is bare.** No folio, no running head. A page carrying a page
number and nothing else is not read as blank; it is read as a page whose text
has gone missing. It still *counts* — pagination runs through it — so folios in
a bound edition skip: 5, then 7.

**Roman front matter, arabic from chapter one.** Front matter is written last
and its length is not known while the book is being set; numbering it separately
means adding two pages of preface does not renumber the book. The restart lands
on a recto, so odd folios sit on right-hand leaves for the whole book. The
boundary is the first `##` heading after the contents; a document with no
contents section has no front matter to number apart and numbers from 1
throughout.

## Running heads

The verso names the book, the recto names the chapter, so one spread names both.
A page a chapter opens carries none — a running head above a chapter title
repeats it.

Parity is taken from the physical leaf rather than the printed folio. The folio
restarts at the main matter, and taking parity from it would put versos on the
right for the whole of the front matter.

The head follows the **chapters**, not every `##`. A top-level heading marked
`{.no-part}` opens no page, so it does not become a running head and does not
take one away from the leaf its text runs on to — the reader is still in the
chapter they were in. See `structure.md` for what `{.no-part}` is for.

## Trims

`trim` lives on the type, not the document:

```toml
[types.thesis]
extends = "book"
trim = "a4"          # a thesis is bound, and bound A4
```

| `trim` | mm | |
|---|---|---|
| `royal` | 156×234 | the academic monograph — the `book` default |
| `b5` | 176×250 | its common European alternative |
| `a5` | 148×210 | |
| `a4` | 210×297 | a thesis, a bound manual — the default everywhere else |

Anything else is refused, with the list. A trim is a decision made with a
printer, and accepting any two numbers invites one made with nobody.

The trim sets the measure, not the other way round. A line the eye can follow
without losing the return sweep runs to about sixty-six characters, and royal
octavo at 10.5pt lands close to it in one column. A4 gives closer to ninety,
which is why an A4 page carrying body text is usually set in two columns and a
book almost never is — see `columns.md`.

## The appendix

An `annex` opens recto like a chapter. Its **sections** open pages, not rectos:
inside an annex every section is a part, and six of them would cost six blank
leaves to say nothing.

## Chrome cannot bind one

A bound document declaring `pdf = "chrome"` is refused. Measured, not assumed —
`break-before: recto`, `@page :left/:right` and `string-set` running heads
printed through headless Chrome and read back:

| | Chrome | Measured |
|---|---|---|
| Trim size | works | `@page { size: 156mm 234mm }` → 442×663pt |
| Mirrored margins | works | recto text at 22.2mm, verso at 17.2mm |
| Chapters open recto | **fails** | breaks to the next page; chapter 2 landed on page 2 |
| Running heads | **fails** | `@top-center { content: string(chapter) }` produced nothing |
| Roman → arabic | **fails** | folios are measured into the HTML, not generated |

Two of five work, which is the problem: the output looks bound. Set
`pdf = "typst"`.

A deck is refused for the same reason `columns` refuses one: a slide is one side
of nothing.

## What a book does not change

**The Word edition is not bound.** `columns` propagates to DOCX because a
journal asks to see two columns; mirrored margins and recto openings are for an
object coming off a press, and an editor working in Word wants a manuscript.
Word can do both (`w:mirrorMargins`, `w:type val="oddPage"`) — this is a
decision about what the edition is *for*.

**The HTML edition is unchanged.** A screen has no verso and no gutter, and a
book on one is a long report.

## Related

`document-types.md` · `assembling.md` · `structure.md` · `print.md` · `columns.md`
