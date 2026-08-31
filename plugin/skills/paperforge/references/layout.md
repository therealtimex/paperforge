# The reading edition: layout and responsiveness

The self-contained HTML is the reading edition — one file, no network at view
time.

## Contents sidebar

A document with a contents section gets a sidebar with scroll-spy and printed
page numbers; short briefs skip all three. The sidebar narrows at 1200px and
holds to 900px.

Below 900px it becomes a **fixed** drawer, capped at 70vh, closing on selection,
Escape or an outside click. Tap targets are 42px.

> `position: sticky` cannot be used for the drawer: in a single-column grid its
> row is exactly its own height, so it has no room to stick and the drawer opens
> off-screen — the toggle appears to do nothing.

## Grid

Use `minmax(0, 1fr)`, never `1fr`, for the content column: a `1fr` track refuses
to shrink below its content's intrinsic width, which is what let a wide table
push the whole page sideways on a phone.

`verify` checks for horizontal overflow at 1440 / 1024 / 768 / 390px, so a
regression here is a build failure rather than something a reader finds.

## Tables

Wide tables scroll rather than being restructured — see `tables.md` for why. A
measured edge fade and a swipe hint appear only where content really is cut off.
Cells tighten below 600px, which cuts the worst table overflow from 2.4× to 1.9×
of screen width.

## The cover lede is prose

A lede is whatever prose stands in the document head between the metadata block
and the contents. It is set **justified and hyphenated**, the same as the body,
because that is what the reader's eye meets next.

Below 900px it goes flush left, with the body — justification is worst on the
narrowest measure, which is why the body gives it up there too.

It was centred until a real one arrived: 389 words, twenty lines, and no
consistent left edge to return to. Centred is right for the sentence or two a
lede is usually written as and hostile at that length — and nothing in the
corpus had a lede at all, so the setting had never been seen with prose in it.
`en-sample` carries one now.

A lede that runs to a full executive summary will push the metadata below the
first screen. That is an editorial decision about what a reader should meet
first, and the theme does not try to solve it.

## Self-containment

No CDN, no runtime library, no external image. Diagrams are inline SVG, maths is
inline SVG, reveal.js is vendored. `verify` fails on any `src`/`href` pointing at
`http(s)://` in the built output.

Chrome and the Mermaid CDN are **build-time only** dependencies; nothing from
them survives into the published file.

## Related

`branding.md` · `tables.md` · `print.md` · `verify.md`
