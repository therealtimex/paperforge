"""Check that the reading edition and the print edition agree.

Two independent emitters render the same source, and they drifted within a day
of the second one being added: parts opened a page in the HTML and ran on
mid-page in the PDF, the annex likewise, and figure captions gained a duplicate
label. None of it was caught, because every existing gate looks at one edition
at a time and each was individually valid.

This compares the two: the same headings must open a page, and both must carry
the same figures.
"""
import html as ihtml
import logging
import re
import warnings

from . import profile


def _pdfplumber():
    """Imported on use, not on import: the cheap checks - bundle drift,
    reference links, version alignment - must run with no PDF tooling present,
    and a module-level import made the whole CLI unusable without it."""
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    import pdfplumber
    return pdfplumber


def _norm(text, fold=True):
    return profile.normalise(ihtml.unescape(re.sub(r'<[^>]+>', ' ', text)), fold)


def page_openers_html(html):
    """Headings the HTML gives a page break: parts, annex sections, annex head."""
    body = html[html.index('<main>'):html.index('</main>')]
    openers = []
    for m in re.finditer(r'<(h2)([^>]*)>(.*?)(?:<a class="anchor")', body, re.S):
        attrs, text = m.group(2), m.group(3)
        if 'part' in attrs or 'annex-title' in attrs:
            openers.append(_norm(text))
    return [o for o in openers if o]


def page_openers_pdf(pdf_path, candidates, words=6):
    """Which of those actually open a page in the PDF.

    The contents repeats every heading, so pages carrying several candidates are
    excluded outright - the same trap that caught the page-number measurement.
    A heading is resolved first against page tops, in document order and never
    backwards; only if that fails is it looked for anywhere.
    """
    with _pdfplumber().open(pdf_path) as pdf:
        pages = [_norm(p.extract_text() or '') for p in pdf.pages]
    probes = {h: ' '.join(h.split()[:words]) for h in candidates if len(h.split()) >= 1}
    skip = {i for i, pg in enumerate(pages)
            if sum(pr in pg for pr in probes.values() if len(pr) > 8) >= 4}

    # Resolved independently rather than in document order: excluding the
    # contents pages already prevents the trap that order was guarding against,
    # and a short heading matching late otherwise blocked every heading before it.
    found = {}
    for heading in candidates:
        probe = probes.get(heading, '')
        if len(probe) < 5:
            continue
        hit = next((i for i, pg in enumerate(pages) if i not in skip
                    and probe in ' '.join(pg.split()[:26])), None)
        if hit is not None:
            found[heading] = (hit + 1, True)
            continue
        # the contents heading itself opens the contents page, which is skipped
        hit = next((i for i in sorted(skip) if probe in ' '.join(pages[i].split()[:26])), None)
        if hit is not None:
            found[heading] = (hit + 1, True)
            continue
        if len(probe) >= 8:
            hit = next((i for i, pg in enumerate(pages) if i not in skip and probe in pg), None)
            if hit is not None:
                found[heading] = (hit + 1, False)
    return found


def compare(html_path, pdf_path, fold=True):
    html = open(html_path, encoding='utf-8').read()
    expected = page_openers_html(html)
    actual = page_openers_pdf(pdf_path, expected)

    mid_page = [(h, p) for h in expected for p, top in [actual.get(h, (None, True))]
                if p and not top]
    missing = [h for h in expected if h not in actual]

    html_figs = html.count('<figcaption>')
    with _pdfplumber().open(pdf_path) as pdf:
        pdf_figs = sum(len(p.images) for p in pdf.pages)

    return {'expected_openers': len(expected), 'mid_page': mid_page, 'unlocated': missing,
            'figures_html': html_figs, 'figures_pdf': pdf_figs,
            'figures_agree': html_figs == pdf_figs}


def _html_headings(html):
    """Every heading the reading edition renders, in order."""
    body = html[html.index('<main>'):html.index('</main>')]
    found = []
    for m in re.finditer(r'<h[1-4][^>]*>(.*?)</h[1-4]>', body, re.S):
        text = re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).strip()
        text = text.rstrip('#').strip()      # the anchor glyph the HTML appends
        if text:
            found.append(text)
    return found


def compare_docx(html_path, docx_path):
    """Word against the reading edition.

    The third emitter. The first two drifted within a day of the second
    existing, and this one drifted on its first build: it carried the embedded
    annex's own title, subtitle and contents, which the reading edition drops
    because the annex is folded into its parent. Counts alone would have hidden
    it - the totals were close - so the headings are compared as sets.

    Pages are not compared. Word paginates the document when it opens it, so
    there is nothing here to hold against a measured page number.
    """
    from . import docx as docx_mod
    web = _html_headings(open(html_path, encoding='utf-8').read())
    built = docx_mod.structure(docx_path)
    doc_heads = [h.rstrip('#').strip() for h in built['headings']]
    html_figs = open(html_path, encoding='utf-8').read().count('<figcaption>')
    html_tables = open(html_path, encoding='utf-8').read().count('<table>')
    return {
        'missing': [h for h in web if h not in doc_heads],
        'extra': [h for h in doc_heads if h not in web],
        'headings_html': len(web), 'headings_docx': len(doc_heads),
        'figures_html': html_figs, 'figures_docx': built['figures'],
        'tables_html': html_tables, 'tables_docx': built['tables'],
    }
