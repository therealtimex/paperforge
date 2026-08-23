"""Integrity checks for a built document.

Cheap structural checks run always; the browser-backed ones (layout overflow,
print clipping) are opt-in because they cost a Chrome launch each.
"""
import html as ihtml
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from . import browser

VOID = {'br', 'hr', 'meta', 'img', 'link', 'input', 'source', 'col', 'area', 'base',
        'wbr', 'embed', 'path', 'circle', 'line', 'rect', 'polygon', 'polyline',
        'ellipse', 'use', 'stop', 'image'}


class _Balance(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append('stray </%s>' % tag)
        elif self.stack[-1] != tag:
            self.errors.append('expected </%s>, got </%s>' % (self.stack[-1], tag))
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i] == tag:
                    del self.stack[i:]
                    break
        else:
            self.stack.pop()


def _visible(html):
    text = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', html, flags=re.S)
    text = re.sub(r'<svg.*?</svg>', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', ' ', text)))


def coverage(html, *sources):
    """Every substantive markdown line must survive into the rendered document."""
    visible, missing = _visible(html), []
    for path in sources:
        if not path:
            continue
        fenced = False
        for n, line in enumerate(Path(path).read_text(encoding='utf-8').split('\n'), 1):
            s = line.strip()
            if s.startswith('```'):
                fenced = not fenced
                continue
            if fenced or not s or set(s) <= set('-*_|: '):
                continue
            t = re.sub(r'^\s*(#{1,6}|[-*+]|\d+\.|>)\s*', '', s)
            t = re.sub(r'\s*\{[^{}]*\}\s*$', '', t)   # explicit heading attributes
            t = re.sub(r'\[!\w+\]', '', t)
            t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
            t = re.sub(r'<br\s*/?>', ' ', t)
            t = t.replace('**', '').replace('*', '').replace('`', '').replace('|', ' ')
            t = re.sub(r'\s+', ' ', ihtml.unescape(t)).strip()
            if len(t) < 12:
                continue
            frags = [f.strip() for f in re.split(r'[:;]', t) if len(f.strip()) >= 25]
            probe = (frags[0] if frags else t)[:55]
            # metadata lines are split across styled spans, so a contiguous probe
            # legitimately fails on them; fall back to a word-presence test
            if probe not in visible:
                # metadata renders as separate spans, which drops the "Key:"
                # colon, so compare on words stripped of punctuation
                words = [w.strip(':.,;()') for w in probe.split()]
                words = [w for w in words if len(w) > 2]
                if sum(w in visible for w in words) < max(2, len(words) - 1):
                    missing.append((Path(path).name, n, s[:60]))
    return missing


def check(html_path, *sources):
    html = Path(html_path).read_text(encoding='utf-8')
    b = _Balance(); b.feed(html)
    ids = set(re.findall(r'id="([^"]+)"', html))
    links = re.findall(r'href="#([^"]+)"', html)
    return {
        'unclosed': b.stack, 'markup_errors': b.errors,
        'missing_content': coverage(html, *sources),
        'broken_anchors': [l for l in links if l not in ids],
        'anchors': len(links),
        'external_refs': sorted(set(re.findall(r'(?:src|href)="(https?://[^"]+)"', html))),
        'leaks': leaks(_visible(html), Path(html_path).name),
        'diagrams': html.count('class="dgm"'), 'tables': html.count('<table>'),
    }


LAYOUT_PROBE = """<pre id="pf"></pre><script>window.addEventListener('load',function(){
var R={viewport:innerWidth,scrollW:document.documentElement.scrollWidth,over:0,clip:0};
R.over=document.documentElement.scrollWidth>innerWidth+1?1:0;
document.querySelectorAll('.table-frame,figure.diagram').forEach(function(f){
 var s=f.querySelector('.table-wrap,.dgm'); if(!s)return;
 if(getComputedStyle(s).overflowX==='visible'&&s.scrollWidth>s.clientWidth+2)R.clip++;});
document.getElementById('pf').textContent=JSON.stringify(R);});</script></body>"""


def layout(html_path, widths=(1440, 1024, 768, 390)):
    """No document should overflow horizontally at any supported width."""
    html = Path(html_path).read_text(encoding='utf-8')
    probe = Path(html_path).with_suffix('.probe.html')
    probe.write_text(html.replace('</body>', LAYOUT_PROBE), encoding='utf-8')
    results = {}
    try:
        for w in widths:
            dom = browser.dump_dom(probe.absolute().as_uri(), budget=9000,
                                   extra=['--window-size=%d,900' % w])
            m = re.search(r'<pre id="pf">(.*?)</pre>', dom, re.S)
            data = json.loads(ihtml.unescape(m.group(1))) if m else {}
            results[w] = data
    finally:
        probe.unlink(missing_ok=True)
    return results


# A character is not the same amount of writing in every script. 80 Latin
# characters is roughly thirteen words; the same thirteen words in Chinese or
# Japanese occupy about a third of that, because the script has no word spaces
# and one character carries a morpheme. Counting characters and comparing every
# script to a Latin floor is the fourth fixed threshold in this pipeline that a
# perfectly good document could never clear.
SCRIPT_FLOOR = {'cjk': 30}


def pagination(pdf_path, floor=80, exempt=(), script='latin'):
    """Pages carrying almost nothing: a stranded heading or an orphaned frame.

    Added after a two-line part banner was found split across two pages, each
    holding one line and nothing else. Visually busy pages (a diagram) are
    exempt - they are sparse in text but not empty.

    The floor is a heuristic. In Latin script, observed stranded headings ran
    22-74 characters while a genuinely short but complete section ran 91+, so
    the default sits between the two and brevity is not reported as a defect.
    `script` rescales it; see SCRIPT_FLOOR.
    """
    floor = SCRIPT_FLOOR.get(script, floor)
    import logging
    import warnings
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    import pdfplumber
    thin = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for n, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or '').strip()
            if n in exempt:          # the contents is legitimately short
                continue
            if len(text) < floor and len(page.curves) + len(page.images) < 20:
                thin.append({'page': n, 'chars': len(text),
                             'text': text[:60].replace('\n', ' ')})
    return {'pages': total, 'thin': thin}


# Raw markup that reached the rendered page. Found after <br> in table cells
# survived into the PDF: the Typst emitter escaped the angle brackets before it
# tried to replace the tag, so the replace could never match. The HTML edition
# handled the same tag correctly, so no single-edition gate had anything to
# compare against.
LEAKS = (
    ('html-tag', re.compile(r'</?[a-zA-Z][a-zA-Z0-9]{0,9}\s*/?>')),
    ('entity', re.compile(r'&(?:[a-zA-Z][a-zA-Z0-9]{1,30}|#\d+);')),
    ('emphasis', re.compile(r'\*\*|(?<![\w`])__(?![\w_])')),
    ('escape', re.compile(r'\\[#$*_<>@\[\]]')),
)


def leaks(text, where=''):
    """Markdown or HTML source that should have been consumed by the renderer."""
    from html.entities import html5
    found = []
    for kind, pattern in LEAKS:
        for m in pattern.finditer(text):
            # "KH&CN;" is prose, "&nbsp;" is an unrendered entity: only names
            # HTML actually defines count, rather than anything ampersand-shaped
            if kind == 'entity' and not m.group(0)[1] == '#' \
                    and m.group(0)[1:] not in html5:
                continue
            s = max(0, m.start() - 25)
            found.append({'kind': kind, 'where': where, 'match': m.group(0),
                          'context': text[s:m.end() + 25].replace('\n', ' ')})
    return found


def print_leaks(pdf_path):
    """The same check against the print edition, reported per page."""
    import logging
    import warnings
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    import pdfplumber
    found = []
    with pdfplumber.open(pdf_path) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            found += leaks(page.extract_text() or '', 'p%d' % n)
    return found
