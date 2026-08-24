# Maths

Sources carry **Typst maths syntax, not LaTeX.**

```markdown
Inline: $a/b$ and $sum_(i=1)^n x_i$.

$$
"TFP share" = 1 - alpha ("K"/"Y") - beta ("L"/"Y")
$$
```

| Want | Typst | Not |
|---|---|---|
| fraction | `a/b` or `frac(a, b)` | `\frac{a}{b}` |
| sum | `sum_(i=1)^n` | `\sum_{i=1}^{n}` |
| Greek | `alpha`, `beta` | `\alpha` |
| text in maths | `"TFP share"` | `\text{TFP share}` |
| derivative | `(dif y)/(dif x)` | `\frac{dy}{dx}` |
| multi-letter name | `"ROI"` | `ROI` (reads as `R O I`) |

Bare multi-letter identifiers are the usual trap: `ROI` sets as three variables.
Quote anything meant as a word.

## Numbered equations

Put a label on the closing fence and the equation is numbered, and referable:

```markdown
$$
"TFP" = g_Y - alpha g_K - (1 - alpha) g_L
$$ {#eq-solow}

The residual is defined in @eq-solow.
```

renders the equation with **(1)** beside it and `@eq-solow` as *Equation 1*,
localised from the profile — *Công thức 1*, *公式 1*. The number comes from the
resolver, not from each emitter's own equation numbering, so all three editions
call the same equation the same thing. See `cross-references.md`.

An unlabelled display block is unnumbered, exactly as before.

## Delimiters

`$$…$$` is display, `$…$` is inline. Inline requires a non-space character
beside each delimiter, so `$5 and $10` in prose is money, not maths — this is
deliberate and it is why currency in policy text does not need escaping.

## How it renders

Typst sets the maths natively in the PDF. For the reading edition the same
expressions are pre-rendered by Typst to **tight-bounding-box SVG**, with the
baseline offset read from the SVG's own transform, so inline maths sits on the
text baseline exactly rather than by eye. Unlike the Mermaid diagrams this SVG
carries no `<foreignObject>`, so it embeds directly, stays vector, and needs no
runtime library.

Both editions therefore come from one engine and cannot disagree.

## Untested territory

The Vietnamese corpus contains no maths, so this has **no real-corpus back
test** — only the fixtures. Check the first document that uses it in both
editions.

## Related

`citations.md` (the other Typst-backed feature) · `print.md`
