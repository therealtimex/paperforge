#!/usr/bin/env python3
"""The note somebody leaves when the pipeline made them do something else.

Four workarounds in one project were found by a person scanning it weeks later:
a document restructured to dodge a defect, a script to generate markup, forty
lines of interpreter archaeology, and a reviewer's own checking code. Each was
reasonable under deadline; each removed the only trace that anything was wrong.

So the rule is solve *and* report, and the note has to carry what an author
cannot be expected to assemble - a version, a scaffold stamp, what is missing,
which run was last. "Paperforge didn't work" is not diagnosable. Those four
things with a sentence are.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paperforge
from paperforge import friction

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    print('what a note carries besides the words')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        got = friction.facts(root)
        check('the version that wrote it', got['version'] == paperforge.__version__)
        check('whether the project guidance is current',
              got['scaffold']['state'] in ('current', 'stale', 'unstamped'))
        check('what is absent, rather than a machine nobody can ask about',
              isinstance(got['missing'], list))
        check('and no run to point at, said plainly', got['last_run'] is None)

        note = friction.render('the lede never reached the PDF', got)
        for wanted in ('Paperforge:', 'Scaffold:', 'Missing:', 'What happened'):
            check('the note states %r' % wanted, wanted in note)
        # the workaround is the part a later reader would otherwise find and
        # mistake for a choice, so the note asks for it explicitly
        check('and asks what was done instead', 'What was done instead' in note)

    print('writing one, and reading it back')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        check('no note is not an error', friction.latest(root) is None)
        path = friction.write(root, 'the claim markup was easier to generate')
        check('the note lands under .paperforge, with the runs',
              path.parent == root / '.paperforge' / 'friction')
        check('and is the latest', friction.latest(root) == path)
        second = friction.write(root, 'and again')
        check('a second note does not replace the first',
              friction.latest(root) == second and path.is_file())

    print('the issue body is printed, never filed')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        got = friction.facts(root)
        body = friction.issue_body('the lede never reached the PDF', got)
        check('it carries the environment a reader would ask for',
              'Paperforge %s' % paperforge.__version__ in body)
        # three times in one week an agent read a symptom correctly and a cause
        # wrongly; a tracker of plausible misattributions is one nobody reads
        check('and says the cause is not diagnosed here',
              'cause is not diagnosed' in body)

    print('the rule reaches a project')
    from paperforge import scaffold
    check('the scaffolded guidance says to report a workaround',
          'work around the pipeline' in scaffold.AGENTS)
    check('and that solving it is still the right thing to do',
          'Solve it' in scaffold.AGENTS)

    print()
    if failures:
        print('%d check(s) failed' % len(failures))
        return 1
    print('friction: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
