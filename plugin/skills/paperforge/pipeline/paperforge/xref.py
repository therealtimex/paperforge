"""Captions and numbered cross-references, resolved once for every edition.

Four emitters now render the same source. Each could number its own figures,
and each would be right on its own - which is exactly how this pipeline's
editions have disagreed before, every single time an emitter was added. So the
numbering happens here, once, and every emitter is handed text that is already
resolved. An emitter that counts is an emitter that will eventually count
differently.

Syntax is the one authors already expect from Pandoc and Quarto:

    ```mermaid
    ...
    ```
    : Robot density by country, 2025 {#fig-density}

    | ... |
    : Legal instruments in force {#tbl-instruments}

    $$
    a^2 + b^2 = c^2
    $$ {#eq-pythagoras}

and a reference is `@fig-density`, which renders as the localised label and
number - "Figure 3", "Sơ đồ 3" - in prose, in a table cell, in a caption.

A label is optional. An unlabelled figure keeps the positional caption it has
always had, so nothing that worked before needs rewriting.
"""
import re

CAPTION_RE = re.compile(r'^:\s+(.*?)\s*\{#((fig|tbl|eq)-[\w-]+)\}\s*$')
DISPLAY_LABEL_RE = re.compile(r'^\$\$\s*\{#((?:eq)-[\w-]+)\}\s*$')
OPEN_FENCE_RE = re.compile(r'^\$\$\s*$')
REF_RE = re.compile(r'(?<![\w@])@((?:fig|tbl|eq)-[\w-]+)\b')
KINDS = ('fig', 'tbl', 'eq')

# Profile labels, with the shape every profile already uses for `figure`.
FALLBACK = {'fig': 'Figure %d', 'tbl': 'Table %d', 'eq': 'Equation %d'}
KEY = {'fig': 'figure', 'tbl': 'table', 'eq': 'equation'}
ANNEX_KEY = {'fig': 'annex_figure', 'tbl': 'annex_table', 'eq': 'annex_equation'}


def label_for(prof, kind, annex=False):
    labels = (prof or {}).get('labels', {})
    if annex:
        text = labels.get(ANNEX_KEY[kind])
        if text:
            return text
        # an annex label the profile does not declare falls back to the body
        # one with an A, matching how annex figures have always been numbered
        base = labels.get(KEY[kind], FALLBACK[kind])
        return base.replace('%d', 'A%d')
    return labels.get(KEY[kind], FALLBACK[kind])


def scan(lines, annex=False):
    """Labelled captions in document order, with what they caption.

    A caption line follows the thing it describes, which is how a reader writes
    it and how Pandoc reads it. Equations carry their label on the closing
    fence instead, because a display block has no natural line after it.
    """
    found = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = CAPTION_RE.match(stripped)
        if m:
            found.append({'line': i, 'id': m.group(2), 'kind': m.group(3),
                          'caption': m.group(1), 'annex': annex})
            continue
        m = DISPLAY_LABEL_RE.match(stripped)
        if m:
            found.append({'line': i, 'id': m.group(1), 'kind': 'eq',
                          'caption': '', 'annex': annex})
    return found


def resolve(prof, body, annex=()):
    """{id: entry} with numbers assigned, body first then annex.

    Numbering restarts in the annex, which is what the annex label expresses:
    Figure A1 is the annex's first, not the document's fourteenth.
    """
    table, counters = {}, {}
    for lines, is_annex in ((body, False), (annex, True)):
        if is_annex:
            counters = {}
        for entry in scan(lines, annex=is_annex):
            counters[entry['kind']] = counters.get(entry['kind'], 0) + 1
            entry['number'] = counters[entry['kind']]
            entry['label'] = label_for(prof, entry['kind'], is_annex) % entry['number']
            table.setdefault(entry['id'], entry)
    return table


def caption_of(entry):
    """"Figure 3. Robot density by country" - the label, then the text."""
    if not entry.get('caption'):
        return entry['label']
    return '%s. %s' % (entry['label'], entry['caption'])


def substitute(text, table, missing=None):
    """Replace @fig-x with its resolved label. Unknown ids are left alone and
    collected, so a reference to nothing is reported rather than silently
    printed as raw source or silently deleted."""
    def one(m):
        entry = table.get(m.group(1))
        if entry:
            return entry['label']
        if missing is not None:
            missing.append(m.group(1))
        return m.group(0)
    return REF_RE.sub(one, text)


def dangling(lines, table):
    """References that point at no label, with the line they are on."""
    found = []
    for i, line in enumerate(lines, 1):
        for m in REF_RE.finditer(line):
            if m.group(1) not in table:
                found.append((i, m.group(1)))
    return found


def duplicates(body, annex=()):
    """Ids declared more than once. The second declaration would be
    unreachable, and every reference would silently mean the first."""
    seen, repeated = set(), []
    for lines, is_annex in ((body, False), (annex, True)):
        for entry in scan(lines, annex=is_annex):
            if entry['id'] in seen:
                repeated.append(entry['id'])
            seen.add(entry['id'])
    return repeated


def take_equation(lines, pos):
    """A display maths block starting at `pos`, if that is what is there.

    Returns (expression, id or None, position after the block). The label lives
    on the closing fence, so nothing else in the pipeline sees it - and until
    this existed, nothing stripped it either and `{#eq-x}` printed on the page.
    """
    if pos >= len(lines) or not OPEN_FENCE_RE.match(lines[pos].strip()):
        return None, None, pos
    body, look = [], pos + 1
    while look < len(lines):
        stripped = lines[look].strip()
        if stripped == '$$' or DISPLAY_LABEL_RE.match(stripped):
            m = DISPLAY_LABEL_RE.match(stripped)
            return '\n'.join(body), (m.group(1) if m else None), look + 1
        body.append(lines[look])
        look += 1
    return None, None, pos          # unterminated: leave it to the paragraph path
