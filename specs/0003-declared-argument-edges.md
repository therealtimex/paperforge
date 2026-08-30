# 0003 — A citation is a call; "supports" is an opinion

**Date:** 2026-08-30
**Status:** accepted

## Context

`paperforge map` is the repo map of a paper: sections as modules, figures and
tables as exported objects, paragraphs with ids as functions, citations and
cross-references as calls. The analogy is productive, and it invites one step
further — if a call graph can be extracted from code, why not extract the
*argument* from a paper? Which claim supports which conclusion, which evidence
carries which finding.

That step is where the analogy stops holding, and the reason is worth writing
down because it will be proposed again.

## Decision

**Def/use edges are extracted. Argument edges are declared, or they are
absent. Neither is ever inferred.**

`@fig-density` and `[@author2024]` resolve or they do not. The answer is in the
file and there is exactly one, which is why `xref.dangling` and
`xref.duplicates` are allowed to block on them.

"This claim supports that conclusion" is written nowhere in the source, has no
resolution procedure, and is the thing reviewers are paid to disagree about. An
author who wants the edge writes `uses=claim-y`, which is source, and is then
checked like any other label — `dangling-uses` and `circular-uses` both block.

## Alternatives rejected

**Infer support from proximity or citation overlap.** Rejected: a check over
inferred argument edges can fire on a correct document, which
[0001](0001-measure-not-compose.md) forbids. The failure is also the worst kind
— confidently wrong about the substance of the paper, in front of somebody
qualified to notice.

**Infer the edges and present them as a picture rather than a check.** Rejected
for the same reason at one remove: a drawn argument is read as the paper's
argument. A tool that draws it has started having opinions about whether the
paper is any good.

**Require `uses=` on every claim.** Rejected: it would make the map complete at
the cost of making it fiction. An author who is made to declare edges will
declare the ones that make the shape look right.

## Consequences

- The map is honest and incomplete. What is on it was written by somebody.
- `nothing-uses-it` is a **note**, not a finding: a claim nothing draws on is
  usually the paper's conclusion, and a refusal for it would fire on every
  correct paper.
- Paperforge can never answer "is this argument sound". It can answer "does
  this reference resolve", "has this paragraph changed since its summary was
  accepted", and "does this claim rest on one that no longer exists".

## Evidence

- `AGENTS.md`, *"A citation is a call; 'supports' is an opinion"*.
- #37, #38, #49. The `uses=` edge, its two blocking checks and the
  `nothing-uses-it` note are in `paperforge/claims.py` and `papermap.py`.
- The `--accept` decision in [0002](0002-authored-gists.md) is the same
  principle applied to summaries rather than edges.
