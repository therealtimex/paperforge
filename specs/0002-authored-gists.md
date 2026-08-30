# 0002 — A gist is written by a person and only ever checked

**Date:** 2026-08-30
**Status:** accepted

## Context

`{#claim-x gist="..."}` gives a paragraph a one-line summary that `paperforge
map` prints and anything reading the document can trust. The obvious next step
is to generate it: models write competent one-line summaries, the author saves
the effort, and the map fills itself in.

Underneath is the problem this whole feature exists for: **a paper has no
compiler.** Rename a function and miss a call site, and the build fails. Change
what a paragraph argues, leave its summary alone, and nothing anywhere
complains. A stale gist is worse than no gist, because whatever reads it — a
person skimming, a model handed the document — trusts it completely, and the
drift is invisible from the output.

## Decision

The pipeline **never writes a gist**. It stores a fingerprint of the paragraph
the gist was accepted against, and refuses the build when the paragraph has
changed and the gist has not been re-accepted.

`paperforge claims --accept` re-stamps. It is a separate, deliberate command
because that is the moment somebody reread the paragraph and said the summary
still holds. Nothing stamps itself.

The fingerprint covers whitespace-collapsed prose with the label stripped, so
rewording the *gist* does not mark it stale and rewriting the *paragraph* does.

`.paperforge/claims.json` is committed. An acceptance only one machine has
vouches for nothing to anybody else.

## Alternatives rejected

**Generate the gist and mark it as generated.** Rejected: it has to be reviewed
before it can be trusted, which is the work it claimed to remove. A reviewed
generated summary is an authored one with extra steps and worse provenance.

**Generate a fresh gist when the paragraph changes.** Rejected: by the time the
prose has drifted, a summary of the prose is a summary of the drift. The
regeneration would hide exactly the change the gate exists to surface.

**Warn instead of block on a stale gist.** Rejected. A stale gist is a
demonstrated contradiction between two things in the same file, which is the
definition of `block` in the severity vocabulary. Nothing about it is a matter
of taste.

**Hash the rendered HTML rather than the source prose.** Rejected: a stylesheet
change would mark every claim in the corpus stale.

## Consequences

- Writing a claim costs the author a sentence. That cost is the feature.
- A document cannot be built with a gist that no longer matches its paragraph,
  which means the map is trustworthy by construction rather than by convention.
- The lock file is a merge conflict surface. That is the correct place for the
  conflict: two people accepted different text for the same claim.
- Nothing in the pipeline can be pointed at an existing corpus and told to fill
  in the gists. Adoption is paragraph by paragraph, by an author.

## Evidence

- #36. `paperforge/claims.py` module docstring carries the same reasoning at
  the point of use.
- The gate was proved by reintroduction: change the prose, watch `claims`
  report `stale-gist` as `block`; restore, watch it clear.
- Two silent failures found while building it: a brace inside a gist
  (`gist="the set {a,b}"`) matched no attribute pattern and registered nothing;
  a quote inside one truncated what was stored. Both are now `malformed-claim`
  and `truncated-gist`, because a claim that silently does not exist is worse
  than one that is refused.
