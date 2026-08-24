# Run records

Every `build` and every `all` writes a record of what it produced to
`.paperforge/runs/`, whether the run passed or failed. Nothing has to be
remembered for this to happen.

```bash
paperforge all --label "run 1, all agents on model X"
paperforge runs                              # what has been recorded
paperforge runs --diff run-1,run-2           # what changed between two of them
```

## Why it exists

A research corpus in this system was drafted twice. The first pass was poor, the
second overwrote it in place, and the drafts of the first are simply gone — so
the two can never be compared, and nothing can be learned from the failure.

The repository had git from the first commit. It did not help. Preserving the
first pass required somebody to remember to commit at the right moment, and four
agent roles all did not. **So the record is a by-product of running the pipeline
rather than an act of discipline.**

## What a record holds

```
.paperforge/runs/20260824T010923Z-run-1-baseline/
  record.json      label, timestamp, manifest hash, stage verdicts, per-document hashes
  sources/         the markdown itself, as it stood
```

The sources are kept, not only their hashes. What was wanted after the fact was
the lost draft; a fingerprint would not have returned it. Markdown is small
enough that keeping it costs nothing, and a scaffolded project deliberately does
**not** gitignore `.paperforge/`.

The stage verdicts are the other half: `figures ok, lint ok, build ok, verify
failed` is the link between a given set of sources and what the gates said about
them. A run that went badly is exactly the one worth being able to look at again,
so a failing run is still recorded.

## Reading a diff

```
20260824T010758Z-run-1-baseline -> 20260824T010923Z-run-3-cover-exempt
  verify     failed -> ok
  unchanged  demo-report.md
```

That is the distinction the record exists to make: the source did not change,
the *tool* did. Without it, "we fixed the report" and "we fixed the renderer"
look identical afterwards.

| Reported | Means |
|---|---|
| `rewritten` | the source, the annex or the rendered HTML differs |
| `unchanged` | byte-identical source and reading edition |
| `added` / `removed` | the manifest gained or lost a document |
| `repaginated` | only the print edition differs — see below |

## One thing it does not claim

Hashing an artifact implies a rebuild reproduces it. The HTML does, byte for
byte. **The Typst PDF does not reliably**: printed page numbers are *measured*,
by printing the document and reading the page back, so a different machine with
different fonts genuinely paginates differently. The PDF hash is recorded as
observed — the field is named `pdf_sha256_observed` — and a difference is
reported as `repaginated` rather than as a rewrite.

## What it cannot tell you

A record says what each run produced. It cannot say why one was better. The
judgment that separated a good pass from a poor one in the corpus above —
*"usable as an orientation narrative, not evidence-ready"* — is not something
any gate emits. What the record buys is the ability to put the two side by side
and see it.

## Related

`commands.md` · `manifest.md` · `verify.md` · `publishing.md`
