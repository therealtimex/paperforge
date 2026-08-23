# Starting a research project

**Interview the user first, then run `init`.** The answers become a manifest
that is already correct, and a manifest written as a placeholder never gets
edited.

Ask only what changes downstream behaviour:

| Ask | Sets |
|---|---|
| Language(s) and script | `--profile` / `--languages` |
| Which publications | `--publications report,annex,brief,deck` |
| Who publishes it | `--organisation`, `--publisher` |
| Where it is served | `--workspace` (RealTimeX) or a directory target |

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
