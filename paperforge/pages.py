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
import unicodedata
import warnings

from . import matching, profile



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


FENCE_RE = re.compile(r'```.*?```', re.S)


def extractable(pdf_path, source_text, floor=0.45, fold_diacritics=True, rtl=False):
    """Whether the PDF's text can be matched back to the document's own words.

    Page numbers and the pagination check both work by finding the source's
    wording on a printed page. Chrome embeds some fonts - CJK body faces among
    them - without a usable ToUnicode map, so the glyphs are drawn but cannot be
    read back. Decline in that case, rather than silently reporting no page
    numbers and a document full of "empty" pages.

    This counted characters once, and a character count is a claim about volume
    being read as a claim about legibility. An Arabic PDF returned 103% of its
    source by volume and 0% by correspondence: every word came back shaped into
    presentation forms and in visual order, so the text was all there and none
    of it matched anything. Volume ranged from 0.07 to 44 across the fixtures
    and separated nothing.

    So a sample of the source's own distinctive words is looked for in the
    extracted text. Measured across every fixture, documents whose print checks
    work score 0.75 to 0.97 and those whose do not score 0.00 to 0.08; the floor
    sits in that gap. `volume` is still reported, for a reader, and decides
    nothing.
    """
    with _pdfplumber().open(pdf_path) as pdf:
        got = '\n'.join((page.extract_text() or '') for page in pdf.pages)
    return correspondence(source_text, got, floor, fold_diacritics, rtl)


def correspondence(source_text, extracted, floor=0.45, fold_diacritics=True,
                   rtl=False):
    """The scoring, apart from the PDF, so it can be exercised without one."""
    from . import profile as profile_mod
    source = profile_mod.normalise(FENCE_RE.sub(' ', source_text), fold_diacritics)
    sample = [w for w in source.split()
              if len(w) >= 4 and not w.replace('.', '').isdigit()][:60]
    if rtl:
        # a right-to-left page comes back in visual order, so "is this word in
        # the text" is a question about tokens, not substrings. Readable here
        # means readable once the direction is accounted for - which is what
        # the checks downstream will do too.
        seen = canonical(extracted, visual=True)
        found = sum(1 for w in sample if canonical(w) <= seen)
    else:
        seen = profile_mod.normalise(extracted, fold_diacritics)
        found = sum(1 for w in sample if w in seen)
    # `or 1` rather than max(1, ...): a denominator guard and a matching
    # threshold are different things, and writing them the same way is how the
    # arithmetic in matching.py went wrong three times. unit_gates refuses a
    # bare max(n, len(...)) for exactly that reason.
    ratio = found / (len(sample) or 1)
    volume = len(extracted.strip()) / (len(re.sub(r'\s+', '', source_text)) or 1)
    if len(sample) < 8:
        # too few distinctive words to be evidence either way. Declining only
        # skips the print checks, which is the safe direction, and it says so
        # rather than reading an empty sample as agreement.
        return {'ratio': ratio, 'usable': False, 'checked': len(sample),
                'found': found, 'volume': volume,
                'why': 'too few distinctive words to tell whether the PDF is readable'}
    return {'ratio': ratio, 'usable': ratio >= floor, 'checked': len(sample),
            'found': found, 'volume': volume,
            'why': None if ratio >= floor else
                   'the PDF\'s text does not match the document\'s own words'}


# Arabic-script ranges, including the presentation forms a PDF comes back in.
ARABIC_RE = re.compile(r'[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]')

# Letters a font's presentation forms map to a different codepoint than the
# source used. NFKC unshapes but does not unify these, so `ي` written in the
# markdown comes back as `ی` and the two never compare equal.
FOLD = {'\u06cc': '\u064a', '\u0649': '\u064a',      # farsi yeh, alef maqsura -> yeh
        '\u06a9': '\u0643',                            # keheh -> kaf
        '\u0623': '\u0627', '\u0625': '\u0627', '\u0622': '\u0627'}   # hamza forms -> alef


def canonical(text, visual=False):
    """Comparison tokens for text that may have come back from a PDF.

    A right-to-left page is extracted in *visual* order, so an Arabic word
    arrives with its characters reversed and the words of a line in the reverse
    of the order they were written. Reversing each Arabic token puts the word
    back; the line's word order is not restored, which is why callers compare
    token *sets* rather than substrings on this path.

    The direction rule is deterministic - only an Arabic-script token from a
    visually ordered extraction is reversed - rather than "whichever of the two
    forms sorts first", which would make every word equal to its own reversal
    and let two different words collide.

    For comparison only. Nothing rendered ever comes from here.
    """
    out = set()
    for token in unicodedata.normalize('NFKC', text).split():
        word = ''.join(FOLD.get(c, c) for c in token if c.isalnum()).casefold()
        if not word:
            continue
        out.add(word[::-1] if visual and ARABIC_RE.search(word) else word)
    return out


def _seen(probe, page, rtl):
    """Whether a probe's wording is on a page, in the terms that page allows."""
    if not rtl:
        return probe in page
    want = {w for w in canonical(probe) if len(w) > 1}
    return bool(want) and want <= canonical(page, visual=True)


def contents_pages(pages, doc, contents_anchor, rtl=False, fold=True):
    """Pages occupied by MỤC LỤC: they echo every title and must never match.

    The contents is one contiguous run, so walk forward from where it starts.
    A body page that happens to carry several short headings (2.7-2.10 share a
    page) is not contiguous with it and is therefore not excluded.
    """
    i = doc.find('<h2 id="%s"' % contents_anchor)
    block = re.sub(r'<span class="toc-pg">\d+</span>', '', doc[i:doc.find('<h2 ', i + 10)])
    labels = [norm(m.group(1), fold)[:40] for m in
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
    hits = lambda t: sum(_seen(l, t, rtl) for l in labels)

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


def measure(html_path, pdf_path, contents_anchor, rtl=False, fold=True):
    """Return {heading id: printed page}, omitting anything unverifiable."""
    doc = open(html_path, encoding='utf-8').read()
    body = doc[doc.index('<main>'):doc.index('</main>')]
    # a "part" heading forces a page break, so it can only be at the top of a page;
    # that distinguishes it from the same words appearing in a summary list
    heads = []
    for m in re.finditer(r'<(h[234])([^>]*)>(.*?)(?:<a class="anchor")', body, re.S):
        attrs, text = m.group(2), norm(m.group(3), fold)
        hid = re.search(r'id="([^"]+)"', attrs)
        if hid and text:
            # 2 = opens the page; 1 = near the top (the annex title sits under a badge)
            breaks = 2 if 'part' in attrs else (1 if 'annex-title' in attrs else 0)
            heads.append((hid.group(1), text, breaks))

    with _pdfplumber().open(pdf_path) as pdf:
        pages = [norm(p.extract_text() or '', fold) for p in pdf.pages]
    total = len(pages)
    skip = contents_pages(pages, doc, contents_anchor, rtl, fold)

    found, missed, lo = {}, [], 0
    for hid, text, breaks in heads:
        words = text.split()
        hit = None
        if rtl:
            # Set containment, because the line's word order is reversed and no
            # substring survives it. The positional refinements below model
            # where on a page a heading sits, which visual order does not
            # preserve either - so this asks for uniqueness instead: exactly one
            # candidate page, or the heading is left unresolved. A page number
            # printed in a contents is worse wrong than absent.
            want = {w for w in canonical(text) if len(w) > 1}
            candidates = [n for n in range(lo, total)
                          if n not in skip and want and want <= canonical(pages[n], visual=True)]
            if len(candidates) == 1:
                found[hid] = candidates[0] + 1
                lo = candidates[0]
            else:
                missed.append(hid)
            continue
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


def _contents_pages(pages, labels, rtl=False):
    """The contents block: one contiguous run of pages echoing the entry list."""
    hits = lambda t: sum(_seen(l[:40], t, rtl) for l in labels if len(l) > 15)
    start = max(range(len(pages)), key=lambda n: (hits(pages[n]), -n))
    run, n = {start}, start + 1
    while n < len(pages) and hits(pages[n]) >= 4:
        run.add(n); n += 1
    n = start - 1
    while n >= 0 and hits(pages[n]) >= 4:
        run.add(n); n -= 1
    return run


def audit(html_path, pdf_path, contents_anchor, part_pattern, section_pattern,
          annex_phrase, rtl=False, fold=True):
    """Confirm every printed page number against the PDF.

    Deliberately does not reuse the matching the build used: a number is only
    accepted if the entry's own wording is found where it claims to be.
    """
    doc = open(html_path, encoding='utf-8').read()
    i = doc.find('<h2 id="%s"' % contents_anchor)
    if i < 0:
        return {'entries': 0, 'confirmed': 0, 'untestable': [], 'wrong': []}
    block = doc[i:doc.find('<h2 ', i + 10)]
    entries = [(norm(m.group(2), fold), int(m.group(1))) for m in re.finditer(
        r'<li><span class="toc-pg">(\d+)</span>((?:(?!<[uo]l>|</li>).)*?)(?:</li>|<[uo]l>)',
        block, re.S)]
    if not entries:
        return {'entries': 0, 'confirmed': 0, 'untestable': [], 'wrong': []}

    with _pdfplumber().open(pdf_path) as pdf:
        pages = [norm(p.extract_text() or '', fold) for p in pdf.pages]
    toc = _contents_pages(pages, [l for l, _ in entries], rtl)

    confirmed, untestable = 0, []
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
            need = matching.quorum(len(want), 3)
            if rtl:
                # visual order gives no "opens the page": the words of a line
                # arrive reversed, so the positional part of this test cannot be
                # made. What is still checkable is that the wording is on the
                # page it claims, and that is all this claims to have checked.
                seen = canonical(text, visual=True)
                found_here = sum(1 for w in want if canonical(w) <= seen)
                ok = bool(want) and found_here >= need
            else:
                ok = (want and sum(w in head for w in want) >= need) or \
                     (m and head.startswith(m.group(1) + ' '))
            if ok:
                confirmed += 1
            else:
                wrong.append((label[:60], page, 'section does not open this page'))
            continue

        words = [w for w in label.split() if len(w) > 1 and not w.isdigit()][:5]
        if len(' '.join(words)) < 10:
            # a skip, not a pass: the entry carries its reason out so the report
            # can say which entries were not tested and why, rather than
            # offering a count nobody can chase
            untestable.append((label[:60], 'too few distinctive words to test'))
        elif (_seen(' '.join(words), text, rtl) if rtl else
              (' '.join(words) in text or
               sum(w in text for w in words) >= matching.quorum(len(words), 3))):
            confirmed += 1
        else:
            wrong.append((label[:60], page, 'wording not found on this page'))

    return {'entries': len(entries), 'confirmed': confirmed,
            'untestable': untestable, 'wrong': wrong}
