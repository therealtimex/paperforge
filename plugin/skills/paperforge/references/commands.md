# The pipeline, command by command

```bash
paperforge status      # what is built, linked and published
paperforge figures     # documents must agree on the project's canonical values
paperforge lint        # refuse documents still carrying internal machinery
paperforge build       # markdown -> self-contained HTML (+ PDF where declared)
paperforge verify      # structural, layout, print and cross-edition checks
paperforge publish     # hard-link into the artifacts dir and expose
paperforge all         # the chain above, stopping on failure
paperforge runs        # what each run produced — see provenance.md
paperforge brief       # what this project declares — see brief.md
```

The entry point is `bin/paperforge` in a Paperforge checkout, and
`pipeline/bin/paperforge` beside the skill when installed as a plugin. A project
that *uses* Paperforge carries no pipeline of its own — only its sources, its
`documents.toml` and its `figures.toml`.

## Scoping and configuration

| Flag | Effect |
|---|---|
| `--only <source \| output \| collection>` | Limit to one document or collection |
| `--config <path>` | Point at another project's `documents.toml` |
| `--no-measure` | Skip printed page numbering while iterating |
| `--expires-at <ISO>` | Publish with an expiry |
| `--quiet` | Findings without surrounding context |
| `--label <name>` | Name this run in the record |
| `--diff <a>,<b>` | `runs`: compare two recorded runs |

With no `--config`, `$PAPERFORGE_CONFIG` is used, then the nearest
`documents.toml` above the working directory. **Every run prints the manifest it
resolved**, because that search is a footgun: a run started from a repository
root that holds a manifest silently acts on whatever it finds. On this
pipeline's first real project, a run labelled as peer review for one report
rebuilt and republished a different, already-approved corpus.

## Two commands that are not stages

```bash
paperforge init      # scaffold a new project — see starting-a-project.md
paperforge selftest  # build the bundled English fixture end to end
paperforge plugin    # re-sync the plugin bundle from the repo
paperforge plugin --check   # fail if the bundle has drifted
```

`selftest` is the check that the pipeline still carries no Vietnamese
assumptions. Fixtures for Chinese, Indonesian, bilingual and citation-bearing
documents ship beside it in `tests/fixtures`.

## Requirements

Headless Chrome (diagram rendering, page measurement, layout checks) ·
`pdfplumber` (reading pagination back) · `python-docx` (Word editions) ·
`typst` (print editions, maths, citations) · `realtimex-pp-cli` (publication).

Chrome and the Mermaid CDN are **build-time only**; published documents carry no
scripts or network dependencies from them.

## Related

`starting-a-project.md` · `manifest.md` · `lint.md` · `verify.md` · `publishing.md` · `provenance.md`
