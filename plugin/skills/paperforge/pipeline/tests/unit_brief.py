#!/usr/bin/env python3
"""The authoring brief: it must state what the project declares, and nothing it
would have to invent.

Written after a handoff where half the brief was the project's own AGENTS.md
paraphrased by hand. That copy asserted lint rules from a pack the project had
not enabled - true of the corpus it was remembered from, false of the project it
was written for. A generated brief cannot make that mistake, which is the whole
argument for generating it.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import brief, cli

failures = []

MANIFEST = """[defaults]
profile = "en"

[[collection]]
slug = "sample"
root = "."
figures = "figures.toml"

  [[collection.document]]
  id = "report"
  type = "report"
  pdf = "chrome"
  source = "report.md"
  publish = true

  [[collection.document]]
  source = "note.md"
  publish = false

[lint]
%s

[internal]
files = ["REVIEW.md"]
reason = "process record"
"""

FIGURES = """[[figure]]
id      = "target"
label   = "Headline target"
context = "target"
pattern = '\\\\d+%'
accept  = ["10%"]
"""


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def build(tmp, lint_section, request=None):
    root = Path(tmp)
    text = MANIFEST % lint_section
    if request:
        text = text.replace('profile = "en"', 'profile = "en"\nrequest = "%s"' % request)
    (root / 'documents.toml').write_text(text, encoding='utf-8')
    (root / 'figures.toml').write_text(FIGURES, encoding='utf-8')
    for name in ('report.md', 'note.md', 'REVIEW.md'):
        (root / name).write_text('# T\n## Title\n\n---\n\nBody.\n', encoding='utf-8')
    cfg, docs = cli.load(str(root / 'documents.toml'))
    return brief.render(cfg, docs, '/usr/local/bin/paperforge')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        text = build(tmp, '')

        print('what the project declares')
        check('the invocation is the real one, not a placeholder',
              '/usr/local/bin/paperforge status' in text and '<paperforge>' not in text)
        check('every declared source is listed', '`report.md`' in text and '`note.md`' in text)
        check('the print edition is named', 'pdf:chrome' in text)
        check('publishable and not publishable are distinguished',
              'publishable |' in text and 'not publishable |' in text)
        check('the internal file is named as never publishable',
              '`REVIEW.md`' in text)
        check('declared figures are listed', '`target`' in text and '`10%`' in text)

        print('the request')
        check('a project that declares none does not invent one',
              '## What was asked' not in text)

        print('what the gates refuse')
        check('unsupported constructs are called out', 'footnotes `[^1]`' in text)
        check('a construct that became supported is no longer listed',
              'caption lines' not in text)
        check('core rules are listed', '`todo`' in text and '`lorem`' in text)
        check('a warn-level rule is not presented as blocking',
              'Reported but not blocking' in text and '`length-spec`' in text)
        check('no pack rule is claimed when none is enabled',
              'loop-id' not in text and 'agent-state' not in text)

        print('with a request declared')
        root = Path(tmp)
        (root / 'ask.md').write_text('Roughly this.\n', encoding='utf-8')
        asked = build(tmp, '', request='ask.md')
        check('the request is cited', '## What was asked' in asked and '`ask.md`' in asked)
        check('and the reading of it is named as the specification',
              'the reading of it *is* the specification' in asked)

        print('with a pack enabled')
        packed = build(tmp, 'packs = ["realtimex-loops"]')
        check('the pack\'s rules now appear', 'loop-id' in packed and 'agent-state' in packed)
        check('and are marked as coming from a pack', '*(pack)*' in packed)

        print('what it refuses to invent')
        low = text.lower()
        check('it says the method is not its to state',
              'not derivable from a manifest' in text)
        check('it does not invent a research method',
              'sources before prose' not in low and 'first draft' not in low)

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nbrief: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
