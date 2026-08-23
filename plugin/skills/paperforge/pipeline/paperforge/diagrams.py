"""Pre-render Mermaid diagrams to static inline SVG.

Rendering at build time rather than shipping the Mermaid runtime keeps the
document self-contained and fixes a real defect: with startOnLoad the library
reused one SVG id across diagrams and emitted several without a viewBox, so
they overlapped each other on the page.
"""
import html as ihtml
import json
import re
import tempfile
from pathlib import Path

from . import browser

# Narrow label wrapping keeps wide flowcharts legible in print: the interagency
# matrix goes from 2171px to 1471px, i.e. ~50% scale on A4 instead of ~34%.
CONFIG = """{
  startOnLoad:false, theme:'base', securityLevel:'loose',
  fontFamily:'"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif',
  themeVariables:{primaryColor:'#e8eef8',primaryTextColor:'#0b2545',primaryBorderColor:'#1c4a80',
    lineColor:'#1c4a80',secondaryColor:'#fdf3e3',tertiaryColor:'#f8fafd',fontSize:'14px',
    clusterBkg:'#f4f7fc',clusterBorder:'#c9d5e6',titleColor:'#0b2545',
    cScale0:'#0b2545',cScale1:'#1c4a80',cScale2:'#c2761a',
    cScaleLabel0:'#ffffff',cScaleLabel1:'#ffffff',cScaleLabel2:'#ffffff'},
  flowchart:{curve:'basis',useMaxWidth:true,htmlLabels:false,nodeSpacing:30,
    rankSpacing:50,wrappingWidth:135,padding:10},
  timeline:{useMaxWidth:true}
}"""

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<pre id="out"></pre>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
const srcs = __SRCS__;
mermaid.initialize(__CONFIG__);
const out=[];
for (let i=0;i<srcs.length;i++){
  try { const {svg} = await mermaid.render('dgm'+i, srcs[i]); out.push(svg); }
  catch(e){ out.push('ERROR: '+e.message); }
}
document.getElementById('out').textContent = JSON.stringify(out);
</script></body></html>"""


def sources(*markdown_files):
    """Mermaid blocks across the given documents, in reading order."""
    found = []
    for path in markdown_files:
        if path:
            found += re.findall(r'```mermaid\n(.*?)\n```',
                                Path(path).read_text(encoding='utf-8'), re.S)
    return found


def render(srcs, cache=None):
    """Render each diagram to SVG. Requires network access for the Mermaid module."""
    if not srcs:
        return []
    if cache and Path(cache).exists():
        cached = json.loads(Path(cache).read_text(encoding='utf-8'))
        # reuse only when the diagram sources are unchanged
        if isinstance(cached, dict) and cached.get('sources') == srcs:
            return cached['svgs']
    page = PAGE.replace('__SRCS__', json.dumps(srcs, ensure_ascii=False)).replace('__CONFIG__', CONFIG)
    with tempfile.TemporaryDirectory() as tmp:
        gen = Path(tmp) / 'render.html'
        gen.write_text(page, encoding='utf-8')
        dom = browser.dump_dom(gen.absolute().as_uri())
    m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    if not m or not m.group(1).strip():
        raise RuntimeError('diagram rendering produced nothing (Mermaid module unreachable?)')
    svgs = json.loads(ihtml.unescape(m.group(1)))
    bad = [i for i, s in enumerate(svgs) if s.startswith('ERROR')]
    if bad:
        raise RuntimeError('diagram %s failed: %s' % (bad, svgs[bad[0]][:160]))
    missing = [i for i, s in enumerate(svgs) if 'viewBox' not in s[:s.find('>')]]
    if missing:
        raise RuntimeError('diagram %s rendered without a viewBox and would overlap' % missing)
    if cache:
        Path(cache).write_text(json.dumps({'sources': srcs, 'svgs': svgs}, ensure_ascii=False),
                               encoding='utf-8')
    return svgs
