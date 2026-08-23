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
    # syntax is printed literally, and a footnote or caption definition becomes
    # a stray paragraph in the published document. Coverage checks cannot catch
    # this because the text is present - it is simply not rendered.
    ('unsupported-footnote', 'block', r'^\[\^[^\]]+\]:|\[\^[^\]]+\](?!:)',
     'footnotes are not rendered; the definition would print as body text'),
    ('unsupported-caption', 'block', r'^:\s+\S.*\{#(?:tbl|fig|eq)-',
     'table and figure captions are not rendered; the line would print as text'),
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
