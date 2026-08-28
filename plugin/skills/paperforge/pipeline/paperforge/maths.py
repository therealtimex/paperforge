"""Maths, rendered once by Typst and used by both outputs.

The source carries Typst maths syntax. That is an authoring decision - the
agent writing the document knows the notation it needs - and it lets one
renderer serve both editions: Typst sets the maths natively in the PDF, and the
same expressions are pre-rendered to SVG for the HTML.

Typst emits tight-box SVG with no <foreignObject>, so unlike the Mermaid
diagrams these embed directly, stay vector, and need no runtime library.
"""
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from . import require

# $$...$$ is display, $...$ inline. The inline form requires non-space next to
# the delimiters so that prices ("$5 and $10") are not mistaken for maths.
DISPLAY_RE = re.compile(r'\$\$(.+?)\$\$', re.S)
INLINE_RE = re.compile(r'(?<![\w$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?![\w$])')


def find(text):
    """Every maths expression in a document, display first, in source order."""
    found = []
    for m in DISPLAY_RE.finditer(text):
        found.append(('display', m.group(1).strip()))
    for m in INLINE_RE.finditer(DISPLAY_RE.sub(' ', text)):
        found.append(('inline', m.group(1).strip()))
    seen, unique = set(), []
    for kind, expr in found:
        if (kind, expr) not in seen:
            seen.add((kind, expr))
            unique.append((kind, expr))
    return unique


def key(kind, expr):
    return '%s:%s' % (kind, hashlib.sha1(expr.encode('utf-8')).hexdigest()[:12])


def render(expressions, font='Georgia', size=11):
    """Render expressions to SVG in a single Typst run.

    Returns {key: {svg, width, height, depth}} where depth is how far the
    expression descends below the baseline - taken from the SVG's own transform,
    so inline maths sits on the text baseline exactly rather than by eye.
    """
    if not expressions:
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pages = []
        for kind, expr in expressions:
            body = '$ %s $' % expr if kind == 'display' else '$%s$' % expr
            pages.append(body)
        src = ('#set page(width: auto, height: auto, margin: 0pt, fill: none)\n'
               '#set text(size: %dpt, font: "%s")\n' % (size, font)
               + '\n#pagebreak()\n'.join(pages) + '\n')
        (tmp / 'm.typ').write_text(src, encoding='utf-8')
        require.demand('typst', 'this document has maths, which renders to SVG '
                                 'through typst even in the reading edition')
        r = subprocess.run(['typst', 'compile', 'm.typ', 'm-{p}.svg', '--format', 'svg'],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('maths failed to render:\n%s' % r.stderr.strip()[:600])
        out = {}
        for i, (kind, expr) in enumerate(expressions, 1):
            svg = (tmp / ('m-%d.svg' % i)).read_text(encoding='utf-8')
            head = svg[:svg.find('>')]
            width = float(re.search(r'width="([\d.]+)pt"', head).group(1))
            height = float(re.search(r'height="([\d.]+)pt"', head).group(1))
            base = re.search(r'matrix\(1 0 0 -1 [\d.-]+ ([\d.-]+)\)', svg)
            depth = height - float(base.group(1)) if base else 0.0
            out[key(kind, expr)] = {'svg': svg, 'width': width, 'height': height,
                                    'depth': max(0.0, depth), 'kind': kind}
        return out


def to_html(entry):
    """One expression as inline SVG, aligned on the text baseline."""
    svg = re.sub(r'^<svg ', '<svg role="math" ', entry['svg'].strip())
    svg = svg.replace('\n', '')
    if entry['kind'] == 'display':
        return ('<span class="maths-display">%s</span>' % svg)
    style = 'height:%.3fpt;width:%.3fpt;vertical-align:-%.3fpt' % (
        entry['height'], entry['width'], entry['depth'])
    return '<span class="maths" style="%s">%s</span>' % (style, svg)
