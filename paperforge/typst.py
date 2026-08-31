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

from . import assemble
from . import browser, citations as cite_mod, front as front_mod
from . import images as img_mod, palette, profile, xref

LIST_RE = xref.LIST_RE
HEAD_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*$')
META_RE = re.compile(r'^\*\*(.+?):\*\*\s*(.*)$')
# One definition, in xref.py: the attribute block now carries a section id
# the whole pipeline shares, not just this emitter's `{.part}`.
ATTR_RE = xref.ATTR_RE
FOOTNOTE_DEF = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$')

# Every character Typst reads as markup rather than as text. `~` is its
# non-breaking space, and leaving it out meant a source reading `~28x` set
# as `28x` in the PDF and `~28x` in the HTML - a table of estimates printed
# as though the numbers were exact. Add to this list when Typst does.
SPECIAL = '\\#$*_`<>@~'
XREF = {}   # resolved once in xref.py; this emitter never counts for itself
# Resolved once in build(), read by every emitter below - the same arrangement
# as XREF, and for the same reason: these are document-wide facts that half a
# dozen small functions need and none of them should be asked to carry. The
# shipped defaults stand in until a document is built, so this module still
# converts markup outside a build.
PAL = dict(palette.TOKENS)
# Author images, copied beside the generated Typst source so the compile root
# holds everything it needs. Same arrangement as XREF and PAL, for the reason
# given above. They were deleted from the text entirely until #86, under a
# comment claiming they were handled as figures; nothing handled them.
PLATES = []       # every image copied, in the order they were referenced
FLOATS = []       # the subset that are figures: an image in a sentence is not
SRC = {'dir': Path('.')}
# floats already numbered when the annex begins. Numbering restarts there -
# Figure A1 is the annex's first - and only the label was switching over.
BASE = {'n': 0}
# Calibrated, not chosen: see `specs/calibration.md`.
RASTER_SCALE = 3   # of natural size, so a diagram is not soft on paper


def plate(src):
    """The name to reference an image by inside the Typst source, or None.

    Copied rather than referenced in place: the compile runs in a working
    directory beside the document, and a path that climbs out of it is a path
    that breaks the moment the project is built from somewhere else.

    An SVG is rasterised rather than placed. Typst draws vector art as vector
    operations, which is the better result on paper and invisible to the gate
    that compares the editions - `figures_agree` counts images in the PDF, so a
    figure present in all three editions read as a figure missing from one.
    Diagrams already take this route, so one kind of picture is not quietly
    treated differently from another.
    """
    found = img_mod.resolve(src, SRC['dir'])
    if not found:
        return None
    i = len(PLATES)
    name = ('plate-%d-0.png' % i if found.suffix.lower() == '.svg'
            else 'plate-%d%s' % (i, found.suffix.lower()))
    PLATES.append((name, found))
    return name


def colour(token):
    """A palette token as a Typst colour.

    Every colour in this emitter comes through here. Writing one as a literal
    produces the right colour by default and ignores the project's palette
    forever, which is a defect that reads as finished code - see palette.py.
    """
    return 'rgb("%s")' % PAL[token]


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
    # an image inside a sentence: set inline, at the height of the line. An
    # image on a line of its own never reaches here - the block pass takes it
    # as a figure - so this is the decorative case, not the illustration.
    def inline_image(m):
        name = plate(m.group(2))
        if name:
            return keep('#box(image("%s", height: 1.1em))' % name)
        # never silence: the block path and the reading edition both show the
        # gap, and an edition that drops content quietly is the failure here
        return keep('#text(style: "italic")[%s]'
                    % esc('[image not found: %s]' % m.group(2)))

    text = img_mod.IMAGE_RE.sub(inline_image, text)
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


# Named trim sizes, in millimetres. Royal octavo is the academic monograph,
# ISO B5 its common European alternative, and A4 is what a thesis is bound in.
# The set is small on purpose: a trim is a decision made with a printer, and
# accepting any two numbers invites one made with nobody.
TRIM = {'a4': (210, 297), 'a5': (148, 210), 'b5': (176, 250), 'royal': (156, 234)}

# A bound page is asymmetric: the inside edge disappears into the gutter, so it
# needs more margin than the outside one, not the same.
BOUND_MARGIN = 'inside: 22mm, outside: 16mm, top: 18mm, bottom: 20mm'
LOOSE_MARGIN = 'x: 15mm, top: 16mm, bottom: 18mm'

# The top margin of a bound page, in points: the band the running head sits in,
# and the band anything reading "what opens this page" has to skip. See
# editions.page_text.
HEADER_BAND = 18 * 72 / 25.4


# A chapter opens on a recto, and the leaf left blank to put it there carries no
# folio and no running head - a page number alone on an empty page is the first
# thing that says nobody typeset this.
#
# The `set` is scoped to the block, so it styles the pages `to: "odd"` skips and
# nothing else: measured, the page before the break keeps its folio and the
# chapter opening gets one. Computing the skip by hand instead - `pagebreak(weak:
# true)` then a context testing `calc.even(here().page())` - does not converge,
# because inserting the break makes the page odd, which removes the break, which
# makes it even. Chapter one landed on a verso.
RECTO = """#let pf-recto() = {
  set page(header: none, footer: none, numbering: none)
  pagebreak(to: "odd", weak: true)
}
"""

# Front matter numbers in roman and the book proper restarts at arabic 1, on a
# recto. The chapter that follows calls pf-recto() again; on an empty odd page
# that break is a no-op, and because no page starts inside its scope the folio
# survives.
MAIN_MATTER = """#pf-recto()
#set page(numbering: "1")
#counter(page).update(1)"""


# The mark the emitter puts on every heading that opens a page. Querying
# `heading.where(level: 1)` instead is a proxy for it, and the proxy is wrong in
# a case that can be stated: a `##` marked {.no-part} is a top-level heading that
# does *not* open a page, so a leaf whose text runs on past one lost its running
# head - measured, page 14 of a bound test came back bare. The emitter already
# knows which headings open a page; it says so rather than leaving the header to
# infer it.
CHAPTER = '<pf-chapter>'


def split_meta(lines):
    """`**Key:** value` lines, and everything that is not one."""
    meta, rest = [], []
    for line in lines:
        m = META_RE.match(line.strip())
        if m and m.group(2).strip():
            meta.append((m.group(1), m.group(2)))
        else:
            rest.append(line)
    return meta, rest


def meta_grid(meta):
    """A head's metadata as the two-column block. Both heads use it.

    The document head has always been set this way; the annex head let its
    metadata fall through as body prose, which keeps the colon that the grid
    drops - "Prepared by: Paperforge" in the print edition against "Prepared
    by | Paperforge" in the reading one. Whether `verify` noticed depended on
    how many words the title had, because the probe is its first six: a
    two-word title put the colon inside the probe and the annex head came back
    unlocated, a four-word title did not.
    """
    if not meta:
        return ''
    rows = ',\n    '.join('[#text(fill: %s)[%s]], [%s]'
                          % (colour('muted'), esc(k), inline(v, {})) for k, v in meta)
    # a grid, not a table: the header styling for content tables would
    # otherwise paint the first metadata row navy
    return ('#align(center)[#block(width: 80%%)[\n  #grid(columns: 2,'
            ' align: (right, left), inset: 3pt,\n    %s\n  )]]' % rows)


def running_head(title, organisation, binding):
    """The line across the top of every page after the first.

    Unbound, that is the document title throughout. Bound, it is the classical
    setting: the book on the verso, the chapter on the recto, and nothing at all
    on a page a chapter opens - a running head above a chapter title repeats it.
    Parity is taken from the physical leaf rather than the printed folio, which
    restarts at the main matter and would put versos on the right.
    """
    if not binding:
        return ('context { if counter(page).get().first() > 1 [\n'
                '    #set text(size: 8pt, fill: ' + colour('muted') + ')\n'
                '    #smallcaps[' + title + '] #h(1fr) ' + organisation + '\n'
                '  ] }')
    return ('context {\n'
            '    let leaf = here().page()\n'
            '    let opens = query(' + CHAPTER + ').any(h => h.location().page() == leaf)\n'
            '    if leaf > 1 and not opens {\n'
            '      set text(size: 8pt, fill: ' + colour('muted') + ')\n'
            '      let seen = query(selector(' + CHAPTER + ').before(here()))\n'
            '      if calc.even(leaf) [ #smallcaps[' + title + '] #h(1fr) '
            + organisation + ' ]\n'
            '      else [ #h(1fr) #emph(if seen.len() > 0 { seen.last().body } else [ ]) ]\n'
            '    }\n'
            '  }')


def span(content, columns):
    """Content that must cross the gutter of a two-column page.

    Typst floats a `scope: "parent"` placement to the top of the page and flows
    the columns around it, which is how a journal sets a figure or a table too
    wide for one column. In a one-column document there is no gutter and the
    content is returned as it is.
    """
    if columns < 2:
        return content
    return '#place(top, scope: "parent", float: true)[\n%s\n]' % content


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
    return ('#table(columns: %d, stroke: 0.4pt + %s, inset: %dpt,\n  %s\n)'
            % (cols, colour('line'), inset, ',\n  '.join(cells))), pos


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


def convert(lines, notes, figures, label, part_banner=None, force_parts=False,
            columns=1, binding=False):
    """Block pass. `figures` receives (index, caption) for each diagram.

    `columns` is carried through because two blocks cannot live inside a
    column: a wide table, which already needs a landscape page of its own, and
    a diagram, which at 88mm is a flowchart nobody can read. Both span the
    full measure instead, which is what a journal does with them.
    """
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
                idx = len(figures)          # which rasterised PNG this is
                ordinal = idx + len(FLOATS) - BASE['n']  # which figure it is
                figures.append(idx)
                # the emitter numbers figures, matching the HTML edition, so
                # Typst's own supplement is suppressed - otherwise the caption
                # reads "Hình 1: Sơ đồ 1", its label and ours doubled up
                entry, pos = take_caption(lines, pos)
                cap = xref.caption_of(entry) if entry else label % (ordinal + 1)
                # '92%', not '92%%': this is an argument to the format, not
                # part of it, so nothing consumes the doubled sign. A stray %%
                # has reached a Typst source here before; it compiles to
                # "invalid number suffix" and nothing earlier says why.
                width = '78%' if columns > 1 else '92%'
                fig = ('#figure(image("fig-%d.png", width: %s), caption: [%s],'
                       ' supplement: none, numbering: none)'
                       % (idx, width, inline(cap, notes)))
                out.append(span(fig, columns))
            else:
                out.append('#raw("%s", block: true)' % '\\n'.join(
                    l.replace('\\', '\\\\').replace('"', '\\"') for l in buf))
            continue

        m = img_mod.ONLY_RE.match(line)
        if m:
            ordinal = len(figures) + len(FLOATS) - BASE['n']
            name = plate(m.group(2))
            FLOATS.append(name)
            pos += 1
            entry, pos = take_caption(lines, pos)
            cap = xref.caption_of(entry) if entry else label % (ordinal + 1)
            if name:
                width = '78%' if columns > 1 else '92%'
                out.append(span('#figure(image("%s", width: %s), caption: [%s],'
                                ' supplement: none, numbering: none)'
                                % (name, width, inline(cap, notes)), columns))
            else:
                # only reachable in a draft build; lint blocks the same
                # reference at publication
                out.append('#align(center)[#text(fill: %s, style: "italic")[%s]]'
                           % (colour('ink-soft'), esc('image not found: %s' % m.group(2))))
            continue

        if re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', stripped):
            out.append('#line(length: 100%%, stroke: 0.5pt + %s)' % colour('line'))
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
                # bound, a chapter opens on the right-hand leaf, which is the
                # difference between a book and a long report printed on both
                # sides; pf-recto() leaves the verso before it properly blank.
                # Not inside an annex: there every section is a part, and a book
                # gives an appendix a recto but not each section within it - six
                # sections would cost six blank leaves to say nothing.
                out.append('#pf-recto()' if binding and not force_parts
                           else '#pagebreak(weak: true)')
            # depth 1 is an annex title, which opens a page from the break
            # written before the annex rather than from here
            opens_page = (is_part and depth == 2) or depth == 1
            heading = '%s %s%s' % ('=' * max(1, depth - 1), inline(text, notes),
                                   ' ' + CHAPTER if binding and opens_page else '')
            # a part banner is a full-bleed block that opens a page, so it
            # crosses the gutter rather than sitting in the left column - the
            # reading edition's print rules span it the same way
            out.append(span(heading, columns) if is_part and depth == 2 else heading)
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
            # the type is what makes a warning a warning. It was matched here,
            # stripped, and thrown away, so `> [!WARNING]` printed in the note
            # colours - a limitation of this emitter, one line above the block
            # it was needed in, and not of Typst
            mark = re.match(r'^\[!(\w+)\]\s*(.*)$', buf[0].strip())
            kind = mark.group(1) if mark else 'note'
            if mark:
                buf[0] = mark.group(2)
            rule, fill, hairline = palette.variant(kind)
            inner = convert(buf, notes, figures, label, part_banner, force_parts,
                            columns, binding)
            # `rest` draws the hairline the reading edition has always drawn
            # around a callout; this block had the edge rule and nothing else
            out.append('#block(fill: %s, inset: 8pt, radius: 3pt, width: 100%%,\n'
                       '  stroke: (left: 3pt + %s, rest: 0.5pt + %s))[\n%s\n]'
                       % (colour(fill), colour(rule), colour(hairline), inner))
            continue

        if stripped.startswith('|') and pos + 1 < n and re.match(r'^\|[\s:|-]+\|?$', lines[pos + 1].strip()):
            block, pos = emit_table(lines, pos, notes, out)
            entry, pos = take_caption(lines, pos)
            caption = ('\n#align(center)[#text(size: 9pt, fill: %s)[%s]]'
                       % (colour('ink-soft'),
                          inline(xref.caption_of(entry), notes))) if entry else ''
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
                    # `columns: 1` is not decoration: a seven-column table
                    # already needs the long edge of the paper, and half of it
                    # is not a smaller version of that problem.
                    out.append('#page(flipped: true, margin: 16mm, columns: 1)[\n'
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
            # A claim's label is not the reader's business. Strip it here or
            # `{#claim-x}` prints at the end of the paragraph, which is the
            # defect take_equation records for `{#eq-x}`.
            text = xref.strip_claims(' '.join(buf))
            out.append(inline(text, notes))
    return '\n\n'.join(out)


PREAMBLE = '''#set document(title: "{title}", author: "{author}")
#set page({page_size}, margin: ({margin}),{columns}
  numbering: "{numbering}", number-align: center,
  header: {header})
{recto}#set text(font: ({body_font}), size: 10.5pt, fill: rgb("{ink}"), lang: "{lang}"{rtl})
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

{cover_open}{logo}#align(center)[
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
{cover_close}'''


def build(source, output, prof, svgs=None, annex=None, title_kind=None,
          organisation='', brand=None, cache=None, contents_heading=None,
          bibliography=None, citation_style='apa', logo=None, review=False,
          includes=(), columns=1, binding=False, trim='a4'):
    """Render one document to PDF through Typst. Returns build facts."""
    brand = brand or {}
    PAL.clear()
    PAL.update(palette.resolve(prof, brand))
    src = Path(source)
    work = Path(cache or src.parent) / ('.typst-%s' % src.stem)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    SRC['dir'] = src.parent
    PLATES.clear()
    FLOATS.clear()
    BASE['n'] = 0
    text = assemble.read(src, includes)
    front, text = front_mod.split(text)
    if review:
        front = front_mod.anonymise(front, prof)
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
    meta, _ = split_meta(head)

    XREF.clear()
    XREF.update(xref.resolve(prof, body, annex_lines))
    figures = []
    label = prof['labels'].get('figure', 'Figure %d').replace('%d', '%d')
    part_banner = prof['structure'].get('part_banner')
    # Front matter is the cover and the contents; the book proper begins at the
    # first top-level heading after them, and that is where roman numbering gives
    # way to arabic. A document with no contents section has no front matter to
    # number apart, so it numbers from 1 throughout - which is also every
    # unbound document, and why this is the only place the split is made.
    main = 0
    if binding and contents_heading:
        main = next((i for i, l in enumerate(body[1:], 1)
                     if l.strip().startswith('## ')), 0)
    if main:
        typ_body = (convert(body[:main], notes, figures, label, part_banner,
                            columns=columns, binding=binding)
                    + '\n\n' + MAIN_MATTER + '\n\n'
                    + convert(body[main:], notes, figures, label, part_banner,
                              columns=columns, binding=binding))
    else:
        typ_body = convert(body, notes, figures, label, part_banner,
                           columns=columns, binding=binding)
    if annex_lines:
        # The annex head runs to its first rule - a badge, a title, a meta block
        # - and the reading edition sets the lot as one title block. Converting
        # the whole file with force_parts made that `##` title an annex section,
        # so it opened a page of its own and the two editions disagreed about
        # where the annex began: verify reported 'annex a worked example
        # prepare' unlocated in the PDF while the HTML had it on the annex head.
        # Same split as markdown.build_annex, for the same reason.
        rule = next((i for i, l in enumerate(annex_lines)
                     if re.fullmatch(r'-{3,}', l.strip())), None)
        head = annex_lines[:rule] if rule is not None else []
        sections = annex_lines[rule + 1:] if rule is not None else annex_lines
        # an appendix opens like a chapter, on the right-hand leaf; unbound it
        # opens a page, which is what it has always done
        head_meta, head_rest = split_meta(head)
        # an image path in the annex is written relative to the annex, which
        # may not be the directory the report sits in
        SRC['dir'] = Path(annex).parent
        BASE['n'] = len(figures) + len(FLOATS)
        # the shared resolver, not a plain get: a profile that declares no
        # annex label still numbers Figure A1, and the fallback belongs in
        # one place or the captioned and uncaptioned figures disagree
        label = xref.label_for(prof, 'fig', annex=True)
        typ_body += ('\n\n%s\n\n' % ('#pf-recto()' if binding else '#pagebreak()')
                     + convert(head_rest, notes, figures, label, part_banner,
                               columns=columns, binding=binding)
                     + '\n\n' + meta_grid(head_meta) + '\n\n'
                     + convert(sections, notes, figures, label, part_banner,
                               force_parts=True, columns=columns, binding=binding))

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
        if front.get('anonymised'):
            bits.append('#align(center)[#text(size: 9pt, style: "italic",'
                        ' fill: %s)[%s]]'
                        % (colour('ink-soft'), esc(str(front['anonymised']))))
        pairs = front_mod.byline(front)
        if pairs:
            bits.append('#align(center)[#text(size: 11pt)[%s]]' % ', '.join(
                '%s#super[%s]' % (esc(n), esc(m)) if m else esc(n) for n, m in pairs))
        aff = front_mod.affiliations(front)
        if aff:
            bits.append('#align(center)[#text(size: 8.5pt, fill: %s)[%s]]'
                        % (colour('ink-soft'),
                           ' \\ '.join('#super[%s]%s' % (esc(k), esc(v))
                                        for k, v in sorted(aff.items()))))
        line = front_mod.corresponding(front, prof)
        if line:
            bits.append('#align(center)[#text(size: 8.5pt, fill: %s)[%s]]'
                        % (colour('ink-soft'), esc(line)))
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

    meta_block = meta_grid(meta)

    # a project's own faces override the profile's, same order as the reading
    # edition, so the two do not disagree about type
    fonts = dict(prof.get('fonts') or {})
    fonts.update({k: v for k, v in brand.items() if k in ('serif', 'sans')})
    def quoted(stack, fallback):
        names = [n.strip().strip('"\'') for n in (stack or fallback).split(',')]
        return ', '.join('"%s"' % n for n in names if n)

    # The title block spans the measure, as it does in every two-column
    # journal: a byline broken over a gutter is not a byline.
    preamble = PREAMBLE.format(
        columns=' columns: %d,' % columns if columns > 1 else '',
        cover_open='#place(top + center, scope: "parent", float: true)[\n' if columns > 1 else '',
        cover_close=']\n' if columns > 1 else '',
        page_size='width: %dmm, height: %dmm' % TRIM[trim],
        margin=BOUND_MARGIN if binding else LOOSE_MARGIN,
        numbering='i' if main else '1', recto=RECTO if binding else '',
        header=running_head(esc(title[:60]), esc(organisation), binding),
        title=esc(title), author=esc(organisation), lang=prof.get('lang', 'en'),
        rtl=', dir: rtl' if prof.get('direction') == 'rtl' else '',
        body_font=quoted(fonts.get('sans'), 'Helvetica Neue, Arial'),
        display_font=quoted(fonts.get('serif'), 'Georgia'),
        navy=PAL['navy'], navy2=PAL['navy-2'], navy3=PAL['navy-3'],
        amber=PAL['amber'], ink=PAL['ink'],
        kind=esc(kind), meta=meta_block + front_block, logo=logo_block)

    entries = front_mod.declarations(front, prof)
    if entries:
        typ_body += ('\n\n#v(14pt)\n#line(length: 100%%, stroke: 0.5pt + %s)\n'
                     '#text(weight: "bold")[%s]\n\n'
                     % (colour('line'), esc(front_mod.label(prof, 'declarations')))
                     + '\n\n'.join('*%s.* %s' % (esc(k), inline(str(v), {}))
                                    for k, v in entries))

    if bibliography and cite_mod.find('\n'.join(lines + annex_lines)):
        bib = Path(bibliography)
        shutil.copy2(bib, work / bib.name)
        typ_body += ('\n\n#bibliography("%s", title: "%s", style: "%s")'
                     % (bib.name, prof['labels'].get('references', 'References'),
                        citation_style))
    # a review copy: true line numbers in the margin and double leading, the
    # two things a journal asks for and the reading edition cannot give
    if review:
        preamble += ('\n#set par.line(numbering: "1")\n'
                     '#set par(leading: 1.5em, spacing: 1.5em)\n')
    # After every pass that can register one. The front matter renders last -
    # an abstract, a metadata value and a declaration all go through inline() -
    # so copying earlier left an image named in an abstract referenced by the
    # Typst source and absent from the directory it compiles in.
    for i, (name, found) in enumerate(PLATES):
        if found.suffix.lower() == '.svg':
            rasterise([found.read_text(encoding='utf-8')], work, prefix='plate-%d' % i)
        else:
            shutil.copy2(found, work / name)

    (work / 'doc.typ').write_text(preamble + '\n' + typ_body + '\n', encoding='utf-8')
    result = subprocess.run(['typst', 'compile', 'doc.typ', str(Path(output).absolute())],
                            cwd=work, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError('typst failed:\n%s' % result.stderr.strip()[:900])
    return {'figures': len(figures) + len(FLOATS), 'footnotes': len(notes),
            'bytes': Path(output).stat().st_size, 'warnings': result.stderr.count('warning:')}


def rasterise(svgs, work, scale=RASTER_SCALE, prefix='fig'):
    """Mermaid puts labels in <foreignObject>, which Typst does not draw, so the
    diagrams are rendered to PNG through Chrome instead of embedded as SVG.

    The prefix keeps two sets of rasters apart in one working directory: the
    diagrams this pipeline drew, and an author's own SVG, which Word cannot
    place either."""
    for i, svg in enumerate(svgs):
        m = re.search(r'viewBox="[^ ]+ [^ ]+ ([\d.]+) ([\d.]+)"', svg)
        w, h = (float(m.group(1)), float(m.group(2))) if m else (800.0, 600.0)
        page = work / ('%s-%d.html' % (prefix, i))
        page.write_text('<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
                        # mermaid sets style="max-width: NNNpx" inline, which capped the
                        # raster at the diagram's natural size and left the rest white
                        'html,body{margin:0}'
                        'svg{display:block;max-width:none!important;width:%dpx;height:%dpx}'
                        '</style></head><body>%s</body></html>' % (w * scale, h * scale, svg),
                        encoding='utf-8')
        # A transparent matte rather than a white one. White is a colour chosen
        # where it is written - correct on white paper and a white rectangle on
        # any other - and the way not to have to brand it is not to paint it.
        browser.run(['--hide-scrollbars', '--virtual-time-budget=8000',
                     '--default-background-color=00000000',
                     '--window-size=%d,%d' % (w * scale, h * scale),
                     '--screenshot=%s' % (work / ('%s-%d.png' % (prefix, i))),
                     page.absolute().as_uri()])
