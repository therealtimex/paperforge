# Front matter

A manuscript's head is data, not prose. Authors carry affiliation markers, an
ORCID and a corresponding flag; the abstract and keywords are labelled and
localised; funding, conflict and ethics declarations belong at the end.

```toml
+++
abstract = "Physical AI reshapes production, and the window is narrow."
keywords = ["Physical AI", "Việt Nam", "robotics"]

[[author]]
name = "Trần Văn A"
affiliation = [1, 2]
orcid = "0000-0002-1825-0097"
corresponding = true
email = "a@example.gov.vn"

[[author]]
name = "Nguyễn Thị B"
affiliation = [2]

[affiliation]
1 = "Ministry of Foreign Affairs"
2 = "National Innovation Centre"

[declarations]
funding = "State budget programme 1493."
conflicts = "None declared."
+++
```

renders a byline with superscript markers, the affiliations beneath it, the
corresponding author's address, a labelled abstract and keyword line, and the
declarations at the foot of the document — in the reading, print and Word
editions. Not in a deck: a slide has no abstract.

## Why TOML

`tomllib` is in the standard library and the manifest is already TOML, so an
author has one syntax to know rather than two. This pipeline vendors reveal.js
and refuses pandoc rather than buy a dependency for one feature; a YAML parser
would be that trade made for exactly one block.

## One rule worth knowing

**Scalar keys go above the first table header.** That is TOML's rule, not ours,
and getting it wrong is quiet: `abstract = "..."` written below `[affiliation]`
becomes an *affiliation* called "abstract", and the abstract vanishes.

The gate names it rather than leaving you to wonder:

```
'abstract' was written after [affiliation], so TOML read it as an
affiliation. Move it above the first table header.
```

## What the gate refuses

| Reported | Why it matters |
|---|---|
| an affiliation marker that is not declared | invisible in the output, wrong for the reader |
| an affiliation nobody cites | usually a marker that was renumbered and missed |
| a malformed ORCID | not in `0000-0000-0000-0000` form |
| no author marked corresponding | most journals require one |
| a scalar key swallowed by `[affiliation]` | the trap above |
| an unclosed or malformed block | an author who mistyped it is told, not handed a document with no author list |

All blocking. A missing author list is not a formatting nit.

## Labels

`abstract`, `keywords`, `corresponding`, `funding`, `conflicts`, `ethics` and
`declarations` come from the profile — *Tóm tắt*, *摘要*, *الملخص* — like every
other rendered string. See `languages.md`.

## Related

`manifest.md` · `structure.md` · `cross-references.md` · `document-types.md`
