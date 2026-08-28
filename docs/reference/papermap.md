# Papermap

```bash
paperforge map           # for a reader
paperforge map --json    # for a machine
paperforge map --out map.txt
```

Nobody reads a repository into a model's context. It is parsed, and what gets
sent is a map of symbols — files, functions, and which calls which. A paper has
structure too, and most of it is already declared. What it usually lacks is a
map of the paragraph-level claims that behave like functions: stated in one
place, drawn on in another.

```
report.md
  sec-methods  Methods
    claim-mle
      gist:    MLE is consistent under A1-A3
      uses:    @white2019, fig-sim-bias
      used-by: claim-finite
  sec-results  Results
    claim-finite
      gist:    -
      uses:    claim-mle
fig-sim-bias  bias vs n for the two estimators
  used-by: claim-mle
cites: white2019
note: nothing-uses-it      claim-finite  (nothing draws on this; the finding, or a leftover)
```

## Everything on it is read from the source

Sections and floats come from the label table. A claim's edges come from the
references and citations inside its own paragraph, plus whatever `uses=` its
author declared — see `claims.md`. `used-by` is the inverse, computed.

Nothing is inferred and nothing is summarised. A gist is the one thing on the
map written by a person, and it is stored, checked and printed, never generated.

## Notes are not findings

| Note | Means |
|---|---|
| `nothing-uses-it` | no claim draws on this one |
| `no-gist` | a labelled claim with nothing said about it |
| `never-referred-to` | a float declared and printed, mentioned in no prose |

**`nothing-uses-it` is deliberately not a gate.** A claim nothing uses is
usually the *finding* — resting on everything below it and supporting nothing
above it. Every well-formed argument has at least one, so a refusal for it would
report a defect on every correct paper. It is worth seeing, and a reader is the
one who can tell a conclusion from a leftover.

`never-referred-to` and `no-gist` also appear as `lint` warnings, where they
belong to a document. Here they belong to a map.

## Related

`claims.md` · `cross-references.md` · `brief.md` · `commands.md`
