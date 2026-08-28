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

## Findings

| Rule | Severity | Means |
|---|---|---|
| `stale-gist` | block | the paragraph changed and the gist was not accepted again |
| `unaccepted` | warn | a gist that has never been accepted against its paragraph |
| `no-gist` | warn | a labelled claim with nothing said about it |
| `orphan-gist` | warn | a lock entry for a claim that no longer exists |

Only `stale-gist` blocks, because only it is a demonstrated contradiction: the
text moved out from under something a person signed off against it. The rest
are incomplete rather than wrong.

## Writing a gist

Plain text. A gist cannot contain `"` or braces, and lint blocks both rather
than letting either fail quietly:

- a **brace** defeats the attribute pattern entirely, so nothing registers the
  claim and nothing strips the label — `{#claim-y ...}` prints on the page
- a **quote** parses, and what is stored stops at the inner quote

Neither says anything in the output, which is why both block.

## Related

`cross-references.md` · `figures.md` · `lint.md` · `commands.md`
