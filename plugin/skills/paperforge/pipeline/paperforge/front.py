"""Structured front matter: authors, affiliations, abstract, declarations.

A document head is prose - `**Publisher:** Ministry of X` - which is right for
a ministry cover and wrong for a manuscript, where the same information has to
be data: an author carries affiliation markers, an ORCID and a flag saying
whether they are the corresponding one, and those markers have to point at
numbered affiliations that actually exist.

TOML rather than YAML, delimited by `+++`. `tomllib` is in the standard library
and the manifest is already TOML, so an author has one syntax to learn rather
than two - and this pipeline vendors reveal.js and refuses pandoc rather than
buy a dependency for one feature.

    +++
    [[author]]
    name = "Trần Văn A"
    affiliation = [1, 2]
    orcid = "0000-0002-1825-0097"
    corresponding = true
    email = "a@example.gov.vn"

    abstract = "..."
    keywords = ["Physical AI", "Việt Nam"]

    [affiliation]
    1 = "Bộ Ngoại giao"
    2 = "Trung tâm Đổi mới sáng tạo Quốc gia"

    [declarations]
    funding = "..."
    conflicts = "None declared."
    +++

Rendering is the emitters' business. This module parses, validates and lays out
the pieces as plain text and marker lists, so three emitters cannot each decide
a different superscript order.

Scalar keys go above the first table header. That is TOML's rule, not ours, and
getting it wrong is quiet - an abstract written below [affiliation] becomes an
affiliation - so problems() names it rather than leaving the author to wonder
where their abstract went.
"""
import re
import tomllib

FENCE = '+++'
LABELS = {
    'abstract': 'Abstract',
    'keywords': 'Keywords',
    'corresponding': 'Corresponding author',
    'funding': 'Funding',
    'conflicts': 'Conflicts of interest',
    'ethics': 'Ethics',
    'declarations': 'Declarations',
}
DECLARATION_ORDER = ('funding', 'conflicts', 'ethics', 'data', 'acknowledgements')


def split(text):
    """(front matter dict, remaining markdown). No fence means no front matter.

    A malformed block is an error rather than a silent skip: an author who has
    written front matter and mistyped it should be told, not handed a document
    with their author list missing.
    """
    lines = text.replace('\r\n', '\n').split('\n')
    if not lines or lines[0].strip() != FENCE:
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == FENCE:
            block = '\n'.join(lines[1:i])
            try:
                data = tomllib.loads(block)
            except tomllib.TOMLDecodeError as err:
                raise ValueError('front matter is not valid TOML: %s' % err) from None
            return data, '\n'.join(lines[i + 1:])
    raise ValueError('front matter opened with +++ and never closed')


def label(prof, key):
    return ((prof or {}).get('labels') or {}).get(key, LABELS[key])


MARKER_RE = re.compile(r'^[0-9a-z]{1,3}$')


def affiliations(front):
    """{marker: text}, markers as written - TOML keys are strings.

    Only marker-shaped keys count. In TOML a bare key written *after* a table
    header belongs to that table, so `abstract = "..."` placed below
    `[affiliation]` silently becomes an affiliation. Filtering here keeps the
    rendering sane; `problems()` says what happened so the author can fix it.
    """
    return {str(k): v for k, v in (front.get('affiliation') or {}).items()
            if MARKER_RE.match(str(k)) and isinstance(v, str)}


def stray(front):
    """Keys that landed in [affiliation] because they were written after it."""
    return [str(k) for k, v in (front.get('affiliation') or {}).items()
            if not (MARKER_RE.match(str(k)) and isinstance(v, str))]


def authors(front):
    """Authors with their markers resolved, in declaration order."""
    known = affiliations(front)
    out = []
    for a in front.get('author') or []:
        markers = [str(m) for m in (a.get('affiliation') or [])]
        out.append({
            'name': a.get('name', ''),
            'markers': markers,
            'unknown': [m for m in markers if m not in known],
            'orcid': a.get('orcid'),
            'email': a.get('email'),
            'corresponding': bool(a.get('corresponding')),
        })
    return out


def byline(front, star='*'):
    """"Trần Văn A^1,2,*^, Nguyễn Thị B^2^" as (name, superscript) pairs.

    Returned as pairs rather than a formatted string because a superscript is
    markup, and three emitters express it three different ways.
    """
    pairs = []
    for a in authors(front):
        marks = list(a['markers'])
        if a['corresponding']:
            marks.append(star)
        pairs.append((a['name'], ','.join(marks)))
    return pairs


def corresponding(front, prof=None):
    """The corresponding author line, or ''."""
    for a in authors(front):
        if a['corresponding'] and a.get('email'):
            return '%s: %s (%s)' % (label(prof, 'corresponding'), a['name'], a['email'])
        if a['corresponding']:
            return '%s: %s' % (label(prof, 'corresponding'), a['name'])
    return ''


def declarations(front, prof=None):
    """[(label, text)] in a stable order, then anything else declared."""
    block = front.get('declarations') or {}
    out = []
    for key in DECLARATION_ORDER:
        if block.get(key):
            out.append((label(prof, key) if key in LABELS else key.title(), block[key]))
    for key, value in block.items():
        if key not in DECLARATION_ORDER and value:
            out.append((key.replace('_', ' ').title(), value))
    return out


def problems(front):
    """What is wrong with the front matter, in the terms an author can fix.

    An affiliation marker pointing at nothing is the same class of defect as a
    dangling cross-reference: invisible in the output and wrong for the reader.
    """
    found = []
    if not front:
        return found
    for key in stray(front):
        found.append('%r was written after [affiliation], so TOML read it as an '
                     'affiliation. Move it above the first table header.' % key)
    known = affiliations(front)
    for a in authors(front):
        if not a['name']:
            found.append('an author has no name')
        for marker in a['unknown']:
            found.append('author %r cites affiliation %s, which is not declared'
                         % (a['name'], marker))
        if a['orcid'] and not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', a['orcid']):
            found.append('ORCID %r for %r is not in 0000-0000-0000-0000 form'
                         % (a['orcid'], a['name']))
    used = {m for a in authors(front) for m in a['markers']}
    for marker in known:
        if marker not in used:
            found.append('affiliation %s is declared but no author cites it' % marker)
    if front.get('author') and not any(a['corresponding'] for a in authors(front)):
        found.append('no author is marked corresponding')
    return found
