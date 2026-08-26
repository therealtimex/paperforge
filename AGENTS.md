# Working on Paperforge

Paperforge is a document pipeline, not a document. The thing being changed here
is the renderer and its gates; the documents live in the projects that use it.

## Layout

```
.nvmrc                  Node 22.16.0 — the version RealtimeX ships
bin/paperforge          entry point (adds the repo root to sys.path)
paperforge/             the package: cli, markdown, typst, lint, verify, publish …
  theme/                paperforge.css, document.html, deck.css, deck.html
  profiles/             vi, en, zh, ar
  vendor/revealjs       inlined into decks; MIT, do not edit
docs/reference/         one file per feature — the documentation surface
plugin/                 the RealTimeX skill bundle; synced from the repo
tests/fixtures/         en, zh, id, bilingual, citations
tests/backtest/         a real multi-language corpus
```

`plugin/skills/paperforge/pipeline/` and `references/` are **generated**. Change
the repo, then run `bin/paperforge plugin`. `plugin --check` fails on drift and
on a reference file that no longer resolves.

## The rule that produced most of this code

**Measure before asserting; verify after building; prove a check catches the
defect it was written for.**

Every gate in `verify.py`, `lint.py` and `editions.py` exists because something
plausible-looking shipped. When adding one, demonstrate it firing against the
artifact as it stood *before* the fix, and put the number in the commit message.

## Two emitters, one source

`markdown.py` renders HTML; `typst.py` renders the print edition. They are
independent and they **drift** — parts opened a page in one and not the other,
figure captions doubled, `<br>` printed literally in table cells. Anything
touching one should be checked against the other, and `editions.py` compares
them automatically.

## Before committing

```bash
bin/paperforge plugin --check
node scripts/node-runtime-contract.mjs      # Node matches the RealtimeX host
node scripts/check-plugin-manifest.mjs      # manifest matches the host contract
for t in tests/unit_*.py; do python3 "$t"; done   # the gates' own rules

# the whole suite under coverage, then the gate CI enforces
rm -f .coverage .coverage.json
python3 -m coverage run bin/paperforge plugin --check
for t in tests/unit_*.py; do python3 -m coverage run "$t"; done
python3 -m coverage run bin/paperforge init --into /tmp/scaffolded --slug ci \
  --title Check --languages en,vi --publications report,book,annex,brief,deck \
  --no-git
python3 -m coverage run bin/paperforge all --config /tmp/scaffolded/documents.toml
for f in tests/fixtures/*/ tests/backtest/; do
  python3 -m coverage run bin/paperforge all --config "$PWD/$f/documents.toml"
done
python3 scripts/check-coverage.py
```

`tests/unit_*.py` are plain scripts, not a framework: each prints a line per
check and exits non-zero on failure. They exist for behaviour a fixture cannot
reach - a rule refusing what it claims to refuse, a link detaching the way git
detaches it, a heading starting mid-page. When one fails, read the label.

The coverage floors live in `scripts/check-coverage.py` and sit just under what
the suite achieves, so they ratchet against regression rather than describing an
ambition. Line and branch are held separately: a single combined figure lets
branch coverage rot while line coverage carries the average, and the defects
here have been branch-shaped - a threshold no short heading could clear, an
emitter that handled the explicit case and not the inferred one. Raise a floor
when the suite improves; lowering one should be visible in a diff.

The two Node scripts are the only JavaScript here. Nothing Paperforge ships
runs on Node — the plugin is declarative — but the manifest is parsed by the
host, so it is checked on the host's runtime. Signals also pins the module ABI
because it loads native addons; there are none here, so pinning one would look
rigorous and check nothing.

The English fixture is the check that no language assumption has crept back in.
The Chinese fixture is expected to decline the print checks with a stated
reason, not to pass them silently — see `docs/reference/print.md`.

## Say whose limitation it is

When something cannot be done, write down **which** thing cannot do it. "Typst
has no landscape page" was recorded here as a limitation of Typst. It was a
limitation of *this emitter*: Typst has had `#page(flipped: true)` all along,
and proving it took one file and two minutes. In between, the false version was
relayed into a routed decision, agreed with, and written into `print.md` as a
documented caveat, where it stayed until someone opened the PDF and saw
landscape pages.

A limitation attributed to a dependency ages into folklore, because nobody
re-tests someone else's tool. A limitation attributed to our own code is a
to-do. Before writing "X cannot", spend the two minutes finding out whether X
cannot, or we have not.

## Gate the trap, not the instance of it you were shown

Front matter is TOML, and a scalar written below a table header belongs to that
table. That was gated for `[affiliation]`, because `[affiliation]` was where it
had been hit. It was not gated for `[[author]]` — the *first* header in every
example anyone writes, including this module's own docstring, where the trap sat
uncorrected for weeks. A manuscript built with two columns simply had no
abstract on the page.

The same shape appears in `verify.coverage()`, whose strip list has been
extended four times, once per feature, each time after a false report. When you
fix one instance, write down what the general trap is and gate that. If you
cannot state the general form, you have not understood the defect.

## The defaults agreed, which is why nothing looked wrong

The design tokens were written down four times: two stylesheet `:root` blocks, a
`DEFAULTS` dict in the Word emitter, and eight colour literals through the Typst
emitter. Every copy carried the same values, so every edition looked right and
every gate passed. They disagreed only for a project that declared a palette of
its own — three of thirteen tokens reached the print edition, two reached Word,
and the most frequent non-black colour on the printed page, 818 of them, was one
the project had overridden and could not change.

A duplicated constant is invisible for as long as everyone is using the default.
Nothing in the output says the value came from four places, and the first to
find out is the first to exercise the feature. When you write a value down, ask
who else has already written it down, and what would fail if the two drifted.
Here the answer was nothing, which is the problem.

## A refusal has to be reachable

`columns = 2` on a deck is meaningless, and the refusal for it was first written
where the column count is used — which a deck never reaches, because the deck
branch returns from the build several steps earlier. A gate that cannot fire is
worse than no gate: it reads as coverage.

Manifest errors belong in `load()`, where every document passes regardless of
what it later becomes. Prove a refusal by triggering it, not by reading it.

## A check that reads an artifact assumes a layout

`editions.py` reads a printed page a line at a time. In two columns both columns
share one leading, so their baselines coincide and the reader runs straight
across the gutter: 55 of 55 lines merged on a measured A4. Nothing failed, and
the text every probe was matched against had stopped being sentences.

Whenever the page changes shape — columns, landscape, RTL — ask what the checks
believe about it, and go and measure rather than reasoning about it.

Binding was the same trap from the other side. Adding a running head puts the
chapter title at the top of every recto of that chapter, and the page-opening
comparison asks which headings open a page by reading the top of each page. It
does not start failing; it starts finding the chapter on four leaves instead of
one, and a chapter that opened no page at all would be reported as opening one.
Nothing about the page's *shape* changed — only what is printed on it. Ask what
a feature adds to the page as well as what it moves.

The fix is worth contrasting with the one above, because it is the same
operation with the opposite verdict. Cropping the top margin is safe: the
running head lives there by construction and the body begins below it. Cropping
down the middle of a page is not: content is entitled to cross a gutter, and two
of three part banners came back unlocated when that was tried. "Crop before
reading" is not a technique that is right or wrong — it depends entirely on
whether the boundary you are cutting on is one the layout guarantees.

Below the text it is the same again. pdfplumber reports both a fill colour and a
stroke colour on every rectangle, line and curve, whichever the paint operator
actually used, so counting both found 44 black objects on a page where every
mark was a brand colour. The colours were real; the black was the unused slot.
An artifact offers more values than it asserts — ask which ones it means.

## Conventions

- No dependency the published document can see. Chrome and the Mermaid CDN are
  build-time only; anything reaching the output must be inlined.
- A gate reports a **finding**, not a style note. If it can fire on correct
  work, it is wrong.
- A check that cannot run says so with a reason. "untestable" is never "passed".
- Comments explain *why*, especially when the reason is a defect that once
  shipped. Do not delete those.
