# The figures gate: canonical values

Not diagrams — see `diagrams.md` for those. This is `paperforge figures`, the
check that every document in a project agrees about a number.

The same value gets stated many times across a project: in one Vietnamese corpus
a single target is written out eight times across four documents, and a decision
number twelve times. Declare the canonical values once in a `figures.toml`
beside the sources, and every document is checked against them, so a figure
corrected in one place cannot quietly disagree with the rest.

```toml
[[figure]]
id      = "tfp-share"
label   = "TFP contribution to GDP growth by 2030"
context = "TFP"                                   # the line is about this fact when it matches
pattern = '\d{2}(?:,\d)?\s*[–-]\s*\d{2}(?:,\d)?\s*%'   # what a statement of it looks like
accept  = ["55–60%", "55-60%", "45,5–47,2%"]      # correct surface forms
```

## Checked, never substituted

Policy prose states a number several ways — "từ 10% trở lên", "≥10%/năm",
"trên 55–60%" — and templating would wreck the sentence. A finding is a
**disagreement**, not a style note: a line that discusses a declared fact and
states a value outside its accepted forms.

## Per-language surface forms

Vietnamese writes `50.000` where English writes `50,000`. Before language
editions existed the gate had no idea which language a file was in and reported
the correct translation as a disagreement:

```toml
[[figure]]
id      = "engineers"
pattern = '\d{2}[.,]\d{3}'
  [figure.surface]
  vi = ["50.000"]
  en = ["50,000"]
```

Each edition declares its language in the manifest, so the gate checks each file
against the right forms.

## Expect to tune the declarations

The first run on one corpus flagged "30.000 kỹ sư" against a target of 50.000 —
correctly spotted, and legitimate: it is the 2028–29 interim milestone, now
declared as an accepted form. A gate that is never adjusted is a gate nobody
reads.

## Related

`manifest.md` · `diagrams.md` · `lint.md`
