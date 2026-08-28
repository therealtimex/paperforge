"""Refuse to publish documents that still carry internal machinery.

Every rule here comes from something that actually reached a ministry-facing
draft in this corpus: a loop issue id, an agent workflow state token, a handoff
instruction, agent role labels, raw source filenames used as reader-facing
cross-references, and an authoring length spec. They are cheap to detect and
embarrassing to ship, so the gate blocks rather than warns.
"""
import re
from pathlib import Path

# (id, severity, pattern, why)
#
# Core rules apply to any research project: an unfinished marker or a raw
# filename shown to a reader is wrong regardless of who wrote it.
CORE = [
    ('source-filename', 'block', r'\((?:[A-Z][A-Z_]+|[a-z][a-z0-9-]+)\.md\)',
     'raw source filename shown to the reader'),
    # a link *target* of ./NAME.md is fine and keeps the markdown navigable;
    # a link *label* of NAME.md is the reader seeing a filename
    ('filename-label', 'block', r'\[`?[A-Za-z_][A-Za-z0-9_-]*\.md`?\]',
     'source filename used as reader-facing link text'),
    ('length-spec', 'warn', r'(?i)dung lượng chuẩn|~\s*\d+\s*[-–]\s*\d+\s*trang',
     'authoring length specification'),
    ('todo', 'block', r'(?i)\b(?:TODO|TBD|FIXME|XXX|PLACEHOLDER)\b',
     'unfinished marker'),
    ('lorem', 'block', r'(?i)lorem ipsum', 'placeholder text'),
    # Constructs the renderer does not interpret. They do not fail loudly: the
    # syntax is printed literally, and a footnote definition becomes a stray
    # paragraph in the published document. Coverage checks cannot catch this
    # because the text is present - it is simply not rendered.
    #
    # `: Caption {#fig-x}` used to be here. It is a supported construct now, so
    # the rule that blocked it is gone and check_references guards the two ways
    # it can go wrong instead.
    ('unsupported-footnote', 'block', r'^\[\^[^\]]+\]:|\[\^[^\]]+\](?!:)',
     'footnotes are not rendered; the definition would print as body text'),
    # A claim is a node in the map, not a name to use in a sentence: `@sec-` and
    # `@fig-` resolve to something a reader can find on the page, and a claim has
    # no such form. Left unblocked it would print as its own source.
    ('claim-reference', 'block', r'(?<![\w@])@claim-[\w-]+\b',
     'a claim cannot be referred to in prose; refer to its section instead'),
]

# Opt-in packs for a particular authoring system. These four exist because that
# exact machinery reached a ministry-facing draft in one corpus; they are noise
# for a project that does not use RealtimeX Loops, and another organisation has
# its own vocabulary - client codenames, ticket ids, "CONFIDENTIAL - DRAFT".
PACKS = {
    'realtimex-loops': [
        ('loop-id', 'block', r'loop-issue-[a-z0-9-]+', 'internal loop issue identifier'),
        ('agent-state', 'block', r'\b\w+\.(?:draft_ready|review_ready|approved|handoff)\b',
         'agent workflow state token'),
        ('handoff', 'block', r'(?i)handoff\s*(?:target|roadmap)|chuyển giao tiếp theo',
         'internal workflow handoff instruction'),
        ('agent-role', 'block',
         r'\((?:Policy Researcher|Peer Reviewer|Research Director|Editor)\)',
         'agent role label'),
    ],
}


def ruleset(packs=(), extra=()):
    """Core rules, plus any enabled packs, plus the project's own.

    A project declares these in its manifest:

        [lint]
        packs = ["realtimex-loops"]
        [[lint.rule]]
        id = "client-codename"
        severity = "block"
        pattern = "PROJECT (?:BLUEBIRD|CONDOR)"
        why = "internal codename"
    """
    rules = list(CORE)
    for name in packs:
        if name not in PACKS:
            raise ValueError('unknown lint pack %r; available: %s'
                             % (name, ', '.join(sorted(PACKS))))
        rules += PACKS[name]
    for r in extra:
        rules.append((r['id'], r.get('severity', 'block'), r['pattern'],
                      r.get('why', 'project rule')))
    return rules


RULES = CORE + PACKS['realtimex-loops']    # default when no manifest is consulted

FENCE = re.compile(r'```.*?```', re.S)


def check_text(text, skip_code=True, rules=None):
    """Findings for one document body."""
    rules = RULES if rules is None else rules
    if skip_code:
        text = FENCE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    findings = []
    for line_no, line in enumerate(text.split('\n'), 1):
        for rule, severity, pattern, why in rules:
            for m in re.finditer(pattern, line):
                findings.append({'rule': rule, 'severity': severity, 'line': line_no,
                                 'match': m.group(0)[:60], 'why': why,
                                 'context': line.strip()[:90]})
    return findings


def check_document(path, rules=None):
    return check_text(Path(path).read_text(encoding='utf-8'), rules=rules)


def check_publishable(source, declared, blocked, embedded=()):
    """Guard the manifest itself: rendering something undeclared is a bug.

    `declared` is every document in the manifest, including drafts carrying
    `publish = false` - a deliberate draft is not an error, it simply does not
    reach `publish`. `embedded` covers files folded into another document (an
    annex), which are legitimately neither standalone-publishable nor internal.
    """
    name = Path(source).name
    if name in embedded:
        return []
    if name in blocked:
        return [{'rule': 'not-publishable', 'severity': 'block', 'line': 0, 'match': name,
                 'why': 'declared internal in documents.toml', 'context': ''}]
    if name not in declared:
        return [{'rule': 'undeclared', 'severity': 'block', 'line': 0, 'match': name,
                 'why': 'not listed in documents.toml', 'context': ''}]
    return []


def summarise(findings):
    blocking = [f for f in findings if f['severity'] == 'block']
    return {'total': len(findings), 'blocking': len(blocking),
            'rules': sorted({f['rule'] for f in findings})}


def check_citations(document, bibliography=None):
    """Citations with nowhere to resolve to.

    Without a declared bibliography the keys reach Typst as bare labels and it
    fails with "label `<nq57>` does not exist in the document" - true, and no
    help at all to an author who has simply not declared their .bib.
    """
    from . import assemble, citations as cite_mod
    text = '\n'.join(Path(p).read_text(encoding='utf-8')
                     for p in assemble.sources(document))
    keys = cite_mod.find(text)
    if keys and not bibliography:
        return [{'rule': 'no-bibliography', 'severity': 'block', 'line': 0,
                 'match': '[@%s]' % keys[0],
                 'why': '%d citation(s) but no `bibliography` in the manifest' % len(keys),
                 'context': ''}]
    return []


def check_orphans(document, prof=None):
    """Labels nothing refers to, and headings with nothing under them.

    The mirror of `check_references`: that one catches a reference to a label
    that is not there, this one a label nothing points at. Both are invisible
    in the output - a figure nobody discusses still prints, correctly numbered,
    and reads as deliberate.

    These warn rather than block. An annex table no paragraph mentions is
    legitimate, and so is a heading a part banner opens; a warning is the
    useful content of a draft report, not a refusal at publication.
    """
    from . import assemble, xref
    body = assemble.read(document['source_path'],
                         document.get('include_paths')).split('\n')
    annex = document.get('annex_path')
    annex_lines = Path(annex).read_text(encoding='utf-8').split('\n') if annex else []
    table = xref.resolve(prof or {}, body, annex_lines)

    referenced = set()
    for lines in (body, annex_lines):
        for line in lines:
            referenced.update(m.group(1) for m in xref.REF_RE.finditer(line))

    findings = []
    for ident, entry in sorted(table.items()):
        # a section label is often there to give a heading a stable anchor
        # rather than to be referred to, so an unreferenced one is not a finding
        if entry['kind'] not in xref.NUMBERED or ident in referenced:
            continue
        findings.append({'rule': 'orphan-label', 'severity': 'warn',
                         'line': entry['line'] + 1, 'match': ident,
                         'why': 'declared and never referred to in the prose',
                         'context': (entry.get('caption') or '')[:80]})

    for lines, where in ((body, ''), (annex_lines, 'annex ')):
        for line_no, depth in _empty_headings(lines):
            findings.append({'rule': 'empty-section', 'severity': 'warn',
                             'line': line_no, 'match': '#' * depth,
                             'why': 'a %sheading with no prose and no heading beneath it'
                                    % where,
                             'context': lines[line_no - 1].strip()[:80]})
    return findings


def _empty_headings(lines):
    """(line, depth) for headings that open nothing.

    A part banner is not empty: it is followed by the headings it opens, and
    reporting those would fire on every book in the corpus. So a heading counts
    as empty only when nothing at all follows it before the next heading at its
    own level or shallower.
    """
    from . import xref
    heads = [(i, len(m.group(1))) for i, line in enumerate(lines)
             if (m := xref.HEADING_RE.match(line.strip()))]
    empty, fenced = [], False
    for n, (i, depth) in enumerate(heads):
        stop = next((j for j, d in heads[n + 1:] if d <= depth), len(lines))
        deeper = any(j < stop for j, d in heads[n + 1:] if d > depth)
        content = False
        for line in lines[i + 1:stop]:
            s = line.strip()
            if s.startswith('```'):
                fenced = not fenced
            if s and not xref.HEADING_RE.match(s):
                content = True
                break
        if not content and not deeper:
            empty.append((i + 1, depth))
    return empty


def check_claims(document):
    """Claim labels that would reach a reader, or store the wrong gist.

    Both are silent. A brace inside a gist - `gist="the set {a,b}"` - is not
    matched by the attribute pattern at all, so nothing registers the claim and
    nothing strips it: `{#claim-y ...}` prints on the page, which is the defect
    `xref.take_equation` records for `{#eq-x}`. A quote inside one is the
    quieter version: the attribute parses, and the gist is truncated at the
    inner quote without anything saying so.
    """
    from . import assemble, claims as claims_mod, xref
    findings = []
    for path in assemble.sources(document):
        for n, line in enumerate(Path(path).read_text(encoding='utf-8').split('\n'), 1):
            s = line.strip()
            if '{#claim-' not in s:
                continue
            if not xref.take_claim(s)[1]:
                findings.append({'rule': 'malformed-claim', 'severity': 'block',
                                 'line': n, 'match': '{#claim-',
                                 'why': 'a claim label the attribute pattern cannot read; '
                                        'it would print on the page. Braces are not allowed '
                                        'inside a gist', 'context': s[:80]})
                continue
            attrs = xref.ATTR_RE.search(s)
            body = attrs.group(1) if attrs else ''
            if claims_mod.GIST_RE.search(body) and body.count('"') > 2:
                findings.append({'rule': 'truncated-gist', 'severity': 'block',
                                 'line': n, 'match': 'gist=',
                                 'why': 'a quote inside a gist; what is stored would stop '
                                        'at it', 'context': s[:80]})
    return findings


def check_front_matter(source):
    """Front matter that would render wrong, in the terms an author can fix.

    An affiliation marker pointing at nothing is invisible in the output and
    wrong for the reader - the same class as a dangling cross-reference. So is
    an abstract that TOML swallowed into [affiliation] because it was written
    below the table header.
    """
    from . import front as front_mod
    text = Path(source).read_text(encoding='utf-8')
    try:
        data, _ = front_mod.split(text)
    except ValueError as err:
        return [{'rule': 'front-matter', 'severity': 'block', 'line': 1,
                 'match': '+++', 'why': str(err), 'context': ''}]
    return [{'rule': 'front-matter', 'severity': 'block', 'line': 1,
             'match': '+++', 'why': problem, 'context': ''}
            for problem in front_mod.problems(data)]


def check_references(document, prof=None):
    """Cross-references that point nowhere, and labels declared twice.

    Neither is visible in the output: an unresolved reference prints as its own
    source - "see @fig-density" - and a repeated label makes every reference to
    it silently mean the first one. Both are the sort of thing a reader finds
    and an author does not.
    """
    from . import assemble, xref
    body = assemble.read(document['source_path'],
                         document.get('include_paths')).split('\n')
    annex = document.get('annex_path')
    annex_lines = Path(annex).read_text(encoding='utf-8').split('\n') if annex else []
    table = xref.resolve(prof or {}, body, annex_lines)
    findings = []
    for path, lines in ((document['source_path'], body), (annex, annex_lines)):
        if not path:
            continue
        for line_no, ident in xref.dangling(lines, table):
            findings.append({'rule': 'dangling-reference', 'severity': 'block',
                             'line': line_no, 'match': '@' + ident,
                             'why': 'reference to a label that does not exist',
                             'context': lines[line_no - 1].strip()[:80]})
    for ident in xref.duplicates(body, annex_lines):
        findings.append({'rule': 'duplicate-label', 'severity': 'block', 'line': 0,
                         'match': ident, 'why': 'label declared more than once; every '
                         'reference would mean the first', 'context': ''})
    return findings
