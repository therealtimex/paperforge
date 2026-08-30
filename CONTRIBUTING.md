# Contributing to Paperforge

Paperforge refuses to publish documents. That is its job, and it means a change
here can stop somebody's work at the worst moment — or, worse, quietly let
something wrong through. Almost everything below follows from that.

Read [`AGENTS.md`](AGENTS.md) first: it holds the doctrine, and each of its
sections exists because something plausible-looking shipped. [`specs/`](specs/)
holds the decisions that took an argument to settle, so you can tell a question
that is open from one that is closed.

## The rule that produced most of this code

**Measure before asserting; verify after building; prove a check catches the
defect it was written for.**

For a change that adds or alters a gate, that is not advice — it is what the
pull request has to show:

1. **Demonstrate the defect** against the artifact as it stood *before* your
   fix. Paste the wrong output. A description of a bug is not evidence of one.
2. **Fix it.**
3. **Reintroduce it** — a temporary patch, `git checkout main -- <file>`, a
   planted literal — and show your new check failing. A check that passes on
   broken code is not coverage; it reads as coverage, which is worse than
   nothing.
4. **Put the numbers in the commit message.** Not "improved matching": *"103%
   by volume, 0% by correspondence."*

If you cannot make your check fail, you have not written a check.

## What is in scope

A feature is in scope if Paperforge can **measure** it, out of scope if it
would have to **compose** it. The test is not whether the output would be
useful — it is whether a finding could be wrong in a way the author cannot
adjudicate. See [`specs/0001`](specs/0001-measure-not-compose.md); it answers
most feature requests in one sentence.

A gate reports a **finding**, not a style note. If it can fire on correct work,
it is wrong.

## Severity

Four, and the difference matters:

| | Means |
|---|---|
| `block` | a demonstrated contradiction; publication stops |
| `manual` | the check ran and the verdict is a person's; the finding must name the act that settles it |
| `warn` | worth a look; the author decides |
| `skip` | the check could not run, **and says why** |

Untestable is never "passed". A check that fires on correct work is worse than
one that admits it has nothing to say.

## Before you open a pull request

```bash
bin/paperforge plugin --check                 # bundle drift, reference links, one version
node scripts/node-runtime-contract.mjs        # Node matches the RealtimeX host
node scripts/check-plugin-manifest.mjs        # manifest matches the host contract
for t in tests/unit_*.py; do python3 "$t"; done
for f in tests/fixtures/*/ tests/backtest/; do
  bin/paperforge all --config "$PWD/$f/documents.toml"
done
```

`AGENTS.md` has the same list under coverage, which is what CI enforces.

Four things catch most mistakes before review:

- **`plugin --check` fails on drift.** `plugin/skills/paperforge/pipeline/` and
  `references/` are **generated**. Change the repo, then run `bin/paperforge
  plugin`. Never edit the copies.
- **Two emitters, one source.** `markdown.py` renders HTML, `typst.py` the
  print edition, `docx.py` Word. They are independent and they drift. Anything
  touching one must be checked against the others; `editions.py` compares them
  and has caught a figure present in three editions and missing from the fourth.
- **Add the shape to a fixture before writing the code.** The corpus decides
  what is tested. Every fixture illustrated itself with a Mermaid diagram, so
  the image path shipped broken for months with lint and verify both green.
  Ask which fixture will *use* your feature, and add it there first.
- **A number that was measured gets a row in
  [`specs/calibration.md`](specs/calibration.md)**, which is gated by
  `tests/unit_calibration.py`.

## Tests

`tests/unit_*.py` are plain scripts, not a framework: each prints a line per
check and exits non-zero. They exist for behaviour a fixture cannot reach.
Write the label so a failure reads as a sentence about the product —
*"a dangling reference refuses publication on its own"*, not *"test_publish_3"*.

Make a test **report** `FAIL` rather than raise, so a regression reads as a
failing check and not a traceback.

Coverage floors live in `scripts/check-coverage.py` and ratchet.

## Comments

Explain *why*, especially when the reason is a defect that once shipped. Those
comments are load-bearing — they are what stops the same mistake being made
again by somebody who reads the code and finds it reasonable. **Do not delete
them.** Several are the only surviving record of a measurement.

A deliberate exception is pinned as a **set**, not described as a tendency:
`SCREEN_ONLY`, `SKIP`, `SCRIPT_FLOOR` and the label kinds are asserted by exact
membership, so a fourth has to be argued for in the diff that adds it.

## Things that will bite you

- **No dependency the published document can see.** Chrome and the Mermaid CDN
  are build-time only. Anything reaching the output is inlined — including
  images, which is why they are data URIs rather than links.
- **The repository is public** and source-available under the RealTimeX
  licence. Files under `[internal]` in a manifest are never publishable, and
  published artifacts have unguessable URLs but are **not authenticated**.
- **External tools are not yours to install.** `bin/paperforge doctor` says what
  is missing and what it was for. A missing tool produces a loud `skip`, never
  a traceback and never a silent pass.
- **Vietnamese was the first language.** A second language is the only real
  proof that no assumption crept back in; that is what the `en`, `zh`, `ar` and
  `id` fixtures are for.

## Releasing

Tag `vX.Y.Z`. The workflow refuses the tag unless it matches the version in
`plugin/realtimex.plugin.json` and the skill frontmatter, re-runs every gate
from the tag rather than trusting the pull request, packages the plugin, builds
a document *from the unpacked zip*, and only then publishes the release with a
checksum.

If you have not cut one before, cut one when nothing depends on it.
