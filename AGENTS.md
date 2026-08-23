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
python3 tests/unit_publish.py               # the hard-link path CI cannot reach

# the whole suite under coverage, then the gate CI enforces
rm -f .coverage .coverage.json
python3 -m coverage run bin/paperforge plugin --check
python3 -m coverage run tests/unit_publish.py
for f in tests/fixtures/*/ tests/backtest/; do
  python3 -m coverage run bin/paperforge all --config "$PWD/$f/documents.toml"
done
python3 scripts/check-coverage.py
```

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

## Conventions

- No dependency the published document can see. Chrome and the Mermaid CDN are
  build-time only; anything reaching the output must be inlined.
- A gate reports a **finding**, not a style note. If it can fire on correct
  work, it is wrong.
- A check that cannot run says so with a reason. "untestable" is never "passed".
- Comments explain *why*, especially when the reason is a defect that once
  shipped. Do not delete those.
