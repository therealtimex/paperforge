# Starting a research project

**Interview the user first, then run `init`.** The answers become a manifest
that is already correct, and a manifest written as a placeholder never gets
edited.

Ask only what changes downstream behaviour:

| Ask | Sets |
|---|---|
| Language(s) and script | `--profile` / `--languages` |
| Which publications | `--publications report,book,brief,deck,annex` |
| Who publishes it | `--organisation`, `--publisher` |
| Where it is served | `--workspace` (RealTimeX) or a directory target |

## The request is usually not well-formed

Everything above is about *production*. None of it asks whether the question
can be answered, and that is the part that decides whether the work is worth
doing.

The first request this pipeline handled was unusually complete: a framing
question, five numbered problem groups, an audience, a horizon, a deliverable
spec. Its five groups became the report's five parts, close to one for one.
**That structure came from the request, not from the researcher.** A request
that arrives as three lines in a chat supplies none of it.

And nothing downstream will notice. `figures` checks that numbers agree, `lint`
that machinery has not leaked, `verify` that the rendering is sound. **No gate
can ask whether the document answers the question**, so a thin request produces
a document that passes every check and tells nobody anything. That failure has
a shape already: a corpus here was returned as *"usable as an orientation
narrative, not evidence-ready"* — fluent, complete, and not worth reading.

So before scaffolding is worth doing, get these answerable:

| Establish | Because |
|---|---|
| What decision this informs, and whose | Fixes the level: an orientation note and a submission are different documents |
| What would make the conclusion wrong | A question with no failure condition produces advocacy |
| What is out of scope | An unbounded question is answered by padding |
| What the reader must be able to *do* with it | Decides whether an annex, a brief or a deck is the deliverable |
| What already exists on this | Stops the work restating the prior corpus |

**When they cannot be answered, do not block.** Write down the reading you are
proceeding on, say plainly that it is an assumption, and put it where it will be
checked — a peer reviewer can argue with a stated assumption and cannot argue
with one that stayed in someone's head.

Declare the request so it travels with the work:

```toml
[defaults]
request = "../research-requests/2026-08-brief.md"
```

Every run then snapshots it alongside the sources, so what was asked stays
readable beside what was produced, and `paperforge brief` cites it. When the
request is thin, **the reading of it is the specification** — and a
specification that exists only in a chat message is one nobody can hold the
delivery against.

```bash
paperforge init --into <dir> --slug <short-name> --title "<Title>" \
                 --languages vi,en --publications report,annex,brief \
                 --organisation "<Org>" --publisher "<Full publisher line>"
```

`--no-git` skips `git init` — which is also skipped automatically inside an
existing work tree, so scaffolding into a subdirectory of a repo does not nest
one.

## What it writes

`documents.toml`, `figures.toml`, `AGENTS.md`, `.gitignore`, skeleton sources
for each requested publication in each requested language, and a git repo.

**A fresh project passes `paperforge all` clean.** That is the acceptance
criterion: a team whose first encounter with the gates is a wall of red on files
they have not written yet learns to ignore the gates.

Two details that come from that:

- Scaffolded documents carry `publish = false`. A document becomes publishable
  by a deliberate edit — which is also when someone decides it is ready.
- Skeleton sections are marked `{.part}` rather than relying on a heading
  pattern, so structure works from the first build in any language.

Dates in the skeleton use the profile's `date_format`, so a Vietnamese project
does not open with "August 2026".

## Why this exists

Everything `init` writes was, in the project that predates it, created
retroactively — and three real failures came from that ordering: internal
metadata reached a ministry-facing draft, a rendered file drifted from its
source, and a brief was typeset as a report.

## Related

`manifest.md` · `languages.md` · `document-types.md` · `figures.md`
