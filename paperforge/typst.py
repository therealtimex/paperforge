"""Markdown -> Typst -> PDF.

Chrome's print engine cannot do footnotes at the foot of a page, chapters
opening recto, chapter titles in running heads, or numbered cross-references.
Typst does all of it natively, and localises figure and table captions from the
document language, which lines up with the profile model.

One constraint drove the design: Mermaid renders node labels inside SVG
<foreignObject>, which Typst does not draw. Embedding our diagram SVGs directly
produced boxes and arrows with **no text at all**, so diagrams are rasterised
through Chrome first - already a build dependency - at 3x for print.
"""
import html as ihtml
import re
import shutil
import subprocess
from pathlib import Path

from . import browser, citations as cite_mod, front as front_mod, profile, xref

LIST_RE = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.*)$')
HEAD_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*$')
META_RE = re.compile(r'^\*\*(.+?):\*\*\s*(.*)$')
ATTR_RE = re.compile(r'\s*\{([^{}]*)\}\s*$')
FOOTNOTE_DEF = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$')

SPECIAL = '\\#$*_`<>@'
XREF = {}   # resolved once in xref.py; this emitter never counts for itself


def esc(text):
    """Typst markup characters that must survive as literal text."""
    for ch in SPECIAL:
        text = text.replace(ch, '\\' + ch)
    return text


def inline(text, footnotes):
    """Markdown inline -> Typst inline. Order matters: stash code, then links."""
    if XREF:
        text = xref.substitute(text, XREF)
    stash = []

    def keep(s):
        stash.append(s)
        return '\x00%d\x00' % (len(stash) - 1)

    # maths is native in Typst; keep it verbatim rather than escaping the $
    # citations are native in Typst: [@a; @b] becomes @a @b
    text = cite_mod.CITE_RE.sub(
        lambda m: keep(' '.join('@%s' % k for k in cite_mod.KEY_RE.findall(m.group(1)))), text)
    text = re.sub(r'\$\$(.+?)\$\$', lambda m: keep('$ %s $' % m.group(1).strip()), text, flags=re.S)
    text = re.sub(r'(?<![\w$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?![\w$])',
                  lambda m: keep('$%s$' % m.group(1).strip()), text)
    text = re.sub(r'`([^`]+)`', lambda m: keep('#raw("%s")' % m.group(1).replace('"', '\\"')), text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)                    # images handled as figures
    text = re.sub(r'\[\^([^\]]+)\]',
                  lambda m: keep('#footnote[%s]' % inline(footnotes.get(m.group(1), ''), {})
                                 if m.group(1) in footnotes else ''), text)
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)',
                  lambda m: keep('#link("%s")[%s]' % (m.group(2), esc(m.group(1)))), text)
    # stashed, not replaced after escaping: esc() turns <br> into \<br\>, so a
    # later literal replace can never match and the tag reaches the page as text
    text = re.sub(r'<br\s*/?>', lambda m: keep(' \\ '), text, flags=re.I)
    text = esc(text)
    text = re.sub(r'\\\*\\\*\\\*(.+?)\\\*\\\*\\\*', r'*_\1_*', text)
    text = re.sub(r'\\\*\\\*(.+?)\\\*\\\*', r'*\1*', text)
    text = re.sub(r'(?<!\\\*)\\\*([^*\n]+?)\\\*(?!\\\*)', r'_\1_', text)
    for i, s in enumerate(stash):
        text = text.replace('\x00%d\x00' % i, s)
    return text


def collect_footnotes(lines):
    """Pull [^id]: definitions out so references can inline them."""
    notes, body = {}, []
    for line in lines:
        m = FOOTNOTE_DEF.match(line.strip())
        if m:
            notes[m.group(1)] = m.group(2)
        else:
            body.append(line)
    return notes, body


def emit_list(lines, pos, level, notes, out):
    marker = LIST_RE.match(lines[pos]).group(2)
    ordered = marker[-1] == '.'
    while pos < len(lines):
        line = lines[pos]
        if not line.strip():
            pos += 1
            continue
        m = LIST_RE.match(line)
        if not m:
            break
        indent = len(m.group(1).expandtabs(4))
        if indent < level:
            break
        if indent > level:
            pos = emit_list(lines, pos, indent, notes, out)
            continue
        if (m.group(2)[-1] == '.') != ordered:
            break
        out.append('%s%s %s' % ('  ' * (level // 2), '+' if ordered else '-',
                                inline(m.group(3), notes)))
        pos += 1
    return pos


MARKER_RE = re.compile(r'^([-+*]|\d+\.)(?=\s)')


def cell(text, notes):
    """A table cell's content is its own block, so a leading "- " would start a
    Typst list while the dashes after each linebreak stay literal - one cell,
    two different marks. The source means all of them as plain text."""
    return MARKER_RE.sub(lambda m: '\\' + m.group(1), inline(text, notes))


WIDE = 6        # columns from which a table needs a page of its own, turned


def emit_table(lines, pos, notes, out):
    """Returns the table's markup and the new position, rather than appending,
    so a wide one can be placed on a flipped page together with its caption."""
    rows = []
    while pos < len(lines) and lines[pos].lstrip().startswith('|'):
        rows.append([c.strip() for c in lines[pos].strip().strip('|').split('|')])
        pos += 1
    if len(rows) < 2:
        return '', pos
    cols = len(rows[0])
    cells = ['[*%s*]' % cell(c, notes) for c in rows[0]]
    for row in rows[2:]:
        cells += ['[%s]' % cell(row[i] if i < len(row) else '', notes) for i in range(cols)]
    inset = 5 if cols >= WIDE else 6
    return ('#table(columns: %d, stroke: 0.4pt + rgb("#dfe4ec"), inset: %dpt,\n  %s\n)'
            % (cols, inset, ',\n  '.join(cells))), pos


def take_caption(lines, pos):
    """Consume a `: text {#fig-x}` line after a block, as the HTML path does."""
    look = pos
    while look < len(lines) and not lines[look].strip():
        look += 1
    if look < len(lines):
        m = xref.CAPTION_RE.match(lines[look].strip())
        if m:
            return XREF.get(m.group(2)), look + 1
    return None, pos


def convert(lines, notes, figures, label, part_banner=None, force_parts=False):
    """Block pass. `figures` receives (index, caption) for each diagram."""
    out, pos, n = [], 0, len(lines)
    while pos < n:
        line, stripped = lines[pos], lines[pos].strip()
        if not stripped:
            pos += 1
            continue

        if stripped.startswith('```'):
            lang = stripped[3:].strip().lower()
            pos += 1
            buf = []
            while pos < n and not lines[pos].strip().startswith('```'):
                buf.append(lines[pos])
                pos += 1
            pos += 1
            if lang == 'mermaid':
                idx = len(figures)
                figures.append(idx)
                # the emitter numbers figures, matching the HTML edition, so
                # Typst's own supplement is suppressed - otherwise the caption
                # reads "Hình 1: Sơ đồ 1", its label and ours doubled up
                entry, pos = take_caption(lines, pos)
                cap = xref.caption_of(entry) if entry else label % (idx + 1)
                out.append('#figure(image("fig-%d.png", width: 92%%), caption: [%s],'
                           ' supplement: none, numbering: none)'
                           % (idx, inline(cap, notes)))
            else:
                out.append('#raw("%s", block: true)' % '\\n'.join(
                    l.replace('\\', '\\\\').replace('"', '\\"') for l in buf))
            continue

        if re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', stripped):
            out.append('#line(length: 100%, stroke: 0.5pt + rgb("#dfe4ec"))')
            pos += 1
            continue

        m = HEAD_RE.match(stripped)
        if m:
            depth, text = len(m.group(1)), m.group(2)
            attrs = ATTR_RE.search(text)
            classes = re.findall(r'\.([\w-]+)', attrs.group(1)) if attrs else []
            if attrs:
                text = text[:attrs.start()].rstrip()
            # Same rule as the HTML renderer: explicit {.part}, or the
            # profile's pattern. Honouring only the explicit form meant the
            # Vietnamese "PHẦN ..." headings never started a new page here,
            # while they did in the HTML - two emitters disagreeing.
            inferred = bool(part_banner and re.match(part_banner, text))
            # inside the annex every section is a part, as in the HTML edition,
            # where build_annex marks them all
            is_part = ('part' in classes) or force_parts or (inferred and 'no-part' not in classes)
            if is_part and depth == 2:
                out.append('#pagebreak(weak: true)')
            out.append('%s %s' % ('=' * max(1, depth - 1), inline(text, notes)))
            pos += 1
            continue

        # display maths: the label is stripped here, and the number comes from
        # the resolver rather than Typst's own equation numbering, so all three
        # editions call the same equation the same thing
        expr, ident, after = xref.take_equation(lines, pos)
        if expr is not None:
            pos = after
            entry = XREF.get(ident) if ident else None
            if entry:
                out.append('#block(width: 100%%)[#grid(columns: (1fr, auto),'
                           ' align: (center + horizon, right + horizon),'
                           '\n  [$ %s $], [(%d)]\n)]'
                           % (expr.strip(), entry['number']))
            else:
                out.append('$ %s $' % expr.strip())
            continue

        if stripped.startswith('>'):
            buf = []
            while pos < n and lines[pos].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[pos]))
                pos += 1
            buf[0] = re.sub(r'^\[!\w+\]\s*', '', buf[0])
            inner = convert(buf, notes, figures, label, part_banner, force_parts)
            out.append('#block(fill: rgb("#fdf3e3"), inset: 8pt, radius: 3pt, width: 100%%,\n'
                       '  stroke: (left: 3pt + rgb("#c2761a")))[\n%s\n]' % inner)
            continue

        if stripped.startswith('|') and pos + 1 < n and re.match(r'^\|[\s:|-]+\|?$', lines[pos + 1].strip()):
            block, pos = emit_table(lines, pos, notes, out)
            entry, pos = take_caption(lines, pos)
            caption = ('\n#align(center)[#text(size: 9pt, fill: rgb("#4a5568"))[%s]]'
                       % inline(xref.caption_of(entry), notes)) if entry else ''
            if block:
                wide = block.startswith('#table(columns: ') and \
                    int(block[len('#table(columns: '):].split(',')[0]) >= WIDE
                if wide:
                    # A6+ column table is wider than A4 portrait, and print does
                    # not scroll - it cuts the right-hand column off the page,
                    # which in an evidence annex is where the sources are. Typst
                    # takes a flipped page for one block and returns to portrait
                    # after it, the same treatment the reading edition's print
                    # rules give a wide table.
                    out.append('#page(flipped: true, margin: 16mm)[\n'
                               '#text(size: 8pt)[\n%s%s\n]\n]' % (block, caption))
                else:
                    out.append(block + caption)
            continue

        if LIST_RE.match(line):
            pos = emit_list(lines, pos, len(LIST_RE.match(line).group(1).expandtabs(4)), notes, out)
            continue

        buf = []
        while pos < n and lines[pos].strip() and not lines[pos].strip().startswith(('```', '>', '|', '#')) \
                and not LIST_RE.match(lines[pos]) \
                and not re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', lines[pos].strip()):
            buf.append(lines[pos].strip())
            pos += 1
        if buf:
            out.append(inline(' '.join(buf), notes))
    return '\n\n'.join(out)


PREAMBLE = '''#set document(title: "{title}", author: "{author}")
#set page(paper: "a4", margin: (x: 15mm, top: 16mm, bottom: 18mm),
  numbering: "1", number-align: center,
  header: context {{ if counter(page).get().first() > 1 [
    #set text(size: 8pt, fill: rgb("#6b7789"))
    #smallcaps[{running}] #h(1fr) {organisation}
  ] }})
#set text(font: ({body_font}), size: 10.5pt, lang: "{lang}"{rtl})
#set par(justify: true, leading: 0.68em, spacing: 1.1em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(width: 100%, above: 1.4em, below: 0.8em)[
  #set text(font: ({display_font}), size: 15pt, fill: white)
  #block(fill: rgb("{navy}"), inset: (x: 10pt, y: 8pt), radius: 3pt, width: 100%)[
    #it.body
  ]
]
#show heading.where(level: 2): it => block(above: 1.2em, below: 0.5em)[
  #set text(font: ({display_font}), size: 12pt, fill: rgb("{navy3}"))
  #it.body
]
#show heading.where(level: 3): it => block(above: 1em, below: 0.4em)[
  #set text(size: 11pt, weight: "bold", fill: rgb("{navy2}"))
  #it.body
]
#show link: set text(fill: rgb("{navy3}"))
#show table.cell.where(y: 0): set text(weight: "bold", fill: white)
// six columns on A4 leave ~25mm each, too narrow to justify: the body text
// setting stretched two words across a whole line
#show table: set par(justify: false)
#set table(fill: (_, y) => if y == 0 {{ rgb("{navy}") }})

{logo}#align(center)[
  #block(inset: (y: 18pt))[
    #text(size: 9pt, fill: rgb("{amber}"), weight: "bold", tracking: 1.5pt)[{kind}]
    #v(6pt)
    #text(font: ({display_font}), size: 20pt, weight: "bold")[{title}]
    #v(4pt)
    #line(length: 30mm, stroke: 1.5pt + rgb("{amber}"))
  ]
]
{meta}
#v(10pt)
'''


def build(source, output, prof, svgs=None, annex=None, title_kind=None,
          organisation='', brand=None, cache=None, contents_heading=None,
          bibliography=None, citation_style='apa', logo=None):
    """Render one document to PDF through Typst. Returns build facts."""
    brand = brand or {}
    src = Path(source)
    work = Path(cache or src.parent) / ('.typst-%s' % src.stem)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    text = src.read_text(encoding='utf-8').replace('\r\n', '\n')
    front, text = front_mod.split(text)
    lines = text.split('\n')
    annex_lines = Path(annex).read_text(encoding='utf-8').split('\n') if annex else []
    notes, lines = collect_footnotes(lines)
    annex_notes, annex_lines = collect_footnotes(annex_lines)
    notes.update(annex_notes)

    # The head runs to the contents section, matching the HTML path. Using the
    # first rule instead put the metadata block into the body, because these
    # documents fence their metadata between two rules.
    start = None
    if contents_heading:
        marker = '## ' + contents_heading
        start = next((i for i, l in enumerate(lines) if l.strip().startswith(marker)), None)
    if start is None:
        start = next((i for i, l in enumerate(lines)
                      if re.fullmatch(r'-{3,}', l.strip())), 0) + 1
    head, body = lines[:start], lines[start:]
    h1 = next((HEAD_RE.match(l.strip()).group(2) for l in head if l.strip().startswith('# ')), None)
    h2 = next((HEAD_RE.match(l.strip()).group(2) for l in head if l.strip().startswith('## ')), None)
    title = h2 or h1 or src.stem
    kind = (h1 if h2 else title_kind) or prof['labels'].get('document', '')
    meta = [(m.group(1), m.group(2)) for m in
            (META_RE.match(l.strip()) for l in head) if m and m.group(2).strip()]

    XREF.clear()
    XREF.update(xref.resolve(prof, body, annex_lines))
    figures = []
    label = prof['labels'].get('figure', 'Figure %d').replace('%d', '%d')
    part_banner = prof['structure'].get('part_banner')
    typ_body = convert(body, notes, figures, label, part_banner)
    if annex_lines:
        typ_body += ('\n\n#pagebreak()\n\n'
                     + convert(annex_lines, notes, figures, label, part_banner,
                               force_parts=True))

    if svgs:
        rasterise(svgs[:len(figures)], work)

    logo_block = ''
    if logo and Path(logo).exists():
        shutil.copy2(logo, work / Path(logo).name)
        logo_block = ('#align(center)[#image("%s", height: 14mm)]\n#v(6pt)\n'
                      % Path(logo).name)

    front_block = ''
    if front:
        bits = []
        pairs = front_mod.byline(front)
        if pairs:
            bits.append('#align(center)[#text(size: 11pt)[%s]]' % ', '.join(
                '%s#super[%s]' % (esc(n), esc(m)) if m else esc(n) for n, m in pairs))
        aff = front_mod.affiliations(front)
        if aff:
            bits.append('#align(center)[#text(size: 8.5pt, fill: rgb("#4a5568"))[%s]]'
                        % ' \\ '.join('#super[%s]%s' % (esc(k), esc(v))
                                       for k, v in sorted(aff.items())))
        line = front_mod.corresponding(front, prof)
        if line:
            bits.append('#align(center)[#text(size: 8.5pt, fill: rgb("#4a5568"))[%s]]'
                        % esc(line))
        if front.get('abstract'):
            bits.append('#v(8pt)\n#block(width: 84%%, inset: (x: 0pt))[\n'
                        '#text(weight: "bold")[%s]\n\n%s\n]'
                        % (esc(front_mod.label(prof, 'abstract')),
                           inline(str(front['abstract']), {})))
        if front.get('keywords'):
            bits.append('#text(size: 9pt)[*%s:* %s]'
                        % (esc(front_mod.label(prof, 'keywords')),
                           esc(', '.join(str(k) for k in front['keywords']))))
        front_block = '\n'.join(bits) + '\n#v(10pt)\n'

    meta_block = ''
    if meta:
        rows = ',\n    '.join('[#text(fill: rgb("#6b7789"))[%s]], [%s]'
                              % (esc(k), inline(v, {})) for k, v in meta)
        # a grid, not a table: the header styling for content tables would
        # otherwise paint the first metadata row navy
        meta_block = ('#align(center)[#block(width: 80%%)[\n  #grid(columns: 2,'
                      ' align: (right, left), inset: 3pt,\n    %s\n  )]]' % rows)

    # a project's own faces override the profile's, same order as the reading
    # edition, so the two do not disagree about type
    fonts = dict(prof.get('fonts') or {})
    fonts.update({k: v for k, v in brand.items() if k in ('serif', 'sans')})
    def quoted(stack, fallback):
        names = [n.strip().strip('"\'') for n in (stack or fallback).split(',')]
        return ', '.join('"%s"' % n for n in names if n)

    preamble = PREAMBLE.format(
        title=esc(title), author=esc(organisation), running=esc(title[:60]),
        organisation=esc(organisation), lang=prof.get('lang', 'en'),
        rtl=', dir: rtl' if prof.get('direction') == 'rtl' else '',
        body_font=quoted(fonts.get('sans'), 'Helvetica Neue, Arial'),
        display_font=quoted(fonts.get('serif'), 'Georgia'),
        navy=brand.get('navy', '#243b53'), navy2=brand.get('navy-2', '#334e68'),
        navy3=brand.get('navy-3', '#486581'), amber=brand.get('amber', '#8a6d1f'),
        kind=esc(kind), meta=meta_block + front_block, logo=logo_block)

    entries = front_mod.declarations(front, prof)
    if entries:
        typ_body += ('\n\n#v(14pt)\n#line(length: 100%%, stroke: 0.5pt + rgb("#dfe4ec"))\n'
                     '#text(weight: "bold")[%s]\n\n' % esc(front_mod.label(prof, 'declarations'))
                     + '\n\n'.join('*%s.* %s' % (esc(k), inline(str(v), {}))
                                    for k, v in entries))

    if bibliography and cite_mod.find('\n'.join(lines + annex_lines)):
        bib = Path(bibliography)
        shutil.copy2(bib, work / bib.name)
        typ_body += ('\n\n#bibliography("%s", title: "%s", style: "%s")'
                     % (bib.name, prof['labels'].get('references', 'References'),
                        citation_style))
    (work / 'doc.typ').write_text(preamble + '\n' + typ_body + '\n', encoding='utf-8')
    result = subprocess.run(['typst', 'compile', 'doc.typ', str(Path(output).absolute())],
                            cwd=work, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError('typst failed:\n%s' % result.stderr.strip()[:900])
    return {'figures': len(figures), 'footnotes': len(notes),
            'bytes': Path(output).stat().st_size, 'warnings': result.stderr.count('warning:')}


def rasterise(svgs, work, scale=3):
    """Mermaid puts labels in <foreignObject>, which Typst does not draw, so the
    diagrams are rendered to PNG through Chrome instead of embedded as SVG."""
    for i, svg in enumerate(svgs):
        m = re.search(r'viewBox="[^ ]+ [^ ]+ ([\d.]+) ([\d.]+)"', svg)
        w, h = (float(m.group(1)), float(m.group(2))) if m else (800.0, 600.0)
        page = work / ('fig-%d.html' % i)
        page.write_text('<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
                        # mermaid sets style="max-width: NNNpx" inline, which capped the
                        # raster at the diagram's natural size and left the rest white
                        'html,body{margin:0;background:#fff}'
                        'svg{display:block;max-width:none!important;width:%dpx;height:%dpx}'
                        '</style></head><body>%s</body></html>' % (w * scale, h * scale, svg),
                        encoding='utf-8')
        browser.run(['--hide-scrollbars', '--virtual-time-budget=8000',
                     '--window-size=%d,%d' % (w * scale, h * scale),
                     '--screenshot=%s' % (work / ('fig-%d.png' % i)),
                     page.absolute().as_uri()])
