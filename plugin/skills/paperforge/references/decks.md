# Presentations

A deck is its own markdown file with `type = "deck"`, rendered to reveal.js.

```markdown
## Three findings          <- a ## heading starts a slide

- Targets are set
- Instruments exist

---                        <- an explicit slide break

> notes: Open with the 2030 date; the room will not know it.
```

`##` starts a slide, `---` breaks one explicitly, and a blockquote whose first
line is `notes:` becomes speaker notes.

reveal.js is **vendored and inlined** (`paperforge/vendor/revealjs`, MIT),
so a deck opens offline like every other document — no CDN, no network at view
time. Export to PDF by appending `?print-pdf` to the URL.

## What the build tells you

`build` reports slides carrying too many words, and tables beyond 7 rows or 5
columns — those will not read from the back of a room. Diagrams are capped at
470px so they fill a slide.

Sections use `box-sizing: border-box`: with `content-box` the 54px padding
pushed slides past reveal's 1280px canvas and cut text off at the right edge.

## The pipeline does not write your deck

**Slicing a report into slides automatically produces noise.** A deck needs a
written narrative, exactly as an executive summary is written rather than
extracted. The pipeline renders and gates; it does not author.

## Related

`document-types.md` · `branding.md` (decks share the tokens) · `layout.md`
