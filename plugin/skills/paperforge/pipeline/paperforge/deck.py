"""Markdown -> a reveal.js presentation, self-contained.

reveal.js is vendored and inlined rather than loaded from a CDN, so a deck
behaves like every other Paperforge document: it opens offline, from a USB
stick or an email attachment, with no network at view time.

Slide conventions
-----------------
    ## Heading        starts a new slide
    ---               explicit slide break
    > notes: ...      speaker notes (blockquote whose first line is "notes:")

Diagrams carry over from the report unchanged; dense comparison tables do not,
and `audit()` reports the ones that will not read at projection size.
"""
import html as ihtml
import re
from pathlib import Path

from . import profile
from .markdown import FIG, SVGS, convert, inline, parse_head

THEME = Path(__file__).parent / 'theme'
VENDOR = Path(__file__).parent / 'vendor/revealjs'

# Beyond this a table stops being readable from the back of a room.
TABLE_LIMIT = {'rows': 7, 'cols': 5}


def _notes(chunk):
    """Split speaker notes out of a slide's markdown."""
    body, notes = [], []
    collecting = False
    for line in chunk:
        stripped = line.strip()
        if re.match(r'^>\s*notes:', stripped, re.I):
            collecting = True
            notes.append(re.sub(r'^>\s*notes:\s*', '', stripped, flags=re.I))
        elif collecting and stripped.startswith('>'):
            notes.append(re.sub(r'^>\s?', '', stripped))
        else:
            collecting = False
            body.append(line)
    return body, notes


def slides(lines):
    """Cut the body into slides on `##` headings and explicit rules."""
    chunks, current = [], []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## ') or re.fullmatch(r'-{3,}', stripped):
            if any(l.strip() for l in current):
                chunks.append(current)
            current = [] if not stripped.startswith('## ') else [line]
        else:
            current.append(line)
    if any(l.strip() for l in current):
        chunks.append(current)
    return chunks


def count_words(text, units='spaces'):
    """Slide length. Scripts without word spaces are counted by character, or a
    dense Chinese slide registers as three or four "words" and never trips the
    length check."""
    if units == 'characters':
        dense = len(re.findall(r'[\u3000-\u9fff\uff00-\uffef\u0e00-\u0e7f]', text))
        latin = len(re.findall(r'[A-Za-z0-9]+', text))
        return int(dense / 2.2) + latin      # ~2 characters carry a word
    return len(re.findall(r'\S+', text))


def audit(html, units='spaces'):
    """Slides that will not survive projection."""
    warnings = []
    for i, section in enumerate(re.findall(r'<section[^>]*>(.*?)</section>', html, re.S), 1):
        rows = section.count('<tr>')
        cols = max([len(re.findall(r'<t[hd][ >]', r)) for r in
                    re.findall(r'<tr>(.*?)</tr>', section, re.S)] or [0])
        if rows > TABLE_LIMIT['rows'] or cols > TABLE_LIMIT['cols']:
            warnings.append('slide %d: table %dx%d exceeds %dx%d and will not read '
                            'from the back of a room' %
                            (i, rows, cols, TABLE_LIMIT['rows'], TABLE_LIMIT['cols']))
        # a diagram's labels are not slide prose; strip SVG before counting
        prose = re.sub(r'<svg.*?</svg>', ' ', section, flags=re.S)
        words = count_words(re.sub(r'<[^>]+>', ' ', prose), units)
        if words > 130:
            warnings.append('slide %d: %d words; a slide is not a page' % (i, words))
    return warnings


def build(source, output, svgs=None, kind_fallback=None, prof=None):
    prof = prof or profile.load('vi')
    import paperforge.markdown as _md
    _md.PROF = prof
    kind_fallback = kind_fallback or prof['labels']['deck']
    SVGS[:] = svgs or []
    FIG.update(n=0, base=0, label=prof['labels']['figure'])
    lines = Path(source).read_text(encoding='utf-8').replace('\r\n', '\n').split('\n')

    head_end = next((i for i, l in enumerate(lines) if re.fullmatch(r'-{3,}', l.strip())), 0)
    h1, subtitle, meta, lede = parse_head(lines[:head_end])
    title = subtitle or h1 or kind_fallback
    kind = h1 if subtitle else kind_fallback

    cover = ['<section class="deck-title">',
             '<p class="deck-kind">%s</p>' % inline(kind),
             '<h1>%s</h1>' % inline(title)]
    if lede:
        cover.append('<div class="deck-lede">%s</div>' % convert(lede, []))
    if meta:
        cover.append('<dl class="deck-meta">%s</dl>' % ''.join(
            '<dt>%s</dt><dd>%s</dd>' % (ihtml.escape(k), inline(v)) for k, v in meta))
    cover.append('</section>')

    out = ['\n'.join(cover)]
    for chunk in slides(lines[head_end + 1:]):
        body, notes = _notes(chunk)
        html = convert(body, [])
        if notes:
            html += '\n<aside class="notes">%s</aside>' % convert(notes, [])
        out.append('<section>\n%s\n</section>' % html)

    shell = (THEME / 'deck.html').read_text(encoding='utf-8')
    filled = {
        'LANG': prof['lang'],
        'DIR': prof.get('direction', 'ltr'),
        'TITLE': ihtml.escape(re.sub(r'\s+', ' ', title)),
        'RESET': (VENDOR / 'reset.css').read_text(encoding='utf-8'),
        'REVEAL_CSS': (VENDOR / 'reveal.css').read_text(encoding='utf-8'),
        'THEME_CSS': (THEME / 'deck.css').read_text(encoding='utf-8'),
        'REVEAL_JS': (VENDOR / 'reveal.js').read_text(encoding='utf-8'),
        'SLIDES': '\n'.join(out),
    }
    for key, value in filled.items():
        shell = shell.replace('{{%s}}' % key, value)
    Path(output).write_text(shell, encoding='utf-8')
    return {'bytes': len(shell.encode('utf-8')), 'slides': len(out),
            'diagrams': FIG['n'],
            'warnings': audit(shell, prof.get('word_units', 'spaces'))}
