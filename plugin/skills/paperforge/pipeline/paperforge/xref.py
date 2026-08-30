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

A section labels itself on its own heading, in the attribute block every
emitter already parses and strips:

    ## Methods {#sec-methods}

and `@sec-methods` renders as the heading's own words. It carries no number:
nothing here numbers headings, and four emitters agreeing on a heading counter
is the thing this module exists to prevent.

A label is optional. An unlabelled figure keeps the positional caption it has
always had, so nothing that worked before needs rewriting.
"""
import re

# The two kind sets, and the regexes are built from them rather than repeating
# them - `KINDS` used to be declared here and consumed by nothing, which is how
# a tuple that looks like the source of truth stops being one.
NUMBERED = ('fig', 'tbl', 'eq')     # carry a number and a profile label
KINDS = NUMBERED + ('sec',)         # everything the reference syntax accepts
LABELLED = KINDS + ('claim',)       # everything that can carry an id at all

# One definition, aliased by every emitter: the caption scanner below has to
# agree with them about where a list begins, or it reads a caption inside one
# as attached to a float.
LIST_RE = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.*)$')
CAPTION_RE = re.compile(r'^:\s+(.*?)\s*\{#((%s)-[\w-]+)\}\s*$' % '|'.join(NUMBERED))
DISPLAY_LABEL_RE = re.compile(r'^\$\$\s*\{#((?:eq)-[\w-]+)\}\s*$')
OPEN_FENCE_RE = re.compile(r'^\$\$\s*$')
REF_RE = re.compile(r'(?<![\w@])@((?:%s)-[\w-]+)\b' % '|'.join(KINDS))

# A heading and its trailing attribute block. Every emitter already parses and
# strips this - three identical copies of the pattern existed - and it now also
# carries a fact the whole pipeline shares, so it belongs here with the rest of
# them. `## Methods {#sec-methods}` or `{.part #sec-methods}`, either order.
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
ATTR_RE = re.compile(r'\s*\{([^{}]*)\}\s*$')
SEC_ID_RE = re.compile(r'#(sec-[\w-]+)')

# A claim labels itself at the end of its own paragraph, which is the only
# place a paragraph has that it does not share with the next one. It is the
# one labelled thing with no rendered form: it is not numbered, `@claim-x` is
# not part of the reference syntax, and lint blocks it in prose. A claim is a
# node in the map, not a name to use in a sentence.
CLAIM_ID_RE = re.compile(r'#(claim-[\w-]+)')

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


def take_claim(text):
    """A paragraph's trailing claim label, and the paragraph without it.

    Returns `(text, id or None)`. Only an attribute that actually carries a
    claim id is taken: a paragraph is entitled to end in braces, and stripping
    one that does would delete an author's words.
    """
    m = ATTR_RE.search(text)
    ident = CLAIM_ID_RE.search(m.group(1)) if m else None
    if not ident:
        return text, None
    return text[:m.start()].rstrip(), ident.group(1)


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
            continue
        # A section labels itself on its own heading, not on a line after it:
        # a heading has no caption, and the attribute block is already where
        # every emitter looks for `{.part}`.
        m = HEADING_RE.match(stripped)
        if m:
            attrs = ATTR_RE.search(m.group(2))
            ident = SEC_ID_RE.search(attrs.group(1)) if attrs else None
            if ident:
                found.append({'line': i, 'id': ident.group(1), 'kind': 'sec',
                              'caption': m.group(2)[:attrs.start()].rstrip(),
                              'annex': annex})
            continue            # a heading is a section; it is never a claim
        _, ident = take_claim(stripped)
        if ident:
            found.append({'line': i, 'id': ident, 'kind': 'claim',
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
            if entry['kind'] == 'claim':
                # Nothing renders a claim, so it has no label to carry. What
                # it says lives in the paragraph; storing that needs block
                # boundaries this line scan does not have. See the map issue.
                entry['number'] = None
                entry['label'] = ''
            elif entry['kind'] == 'sec':
                # A section has no number to have - nothing in this pipeline
                # numbers headings, and four emitters agreeing on a counter is
                # the failure this module exists to prevent. A reference to a
                # section renders as the heading's own words. `caption` is
                # cleared so `caption_of` cannot say "Methods. Methods".
                entry['number'] = None
                entry['label'] = entry['caption']
                entry['caption'] = ''
            else:
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


def attached_captions(lines):
    """Line indices where a caption is attached to something that carries one.

    A caption is not free-standing markup: it belongs to the block above it,
    and every emitter takes it by looking back from a float. When it is written
    under something no emitter treats as a float - a paragraph, a list, an
    image before #86 - nothing consumes it and it prints to the reader as
    prose, braces and all, while `@fig-x` still resolves to a number that names
    nothing on the page. Neither `dangling` nor the orphan check can see that:
    the label exists and is referred to. Only this can.

    The three kinds here are the three the emitters take captions after. If a
    fourth is added and this is not, the failure is a false report on a correct
    document - loud, and fixed in one place - rather than another float that
    silently prints its own caption.
    """
    from . import images as img_mod

    slots, pos, n = set(), 0, len(lines)

    def next_line(i):
        while i < n and not lines[i].strip():
            i += 1
        return i

    while pos < n:
        stripped = lines[pos].strip()
        if stripped.startswith('```'):
            lang = stripped[3:].strip().lower()
            pos += 1
            while pos < n and not lines[pos].strip().startswith('```'):
                pos += 1
            pos += 1
            if lang == 'mermaid':
                slots.add(next_line(pos))
            continue
        if (stripped.startswith('|') and pos + 1 < n
                and re.match(r'^\|[\s:*|-]+\|?$', lines[pos + 1].strip())):
            pos += 2
            while pos < n and lines[pos].strip().startswith('|'):
                pos += 1
            slots.add(next_line(pos))
            continue
        if LIST_RE.match(lines[pos]):
            # a list swallows its own indented content, so an image inside one
            # is rendered in the item and the caption under the list is left as
            # prose. Skipping the block is what makes that reportable.
            pos += 1
            while pos < n and (not lines[pos].strip() or LIST_RE.match(lines[pos])
                               or lines[pos][:1].isspace()):
                pos += 1
            continue
        if img_mod.ONLY_RE.match(lines[pos]):
            slots.add(next_line(pos + 1))
        pos += 1
    return slots
