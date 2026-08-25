"""Markdown -> self-contained HTML for Paperforge documents."""
import hashlib
import html as ihtml
import re
import unicodedata
from pathlib import Path

from . import assemble
from . import citations as cite_mod
from . import maths as maths_mod
from . import front as front_mod, profile, xref

LIST_RE = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.*)$')
HEAD_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*$')
META_RE = re.compile(r'^\*\*(.+?):\*\*\s*(.*)$')
# Explicit structure, written by the research team, e.g.
#   ## 第三部分：国际经验 {.part}      mark a heading as opening a part
#   ## Background {#context}          give it an anchor of your choosing
#   ## Appendix {.no-part}            suppress a pattern that would otherwise match
# Explicit always wins over pattern inference, so a project can carry structure
# the pipeline has no profile for.
ATTR_RE = re.compile(r'\s*\{([^{}]*)\}\s*$')

SVGS = []  # pre-rendered Mermaid diagrams, injected inline so the file is self-contained
STATS = {}  # what structure was detected, so a profile that matches nothing is reported
MATHS = {}  # expressions pre-rendered by Typst, shared with the PDF edition
CITES = {}  # in-text citation markers, formatted by Typst from the .bib
XREF = {}   # labelled captions, numbered once in xref.py for every edition
XREF_MISSING = []  # references pointing at no label
FRONT = {}  # structured front matter: authors, affiliations, abstract
BIB_WARNINGS = []  # bibliography entries that will render oddly
FIG = {'n': 0, 'base': 0, 'label': '%d'}   # figure counter shared across report + annex
PROF = profile.load('vi')                  # replaced per build; never assume a language

# ---------------------------------------------------------------- inline pass


def slugify(text, fold_diacritics=True):
    """Anchor id for a heading.

    Latin script is folded to ASCII so anchors stay typeable. Other scripts keep
    their own characters - HTML5 ids and URL fragments both allow them - because
    transliterating would be lossy and stripping them collapsed every heading in
    a Chinese or Arabic document onto the same id.
    """
    text = re.sub(r'`|\*|\[|\]', '', text)
    text = text.replace('Đ', 'D').replace('đ', 'd')
    if fold_diacritics:
        folded = unicodedata.normalize('NFD', text)
        folded = ''.join(c for c in folded if not unicodedata.combining(c))
        ascii_slug = re.sub(r'[^A-Za-z0-9]+', '-', folded).strip('-').lower()
        if ascii_slug:
            return ascii_slug[:60]
    kept = ''.join(c if (c.isalnum() or unicodedata.category(c).startswith('M'))
                   else '-' for c in unicodedata.normalize('NFC', text))
    slug = re.sub(r'-+', '-', kept).strip('-').casefold()
    if slug:
        return slug[:60]
    return 'sec-' + hashlib.sha1(text.encode('utf-8')).hexdigest()[:6]


def inline(text):
    """Escape then apply inline markdown: code, links, bold, italic."""
    if XREF:
        text = xref.substitute(text, XREF, XREF_MISSING)
    codes = []
    # pre-rendered HTML (maths, citations) is inserted verbatim; the code stash
    # wraps its contents in <code>, which put citations in a monospace box
    ready = []

    def stash(m):
        codes.append(ihtml.escape(m.group(1)))
        return '\x00c%d\x00' % (len(codes) - 1)

    # maths is pre-rendered SVG: stash it before escaping so the source is not mangled
    def stash_maths(kind):
        def repl(m):
            entry = MATHS.get(maths_mod.key(kind, m.group(1).strip()))
            if not entry:
                return m.group(0)
            ready.append(maths_mod.to_html(entry))
            return '\x00r%d\x00' % (len(ready) - 1)
        return repl

    def stash_cite(m):
        rendered = cite_mod.to_html(CITES, m.group(1))
        if not rendered:
            return m.group(0)
        ready.append(rendered)
        return '\x00r%d\x00' % (len(ready) - 1)

    text = cite_mod.CITE_RE.sub(stash_cite, text)
    text = maths_mod.DISPLAY_RE.sub(stash_maths('display'), text)
    text = maths_mod.INLINE_RE.sub(stash_maths('inline'), text)
    text = re.sub(r'`([^`]+)`', stash, text)
    text = ihtml.escape(text)

    def link(m):
        label, href = m.group(1), m.group(2)
        ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
        return '<a href="%s"%s>%s</a>' % (href, ext, label)

    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'<em>\1</em>', text)
    text = text.replace('  \n', '<br>\n')
    # the sources use literal <br> inside table cells: let that one tag through
    text = re.sub(r'&lt;br\s*/?&gt;', '<br>', text)
    for i, c in enumerate(codes):
        text = text.replace('\x00c%d\x00' % i, '<code>%s</code>' % c)
    for i, r in enumerate(ready):
        text = text.replace('\x00r%d\x00' % i, r)
    return text


# ----------------------------------------------------------------- block pass


def take_caption(lines, pos):
    """Consume a `: text {#fig-x}` line following a block, if there is one.

    Returns (entry or None, new position). A caption that labels nothing is
    left where it is; lint reports it rather than the renderer printing it as
    a stray paragraph, which is what it used to do."""
    look = pos
    while look < len(lines) and not lines[look].strip():
        look += 1
    if look < len(lines):
        m = xref.CAPTION_RE.match(lines[look].strip())
        if m:
            return XREF.get(m.group(2)), look + 1
    return None, pos


def parse_list(lines, pos, level):
    m = LIST_RE.match(lines[pos])
    ordered = m.group(2)[-1] == '.'
    items = []
    while pos < len(lines):
        line = lines[pos]
        if not line.strip():
            pos += 1
            continue
        m = LIST_RE.match(line)
        if m:
            indent = len(m.group(1).expandtabs(4))
            if indent < level:
                break
            if indent > level:
                if not items:
                    break
                sub, pos = parse_list(lines, pos, indent)
                items[-1].append(sub)
                continue
            if (m.group(2)[-1] == '.') != ordered:
                break
            items.append([inline(m.group(3))])
            pos += 1
        else:
            indent = len(line) - len(line.lstrip())
            if indent <= level or not items:
                break
            items[-1].append('<p>%s</p>' % inline(line.strip()))
            pos += 1
    tag = 'ol' if ordered else 'ul'
    out = ['<%s>' % tag]
    for parts in items:
        out.append('<li>%s</li>' % ''.join(parts))
    out.append('</%s>' % tag)
    return '\n'.join(out), pos


def parse_table(lines, pos):
    rows = []
    while pos < len(lines) and lines[pos].lstrip().startswith('|'):
        raw = lines[pos].strip()
        cells = [c.strip() for c in raw.strip('|').split('|')]
        rows.append(cells)
        pos += 1
    if len(rows) < 2:
        return '', pos
    aligns = []
    for c in rows[1]:
        left, right = c.startswith(':'), c.endswith(':')
        aligns.append('center' if left and right else 'right' if right else 'left')
    ncol = len(rows[0])
    # Print cannot scroll a wide table; it cuts the right-hand column off the
    # page, and in an evidence annex that is the column holding the sources.
    # CSS cannot count columns, so the renderer marks the table and the print
    # rules give it a face that fits.
    wide = ' wide' if ncol >= 6 else ''
    out = ['<div class="table-frame%s"><div class="table-wrap"><table>' % wide, '<thead><tr>']
    for i, c in enumerate(rows[0]):
        a = aligns[i] if i < len(aligns) else 'left'
        out.append('<th style="text-align:%s">%s</th>' % (a, inline(c)))
    out.append('</tr></thead><tbody>')
    for row in rows[2:]:
        out.append('<tr>')
        for i in range(ncol):
            c = row[i] if i < len(row) else ''
            a = aligns[i] if i < len(aligns) else 'left'
            cls = ' class="empty"' if not c else ''
            out.append('<td style="text-align:%s"%s>%s</td>' % (a, cls, inline(c)))
        out.append('</tr>')
    out.append('</tbody></table></div></div>')
    return '\n'.join(out), pos


def convert(lines, toc):
    out = []
    pos = 0
    n = len(lines)
    while pos < n:
        line = lines[pos]
        stripped = line.strip()

        if not stripped:
            pos += 1
            continue

        # fenced blocks -------------------------------------------------
        if stripped.startswith('```'):
            lang = stripped[3:].strip().lower()
            pos += 1
            buf = []
            while pos < n and not lines[pos].strip().startswith('```'):
                buf.append(lines[pos])
                pos += 1
            pos += 1
            body = ihtml.escape('\n'.join(buf))
            if lang == 'mermaid':
                FIG['n'] += 1
                fig = FIG['n']
                svg = SVGS[fig - 1] if fig - 1 < len(SVGS) else None
                if svg:
                    m2 = re.search(r'max-width:\s*([\d.]+)px', svg[:svg.find('>')])
                    natural = float(m2.group(1)) if m2 else 0
                    # never shrink a wide diagram below ~70% of its natural size;
                    # the figure scrolls horizontally instead of turning illegible
                    floor = int(natural * 0.7) if natural > 900 else 0
                    style = ' style="min-width:%dpx"' % floor if floor else ''
                    inner = '<div class="dgm"><div class="dgm-in"%s>%s</div></div>' % (style, svg)
                else:
                    inner = '<div class="mermaid">%s</div>' % body
                entry, pos = take_caption(lines, pos)
                cap = xref.caption_of(entry) if entry else FIG['label'] % (fig - FIG['base'])
                anchor = ' id="%s"' % entry['id'] if entry else ''
                out.append('<figure class="diagram"%s>\n%s\n'
                           '<figcaption>%s</figcaption>\n</figure>' % (anchor, inner, inline(cap)))
            else:
                out.append('<pre><code>%s</code></pre>' % body)
            continue

        # horizontal rule ------------------------------------------------
        if re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', stripped):
            out.append('<hr>')
            pos += 1
            continue

        # heading --------------------------------------------------------
        m = HEAD_RE.match(stripped)
        if m:
            depth = len(m.group(1))
            text = m.group(2)
            classes, explicit_id = [], None
            attrs = ATTR_RE.search(text)
            if attrs:
                classes = re.findall(r'\.([\w-]+)', attrs.group(1))
                ids = re.findall(r'#([\w-]+)', attrs.group(1))
                explicit_id = ids[0] if ids else None
                text = text[:attrs.start()].rstrip()
            slug = explicit_id or slugify(text, PROF.get('fold_diacritics', True))
            base, k = slug, 2
            while not explicit_id and any(s == slug for s, _, _ in toc):
                slug = '%s-%d' % (base, k)
                k += 1
            toc.append((slug, depth, re.sub(r'<[^>]+>', '', inline(text))))
            if depth == 2:
                STATS['h2'] = STATS.get('h2', 0) + 1
            inferred = bool(re.match(PROF['structure']['part_banner'], text))
            if inferred:
                STATS['inferred_parts'] = STATS.get('inferred_parts', 0) + 1
            if 'part' in classes:
                STATS['explicit_parts'] = STATS.get('explicit_parts', 0) + 1
            # explicit marking wins in both directions
            is_part = ('part' in classes) or (inferred and 'no-part' not in classes)
            extra = [c for c in classes if c not in ('part', 'no-part')]
            names = (['part'] if is_part else []) + extra
            cls = ' class="%s"' % ' '.join(names) if names else ''
            out.append('<h%d id="%s"%s>%s<a class="anchor" href="#%s" aria-label="Liên kết mục">#</a></h%d>'
                       % (depth, slug, cls, inline(text), slug, depth))
            pos += 1
            continue

        # display maths --------------------------------------------------
        # taken in the block pass, not left to the paragraph path: the label
        # lives on the closing fence, and until this existed nothing stripped
        # it, so `{#eq-x}` printed on the page and the equation had no number
        # for its own reference to point at
        expr, ident, after = xref.take_equation(lines, pos)
        if expr is not None:
            pos = after
            entry = MATHS.get(maths_mod.key('display', expr.strip()))
            body = maths_mod.to_html(entry) if entry else ihtml.escape(expr)
            ref = XREF.get(ident) if ident else None
            number = ('<span class="eq-number">(%d)</span>' % ref['number']) if ref else ''
            out.append('<div class="equation"%s>%s%s</div>'
                       % (' id="%s"' % ident if ident else '', body, number))
            continue

        # blockquote / callout -------------------------------------------
        if stripped.startswith('>'):
            buf = []
            while pos < n and lines[pos].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[pos]))
                pos += 1
            first = buf[0] if buf else ''
            kind, title = 'note', 'GHI CHÚ'
            m2 = re.match(r'^\[!(\w+)\]\s*(.*)$', first.strip())
            if m2:
                kind = m2.group(1).lower()
                buf[0] = m2.group(2)
            inner = convert([l for l in buf], [])
            out.append('<aside class="callout %s"><div class="callout-body">%s</div></aside>'
                       % (kind, inner))
            continue

        # table -----------------------------------------------------------
        if stripped.startswith('|') and pos + 1 < n and re.match(r'^\|[\s:*|-]+\|?$', lines[pos + 1].strip()):
            block, pos = parse_table(lines, pos)
            entry, pos = take_caption(lines, pos)
            if entry:
                block = block.replace('<div class="table-frame',
                                      '<div id="%s" class="table-frame' % entry['id'], 1)
                block += ('\n<p class="table-caption">%s</p>' % inline(xref.caption_of(entry)))
            out.append(block)
            continue

        # list --------------------------------------------------------------
        m = LIST_RE.match(line)
        if m:
            block, pos = parse_list(lines, pos, len(m.group(1).expandtabs(4)))
            out.append(block)
            continue

        # paragraph -----------------------------------------------------------
        buf = []
        while pos < n and lines[pos].strip() and not lines[pos].strip().startswith(('```', '>', '|', '#')) \
                and not LIST_RE.match(lines[pos]) and not re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', lines[pos].strip()):
            buf.append(lines[pos].rstrip())
            pos += 1
        if buf:
            out.append('<p>%s</p>' % inline('\n'.join(buf)))
    return '\n'.join(out)


# ------------------------------------------------------------------- assembly

def parse_head(head_lines):
    """Pull the title, subtitle and **Key:** value metadata off a document head.

    Returns leftovers too: short documents often carry an audience note or a
    scope line here, and dropping them silently loses content.
    """
    title = kind = None
    for l in head_lines:
        st = l.strip()
        if st.startswith('# ') and kind is None:
            kind = HEAD_RE.match(st).group(2)
        elif st.startswith('## ') and title is None:
            title = HEAD_RE.match(st).group(2)
    meta, rest = [], []
    seen_title = seen_kind = False
    for l in head_lines:
        st = l.strip()
        m = META_RE.match(st)
        if m and m.group(2).strip():
            meta.append((m.group(1), m.group(2).strip()))
        elif st.startswith('# ') and not seen_kind:
            seen_kind = True
        elif st.startswith('## ') and not seen_title:
            seen_title = True
        elif re.fullmatch(r'\*\*[^*]+:\*\*', st) and not seen_title:
            continue                      # a label introducing the title, e.g. "**ĐỀ TÀI:**"
        elif st and not re.fullmatch(r'-{3,}', st):
            rest.append(l)
    return kind, title, meta, rest


def front_html(data, prof):
    """The manuscript block: byline, affiliations, corresponding, abstract."""
    if not data:
        return ''
    parts = []
    if data.get('anonymised'):
        parts.append('<p class="anonymised">%s</p>' % inline(str(data['anonymised'])))
    pairs = front_mod.byline(data)
    if pairs:
        parts.append('<p class="byline">%s</p>' % ', '.join(
            '%s%s' % (inline(name), '<sup>%s</sup>' % ihtml.escape(marks) if marks else '')
            for name, marks in pairs))
    aff = front_mod.affiliations(data)
    if aff:
        parts.append('<ol class="affiliations">%s</ol>' % ''.join(
            '<li value="%s">%s</li>' % (ihtml.escape(k), inline(v))
            for k, v in sorted(aff.items())))
    line = front_mod.corresponding(data, prof)
    if line:
        parts.append('<p class="corresponding">%s</p>' % inline(line))
    if data.get('abstract'):
        parts.append('<section class="abstract"><h2>%s</h2>%s</section>'
                     % (ihtml.escape(front_mod.label(prof, 'abstract')),
                        convert(str(data['abstract']).split('\n'), [])))
    if data.get('keywords'):
        parts.append('<p class="keywords"><strong>%s:</strong> %s</p>'
                     % (ihtml.escape(front_mod.label(prof, 'keywords')),
                        inline(', '.join(str(k) for k in data['keywords']))))
    return '\n'.join(parts)


def declarations_html(data, prof):
    entries = front_mod.declarations(data, prof)
    if not entries:
        return ''
    return ('<section class="declarations"><h2>%s</h2>%s</section>'
            % (ihtml.escape(front_mod.label(prof, 'declarations')),
               ''.join('<p><strong>%s.</strong> %s</p>'
                       % (ihtml.escape(k), inline(str(v))) for k, v in entries)))


def meta_grid(meta, cls='meta-grid'):
    return '<div class="%s">\n%s\n</div>' % (cls, '\n'.join(
        '<div class="meta-item"><span class="meta-k">%s</span><span class="meta-v">%s</span></div>'
        % (ihtml.escape(k), inline(v)) for k, v in meta))


def build_toc(toc):
    items = []
    for slug, depth, text in toc:
        if depth == 0:
            items.append('<div class="toc-divider">%s</div>' % text)
            continue
        if depth == 1 or depth > 3:
            continue
        cls = 'lvl2' if depth == 2 else 'lvl3'
        items.append('<a class="%s" href="#%s">%s</a>' % (cls, slug, text))
    return '\n'.join(items)


def _norm(text):
    t = re.sub(r'<[^>]+>', '', text).replace('Đ', 'D').replace('đ', 'd').replace('Ð', 'D')
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s.:]', ' ', t)).strip()


def _sig(t, n=6):
    return 'w:' + ''.join(re.sub(r'[^a-z0-9]', '', w) for w in t.split()[:n])


def entry_keys(text, annex=False, top=False):
    """Candidate identities for a heading or a contents line; a shared key is a match.

    The two forms are worded differently on purpose, so match on the numbering
    wherever there is any, and only fall back to the opening words.
    """
    t = _norm(text)
    keys = set()

    st = PROF['structure']
    # "Mục 4. ..." in the contents <-> "4. ..." as an annex section heading.
    # The pattern comes from the profile: numbering shape is language-specific
    # ("PART III", "PHẦN III", "第三部分" - no space, no roman numerals).
    m = re.match(st.get('section_pattern') or (r'^%s\s+(\d+)[.:]' % st['section_word']), t)
    if m:
        keys.add('a:' + m.group(1))
        t = t[m.end():].strip()
    elif annex and top:          # only a section heading owns "a:N"; 3.1 must not claim a:3
        m = re.match(r'^(\d+)[.:]', t)
        if m:
            keys.add('a:' + m.group(1))
            t = t[m.end():].strip()

    # the contents prefixes each top-level line with its own ordinal
    t = re.sub(r'^\d+\.\s+(?=[a-z])', '', t)

    # numbered subsections agree exactly on both sides
    m = re.match(r'^(\d+\.\d+(?:\.\d+)*)\.', t)
    if m:
        keys.add('n:' + m.group(1))

    # "PHẦN VIII: KẾT LUẬN" must also answer to a contents line reading "KẾT LUẬN"
    m = re.match(st.get('part_pattern') or
                 (r'^%s\s+([ivx]+)\s*[:.]?\s*(.*)$' % st['part_word']), t)
    if m:
        keys.add('p:' + m.group(1))
        if m.group(2).strip():
            keys.add(_sig(m.group(2)))
    if profile.normalise(PROF['labels']['annex_divider']).startswith(t[:14]) or \
       (PROF['structure']['annex_word'] in t and t.startswith(PROF['structure']['annex_word'])):
        keys.add('a:root')
    keys.add(_sig(t))
    return keys


def number_contents(body, toc, pages, contents_anchor):
    """Print-only page numbers on the MỤC LỤC entries, from the measured PDF."""
    by_key, ambiguous, in_annex = {}, set(), False
    for slug, depth, text in toc:
        if depth == 0:
            in_annex = True
            continue
        for k in entry_keys(text, annex=in_annex, top=(depth == 2)):
            if k in by_key and by_key[k] != slug:
                ambiguous.add(k)          # two headings answer to it: trust neither
            else:
                by_key[k] = slug
    for k in ambiguous:
        by_key.pop(k, None)
    by_key['a:root'] = PROF['structure']['annex_anchor']

    start = body.find('<h2 id="%s"' % contents_anchor)
    if start < 0:
        return body, 0
    end = body.find('<h2 ', start + 10)
    added = 0

    def per_item(m):
        """Number one entry from its own label, leaving any nested list alone."""
        nonlocal added
        label, tail = m.group(1), m.group(2)
        page = None
        for k in sorted(entry_keys(label), key=lambda k: k.startswith('w:')):
            page = pages.get(by_key.get(k))
            if page:
                break
        if not page:
            return m.group(0)
        added += 1
        return '<li><span class="toc-pg">%d</span>%s%s' % (page, label, tail)

    block = re.sub(r'<li>((?:(?!<[uo]l>|</li>).)*)(</li>|<[uo]l>)',
                   per_item, body[start:end], flags=re.S)
    return body[:start] + block + body[end:], added


def build_annex(path, toc, nav_label=None):
    """Render the annex as an in-document appendix and return (html, anchor_map)."""
    lines = open(path, encoding='utf-8').read().replace('\r\n', '\n').split('\n')
    # the head runs up to the first horizontal rule
    hr = next(i for i, l in enumerate(lines) if re.fullmatch(r'-{3,}', l.strip()))
    kind, subtitle, meta, _ = parse_head(lines[:hr])

    anchor = PROF['structure']['annex_anchor']
    toc.append((0, 0, PROF['labels']['annex_divider']))     # sidebar group divider
    # Sidebar label derived from the annex title with a leading "annex" word
    # removed. The test runs on the normalised form so diacritics cannot defeat
    # it, then the same number of words is dropped from the original text.
    label = kind or subtitle or ''
    annex_word = PROF['structure']['annex_word']
    if profile.normalise(label).startswith(annex_word):
        label = ' '.join(label.split()[len(annex_word.split()):])
    if len(label) > 52:                       # a sidebar entry, not a title page
        label = label[:52].rsplit(' ', 1)[0] + '…'
    toc.append((anchor, 2, nav_label or '%s: %s' % (PROF['labels']['annex_entry'], label)))

    FIG['base'] = FIG['n']
    FIG['label'] = PROF['labels']['annex_figure']
    mark = len(toc)
    body = convert(lines[hr + 1:], toc)
    # annex sections get the banner treatment, tinted differently from the report parts
    body = re.sub(r'<h2 id="', '<h2 class="part annex-part" id="', body)

    anchors = {}
    for slug, depth, text in toc[mark:]:
        m = re.match(r'^(\d+(?:\.\d+)?)\.', text.strip())
        if m and m.group(1) not in anchors:
            anchors[m.group(1)] = slug
    anchors['root'] = anchor

    head = ('<section class="annex">\n'
            '<header class="annex-head">\n'
            '<span class="annex-badge">%s</span>\n'
            '<h2 id="%s" class="annex-title">%s</h2>\n'
            '<p class="annex-sub">%s</p>\n%s\n</header>\n'
            % (ihtml.escape(PROF['labels']['annex_badge']), anchor,
               inline(kind or PROF['labels']['annex_entry']), inline(subtitle or ''),
               meta_grid(meta, 'annex-meta')))
    return head + body + '\n</section>', anchors


def link_annex(html_body, anchors, annex_file):
    """Point every annex reference at the embedded copy instead of the .md file."""
    def by_label(m):
        label = m.group(1)
        num = re.search(r'%s\s+(\d+(?:\.\d+)?)' % PROF['structure']['section_word'],
                        profile.normalise(re.sub(r'<[^>]+>', '', label)))
        target = anchors.get(num.group(1)) if num else None
        return '<a href="#%s">%s</a>' % (target or anchors['root'], label)

    html_body = re.sub(r'<a href="\./%s"[^>]*>(.*?)</a>' % re.escape(annex_file),
                       by_label, html_body, flags=re.S)

    phrase = PROF['structure']['annex_reference']

    def by_mention(m):
        num = m.group(1)
        target = anchors.get(num)
        return ('<a href="#%s"><em>%s %s</em></a>' % (target, phrase, num)) if target else m.group(0)

    return re.sub(r'<em>%s ([\d.]+)</em>' % re.escape(phrase), by_mention, html_body)


THEME = Path(__file__).parent / 'theme'

# Applied when a profile declares fonts or right-to-left text. Kept as an
# override rather than edited into the stylesheet so one design system serves
# every script: Georgia carries no CJK or Arabic glyphs, and a right-to-left
# document needs the sidebar, rules and banners mirrored.
RTL_CSS = """
body { direction: rtl; }
.shell { direction: rtl; }
nav.toc a { border-left: 0; border-right: 2px solid transparent; border-radius: 4px 0 0 4px;
  padding: 5px 12px 5px 10px; }
nav.toc a.active { border-right-color: var(--amber); }
nav.toc a.lvl3 { padding-right: 24px; padding-left: 10px; }
main h2.part { border-left: 0; border-right: 5px solid var(--amber); }
main h3 { border-left: 0; border-right: 4px solid var(--amber); padding-left: 0; padding-right: 14px; }
.callout { border-left: 0; border-right: 5px solid var(--amber); }
.annex-head { border-left: 0; border-right: 6px solid var(--amber); }
main ul, main ol { padding-left: 0; padding-right: 26px; }
.toc-pg { float: left; padding-left: 0; padding-right: 8px; }
.anchor { margin-left: 0; margin-right: 10px; }
thead th, tbody td { text-align: right; }
.is-scrollable::after { right: auto; left: 1px; border-radius: 9px 0 0 9px;
  background: linear-gradient(to right, rgba(11,37,69,.13), rgba(11,37,69,0)); }
"""


def logo_tag(path, height=46):
    """A project mark, inlined so the document stays self-contained.

    An SVG goes in as markup, anything else as a data URI. A logo that loads
    from a URL would be the one network dependency in a document whose whole
    claim is that it opens offline.
    """
    import base64
    import mimetypes
    path = Path(path)
    if not path.exists():
        return ''
    if path.suffix.lower() == '.svg':
        svg = path.read_text(encoding='utf-8')
        svg = re.sub(r'<\?xml.*?\?>|<!DOCTYPE.*?>', '', svg, flags=re.S).strip()
        return '<div class="logo" style="--logo-h:%dpx">%s</div>' % (height, svg)
    mime = mimetypes.guess_type(str(path))[0] or 'image/png'
    data = base64.b64encode(path.read_bytes()).decode('ascii')
    return ('<div class="logo" style="--logo-h:%dpx">'
            '<img src="data:%s;base64,%s" alt=""></div>' % (height, mime, data))


def theme_override(prof, brand=None):
    """Per-project CSS: brand colours, script-appropriate fonts, RTL mirroring.

    A project declares its own palette under [brand] in the manifest; the
    stylesheet ships neutral defaults so an unbranded project does not come out
    wearing someone else's colours.
    """
    parts = []
    # profile first, brand second: the profile knows which faces carry the
    # script's glyphs, the project knows its own house type, and a project that
    # names one has taken responsibility for the coverage - see languages.md
    tokens = dict(prof.get('fonts') or {})
    tokens.update(brand or {})
    if tokens:
        decl = ''.join('  --%s: %s;\n' % (k, v) for k, v in sorted(tokens.items()))
        parts.append(':root {\n%s}' % decl)
    if prof.get('direction') == 'rtl':
        parts.append(RTL_CSS)
    return '\n'.join(parts)


def render(name, mapping):
    """Fill {{PLACEHOLDER}} markers. Plain replacement, so CSS and JS braces
    need no escaping - which str.format could not offer."""
    text = (THEME / name).read_text(encoding='utf-8')
    for key, value in mapping.items():
        if value == '':
            text = re.sub(r'^[ \t]*\{\{%s\}\}\n' % key, '', text, flags=re.M)
        text = text.replace('{{%s}}' % key, value)
    left = re.findall(r'\{\{(\w+)\}\}', text)
    if left:
        raise ValueError('unfilled placeholders: %s' % sorted(set(left)))
    return text


def build(source, output, svgs=None, annex=None, pages=None,
          contents_heading=None, kind_fallback=None, layout='report', prof=None,
          organisation=None, publisher=None, footer_note=None, annex_label=None,
          brand=None, bibliography=None, citation_style='apa', logo=None,
          review=False, includes=()):
    """Render one markdown document. Contents section and annex are optional."""
    global PROF
    PROF = prof or profile.load('vi')
    kind_fallback = kind_fallback or PROF['labels']['document']
    contents_heading = contents_heading or None
    SVGS[:] = svgs or []
    raw = assemble.read(source, includes)
    # structured front matter comes off first, so nothing downstream sees
    # a +++ block and tries to render it as prose
    FRONT.clear()
    front_data, raw = front_mod.split(raw)
    if review:
        # anonymised before anything renders: the identifying fields never
        # reach an emitter, so there is nothing left to leak
        front_data = front_mod.anonymise(front_data, prof)
    FRONT.update(front_data)
    lines = raw.split('\n')

    # The head is everything before the contents section, or before the first
    # rule when a document has no contents (short briefs do not).
    start = None
    if contents_heading:
        marker = '## ' + contents_heading
        start = next((i for i, l in enumerate(lines) if l.strip().startswith(marker)), None)
    if start is None:
        start = next((i for i, l in enumerate(lines)
                      if re.fullmatch(r'-{3,}', l.strip())), 0) + 1

    h1, subtitle, meta, lede = parse_head(lines[:start])
    if subtitle:
        # report form: "# KIND" over "## TITLE"
        doc_kind, title = h1 or kind_fallback, subtitle
    else:
        # brief form: a single "# TITLE", with the kind supplied by config
        doc_kind, title = kind_fallback, h1 or kind_fallback
    # do not print the kind twice when the title already opens with it
    if title.lower().startswith(doc_kind.lower()):
        doc_kind = ''

    MATHS.clear()
    CITES.clear()
    XREF.clear()
    XREF_MISSING[:] = []
    # numbered once, for every edition: see xref.py
    annex_lines = Path(annex).read_text(encoding='utf-8').split('\n') if annex else []
    XREF.update(xref.resolve(PROF, raw.split('\n'), annex_lines))
    source_text = raw + ('\n' + Path(annex).read_text(encoding='utf-8') if annex else '')
    found = maths_mod.find(source_text)
    if found:
        MATHS.update(maths_mod.render(found))
    biblio_html = ''
    keys = cite_mod.find(source_text) if bibliography else []
    if keys:
        markers, biblio_html = cite_mod.render(
            keys, bibliography, citation_style,
            PROF['labels'].get('references', 'References'), PROF.get('lang', 'en'))
        CITES.update(markers)
        BIB_WARNINGS[:] = cite_mod.dangling_dates(bibliography, set(keys))

    toc = []
    STATS.clear()
    FIG.update(n=0, base=0, label=PROF['labels']['figure'])
    body = convert(lines[start:], toc)

    annex_html = ''
    if annex:
        annex_html, anchors = build_annex(annex, toc, annex_label)
        body = link_annex(body, anchors, Path(annex).name)

    numbered = 0
    contents_anchor = slugify(contents_heading) if contents_heading else ''
    if pages and contents_anchor:
        body, numbered = number_contents(body, toc, pages, contents_anchor)

    nav = build_toc(toc)
    ui = PROF['ui']
    html = render('document.html', {
        'BODYCLASS': 'doc-' + layout + (' doc-review' if review else ''),
        'LANG': PROF['lang'],
        'DIR': PROF.get('direction', 'ltr'),
        'THEME_OVERRIDE': theme_override(PROF, brand),
        'LOGO': logo_tag(logo) if logo else '',
        'UI_CONTENTS': ihtml.escape(ui['contents_button']),
        'UI_PRINT': ihtml.escape(ui['print_button']),
        'UI_NAV_TITLE': ihtml.escape(ui['nav_title']),
        'UI_SCROLL_HINT': ihtml.escape(ui['scroll_hint']),
        'UI_FOOTER': ihtml.escape(footer_note or ui['footer_note']),
        'ORGANISATION': ihtml.escape(organisation or 'Paperforge'),
        'PUBLISHER': ihtml.escape(publisher or organisation or 'Paperforge'),
        # the file keeps its POSIX trailing newline; the shell supplies its own
        'CSS': (THEME / 'paperforge.css').read_text(encoding='utf-8').strip(),
        'TITLE': ihtml.escape(re.sub(r'\s+', ' ', title)),
        'SHORT': ihtml.escape(re.split(r'[:：]', title)[0].strip().title()),
        'KIND': ('<span class="kind">%s</span>' % inline(doc_kind)) if doc_kind else '',
        'HEADING': inline(title),
        'LEDE': ('  <div class="cover-lede">%s</div>\n' % convert(lede, [])) if lede else '',
        'META': meta_grid(meta) + front_html(FRONT, PROF),
        'NAV': nav if nav.strip() else ('<p class="toc-empty">%s</p>'
                                        % ihtml.escape(PROF['labels']['short_document'])),
        'BODY': body + declarations_html(FRONT, PROF) + annex_html + biblio_html,
    })
    Path(output).write_text(html, encoding='utf-8')
    return {'bytes': len(html.encode('utf-8')), 'structure': dict(STATS),
            'bib_warnings': list(BIB_WARNINGS),
            'headings': len([t for t in toc if t[1]]),
            'nav': nav.count('<a '), 'diagrams': len(SVGS), 'numbered': numbered,
            'annex': bool(annex)}
