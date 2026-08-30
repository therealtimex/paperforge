# Specs

Decisions, and the numbers that were measured rather than chosen.

This directory exists for one reason: **everything else in this repository
describes a state, and a description of a state goes stale.** `docs/reference/`
says what the pipeline does today. `AGENTS.md` says how to work on it today.
The code says what it is. All three are rewritten as the software changes,
which is correct, and it means none of them can tell you what was *decided* —
what the alternatives were, what evidence closed the question, and which
arguments have already been had.

So a decision record here is written once and, **once merged, not edited
afterwards**. It records a moment. A moment cannot drift, which is the whole point: this
codebase has repeatedly been bitten by a second copy of something that fell out
of step with the first — a regex defined in three modules, a check list that
`publish` kept its own shorter copy of, a comment asserting that images were
handled as figures when nothing handled them. A `specs/` directory that
restated the current behaviour would be the next one.

## What goes here

- **Decision records** (`NNNN-slug.md`) — a question that took an argument to
  settle. The alternatives that were rejected matter as much as the one that
  was taken; without them the question gets reopened every year by someone who
  cannot see why it was closed.
- **`calibration.md`** — every number in the pipeline that was measured against
  a corpus rather than picked. This one is *living*, and it is gated:
  `tests/unit_calibration.py` fails if a value here and the constant in the
  code disagree.

## What does not go here

Feature descriptions (`docs/reference/`), module layout (`AGENTS.md`), API
shapes (the code), or a roadmap. If a document here would have to be edited
when the software changes, it is in the wrong place — with the single exception
above, which is allowed only because a test holds it to the code.

## Writing one

Number it, date it, and state the decision in the title as a claim rather than
a topic. Then:

**Context** — what forced the question. Name the defect, the issue or the
document that made it unavoidable.
**Decision** — what was decided, in the present tense.
**Alternatives rejected** — each one, with why. This is the section that stops
the question being reopened.
**Consequences** — what this makes easy, what it makes impossible, what it
costs.
**Evidence** — measurements, issue numbers, commits. What a reader would need
to check the reasoning rather than take it.

Superseding a record is done by writing a new one that says so and adding a
line to the old one pointing at it. The old text stays as written.

If a merged record turns out to be **wrong** rather than outdated, append a
`## Correction` section saying what it got wrong and leave the original text
above it. A record that can be quietly rewritten is worth less than no record:
the whole value here is that you can trust what it says was believed at the
time. 0004 carries one, from review of the pull request that added it.

## The records

| | Decision |
|---|---|
| [0001](0001-measure-not-compose.md) | Paperforge measures; it does not compose |
| [0002](0002-authored-gists.md) | A gist is written by a person and only ever checked |
| [0003](0003-declared-argument-edges.md) | A citation is a call; "supports" is an opinion |
| [0004](0004-runs-are-events-not-acts.md) | Git records acts; the run record records events |
