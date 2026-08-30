# 0004 — Git records acts; the run record records events

**Date:** 2026-08-30
**Status:** accepted

## Context

`.paperforge/runs/` keeps a record per run: which documents were built, which
stages passed, the manifest hash, and optionally a copy of the sources. Git is
already in the project — `init` creates a repository — so the obvious
simplification is to drop the run record and read history from git instead, or
to commit each run.

The question came up directly: *if git is enabled, should runs be incremental
changes agents can `git diff`?*

## Decision

**The two record different things and neither replaces the other.**

Git records **acts**: somebody decided this text was worth keeping. A commit is
a deliberate act of authorship.

The run record records **events**: this build happened, these gates ran, this
is what they said. A build is not a decision, and most builds are never
committed — the draft that made a gate necessary usually never was.

So `.paperforge/runs/` is not git-backed and its contents are gitignored.
`.paperforge/claims.json` **is** committed, because an acceptance is an act.

`runs --diff --sources` compares two runs' inputs directly, and reports
`(None, [names])` — not an empty diff — when the sources were not kept, because
an empty diff means "nothing changed".

## Alternatives rejected

**Commit each run.** Rejected: it makes a build an act of authorship. The
history fills with commits nobody chose to make, and the acts that matter stop
being visible among them.

**Drop the run record and read git.** Rejected: git has nothing to say about a
build that was never committed, which is most of them, including every build
that failed a gate — the ones worth being able to look at again.

**Require git.** Rejected: `doctor` reports a missing tool and what it was for,
and asks. A project without git is a project with a weaker record, not a
project the pipeline refuses. See the `--no-git` path in `init`.

## Consequences

- A run can be inspected after a failure without anything having been
  committed, which is the case the record exists for.
- The two records can disagree — the working tree can be dirty relative to the
  last commit while a run reflects it exactly. That is not a defect; they are
  answering different questions.
- `.gitignore` is narrow (`tests/**/.paperforge/runs/`) so a project's own
  claims lock is never accidentally excluded with the runs.

## Evidence

- #81 (`runs --diff` says which documents changed, never what changed in them),
  #71 (`init` without git), #84 (an acceptance nobody else has is not one).
- `paperforge/runs.py`; `scaffold.py` decides about git before writing anything.
