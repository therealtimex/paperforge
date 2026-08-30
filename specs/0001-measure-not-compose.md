# 0001 — Paperforge measures; it does not compose

**Date:** 2026-08-30
**Status:** accepted

## Context

The pipeline began as a publishing engine and grew an authoring layer:
`claims`, `map`, cross-references, the lint gates. Every one of those raised
the same question in a different costume — *should the tool also tell the
author what to write?* Suggest a better caption. Summarise a section. Draw the
argument. Flag a weak conclusion.

There was no stated line, so the question was re-argued per feature, and the
answers were drifting. A tool that starts having opinions about whether a paper
is any good will eventually be confidently wrong in front of a reviewer who is
not.

## Decision

**A feature is in scope if Paperforge can measure it. It is out of scope if it
would have to compose it.**

The test is not whether the output would be useful. It is whether **a finding
could be wrong in a way the author cannot adjudicate.**

A dangling `@fig-density` is measured: the label is absent, the answer is in
the file, and there is exactly one. A paragraph's one-line summary is composed:
two readers would write it differently, and there is no procedure that settles
which is right.

## Alternatives rejected

**Generate what can be reviewed.** Produce the summary, the caption, the
argument graph, and let the author accept or correct it. Rejected because a
generated summary has to be read against the paragraph before it can be
trusted, which is exactly the work it claimed to remove — and by the time the
prose has drifted, a summary of the prose is a summary of the drift.

**Ship composed findings as warnings rather than blocks.** Rejected on the
evidence: a warning nobody can act on is how people learn to ignore warnings.
The severity vocabulary (#54) exists so that a check which cannot answer says
`skip` with a reason, not `warn`.

**Decide per feature.** This was the status quo. It produced inconsistent
answers to the same question and no way to settle the next one.

## Consequences

- Everything in `lint.py`, `verify.py` and `editions.py` is a resolution
  procedure over the source or the built artifact. If a proposed check has no
  such procedure, it does not get written.
- `paperforge map` reports and refuses. `nothing-uses-it` is a note, not a
  finding, because a claim nothing draws on is usually the paper's conclusion,
  and blocking on it would fire on every correct document.
- Authors carry the composing work: the gist, the `uses=` edge, the caption.
  The tool's job is to notice when one has gone stale.
- Feature requests are answerable in one sentence, by whoever gets them.

## Evidence

- `AGENTS.md`, *"The tool may say what is there, never what it means"*.
- #36 (an authored gist), #37 (report-only reverse checks), #38 and #49
  (papermap), #54 (four severities) — each settled by this line.
- The counter-example that motivated it: `extractable()` once counted
  characters and reported 103% readable for an Arabic PDF that matched nothing.
  Volume was measurable and meant nothing; correspondence was the measurement
  that answered the question being asked. Measuring the wrong thing is still
  measuring — see [calibration.md](calibration.md) for how a number earns
  its place.
