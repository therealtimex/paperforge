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

## What changed, not only which

```bash
paperforge runs --diff <a>,<b>            # which documents were rewritten
paperforge runs --diff <a>,<b> --sources  # what changed in them
```

A run keeps the sources themselves rather than their fingerprints, so the second
form is a unified diff computed from what was actually built — no repository
needed, and nothing that a rewritten history can take away.

**This is not a replacement for `git diff`, and not a competitor to it.** Git
records what somebody chose to commit; a run records what the pipeline built.
They diverge exactly where it matters: the draft that was lost here was never
committed. In a repository an author wants both — `git diff` for what has
changed since they last committed, `runs --diff --sources` for what changed
between two builds regardless of what anyone committed.

Backing the record with git was considered and rejected for the reason at the
top of this page: the record is a by-product of running the pipeline rather than
an act of discipline, and a commit is an act.

## Related

`commands.md` · `manifest.md` · `verify.md` · `publishing.md`

## Friction: what the pipeline made somebody do instead

`paperforge report "what happened"` writes a note under `.paperforge/friction/`,
beside the run records and for the same reason: it is a by-product of working,
not an act of discipline somebody has to remember.

```
paperforge report "the lede never reached the printed PDF, so I moved it into the body"
paperforge report --issue      # the latest note, as something to paste into a tracker
```

The note carries what an author cannot be expected to assemble — the pipeline
version, whether the project's guidance is current, what is missing from the
machine, and which run was the last one. *"Paperforge didn't work"* is not
diagnosable; those four things with a sentence are.

**Solve it and report it.** Working around a blocked pipeline is the right call
under a deadline. Four workarounds in one project — a document restructured to
dodge a defect, a script to generate claim markup, forty lines of interpreter
archaeology, a reviewer's own checking code — were each reasonable, and each
removed the only trace that anything was wrong. All four were found weeks later
by a person asking *"what did they have to write around us?"*, not by any gate.

`--issue` **prints**; it never files. An agent's reading of a symptom is usually
right and its reading of a cause often is not, and a tracker of plausible
misattributions is one nobody reads.
