# Assembling a document from several files

```toml
[[collection.document]]
source  = "thesis.md"                 # front matter, title, contents
include = ["ch01-intro.md",
           "ch02-method.md",
           "ch03-results.md"]
annex   = "appendix.md"
```

An included file is **body markdown**: a fragment of one document, not a
document. It carries no front matter and no title of its own. The pieces are
concatenated in declared order before anything parses them.

## Why concatenate first

Because everything that matters has to see the whole work. Cross-references
resolve across files — a chapter can say `@fig-shift` about a figure declared
three files earlier — figures and tables number continuously, and the contents
covers the lot. None of that is possible if each file is parsed alone.

The same reasoning applies to the gates: lint, the coverage check, the
reference and citation gates, and the run record all read **every** file. A
document assembled from five files whose provenance records one of them is a
record that lies.

## The annex is unchanged

`annex` keeps its own treatment: its own title, its own page break, and its
figure numbering restarts — *Figure A1* is the annex's first. An `include` is
not an annex; it is more of the same document.

## What the gate refuses

| Reported | Why |
|---|---|
| an include that is not there | a chapter silently missing is worse than a build that stops |
| an include opening with `+++` | a fragment is not a document; only the source carries the head |
| the source listed as its own include | it would be assembled twice |

## When to split

A report of twenty pages is fine in one file. A thesis is not: a two-hundred
page markdown file is neither editable by a human nor reviewable in a diff. The
threshold is whoever has to work on it, not a page count.

## Related

`structure.md` · `front-matter.md` · `cross-references.md` · `provenance.md`
