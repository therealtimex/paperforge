# Claims and their gists

A labelled paragraph can carry a one-line statement of what it is for:

```markdown
The estimator is consistent under A1-A3.
{#claim-consistency gist="MLE is consistent under A1-A3"}
```

The label and the gist are stripped from every edition; neither reaches a
reader. See `cross-references.md` for the label itself.

## The gist is written by a person

Paperforge never generates one. A generated summary has to be reviewed before
it can be trusted, which is the work it claimed to remove — and by the time the
prose has drifted, a summary of the prose is a summary of the drift.

A claim with no gist is reported as a **hole**, not filled in. That is the
point: a visible gap is worth more than a plausible invention.

## The gate: a paper has no compiler

Code has one. Rename a function, miss a call site, and the build fails. A paper
has nothing — change what a paragraph argues, leave its gist alone, and nothing
anywhere complains. A stale gist is worse than no gist, because whatever reads
it trusts it completely and the drift is invisible from the output.

So a gist is *accepted* against the paragraph it describes:

```bash
paperforge claims            # what is missing, unaccepted, stale or orphaned
paperforge claims --accept   # I have reread these paragraphs; the gists hold
```

`--accept` stamps a fingerprint of the paragraph into `.paperforge/claims.json`.
Nothing stamps itself: accepting is the moment somebody read the paragraph and
said the gist still stands.

**Commit the lock.** It is not ignored by the scaffolded `.gitignore`, and a
lock that only exists on one machine vouches for nothing anywhere else.

## What counts as a change

The fingerprint is taken over the paragraph's prose with the label stripped,
and whitespace collapsed.

| Edit | Stale? |
|---|---|
| Rewriting what the paragraph says | **yes** — blocks |
| Rewording the gist | no — the paragraph did not move |
| Rewrapping the lines, or extra spaces | no — whitespace is not a change |
| Deleting the claim | no — the lock entry is reported as orphaned, and `--accept` drops it |

## What a claim draws on

```markdown
The estimator is consistent under A1-A3, given the likelihood in @eq-l.
{#claim-mle gist="MLE is consistent under A1-A3" uses=claim-likelihood,claim-regularity}
```

Most edges need no syntax. A `@fig-`, `@tbl-`, `@eq-`, `@sec-` reference or a
`[@citation]` **inside the paragraph** is already an edge — reading it is the
same measurement `dangling()` does, scoped to one block.

`uses=` exists for the one edge that cannot be read: **claim to claim**.
`@claim-x` is blocked in prose, because a claim has no rendered form to point
at, so nothing on the page records that one claim rests on another. Per the
doctrine in `AGENTS.md`, an argument edge is declared by the author or it is
absent — Paperforge never infers one.

`uses=` is bare and comma-separated. A label id cannot hold a space, a comma or
a quote, so quoting would buy nothing and add the failure mode `truncated-gist`
exists to catch. It may name any label, not only a claim: a claim may rest on a
figure the paragraph does not textually cite.

Editing `uses=` does not make a gist stale. The fingerprint covers the prose
with the whole attribute stripped, and an edge is not a claim about the wording.

**`used-by` is not written.** It is the inverse of `uses`, computed, together
with the section each user sits in.

## What is not checked: a claim nothing uses

Deliberately. A claim nothing uses is usually the **finding** — the thing the
paper exists to state, resting on everything below it and supporting nothing
above it. Every well-formed argument has one, so a gate for it would report a
defect on every correct paper. It is worth *showing*, and belongs in the map
rather than in a refusal.

## Findings

| Rule | Severity | Means |
|---|---|---|
| `stale-gist` | block | the paragraph changed and the gist was not accepted again |
| `unaccepted` | manual | a gist that has never been accepted against its paragraph; names `claims --accept` |
| `no-gist` | warn | a labelled claim with nothing said about it |
| `orphan-gist` | warn | a lock entry for a claim that no longer exists |
| `dangling-uses` | block | a `uses=` naming a label that does not exist |
| `circular-uses` | block | a claim reachable from itself; an argument resting on itself |
| `unknown-attribute` | block | part of the attribute was not understood, so what it meant was dropped |

Only `stale-gist` blocks, because only it is a demonstrated contradiction: the
text moved out from under something a person signed off against it.

`unaccepted` is `manual` rather than a warning — nobody has vouched for that
gist against that paragraph, so the pipeline has no verdict to give, and the
finding names the command that settles it. The rest are incomplete rather than
wrong. See `lint.md` for what each severity means.

## Writing a gist

Plain text. A gist cannot contain `"` or braces, and lint blocks both rather
than letting either fail quietly:

- a **brace** defeats the attribute pattern entirely, so nothing registers the
  claim and nothing strips the label — `{#claim-y ...}` prints on the page
- a **quote** parses, and what is stored stops at the inner quote

Neither says anything in the output, which is why both block.

## Where the label may sit

At the end of the paragraph, or at the end of a line inside it — both work, and
both are stripped from every edition before a reader sees them:

```markdown
A single jurisdiction refines the majority of several critical inputs.
{#claim-concentration gist="One jurisdiction refines most critical inputs"}
The next sentence, in the same paragraph because no blank line separates them.
```

The claim's own text is the run of lines **ending on its label** — the sentence
after it belongs to the paragraph a reader sees and not to what the gist is
hashed against. That is what lets a claim mark one assertion inside a longer
block.

This is worth stating because it did not work: a label that ended a line
without ending the paragraph was registered by the claims layer and printed to
the reader by every emitter, on the cover of a 95-page dossier, with `lint`
reporting the document clean.

## A label has to be attached to something

`empty-claim` **blocks**. It fires when a label is written where the run of
lines above it is empty, which is what happens when it stands alone after a
list:

```markdown
- the first commitment
- the second commitment

{#claim-programme gist="Two commitments, both statutory"}   <- attached to nothing
```

The gist is then hashed against empty text — `e3b0c442…`, the SHA-256 of the
empty string — and **the gate can never fire**: there is no prose under the
hash for an edit to move. A peer reviewer found six of seven accepted claims in
a real dossier in that state, by opening the lock file and recognising the
prefix. Everything reported them current.

Where the label goes instead:

| Written | The claim covers |
|---|---|
| after a list, on its own line | **nothing — refused** |
| on the last list item | that item |
| after a paragraph, on its own line | the paragraph |
| at the end of a paragraph's last line | the paragraph |
| after a list, then prose, then the label | the prose |

A claim's text stops at a list item on purpose, so the hash covers what a
reader sees as one block. That is why a label after a list has nothing above it
to collect, and why the answer is to attach the label to the statement rather
than to loosen the boundary.

## When not to use one

A gist is a standing commitment: one sentence to write, and a re-accept every
time that paragraph materially changes. That cost is worth paying for the
claims an argument rests on and nothing else.

**Label the load-bearing claims, not the paragraphs.** In a six-domain report in
four-part shape that is roughly one per part per domain — around two dozen, not
sixty. Applied to everything, the gate becomes noise and the map becomes
something nobody reads.

**Take the cheap wins first.** `{#sec-}` ids on headings and labels on the
floats the prose points at cost nothing ongoing, need no discipline, and give
`paperforge map` real structure. Do those before deciding about gists — they
are not the same commitment and suggesting them together makes the cheap one
look as expensive as the dear one.

**Adopt when the prose stops moving.** The value of the gate is proportional to
how much the document changes *after* a claim was written, which is exactly why
adopting mid-rewrite is a week of re-accepting. The moment is when the draft
settles and before `publish` is flipped.

**The gate is only as good as the rereading.** `--accept` re-stamps; it cannot
know whether anybody read anything. A gist accepted without being reread is a
trusted summary that is wrong, and nothing downstream can tell — which is worse
than never having written one. `--accept CLAIM` exists for this reason: it
stamps that one claim and prints the paragraph beside its gist, so a build
blocked on one paragraph is not cleared by an action that touches every other.
Bare `--accept` still re-stamps all of them. The discipline is yours either way
and no design replaces it.

**A gist nobody reads is overhead.** If no reviewer opens the map and nothing
is handed the document, the sentences are a cost with no reader.

## Related

`cross-references.md` · `figures.md` · `lint.md` · `commands.md` ·
`papermap.md`
