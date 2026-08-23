"""Printed page numbers: measure them from the PDF, never estimate them.

Two traps this guards against, both of which produced plausible-looking numbers
during development:
  * the contents pages repeat every heading verbatim, so a heading can appear to
    live on the contents page it is listed on;
  * an annex section heading is worded identically to its entry in the annex's
    own summary list, so entries resolved onto the summary instead of the section.
Hence: contents pages are excluded, headings resolve in document order and never
backwards, and a section that forces a page break must open the page it claims.
"""
import html as ihtml
import json
import logging
import re
import warnings

from . import profile



def _pdfplumber():
    """Imported on use, not on import: the cheap checks must run on a machine
    with no PDF tooling, and a module-level import made the whole CLI unusable
    without it - which is how the CI contract job first failed."""
    warnings.filterwarnings('ignore')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)   # noisy FontBBox complaints
    import pdfplumber
    return pdfplumber



def norm(t, fold_diacritics=True):
    """Shared with the renderer so page matching sees the same text it built."""
    return profile.normalise(ihtml.unescape(re.sub(r'<[^>]+>', ' ', t)), fold_diacritics)


def extractable(pdf_path, source_chars, floor=0.45):
    """How much of the document's text can be read back out of the PDF.

    Page numbers and the pagination check both work by reading the PDF's text.
    Chrome embeds some fonts - CJK body faces among them - without a usable
    ToUnicode map, so the glyphs are drawn but cannot be read back: a Chinese
    fixture returned 16% of its source. Detect that and decline, rather than
    silently reporting no page numbers and a document full of "empty" pages.
    """
    with _pdfplumber().open(pdf_path) as pdf:
        got = sum(len((page.extract_text() or '').strip()) for page in pdf.pages)
    ratio = got / max(1, source_chars)
    return {'ratio': ratio, 'usable': ratio >= floor, 'extracted': got,
            'source': source_chars}


def contents_pages(pages, doc, contents_anchor):
    """Pages occupied by MỤC LỤC: they echo every title and must never match.

    The contents is one contiguous run, so walk forward from where it starts.
    A body page that happens to carry several short headings (2.7-2.10 share a
    page) is not contiguous with it and is therefore not excluded.
    """
    i = doc.find('<h2 id="%s"' % contents_anchor)
    block = re.sub(r'<span class="toc-pg">\d+</span>', '', doc[i:doc.find('<h2 ', i + 10)])
    labels = [norm(m.group(1))[:40] for m in
              re.finditer(r'<li>((?:(?!<[uo]l>|</li>).)*?)(?:</li>|<[uo]l>)', block, re.S)]
    # A fixed length floor here is the trap that has now bitten three separate
    # checks: a legitimately short entry ("2. Sources") can never clear it. With
    # every label filtered out, the search below scored every page zero and
    # silently returned the cover - exempting the wrong page entirely. Drop the
    # short ones only while enough remain to discriminate.
    discriminating = [l for l in labels if len(l) > 15]
    labels = discriminating if len(discriminating) >= 3 else [l for l in labels if l]
    if not labels:
        return set()
    hits = lambda t: sum(l in t for l in labels)

    start = max(range(len(pages)), key=lambda n: (hits(pages[n]), -n))
    if not hits(pages[start]):          # the contents could not be located
        return set()
    # the run threshold scales for the same reason: with two entries, four is
    # unreachable and the contents could never span a page
    floor = max(2, min(4, len(labels)))
    run = {start}
    n = start + 1                       # the contents may run onto later pages
    while n < len(pages) and hits(pages[n]) >= floor:
        run.add(n)
        n += 1
    n = start - 1                       # ...and may have begun on earlier ones
    while n >= 0 and hits(pages[n]) >= floor:
        run.add(n)
        n -= 1
    return run


def measure(html_path, pdf_path, contents_anchor):
    """Return {heading id: printed page}, omitting anything unverifiable."""
    doc = open(html_path, encoding='utf-8').read()
    body = doc[doc.index('<main>'):doc.index('</main>')]
    # a "part" heading forces a page break, so it can only be at the top of a page;
    # that distinguishes it from the same words appearing in a summary list
    heads = []
    for m in re.finditer(r'<(h[234])([^>]*)>(.*?)(?:<a class="anchor")', body, re.S):
        attrs, text = m.group(2), norm(m.group(3))
        hid = re.search(r'id="([^"]+)"', attrs)
        if hid and text:
            # 2 = opens the page; 1 = near the top (the annex title sits under a badge)
            breaks = 2 if 'part' in attrs else (1 if 'annex-title' in attrs else 0)
            heads.append((hid.group(1), text, breaks))

    with _pdfplumber().open(pdf_path) as pdf:
        pages = [norm(p.extract_text() or '') for p in pdf.pages]
    total = len(pages)
    skip = contents_pages(pages, doc, contents_anchor)

    found, missed, lo = {}, [], 0
    for hid, text, breaks in heads:
        words = text.split()
        hit = None
        # "Context" is 7 characters. A fixed 12-character floor skipped every
        # short heading; a heading that must OPEN its page can be matched on a
        # short probe without risking a false hit, so scale the floor to how
        # strong the positional constraint is.
        floor = 5 if breaks == 2 else 12
        for size in (9, 6, 4):
            probe = ' '.join(words[:size])
            if len(probe) < floor:
                continue
            if breaks == 2:      # must open the page it is on
                hit = next((n for n in range(lo, total)
                            if n not in skip and pages[n].startswith(probe)), None)
            elif breaks == 1:    # must be at the very top of the page
                hit = next((n for n in range(lo, total)
                            if n not in skip and probe in pages[n][:160]), None)
            else:
                hit = next((n for n in range(lo, total)
                            if n not in skip and probe in pages[n]), None)
            if hit is not None:
                break
        if hit is None:
            missed.append(hid)
            continue
        found[hid] = hit + 1
        lo = hit                      # document order: never resolve backwards

    return found, {'pages': total, 'contents': sorted(n + 1 for n in skip),
                   'headings': len(heads), 'located': len(found), 'unresolved': missed}


def _contents_pages(pages, labels):
    """The contents block: one contiguous run of pages echoing the entry list."""
    hits = lambda t: sum(l[:40] in t for l in labels if len(l) > 15)
    start = max(range(len(pages)), key=lambda n: (hits(pages[n]), -n))
    run, n = {start}, start + 1
    while n < len(pages) and hits(pages[n]) >= 4:
        run.add(n); n += 1
    n = start - 1
    while n >= 0 and hits(pages[n]) >= 4:
        run.add(n); n -= 1
    return run


def audit(html_path, pdf_path, contents_anchor, part_pattern, section_pattern,
          annex_phrase):
    """Confirm every printed page number against the PDF.

    Deliberately does not reuse the matching the build used: a number is only
    accepted if the entry's own wording is found where it claims to be.
    """
    doc = open(html_path, encoding='utf-8').read()
    i = doc.find('<h2 id="%s"' % contents_anchor)
    if i < 0:
        return {'entries': 0, 'confirmed': 0, 'untestable': 0, 'wrong': []}
    block = doc[i:doc.find('<h2 ', i + 10)]
    entries = [(norm(m.group(2)), int(m.group(1))) for m in re.finditer(
        r'<li><span class="toc-pg">(\d+)</span>((?:(?!<[uo]l>|</li>).)*?)(?:</li>|<[uo]l>)',
        block, re.S)]
    if not entries:
        return {'entries': 0, 'confirmed': 0, 'untestable': 0, 'wrong': []}

    with _pdfplumber().open(pdf_path) as pdf:
        pages = [norm(p.extract_text() or '') for p in pdf.pages]
    toc = _contents_pages(pages, [l for l, _ in entries])

    confirmed = untestable = 0
    wrong, prev = [], 0
    for label, page in entries:
        if not 1 <= page <= len(pages):
            wrong.append((label[:60], page, 'page out of range')); continue
        if page - 1 in toc:
            wrong.append((label[:60], page, 'points back into the contents')); continue
        if page < prev:
            wrong.append((label[:60], page, 'runs backwards (after p%d)' % prev)); continue
        prev = page
        text = pages[page - 1]

        # A part or annex section forces a page break, so it must open its page.
        # This is what catches a number aimed at a summary list of the same words.
        section = re.match(part_pattern, label) or re.match(section_pattern, label) \
            or annex_phrase in label
        if section:
            m = re.match(section_pattern, label)
            want = [w for w in re.sub(section_pattern, '', label).split()
                    if len(w) > 1][:6]
            head = text[:170]
            # Scale the requirement to the words available: a short title such as
            # "PART I: CONTEXT" reduces to ['part','context'] and could never
            # reach a fixed threshold of four.
            need = len(want) if len(want) <= 3 else max(3, len(want) - 1)
            if (want and sum(w in head for w in want) >= need) or \
               (m and head.startswith(m.group(1) + ' ')):
                confirmed += 1
            else:
                wrong.append((label[:60], page, 'section does not open this page'))
            continue

        words = [w for w in label.split() if len(w) > 1 and not w.isdigit()][:5]
        if len(' '.join(words)) < 10:
            untestable += 1                      # too few distinctive words to test
        elif ' '.join(words) in text or sum(w in text for w in words) >= max(3, len(words) - 1):
            confirmed += 1
        else:
            wrong.append((label[:60], page, 'wording not found on this page'))

    return {'entries': len(entries), 'confirmed': confirmed,
            'untestable': untestable, 'wrong': wrong}
