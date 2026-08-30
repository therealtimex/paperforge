# The pipeline, command by command

```bash
paperforge doctor      # external tools: what is here, what is missing, what for
paperforge status      # what is built, linked and published
paperforge figures     # documents must agree on the project's canonical values
paperforge claims      # a gist still says what its paragraph says — see claims.md
paperforge lint        # refuse documents still carrying internal machinery
paperforge build       # markdown -> self-contained HTML (+ PDF where declared)
paperforge verify      # structural, layout, print and cross-edition checks
paperforge publish     # hard-link into the artifacts dir and expose
paperforge all         # the chain above, stopping on failure
paperforge runs        # what each run produced — see provenance.md
paperforge brief       # what this project declares — see brief.md
paperforge map         # what a document declares, and what points at what
```

The entry point is `bin/paperforge` in a Paperforge checkout, and
`pipeline/bin/paperforge` beside the skill when installed as a plugin. A project
that *uses* Paperforge carries no pipeline of its own — only its sources, its
`documents.toml` and its `figures.toml`.

## Drafting

Every gate here fires at the end, which is the worst moment to learn something.
`todo` blocks and every draft has TODOs, so `all` is unusable while a document
is being written — which is why it is not run until somebody believes they are
finished, exactly when a refusal costs most.

```bash
paperforge all --draft
```

Same checks, same findings, different consequence. Nothing is held back, the
document builds so there is something to look at, `verify` still runs, and the
run ends with the inventory:

```
draft: nothing was held back. Publication would refuse:
  1 document(s) with blocking lint findings: report.html
```

**A draft run cannot publish.** `publish --draft` is refused outright, and
`all --draft` stops before the publish stage and says so. That is what makes the
mode defensible rather than a documented way around the gates — which the
scaffolded `AGENTS.md` tells agents in as many words not to take.

The run record shows what it was: `lint: blocked`, `publish: draft`. A draft run
is in the provenance like any other, and honest about which gates it ignored.

## What this needs from the machine

`typst` for print editions, rendered maths and formatted citations; headless
Chrome for diagrams, page measurement and layout checks; `git` only to create a
repository for a new project; `realtimex-pp-cli` only for the default publish
target. `paperforge doctor` says which are present.

A tool that is missing is reported, never raised as a traceback, and the run
continues wherever the work it was needed for was optional:

| Missing | Then |
|---|---|
| `typst`, and the document has maths or citations | the document is **refused** — its reading edition would be wrong |
| `typst`, and only a print edition needed it | the print edition is **skipped**, loudly; everything else builds |
| `git` at `init` | the repository is **skipped**; the project is scaffolded |
| `realtimex-pp-cli` at publish | publishing is **skipped**; every other verdict stands |
| headless Chrome does not return within its timeout | the measurement or probe that needed it is **skipped**, named |

So a green `all` on a machine missing a tool means less than one on a machine
that has them all, which is why the skip names the tool, what was lost, and
where to get it.

**Installing them is not the pipeline's to do.** The message points at a page
rather than offering a command: the command differs per platform, and a
copy-pasteable one invites an agent with shell access to run it. Changing a
machine is somebody's decision, not a build step.

## Scoping and configuration

| Flag | Effect |
|---|---|
| `--only <source \| output \| collection>` | Limit to one document or collection |
| `--config <path>` | Point at another project's `documents.toml` |
| `--no-measure` | Skip printed page numbering while iterating |
| `--expires-at <ISO>` | Publish with an expiry |
| `--quiet` | Findings without surrounding context |
| `--draft` | Report every finding and refuse nothing; cannot publish |
| `--label <name>` | Name this run in the record |
| `--diff <a>,<b>` | `runs`: compare two recorded runs |
| `--sources` | `runs --diff`: show what changed in the sources, not only which |
| `--accept` | `claims`: re-stamp every gist against its paragraph |
| `--json` | `map`: emit the map as JSON rather than for a reader |

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
