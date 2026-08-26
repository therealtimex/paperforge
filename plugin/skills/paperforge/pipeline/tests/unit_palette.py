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


HEX = re.compile(r'#[0-9a-fA-F]{6}\b')

# Read from the palette instead, and stated as an exception rather than left
# out silently: a gate that quietly skips a file reads as covering it.
#   diagrams.py   Mermaid's theme variables are a different vocabulary from
#                 these tokens, and the diagram cache would have to key on the
#                 palette as well - github.com/therealtimex/paperforge/issues/22
EMITTERS = ('typst.py', 'docx.py')


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


def main():
    root = Path(__file__).resolve().parents[1] / 'paperforge'

    print('the trap: a colour literal in an emitter')
    for name in EMITTERS:
        found = literals((root / name).read_text(encoding='utf-8'))
        check('%s takes every colour from the palette' % name, not found)
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
    unknown = sorted(used - set(palette.TOKENS))
    check('every token the stylesheets consume is declared in the table',
          not unknown)
    if unknown:
        print('       orphaned: %s' % ', '.join(unknown))
    dead = sorted(set(palette.TOKENS) - used)
    check('and every token in the table is consumed by a stylesheet', not dead)
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
    check('thirteen colour tokens, and the fonts are not among them',
          len(palette.COLOURS) == 13 and 'sans' not in palette.COLOURS)

    return measured()


def _root_of(css):
    m = re.search(r':root \{(.*?)\n\}', css, re.S)
    return sorted(re.findall(r'--([a-z0-9-]+):', m.group(1))) if m else []


# Every value distinct from every shipped default, so a token that failed to
# apply cannot be mistaken for one that applied and happened to match. An
# earlier version of this file set `ink-soft` to the shipped `#4a5568` and could
# not tell the two apart.
BRAND = {'navy': '#5b2333', 'navy-2': '#7a3145', 'navy-3': '#9a4058',
         'amber': '#2f6d5b', 'amber-soft': '#eaf3f0', 'red': '#8c2f39',
         'ink': '#231f20', 'ink-soft': '#7a5c00', 'muted': '#7a736b',
         'bg': '#f7f4ef', 'paper': '#fffdf9', 'line': '#e3ddd4',
         'line-soft': '#d8d2c8'}
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

> A callout, which each edition used to give a colour of its own.

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
        md.build(src, html_out, prof=prof, brand=BRAND, organisation='Paperforge',
                 contents_heading='CONTENTS')
        html = html_out.read_text(encoding='utf-8')
        missing = sorted(k for k, v in BRAND.items() if v not in html)
        check('the reading edition carries all thirteen tokens', not missing)
        if missing:
            print('       missing: %s' % ', '.join(missing))

        pdf_out = work / 'paper.pdf'
        try:
            typst.build(src, pdf_out, prof, brand=BRAND, organisation='Paperforge',
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

        docx_out = work / 'paper.docx'
        docx_mod.build(src, docx_out, prof, brand=BRAND, organisation='Paperforge',
                       contents_heading='CONTENTS')
        with zipfile.ZipFile(docx_out) as z:
            word = (z.read('word/document.xml') + z.read('word/styles.xml')).decode('utf-8')
        for token in ('navy', 'ink', 'amber', 'muted', 'ink-soft'):
            check('Word sets %s from the project palette' % token,
                  BRAND[token].lstrip('#').upper() in word.upper())

    return 1 if failures else 0


if __name__ == '__main__':
    print(__doc__.strip().split('\n')[0])
    code = main()
    if failures:
        print('\n%d check(s) failed:' % len(failures))
        for f in failures:
            print('  - %s' % f)
    sys.exit(code)
