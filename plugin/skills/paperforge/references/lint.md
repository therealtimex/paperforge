# The lint gate

Lint refuses to publish documents still carrying internal machinery. Every core
rule exists because that exact thing reached a ministry-facing draft.

Findings are `block` or `warn`. `publish` re-runs the gate and refuses anything
blocking, so the allowlist says what *may* ship and lint says whether it is
*fit* to.

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
| `unsupported-caption` | `: Caption {#fig-1}` |
| `length-spec` (warn) | an authoring length specification left in the text |

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
