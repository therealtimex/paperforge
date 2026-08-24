# The authoring brief

```bash
paperforge brief              # to stdout
paperforge brief --out BRIEF.md
```

Prints what the project declares, generated from its own manifest: how to run
the pipeline *here*, which documents exist and whether they may be published,
what the gates will refuse, which values must agree across documents, and where
the last run left things.

## Why it is generated rather than written

It came out of a real handoff. The brief given to a research team was good, and
roughly half of it was the project's own `AGENTS.md` paraphrased by hand into a
message. That copy asserted lint rules from a pack the project had **not**
enabled — true of the corpus they were remembered from, false of the project
they were written for.

A hand-written brief about the gates is a second source of truth for the gates.
It goes stale the moment a rule changes, and nothing tells you. This one cannot:
it reads the manifest, the active packs and the declared figures every time.

Regenerate it rather than quoting it. That is the whole point.

## What it deliberately does not say

The research method. Who holds which role. What evidence a handoff has to carry.

Those are decisions for whoever is running the work, and none of them is
derivable from a manifest. In the handoff that prompted this command, the
instruction that mattered most was *sources before prose* — because the previous
corpus had been returned as "usable as an orientation narrative, not
evidence-ready" for exactly the opposite ordering. No tool could have known
that, and a tool that invented something in its place would be worse than one
that stays quiet.

So the brief carries the facts and says plainly, at the end, that the judgement
is missing and whose it is.

## In a loop

The factual half of a routed handoff can be `paperforge brief` output; the
routing message then carries only the method, the role and the expected
evidence. The researcher can regenerate the facts at any point instead of
trusting a brief written ten rounds earlier.

## Related

`starting-a-project.md` · `manifest.md` · `lint.md` · `figures.md` · `provenance.md`
