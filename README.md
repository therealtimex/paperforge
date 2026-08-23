# Paperforge

Markdown in, published research documents out — academic, policy or business.
One source, several editions: a self-contained HTML reading edition, a Typst
print edition, and reveal.js slides, all gated before anything ships.

Paperforge **renders and gates; it does not author.** It will not write your
report, and it will not decide what a document should say.

## What it does

- **Builds** markdown into a single self-contained HTML file — diagrams,
  maths and slides inlined, no CDN, opens offline.
- **Prints** through Typst: footnotes at the foot of the page, running heads,
  parts opening on a new page, native citations and maths.
- **Measures** printed page numbers rather than estimating them: print, read
  the PDF back, bake the numbers in, reprint until the mapping settles.
- **Gates** on internal machinery reaching a reader, on numbers disagreeing
  between documents, on markup that never rendered, and on the two editions
  drifting apart.
- **Publishes** by hard link, so a rebuild is live with no copy step.

Any language: profiles for `vi`, `en`, `zh` and `ar` ship, and a project can
supply its own without a release. Script behaviour — diacritic folding,
combining marks, direction, font glyph coverage — stays with the pipeline.

## Quick start

```bash
bin/paperforge init --into ~/research/my-project --slug my-project \
                    --title "My research project" --languages en \
                    --publications report,annex --publisher "My Institute"

bin/paperforge all --config ~/research/my-project/documents.toml
```

A freshly scaffolded project passes `all` clean. That is the acceptance
criterion: a team whose first encounter with the gates is a wall of red on
files they have not written learns to ignore the gates.

## The pipeline

```bash
paperforge status      # what is built, linked and published
paperforge figures     # documents must agree on the project's canonical values
paperforge lint        # refuse documents still carrying internal machinery
paperforge build       # markdown -> self-contained HTML (+ PDF where declared)
paperforge verify      # structural, layout, print and cross-edition checks
paperforge publish     # hard-link into the artifacts dir and expose
paperforge all         # the chain above, stopping on failure
```

## Documentation

`docs/reference/` holds one file per feature. Start from the routing table in
[plugin/skills/paperforge/SKILL.md](plugin/skills/paperforge/SKILL.md), which is
also what an agent reads when the plugin is installed.

Authoring: [structure](docs/reference/structure.md) ·
[tables](docs/reference/tables.md) · [diagrams](docs/reference/diagrams.md) ·
[callouts](docs/reference/callouts.md) ·
[citations](docs/reference/citations.md) · [maths](docs/reference/maths.md) ·
[cross-references](docs/reference/cross-references.md) ·
[decks](docs/reference/decks.md) ·
[unsupported syntax](docs/reference/unsupported-syntax.md)

Projects: [starting a project](docs/reference/starting-a-project.md) ·
[manifest](docs/reference/manifest.md) ·
[document types](docs/reference/document-types.md) ·
[languages](docs/reference/languages.md) ·
[branding](docs/reference/branding.md) · [layout](docs/reference/layout.md) ·
[print](docs/reference/print.md) · [figures](docs/reference/figures.md) ·
[lint](docs/reference/lint.md) · [verify](docs/reference/verify.md) ·
[publishing](docs/reference/publishing.md) ·
[commands](docs/reference/commands.md)

## Installing as a plugin

`plugin/` is a RealTimeX declarative skill plugin — no entry point, the skill
carries the pipeline. `bin/paperforge plugin` re-syncs the bundle from the repo;
`bin/paperforge plugin --check` fails if it has drifted, so a stale plugin is a
visible failure rather than a silent one.

```bash
realtimex-pp-cli install-plugin --path "$PWD/plugin" --agent
```

## Requirements

`python3`, headless Chrome (diagrams, page measurement, layout checks),
`pdfplumber`, `typst` (print editions, maths, citations), and `realtimex-pp-cli`
for the default publish target. Chrome and the Mermaid CDN are **build-time
only** — published documents carry no scripts or network dependencies.

```bash
brew install typst
pip install pdfplumber
```

## Tests

```bash
bin/paperforge selftest         # builds the English fixture end to end
bin/paperforge plugin --check   # bundle drift, reference links, one version
node scripts/check-plugin-manifest.mjs   # the RealtimeX manifest contract
```

The Node scripts run on the version in `.nvmrc` — 22.16.0, the one RealtimeX
ships — so the manifest is parsed by the runtime that will parse it in
production.

`tests/fixtures/` also holds Chinese, Indonesian, bilingual and
citation-bearing projects; `tests/backtest/` holds a scaffolded multi-language
project. The English fixture is the check that no Vietnamese assumption has
crept back in — a second language is the only real proof.

CI runs every fixture as its own matrix job, so a failure names the language
that broke. See `.github/workflows/`.

## Releasing

Tag `vX.Y.Z`. The release workflow refuses the tag unless it matches the version
in `plugin/realtimex.plugin.json` and in the skill frontmatter, re-runs every
gate rather than trusting the pull request, packages the plugin, builds a
document *from the unpacked zip*, and only then publishes the GitHub Release
with a checksum.

```bash
bin/paperforge plugin --package dist   # the same zip, locally
```

## Licence

Source available, all rights reserved to RealTimeX — see [LICENSE](LICENSE).
The source is published for reference; it is **not** open source, and no right
to use, fork or redistribute it is granted. Vendored reveal.js remains MIT and
is inlined into every generated deck; see [NOTICE](NOTICE).
