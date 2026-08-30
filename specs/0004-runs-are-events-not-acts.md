# 0004 — Git records acts; the run record records events

**Date:** 2026-08-30
**Status:** accepted

## Context

A research corpus in this system was drafted twice. The first pass was poor and
was **overwritten in place** by the second. The repository had git from the
start and it did not help, because preserving the first pass required somebody
to remember to commit at the right moment, and four agent roles all did not.
The drafts are simply gone; the two passes can never be compared.

That is the failure this record is about. It is not a failure of git. It is a
failure of relying on an act of discipline to preserve something that was
produced by a process.

## Decision

**The run record is a by-product of running the pipeline, not an act of
discipline.** `all` and `build` write one every time, into
`.paperforge/runs/<timestamp>/`, without being asked.

It holds **the sources themselves**, not only their hashes. What was wanted
afterwards was the lost draft, and a fingerprint would not have returned it.

Git and the run record answer different questions and neither replaces the
other:

- Git records **acts** — somebody decided this text was worth keeping.
- The run record records **events** — this build happened, these gates ran,
  this is what they said.

A scaffolded project therefore **tracks its run records**: `scaffold.py`'s
`.gitignore` says in as many words that `.paperforge/runs` is deliberately not
ignored. Paperforge itself never runs git. Whether to commit is the project's
decision; the pipeline's job is to make sure there is something to commit.

`.paperforge/claims.json` is committed for a different reason — an acceptance
*is* an act, and one only your machine has vouches for nothing to anybody else.

## Alternatives rejected

**Rely on git history.** This was the status quo when the drafts were lost. Git
was present and preserved nothing, because the moment that mattered was between
two runs and no human was in it.

**Record hashes only.** Rejected: a fingerprint tells you the draft changed and
cannot give it back. The record exists because somebody wanted the file.

**Have the pipeline commit each run.** Rejected twice over. It makes a build an
act of authorship, so the history fills with commits nobody chose to make and
the acts that matter stop being visible among them. And running git against
somebody's repository is not a build step — the same reason `doctor` reports a
missing tool rather than installing it.

**Require git.** Rejected: `init --no-git` is supported, and a project without
git has a weaker record, not a refusal.

## Consequences

- A run can be inspected after a failure without anything having been
  committed, which is the case the record exists for.
- Run records **churn**: every build writes one, and a project that tracks them
  accepts that in its history. That is the accepted cost of not losing a draft.
- The PDF hash is recorded **as observed**, not as a reproducibility claim.
  Printed page numbers are measured by printing the document and reading the
  page back, so a machine with different fonts genuinely paginates differently;
  `runs --diff` reports a changed PDF hash as a note, not a discrepancy.
- The two records can disagree — a dirty working tree against the last commit —
  and that is not a defect. They are answering different questions.
- This repository ignores `tests/**/.paperforge/runs/`. That is fixture output,
  not a statement about projects.

## Evidence

- `paperforge/runs.py` module docstring, which carries the lost-draft account
  at the point of use; `paperforge/scaffold.py` `GITIGNORE`.
- #81 (`runs --diff` said which documents changed, never what changed in them),
  #71 (`init` without git), #84 (an acceptance nobody else has is not one).

## Correction

The first version of this record, in the pull request that added it, asserted
that `.paperforge/runs/` is gitignored and not git-backed. That is the opposite
of what the scaffold does, and it was caught in review before merge. The
distinction it was reaching for is real — the pipeline never commits — but the
record stated it as a fact about projects that was false. Noted here rather
than quietly rewritten, because a specs directory whose records can be wrong
without trace is worse than no specs directory.
