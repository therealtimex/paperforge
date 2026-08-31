#!/usr/bin/env python3
"""One palette, four surfaces.

A colour written as a literal in an emitter is correct by default and
unbrandable forever, and it reads as finished code either way. That is why this
file gates the *form* rather than any particular colour: a hex literal appearing
anywhere in the Typst or Word emitter fails the first check here, whatever it is
and however right it looks.

Measured before the fix, on the English fixture with all thirteen colour tokens
declared: three reached the print edition and two reached Word. The most
frequent non-black colour on the printed page, at 818 occurrences, was one the
project had overridden and could not change - `#6b7789`, the shipped `muted`,
in every running head and every metadata label. The measured half below fails
against that build.

Needs typst, python-docx and pdfplumber.
"""
import io
import re
import sys
import tempfile
import tokenize
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import docx as docx_mod, markdown as md, palette, profile, typst

failures = []


def check(label, condition):
    print('  %-64s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


# Three digits as well as six: #fff is a colour chosen where it is written just
# as #ffffff is, and a gate about literals that shorthand walks through is not a
# gate. Widening it found the last one - a white matte painted behind every
# rasterised diagram, now transparent, because the way not to have to brand a
# colour is not to paint it.
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')

EMITTERS = ('typst.py', 'docx.py', 'diagrams.py', 'markdown.py', 'deck.py',
            'papermap.py')
SHEETS = ('paperforge.css', 'deck.css', 'map.css')

# Translucency counts. A stylesheet free of hex and full of rgba() is a
# stylesheet whose topbar still does not follow the brand, which was true of
# this one for exactly one commit.
PAINT = re.compile(r'#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(')


def literals_source(path):
    """A module's source with comments stripped, for the paint check."""
    return ' '.join(tok.string for tok in
                    tokenize.generate_tokens(io.StringIO(
                        path.read_text(encoding='utf-8')).readline)
                    if tok.type != tokenize.COMMENT)


def literals(source):
    """Colour literals in Python source, comments excluded.

    Comments are stripped rather than searched because the reason a colour was
    once wrong is worth writing down beside the fix, and AGENTS.md says not to
    delete those. Strings are *not* stripped: a literal in an emitter lives in
    the markup it emits, which is a string.
    """
    stripped = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type != tokenize.COMMENT:
            stripped.append(tok.string)
    return HEX.findall(' '.join(stripped))


# WCAG 2.1 relative luminance and contrast, both straight from the spec, so a
# floor here means what it means to everybody else.
def _lum(hex_colour):
    h = hex_colour.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# The cover is a gradient, so every stop counts: text that clears the darkest
# end and fails the lightest has still failed.
COVER_BACKS = ('navy-deep', 'navy-dark', 'navy-mid')
ON_COVER = ('paper',         # the cover's own text colour
            'navy-wash',     # the lede, and what bold text inside it inherits
            'amber-bright')  # the kind badge, links, code
FLOOR = 4.5                  # WCAG AA for body text


def main():
    root = Path(__file__).resolve().parents[1] / 'paperforge'

    print('the trap: a colour literal in an emitter')
    for name in EMITTERS:
        found = literals((root / name).read_text(encoding='utf-8'))
        check('%s takes every colour from the palette' % name, not found)
        if found:
            print('       found: %s' % ', '.join(sorted(set(found))))

    for sheet in SHEETS:
        found = PAINT.findall((root / 'theme' / sheet).read_text(encoding='utf-8'))
        check('%s paints with tokens, not colours' % sheet, not found)
        if found:
            print('       found %d: %s' % (len(found), ', '.join(sorted(set(found)))))
    # the emitters' own CSS is the same surface: RTL_CSS lives in markdown.py
    # and carried the scroll fade in rgba long after the stylesheet stopped
    found = PAINT.findall(literals_source(root / 'markdown.py'))
    check('the emitters ship no CSS colours either', not found)
    if found:
        print('       found: %s' % ', '.join(sorted(set(found))))

    # the gate has to fail on the thing it was written for, so here is that
    # thing: the line as typst.py carried it until this commit
    defect = 'x = \'#text(fill: rgb("#6b7789"))\'  # the shipped muted\n'
    check('and the check fails on the literal it was written for',
          literals(defect) == ['#6b7789'])
    check('a colour named only in a comment is not a finding',
          literals('# once printed #fdf3e3, which was not a token\nx = 1\n') == [])

    print('the tokens are declared once')
    themes = {}
    for sheet in ('paperforge.css', 'deck.css'):
        text = palette.stylesheet(root / 'theme' / sheet)
        themes[sheet] = text
        check('%s has its :root filled from the table' % sheet,
              '{{TOKENS}}' not in text and '--navy: #243b53' in text)
    check('the two stylesheets declare the same tokens',
          _root_of(themes['paperforge.css']) == _root_of(themes['deck.css']))

    # a stylesheet with nowhere to put the tokens would otherwise ship with no
    # :root at all, and every var() in it would fall back to nothing
    with tempfile.TemporaryDirectory() as tmp:
        bare = Path(tmp) / 'bare.css'
        bare.write_text('body { color: var(--ink); }', encoding='utf-8')
        try:
            palette.stylesheet(bare)
            refused = False
        except ValueError as exc:
            refused = 'bare.css' in str(exc)
    check('a stylesheet with no {{TOKENS}} block is refused, by name', refused)

    # A project's override is matched to the stylesheet by name. Rename a token
    # in the CSS and every project overriding it silently stops applying, with
    # nothing saying so - the deck defect with the arrow reversed.
    used = set()
    for text in themes.values():
        used |= set(re.findall(r'var\(--([a-z0-9-]+)', text))
    # set per element as an inline style, so no project can address it
    used.discard('logo-h')
    # a veil and the shadow are emitted alongside the table rather than in it,
    # because each is written twice - a resolved value and a color-mix
    declared = set(palette.TOKENS) | set(palette.VEILS) | {'shadow'}
    unknown = sorted(used - declared)
    check('every token the stylesheets consume is declared in the table',
          not unknown)
    if unknown:
        print('       orphaned: %s' % ', '.join(unknown))
    # A token nothing reads is a token a project can set with no effect, which
    # is the same silence this whole file is about, pointed the other way. The
    # surfaces are the two stylesheets, the two mappings, and the emitters' own
    # calls - listing them here is also the record of where each token is used.
    live = set(used) | set(palette.MERMAID.values())
    live |= {tok for triple in palette.CALLOUTS.values() for tok in triple}
    READS = re.compile(r"colour\('([a-z0-9-]+)'\)"
                       r"|_colour\(brand, '([a-z0-9-]+)'\)"
                       r"|(?:PAL|tokens)\['([a-z0-9-]+)'\]")
    for name in EMITTERS:
        live |= {tok for group in READS.findall((root / name).read_text(encoding='utf-8'))
                 for tok in group if tok}
    live |= {base for base, _ in palette.VEILS.values()}
    dead = sorted(declared - live - set(palette.VEILS) - {'shadow'})
    check('and every token in the table is read by something', not dead)
    if dead:
        print('       unused: %s' % ', '.join(dead))

    print('resolution order')
    prof = profile.load('vi')
    check('the defaults stand alone', palette.resolve()['navy'] == '#243b53')
    check("the profile's faces beat the shipped stack",
          palette.resolve(prof)['sans'] == prof['fonts']['sans'])
    check("and the project's own beat the profile's",
          palette.resolve(prof, {'sans': 'Palatino'})['sans'] == 'Palatino')
    check('a token the table does not know is carried through, not dropped',
          palette.resolve(prof, {'houseblue': '#010203'})['houseblue'] == '#010203')
    check('thirty-one colour tokens, and the fonts are not among them',
          len(palette.COLOURS) == 31 and 'sans' not in palette.COLOURS)

    print('the shade table')
    # The finding that produced the table: the palette was already a shade
    # system and nobody had written the system down. If a fitted row stops
    # reproducing the value it was fitted to, the table has become a different
    # design rather than a description of this one.
    SHIPPED = {'navy-2': '#334e68', 'navy-3': '#486581', 'navy-soft': '#e8eef8',
               'amber-soft': '#faf6ec', 'amber-line': '#f0dcbb',
               'red-soft': '#fdf0f0', 'red-line': '#f0c9c9',
               'green-soft': '#eefaf3', 'green-line': '#c6e9d6',
               'ink-soft': '#4a5568', 'muted': '#6b7789', 'line': '#dfe4ec',
               'line-soft': '#eef1f6', 'bg': '#eef1f6'}
    off = {k: (v, palette.TOKENS[k]) for k, v in SHIPPED.items()
           if palette.TOKENS[k] != v}
    check('every shade reproduces the value it was fitted to, exactly', not off)
    if off:
        print('       drifted: %s' % off)
    check('six bases, twenty-five shades, eleven veils',
          len(palette.BASE) - 2 == 6 and len(palette.SHADES) == 25
          and len(palette.VEILS) == 11)
    house = palette.resolve(None, {'navy': '#5b2333'})
    check('one base recolours everything hanging off it',
          house['navy-deep'] != palette.TOKENS['navy-deep']
          and house['navy-tint'] != palette.TOKENS['navy-tint'])
    check('and leaves the shades of other bases alone',
          house['muted'] == palette.TOKENS['muted']
          and house['amber-deep'] == palette.TOKENS['amber-deep'])
    pinned = palette.resolve(None, {'navy': '#5b2333', 'navy-deep': '#010203'})
    check('a shade the project names for itself wins over the rule',
          pinned['navy-deep'] == '#010203' and pinned['navy-dark'] == house['navy-dark'])
    check('a shade keeps its base hue', palette.shade('#5b2333', 90.0)[1:3] > '9')

    # This count has been written down by hand beside the thing it counts three
    # times and been wrong twice - "seven" while thirteen were declared, then
    # "thirteen" while twenty were. A number in prose next to the table it
    # describes is a copy, and copies drift; this is the same defect the whole
    # module exists for, in English rather than in CSS.
    WORDS = {20: 'Twenty', 24: 'Twenty-four', 30: 'Thirty', 31: 'Thirty-one',
             32: 'Thirty-two'}
    doc = (Path(__file__).resolve().parents[1]
           / 'docs/reference/branding.md').read_text(encoding='utf-8')
    said = re.search(r'^(\w+(?:-\w+)?) colour tokens\b', doc, re.M)
    check('branding.md states the number of tokens the table declares',
          said is not None and said.group(1) == WORDS.get(len(palette.COLOURS)))
    if said and said.group(1) != WORDS.get(len(palette.COLOURS)):
        print('       branding.md says %r, the table declares %d'
              % (said.group(1), len(palette.COLOURS)))

    print('callout variants')
    check('a warning is not a note', palette.variant('warning')[0] == 'red')
    check('the type is read case-insensitively, as the class name is',
          palette.variant('WARNING') == palette.variant('warning'))
    check('a type nothing styles is a note, in every edition',
          palette.variant('caution') == palette.variant('note'))
    check('and so is a blockquote with no type at all',
          palette.variant(None) == palette.variant('note'))

    print('translucency')
    check('every veil names a token that exists',
          all(base in palette.TOKENS for base, _ in palette.VEILS.values()))
    rules = palette.veil_rules(palette.TOKENS)
    check('each veil is written twice: a resolved value, then a color-mix',
          len(rules) == 2 * len(palette.VEILS)
          and rules[0].count('color-mix') == 0 and 'color-mix' in rules[1])
    check('the fallback is the resolved colour, not an approximation of it',
          '  --navy-veil: %sf7;' % palette.TOKENS['navy-dark'] in rules)
    housed = palette.resolve(None, {'navy': '#5b2333'})
    check('a veil follows its base rather than the shipped default',
          '  --navy-veil: %sf7;' % housed['navy-dark']
          in palette.veil_rules(housed))
    check('and only the veils whose base moved are re-emitted',
          [r for r in palette.veil_rules(housed, {'navy-dark'})
           if r.startswith('  --amber')] == [])
    check('and the shadow, which is two of them, follows too',
          palette.shadow(housed) != palette.shadow(palette.TOKENS)
          and housed['navy-dark'].lstrip('#') in palette.shadow(housed))

    print('the diagram theme')
    from paperforge import diagrams
    themed = diagrams.config(palette.resolve(None, BRAND))
    check('a diagram is drawn in the document palette',
          BRAND['navy-soft'] in themed and BRAND['navy'] in themed)
    check('and no longer in the one it kept for itself',
          '#0b2545' not in themed and '#1c4a80' not in themed)
    check("the diagram takes the document's font stack too",
          palette.resolve(profile.load('vi'))['sans'] in
          diagrams.config(palette.resolve(profile.load('vi'))))
    check('every Mermaid variable names a token that exists',
          all(v in palette.TOKENS for v in palette.MERMAID.values()))

    return measured()


def _root_of(css):
    m = re.search(r':root \{(.*?)\n\}', css, re.S)
    return sorted(re.findall(r'--([a-z0-9-]+):', m.group(1))) if m else []


# Six colours, which is all a project writes. Everything the editions are then
# checked for is *derived* from these, so this is a test of the shade table and
# not a list of values handed to the emitters one at a time.
#
# Every one is distinct from every shipped default, so a token that failed to
# apply cannot be mistaken for one that applied and happened to match. An
# earlier version of this file set `ink-soft` to the shipped `#4a5568` and could
# not tell the two apart.
HOUSE = {'navy': '#5b2333', 'amber': '#2f6d5b', 'red': '#8c2f39',
         'green': '#3f6d2f', 'ink': '#231f20', 'paper': '#fffdf9'}
BRAND = {k: v for k, v in palette.resolve(None, HOUSE).items() if v.startswith('#')}
BY_VALUE = {v: k for k, v in BRAND.items()}

SOURCE = """# WORKING PAPER
## The Palette Reaches The Page

---
**Prepared by:** Paperforge
**Date:** 2026

---

## CONTENTS

- [1. Findings](#findings)

## 1. FINDINGS {.part}

Body text, which the print edition set in black whatever the project asked for.

### 1.1. A subheading

> A note, which each edition used to give a colour of its own.

> [!WARNING]
> A warning, which two of the three editions used to draw as a note.

> [!TIP]
> A tip, likewise.

> [!CAUTION]
> A type no edition styles, which must come out a note in all of them.

| Measure | Value |
|---|---|
| Tokens | Thirteen |

: A table caption {#tbl-one}

---

Closing prose after a rule.
"""


def _hex(colour):
    """A pdfplumber colour as #rrggbb, or None if it is not one."""
    if colour is None:
        return None
    if isinstance(colour, (int, float)):
        colour = (colour, colour, colour)
    colour = tuple(colour)
    if len(colour) == 1:
        colour *= 3
    if len(colour) == 4:
        c, m, y, k = colour
        colour = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    if len(colour) != 3:
        return None
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v * 255))) for v in colour)


def printed(pdf_path):
    """Every colour actually painted on the page.

    Only the slot the paint operator used counts. pdfplumber reports both a fill
    and a stroke colour on every object regardless of which was applied, and
    reading both reported 44 black objects on a page whose every mark was a
    brand colour - the graphics answer to reading a running head as body text.
    """
    import warnings, logging
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    import pdfplumber
    seen = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for ch in page.chars:
                seen[_hex(ch['non_stroking_color'])] = seen.get(
                    _hex(ch['non_stroking_color']), 0) + 1
            for objs in (page.rects, page.lines, page.curves):
                for ob in objs:
                    for flag, key in (('fill', 'non_stroking_color'),
                                      ('stroke', 'stroking_color')):
                        if ob.get(flag):
                            hx = _hex(ob.get(key))
                            seen[hx] = seen.get(hx, 0) + 1
    seen.pop(None, None)
    return seen


def measured():
    print('measured: the palette on the artifact')
    prof = profile.load('en')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        src = work / 'paper.md'
        src.write_text(SOURCE, encoding='utf-8')

        html_out = work / 'paper.html'
        md.build(src, html_out, prof=prof, brand=HOUSE, organisation='Paperforge',
                 contents_heading='CONTENTS')
        html = html_out.read_text(encoding='utf-8')
        missing = sorted(k for k, v in BRAND.items() if v not in html)
        check('six declared colours reach the reading edition as thirty-one',
              not missing)
        if missing:
            print('       missing: %s' % ', '.join(missing))

        pdf_out = work / 'paper.pdf'
        try:
            typst.build(src, pdf_out, prof, brand=HOUSE, organisation='Paperforge',
                        contents_heading='CONTENTS', cache=work)
        except (RuntimeError, FileNotFoundError) as exc:
            check('the print edition builds (typst present?): %s' % str(exc)[:40], False)
            return 1 if failures else 0

        seen = printed(pdf_out)
        stray = sorted(hx for hx in seen if hx not in BY_VALUE and hx != '#ffffff')
        check('every colour on the printed page is a token or white', not stray)
        if stray:
            print('       stray: %s' % ', '.join('%s x%d' % (s, seen[s]) for s in stray))
        # the 818-occurrence defect, named: the shipped muted in every running
        # head and metadata label, on a document that declared its own
        check('the shipped muted is nowhere on the page', '#6b7789' not in seen)
        check('the shipped line is nowhere on the page', '#dfe4ec' not in seen)
        check('body text is the project ink, not black',
              seen.get(BRAND['ink'], 0) > 100 and '#000000' not in seen)
        for token in ('navy', 'navy-3', 'amber', 'muted', 'line', 'amber-soft'):
            check('print sets %s from the project palette' % token,
                  BRAND[token] in seen)

        # the defect this half was written for: `> [!WARNING]` printed in the
        # note colours, because the type was matched, stripped and discarded one
        # line above the block that needed it
        for kind, token in (('warning', 'red-soft'), ('tip', 'green-soft')):
            check('a %s prints in its own fill, not the note fill' % kind,
                  BRAND[token] in seen)
        check('and the hairline around a callout is drawn, as on screen',
              BRAND['red-line'] in seen and BRAND['amber-line'] in seen)
        check('a type nothing styles falls back to the note fill',
              # four callouts, three variants: note and caution share a fill
              seen[BRAND['amber-soft']] >= 2)

        docx_out = work / 'paper.docx'
        docx_mod.build(src, docx_out, prof, brand=HOUSE, organisation='Paperforge',
                       contents_heading='CONTENTS')
        with zipfile.ZipFile(docx_out) as z:
            word = (z.read('word/document.xml') + z.read('word/styles.xml')).decode('utf-8')
        for token in ('navy', 'ink', 'amber', 'muted', 'ink-soft'):
            check('Word sets %s from the project palette' % token,
                  BRAND[token].lstrip('#').upper() in word.upper())
        for kind, token in (('warning', 'red'), ('tip', 'green')):
            check('Word tells a %s from a note' % kind,
                  BRAND[token].lstrip('#').upper() in word.upper())

    print('what the cover paints, and what stays readable on it')
    # `strong { color:var(--navy-strong) }` is ink for white paper, and a rule
    # that colours an element directly beats the colour it inherits from the
    # cover - so the bolded lede of a 95-page dossier rendered at 1.09:1
    # against its own background, through nineteen rounds of review. Nothing
    # here read a contrast ratio, which is why it took a screenshot.
    tokens = palette.resolve({}, {})
    for fg in ON_COVER:
        worst = min(contrast(tokens[fg], tokens[bg]) for bg in COVER_BACKS)
        check('%s reads on the cover (%.1f:1)' % (fg, worst), worst >= FLOOR)
    # the specific one that shipped: body ink, which nothing on the cover may
    # inherit or be given
    worst = max(contrast(tokens['navy-strong'], tokens[bg]) for bg in COVER_BACKS)
    check('body ink on the cover would be unreadable, so nothing may set it',
          worst < FLOOR)
    css = (Path(__file__).resolve().parents[1]
           / 'paperforge' / 'theme' / 'paperforge.css').read_text(encoding='utf-8')
    # what the rule does, not how it is typed: an exact-string match on a
    # hand-maintained stylesheet fires on reformatting that changes nothing
    check('and the cover restates what a bare element rule would take',
          bool(re.search(r'\.cover\s+strong\s*\{[^}]*color\s*:\s*inherit', css)))
    # justification without hyphenation opens rivers on a wide measure, which
    # is why `main p` carries both. A lede set centred read badly at the twenty
    # lines a real one runs to, and the block had no fixture to be seen in
    lede = re.search(r'\.cover-lede\s+p\s*\{([^}]*)\}', css)
    check('the lede is set as prose, not as a caption',
          bool(lede) and 'justify' in lede.group(1))
    # the property name is not the setting: `hyphens:none` is in this same
    # stylesheet, and would have passed a check that only looked for the word
    check('and justified text is hyphenated, as the body is',
          bool(lede) and re.search(r'hyphens\s*:\s*auto', lede.group(1)))
    # justification is worst on the narrowest measure, which is why the body
    # gives it up there; the lede has to give it up with the body
    narrow = re.search(r'@media\s*\(max-width:900px\)\s*\{(.*?)\n\}', css, re.S)
    check('and both give it up on a narrow measure',
          bool(narrow) and re.search(r'\.cover-lede\s+p[^{]*\{[^}]*left|'
                                     r'main p[^{]*\.cover-lede p\s*\{[^}]*left',
                                     narrow.group(1)))

    return 1 if failures else 0


if __name__ == '__main__':
    print(__doc__.strip().split('\n')[0])
    code = main()
    if failures:
        print('\n%d check(s) failed:' % len(failures))
        for f in failures:
            print('  - %s' % f)
    sys.exit(code)
