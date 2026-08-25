"""Integrity checks for a built document.

Cheap structural checks run always; the browser-backed ones (layout overflow,
print clipping) are opt-in because they cost a Chrome launch each.
"""
import html as ihtml
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from . import browser, citations as cite_mod, maths as maths_mod, xref

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


def _visible(html, keep_code=True):
    text = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', html, flags=re.S)
    text = re.sub(r'<svg.*?</svg>', ' ', text, flags=re.S)
    if not keep_code:
        # a code span holds text the author deliberately wrote as literal
        # markup; reading it back as an unrendered tag is the checker failing
        # to tell "this rendered correctly" from "this did not render"
        text = re.sub(r'<pre>.*?</pre>|<code>.*?</code>', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', ' ', text)))


def coverage(html, *sources):
    """Every substantive markdown line must survive into the rendered document."""
    visible, missing = _visible(html), []
    for path in sources:
        if not path:
            continue
        fenced = display = False
        lines = Path(path).read_text(encoding='utf-8').split('\n')
        # front matter is TOML, not prose: it renders as a byline, an abstract
        # and a declarations block, so probing `abstract = "..."` for its own
        # text reports the whole head as missing content
        start = 0
        if lines and lines[0].strip() == '+++':
            close = next((i for i in range(1, len(lines))
                          if lines[i].strip() == '+++'), None)
            start = close + 1 if close is not None else 0
        for n, line in enumerate(lines[start:], start + 1):
            s = line.strip()
            if s.startswith('```'):
                fenced = not fenced
                continue
            # a display block writes its $$ fences on their own lines, so the
            # expression between them is never seen as maths by a line-at-a-time
            # substitution - it has to be tracked like a code fence
            if s == '$$':
                display = not display
                continue
            if fenced or display or not s or set(s) <= set('-*_|: '):
                continue
            t = re.sub(r'^\s*(#{1,6}|[-*+]|\d+\.|>)\s*', '', s)
            t = re.sub(r'\s*\{[^{}]*\}\s*$', '', t)   # explicit heading attributes
            t = re.sub(r'\[!\w+\]', '', t)
            t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
            # Constructs that do not render as their own text have to be
            # removed before probing, or the line they sit on is reported as
            # missing content. This list has grown four times, once per feature
            # - maths, citations, cross-references, front matter - and each time
            # the symptom was the same: a correct document failing coverage.
            # Anything added here that renders as something else belongs below.
            t = maths_mod.DISPLAY_RE.sub(' ', t)     # renders as an SVG image
            t = maths_mod.INLINE_RE.sub(' ', t)
            t = cite_mod.CITE_RE.sub(' ', t)         # renders as a formatted marker
            t = xref.REF_RE.sub(' ', t)              # renders as "Figure 3"
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
        'leaks': leaks(_visible(html, keep_code=False), Path(html_path).name),
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


URL_RE = re.compile(r'https?://[^\s)>\]|"<]+')


def print_truncation(pdf_path, *sources):
    """Citations the printed edition lost.

    Print does not scroll a wide table - it cuts the right-hand column off the
    page. In an evidence annex that is the column holding the sources, so a
    reader of the printed copy could not check a single one. It happened on a
    real report: a seven-column source ledger printed with every URL ending
    mid-token, and every other gate passed, because the reading edition scrolls
    and nothing compared the two.

    A URL is the right probe. It is unambiguous, it is exactly what gets lost,
    and losing one is not a formatting nit - it is the difference between an
    evidence annex and a list of assertions.

    What this cannot see: a table row taller than the page continues on the
    next one, and no reconstruction here joins a URL split across that break.
    Those come back as unlocated, which is why the finding is reported and not
    blocking - on the report that prompted it, three of twenty-six were
    page-spanning cells that were in fact intact. Treat a report as "look at
    these pages", not as "the document is broken".
    """
    import logging
    import warnings
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    import pdfplumber
    wanted = []
    for path in sources:
        if not path:
            continue
        for url in URL_RE.findall(Path(path).read_text(encoding='utf-8')):
            if url not in wanted:
                wanted.append(url.rstrip('.,;'))
    if not wanted:
        return {'checked': 0, 'unlocated': []}
    # A URL wrapped inside a table cell has its fragments on several lines, and
    # every other column's text sits between them - so a whole-page flatten
    # cannot see it. Rebuild each cell from the table geometry instead.
    # Reading order interleaves a wrapped URL with its neighbouring columns, so
    # a whole-page flatten only finds one whose neighbours happen to be blank.
    # Rebuilding each column strip in reading order is what survives both
    # wrapping and a row that continues onto the next page. All three views are
    # searched and a citation counts as present in any of them: a gate that
    # cries wolf over a correct annex is worse than no gate.
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(''.join(c['text'] for c in page.chars))
            edges = sorted({round(c[0]) for t in page.find_tables()
                            for row in t.rows for c in row.cells if c})
            for left, right in zip(edges, edges[1:] + [page.width]):
                strip = [c for c in page.chars if left - 1 <= c['x0'] < right]
                strip.sort(key=lambda c: (round(c['top'], 1), c['x0']))
                chunks.append(''.join(c['text'] for c in strip))
    flat = re.sub(r'\s+', '', ''.join(chunks))
    return {'checked': len(wanted),
            'unlocated': [u for u in wanted if re.sub(r'\s+', '', u) not in flat]}
