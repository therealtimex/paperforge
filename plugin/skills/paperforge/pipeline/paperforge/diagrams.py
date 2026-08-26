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

from . import browser, palette

# Narrow label wrapping keeps wide flowcharts legible in print: the interagency
# matrix goes from 2171px to 1471px, i.e. ~50% scale on A4 instead of ~34%.
SHAPE = """  flowchart:{curve:'basis',useMaxWidth:true,htmlLabels:false,nodeSpacing:30,
    rankSpacing:50,wrappingWidth:135,padding:10},
  timeline:{useMaxWidth:true}"""


def config(tokens=None):
    """Mermaid's configuration for this document's palette.

    This was a module constant carrying twelve colours of its own - a third
    palette, near enough the document's to look deliberate and far enough to be
    visible beside it. A project that declared a full brand got a branded cover,
    branded parts, branded tables and Paperforge-blue flowcharts between them.

    The font stack comes from the palette too. The constant named `"Segoe UI"`
    first and no Vietnamese-safe face at all, so a diagram's labels were set in
    whatever the profile had been chosen to avoid.
    """
    tokens = tokens or palette.TOKENS
    theme = ',\n    '.join("%s:'%s'" % (k, tokens[v])
                           for k, v in palette.MERMAID.items())
    return ("{\n  startOnLoad:false, theme:'base', securityLevel:'loose',\n"
            "  fontFamily:'%s',\n"
            "  themeVariables:{fontSize:'14px',\n    %s,\n"
            # reversed out of the scale colours above, so it is the absence of
            # ink rather than a colour the project can set
            "    cScaleLabel0:'white',cScaleLabel1:'white',cScaleLabel2:'white'},\n"
            "%s\n}" % (tokens['sans'].replace("'", "\\'"), theme, SHAPE))

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


def render(srcs, cache=None, tokens=None):
    """Render each diagram to SVG. Requires network access for the Mermaid module."""
    if not srcs:
        return []
    theme = config(tokens)
    if cache and Path(cache).exists():
        cached = json.loads(Path(cache).read_text(encoding='utf-8'))
        # Reuse only when the sources *and* the theme are unchanged. The key was
        # the sources alone, so changing a palette and rebuilding served the
        # diagrams back in the old colours - on a machine where everything else
        # had changed, with the build reporting success. A cache written before
        # this carries no theme, compares unequal, and re-renders.
        if (isinstance(cached, dict) and cached.get('sources') == srcs
                and cached.get('theme') == theme):
            return cached['svgs']
    page = PAGE.replace('__SRCS__', json.dumps(srcs, ensure_ascii=False)).replace('__CONFIG__', theme)
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
        Path(cache).write_text(
            json.dumps({'sources': srcs, 'theme': theme, 'svgs': svgs},
                       ensure_ascii=False), encoding='utf-8')
    return svgs
