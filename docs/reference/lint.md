# The lint gate

Lint refuses to publish documents still carrying internal machinery. Every core
rule exists because that exact thing reached a ministry-facing draft.

`publish` re-runs the gate and refuses anything blocking, so the allowlist says
what *may* ship and lint says whether it is *fit* to.

## What a finding is allowed to say

| Severity | Means | Stops publication |
|---|---|---|
| `block` | a demonstrated contradiction | yes |
| `manual` | the check ran and the verdict is a person's to give; the finding names the act that settles it | no |
| `warn` | worth a look; you decide whether it matters | no |
| `skip` | the check could not run, and says why | no |

`manual` and `skip` were both `warn` once, and the merge cost something. A
reader could not tell *"you may want to look at this"* from *"I cannot answer
this; you must"* — and a warning nobody can act on is how people learn to ignore
warnings.

A `manual` finding is not useful without the act, so it always carries one:

```
manual  demo-report.md:43  claim-c  unaccepted
    a gist never accepted against its paragraph
    -> paperforge claims --accept
```

`skip` is the conventions rule given a name: a check that cannot run says so
with a reason, and untestable is never *passed*.

## Where the gate runs

Every rule below runs in both places: the `lint` stage, and the re-check
`publish` makes before it ships anything. One list — `lint.check_all` — so a
rule cannot reach one and not the other, which it could when `publish` kept its
own shorter copy. See `publishing.md`.

## Three layers

**Core** — applies to any research project. An unfinished marker or a raw
filename shown to a reader is wrong regardless of who wrote it:

| Rule | Blocks |
|---|---|
| `source-filename` | `(SOME_FILE.md)` in prose |
| `filename-label` | a source filename used as reader-facing link text |
| `todo` | `TODO`, `TBD`, `FIXME`, `XXX`, `PLACEHOLDER` |
| `lorem` | placeholder text |
| `unsupported-footnote` | `[^1]` — see `unsupported-syntax.md` |
| `claim-reference` | `@claim-x` in prose — a claim has no rendered form to point at |
| `malformed-claim` | a claim label with braces inside its gist — it would print on the page |
| `truncated-gist` | a quote inside a gist — what is stored would stop at it |
| `empty-claim` | a claim label attached to nothing — its gate could never fire; see `claims.md` |
| `dangling-uses` | a `uses=` edge naming a label that does not exist — see `claims.md` |
| `circular-uses` | a claim reachable from itself through `uses=` |
| `unknown-attribute` | part of a claim's attribute was not understood, so it was dropped |
| `dangling-reference` | `@fig-absent` — a reference to a label that does not exist |
| `duplicate-label` | the same id declared twice |
| `missing-image` | `![a](figures/gone.png)` — no file at that path, relative to the document |
| `remote-image` | an image loaded over the network; a published document carries its own |
| `stray-caption` | a caption under something that carries none — see `images.md` |
| `no-bibliography` | citations with no `bibliography` declared — Typst would fail with an unhelpful "label does not exist" |
| `front-matter` | an affiliation marker pointing at nothing, a malformed ORCID, a block that is not TOML |
| `length-spec` (warn) | an authoring length specification left in the text |
| `orphan-label` (warn) | a figure, table or equation declared and never referred to |
| `empty-section` (warn) | a heading with no prose and no heading beneath it |

**Packs** — opt-in, for a particular authoring system. `realtimex-loops` catches
loop issue ids, agent workflow state tokens (`*.draft_ready`), handoff
instructions and agent role labels. Noise for a project that does not use Loops.

**Project rules** — every organisation has its own vocabulary:

```toml
[lint]
packs = ["realtimex-loops"]
  [[lint.rule]]
  id = "client-codename"
  severity = "block"
  pattern = "PROJECT (?:BLUEBIRD|CONDOR)"
  why = "internal codename"
```

Against one corpus's pre-cleanup sources the core alone raises 8 findings; with
the Loops pack, 15.

Fenced code blocks are exempt, so a rule cannot fire on a sample.

## The allowlist

Lint also enforces the manifest: a document is publishable only if declared
there with `publish = true`. Process records live under `[internal]` and can
never be published by accident.

## Related

`unsupported-syntax.md` · `manifest.md` · `publishing.md` · `figures.md`
