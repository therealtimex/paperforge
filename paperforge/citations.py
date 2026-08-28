"""Citations and a bibliography, formatted once by Typst for both editions.

Sources cite in the familiar bracketed form, `[@smith2020]`. Typst formats both
the in-text marker and the reference list from a BibTeX file, in a named style,
so no CSL processing is reimplemented here.

For the PDF the citations are native. For the HTML they are rendered through
Typst's HTML export, which is explicitly experimental - so it is used for
nothing but the citations and the reference list. If that output ever changes
shape, citation formatting is the only thing affected, and `parse` fails loudly
rather than emitting something wrong.
"""
import re
import subprocess
import tempfile
from pathlib import Path

from . import require

CITE_RE = re.compile(r'\[(@[A-Za-z][\w:.-]*(?:\s*;\s*@[A-Za-z][\w:.-]*)*)\]')
KEY_RE = re.compile(r'@([A-Za-z][\w:.-]*)')


def find(text):
    """Cited keys in source order, de-duplicated."""
    keys, seen = [], set()
    for m in CITE_RE.finditer(text):
        for key in KEY_RE.findall(m.group(1)):
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


ENTRY_RE = re.compile(r'@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@|\Z)', re.S)


def dangling_dates(bib_path, keys=None):
    """Entries that will render with a stray comma for want of a full date.

    APA formats `@legislation` and `@misc` as "(year, month day)". Given only a
    year the comma is still emitted - "(2026,)." - which reads as a typo in the
    finished document. `@report` has no such template and is clean. Reported
    rather than corrected: the fix is a full date or a different entry type,
    and both are the author's call.
    """
    text = Path(bib_path).read_text(encoding='utf-8')
    flagged = []
    for kind, key, body in ENTRY_RE.findall(text):
        if keys is not None and key not in keys:
            continue
        if kind.lower() in ('legislation', 'misc') and 'year' in body and 'month' not in body:
            flagged.append((key, kind.lower()))
    return flagged


def render(keys, bib_path, style='apa', title='References', lang='en'):
    """Formatted in-text markers and a reference list, as HTML fragments."""
    if not keys:
        return {}, ''
    bib = Path(bib_path)
    if not bib.exists():
        raise FileNotFoundError('bibliography not found: %s' % bib)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / bib.name).write_bytes(bib.read_bytes())
        # one marked paragraph per key, so each rendering can be recovered
        # the language must reach the citation renderer too, or a Vietnamese
        # document gets English month names in its reference list
        lines = ['#set text(size: 10pt, lang: "%s")' % lang]
        for i, key in enumerate(keys):
            lines.append('KEYMARK%d @%s' % (i, key))
        lines.append('#bibliography("%s", title: "%s", style: "%s")'
                     % (bib.name, title, style))
        (tmp / 'c.typ').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
        require.demand('typst', 'this document has citations, whose bibliography '
                                 'is formatted by typst')
        r = subprocess.run(['typst', 'compile', 'c.typ', 'c.html',
                            '--format', 'html', '--features', 'html'],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('citations failed to render:\n%s' % r.stderr.strip()[:600])
        return parse((tmp / 'c.html').read_text(encoding='utf-8'), keys)


def parse(page, keys):
    """Pull the per-key markers and the reference list out of Typst's HTML.

    Raises rather than guessing: Typst's HTML export is experimental, and a
    silent change of shape would put unformatted citations into a document.
    """
    markers = {}
    for i, key in enumerate(keys):
        m = re.search(r'KEYMARK%d\s*(.*?)</p>' % i, page, re.S)
        if not m or not m.group(1).strip():
            raise RuntimeError('could not recover the rendering of citation %r; '
                               "Typst's HTML export may have changed shape" % key)
        markers[key] = m.group(1).strip()
    biblio = re.search(r'<section[^>]*doc-bibliography.*?</section>', page, re.S)
    if not biblio:
        raise RuntimeError("no reference list in Typst's HTML output")
    return markers, biblio.group(0)


def to_html(markers, group):
    """Render one bracketed citation, which may name several keys."""
    parts = [markers.get(k) for k in KEY_RE.findall(group)]
    if any(p is None for p in parts):
        return None
    return '<span class="citation">%s</span>' % '; '.join(parts)
