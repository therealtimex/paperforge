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
    abstract = "..."
    keywords = ["Physical AI", "Việt Nam"]

    [[author]]
    name = "Trần Văn A"
    affiliation = [1, 2]
    orcid = "0000-0002-1825-0097"
    corresponding = true
    email = "a@example.gov.vn"

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

Scalar keys go above the first table header - the *first*, which in practice is
[[author]]. That is TOML's rule, not ours, and getting it wrong is quiet: an
abstract written below [[author]] becomes a key of that author, and one written
below [affiliation] becomes an affiliation. Either way it leaves the page with
nothing said. This module's own example had the trap in it until a two-column
manuscript was built and the abstract was not there, so problems() names both
rather than leaving the author to wonder where their abstract went.
"""
import re
import tomllib

FENCE = '+++'
# A funder identifies a group as reliably as a name does, and an
# acknowledgements list names colleagues; neither belongs in a blind copy.
IDENTIFYING = ('funding', 'acknowledgements')
ANONYMISED = 'Author details removed for blind review.'
LABELS = {
    'abstract': 'Abstract',
    'keywords': 'Keywords',
    'corresponding': 'Corresponding author',
    'funding': 'Funding',
    'conflicts': 'Conflicts of interest',
    'ethics': 'Ethics',
    'declarations': 'Declarations',
    'anonymised': ANONYMISED,
}
DECLARATION_ORDER = ('funding', 'conflicts', 'ethics', 'data', 'acknowledgements')
# What an author is allowed to carry. Anything else under [[author]] is a
# document key TOML swallowed because it was written below the header.
AUTHOR_KEYS = ('name', 'affiliation', 'orcid', 'email', 'corresponding')


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


def misplaced(front):
    """Keys under [[author]] that an author does not carry, with whose they are.

    Almost always a document key written below the header: [[author]] is the
    first table header in every example anyone writes, so this is the likelier
    half of the scalar-placement trap - and the half that was missed when the
    [affiliation] half was gated. It also catches a key that is simply not
    supported, which renders nowhere either.
    """
    found = []
    for a in front.get('author') or []:
        for key in a:
            if key not in AUTHOR_KEYS:
                found.append((key, a.get('name', '')))
    return found


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
    for key, name in misplaced(front):
        # Two things produce this - a document key written below [[author]], and
        # a key an author simply does not carry - and the message has to hold
        # for both rather than assert the likelier one and be wrong about the
        # other. Either way the value renders nowhere, which is the finding.
        found.append('%r is not a key an author carries, so nothing renders it. '
                     'If it belongs to the document, move it above the first table '
                     'header: TOML reads a scalar written below [[author]] as a key '
                     'of that author (%r).' % (key, name))
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


def anonymise(front, prof=None):
    """The same front matter with everything identifying removed.

    Not a redaction of the rendered page - the identifying fields never reach
    an emitter, so there is nothing to leak. The abstract, keywords and the
    non-identifying declarations stay, because a reviewer needs them.
    """
    if not front:
        return front
    kept = {k: v for k, v in front.items() if k not in ('author', 'affiliation')}
    block = {k: v for k, v in (front.get('declarations') or {}).items()
             if k not in IDENTIFYING}
    if block:
        kept['declarations'] = block
    else:
        kept.pop('declarations', None)
    kept['anonymised'] = label(prof, 'anonymised') if prof else ANONYMISED
    return kept
