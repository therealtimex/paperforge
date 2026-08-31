"""What somebody had to do because the pipeline would not.

Four workarounds were found in one project by scanning it weeks later: a
document restructured to dodge a defect, a script to generate markup, forty
lines of interpreter archaeology, and a reviewer's own checking code. Each was
reasonable under deadline. Each removed the only trace that anything was wrong,
and all four were found by a person asking rather than by any gate.

So the rule is not "solve or report" - an author with a deadline should solve
it - but **solve and report**. This writes the report, and carries the facts an
agent cannot be expected to assemble: what version, scaffolded by what, which
tools are present, which run was the last one. "Paperforge didn't work" is not
diagnosable; those four things with a sentence are.

Local, never filed. Three times in one week an agent's diagnosis was right
about the symptom and wrong about the cause, and an auto-filed tracker fills
with plausible misattributions until nobody reads it - the failure the severity
vocabulary exists to prevent. A person turns a note into an issue.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, require, scaffold

NOTES = '.paperforge/friction'


def facts(root, config=None):
    """What the note carries besides the words: the state nobody types by hand."""
    tools = {name: bool(path) for name, path, _ in require.report()}
    tools.update({name: ok for name, ok, _, _ in require.libraries()})
    runs = sorted((Path(root) / '.paperforge' / 'runs').glob('*/record.json'))
    last = None
    if runs:
        try:
            last = {'id': runs[-1].parent.name,
                    'stages': json.loads(runs[-1].read_text(encoding='utf-8'))['stages']}
        except (ValueError, KeyError):
            last = {'id': runs[-1].parent.name, 'stages': 'unreadable'}
    return {
        'version': __version__,
        'scaffold': scaffold.drift(root),
        'missing': sorted(k for k, ok in tools.items() if not ok),
        'last_run': last,
        'config': str(config) if config else None,
    }


def write(root, what, root_facts=None):
    """Record one piece of friction. Returns the path written."""
    got = root_facts or facts(root)
    when = datetime.now(timezone.utc)
    path = Path(root) / NOTES / ('%s.md' % when.strftime('%Y%m%dT%H%M%SZ'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(what, got, when), encoding='utf-8')
    return path


def render(what, got, when=None):
    """The note. Written for somebody who was not there and cannot ask."""
    when = when or datetime.now(timezone.utc)
    lines = ['# Friction: %s' % (what.strip().split('\n')[0][:70] or 'unnamed'),
             '',
             '**When:** %s  ' % when.isoformat(timespec='seconds'),
             '**Paperforge:** %s  ' % got['version'],
             '**Scaffold:** %s — %s  ' % (got['scaffold']['state'], got['scaffold']['why']),
             '**Missing:** %s  ' % (', '.join(got['missing']) or 'nothing'),
             ]
    if got.get('last_run'):
        lines.append('**Last run:** %s — %s  '
                     % (got['last_run']['id'], got['last_run']['stages']))
    lines += ['', '## What happened', '', what.strip(), '',
              '## What was done instead', '',
              '_If the pipeline was worked around, say how. The workaround is the '
              'part worth knowing: it is what a later reader would otherwise find '
              'and mistake for a choice._', '']
    return '\n'.join(lines)


def latest(root):
    """The most recent note, or None."""
    found = sorted((Path(root) / NOTES).glob('*.md')) if (Path(root) / NOTES).is_dir() else []
    return found[-1] if found else None


def issue_body(what, got):
    """The same note as something to paste into a tracker.

    Printed, never filed. An agent's diagnosis of a symptom is usually right
    and its diagnosis of a cause often is not; a person decides whether this is
    one issue, three, or a misreading.
    """
    return '\n'.join([
        what.strip(), '',
        '## Environment', '',
        '- Paperforge %s' % got['version'],
        '- scaffold: %s' % got['scaffold']['state'],
        '- missing: %s' % (', '.join(got['missing']) or 'nothing'),
        '- last run: %s' % (got['last_run']['id'] if got.get('last_run') else 'none'),
        '',
        '_Reported from a project by `paperforge report --issue`. The symptom is '
        'observed; the cause is not diagnosed here._',
    ])
