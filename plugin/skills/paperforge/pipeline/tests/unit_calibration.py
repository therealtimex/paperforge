#!/usr/bin/env python3
"""Every measured number, held to the file that records what was measured.

`specs/calibration.md` exists because these numbers cannot be re-derived by
reading the code: the corpus they were fitted to is not in this repository.
That makes the file the only record, and a record nothing checks is the failure
this codebase keeps finding - a second copy that fell out of step with the
first, silently, because nothing ran it.

So the table is parsed and each value compared with the constant it names. A
number changed in one place and not the other is a failing check rather than a
document that quietly stops being true.

The prose in that file is not gated and could drift from the docstring holding
the full reasoning. The number cannot, and the number is what decides what the
pipeline refuses.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import markdown, pages, typst, verify

failures = []


def spec_file():
    """The calibration table, or None if this copy is the shipped bundle.

    The bundle ships `bin/`, `paperforge/` and `tests/` and nothing else, so
    the copy inside it has no table to check - and this file resolved to
    `pipeline/specs/calibration.md`, which raised FileNotFoundError before a
    single check ran.

    `docs/reference/` is the marker, and no ancestor is walked. Walking looked
    for AGENTS.md, which every scaffolded project has: a bundle installed under
    one would have been read as a source tree with its specs deleted, and the
    skip would have been a failure instead.

    Inside the source tree a missing table is a failure - somebody deleted the
    only record of what was measured. Outside it there is nothing to check.
    """
    root = Path(__file__).resolve().parents[1]
    if not (root / 'docs' / 'reference').is_dir():
        return None
    found = root / 'specs' / 'calibration.md'
    return found if found.is_file() else False

# `module.NAME` or `module.NAME['key']`, then a backticked value
ROW_RE = re.compile(r'^\|\s*`([\w.]+)(?:\[\'([^\']+)\'\])?`\s*\|\s*`([^`]+)`\s*\|')

MODULES = {'verify': verify, 'pages': pages, 'markdown': markdown, 'typst': typst}


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def declared():
    """(dotted name, key or None, value as written) for every row in the table."""
    rows = []
    for line in SPEC.read_text(encoding='utf-8').split('\n'):
        m = ROW_RE.match(line.strip())
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def live(dotted, key):
    module, name = dotted.split('.', 1)
    value = getattr(MODULES[module], name)
    return value[key] if key is not None else value


def main():
    global SPEC
    SPEC = spec_file()
    if SPEC is None:
        print('  %-58s skip (no source tree here; specs/ is not shipped)'
              % 'the calibration table')
        return 0
    if SPEC is False:
        print('  %-58s FAIL (specs/calibration.md is gone)'
              % 'the calibration table')
        return 1

    print('the table is read, not assumed')
    rows = declared()
    # a parser that silently matches nothing would pass every check below
    check('the calibration table has rows', len(rows) >= 8)
    check('and every module named in it is one this pipeline has',
          all(d.split('.', 1)[0] in MODULES for d, _, _ in rows))

    print('every measured number matches the constant it names')
    for dotted, key, written in rows:
        label = '%s%s is %s' % (dotted, "['%s']" % key if key else '', written)
        try:
            value = live(dotted, key)
        except (AttributeError, KeyError) as e:
            check(label + ' (%s)' % type(e).__name__, False)
            continue
        check(label, str(value) == written)

    print('the constants exist as constants, not as defaults in a signature')
    # a threshold written as a default argument is a threshold per signature:
    # `pages.FLOOR` was 0.45 twice, in two functions, before it had a name
    import inspect
    for fn in (pages.extractable, pages.correspondence):
        sig = inspect.signature(fn)
        check('%s takes its floor from the constant' % fn.__name__,
              sig.parameters['floor'].default is None)
    check('and pagination no longer takes a floor it overwrites',
          'floor' not in inspect.signature(verify.pagination).parameters)

    print('an unmeasured script is skipped, not given another script\'s number')
    out = verify.pagination.__doc__ or ''
    check('the refusal is documented where the floor is used',
          'has been measured' in out or 'measured floor' in out
          or 'borrowing' in out)
    # membership, not equality against a literal set: a third script that has
    # been measured and written up should pass, and only one that has not
    # should fail. Pinning the set here would make the honest case a test edit
    check('and no script is in SCRIPT_FLOOR without a row here',
          all(('verify.SCRIPT_FLOOR', s) in {(d, k) for d, k, _ in rows}
              for s in verify.SCRIPT_FLOOR))

    print('the index lists every record, and every link resolves')
    root = SPEC.parent
    records = sorted(p.name for p in root.glob('[0-9][0-9][0-9][0-9]-*.md'))
    index = (root / 'README.md').read_text(encoding='utf-8')
    # a record nothing links to is a record nobody reads; the index is the only
    # way in, so it is checked rather than trusted
    check('every decision record is in the index',
          all('(%s)' % name in index for name in records))
    linked = set(re.findall(r'\]\(([\w./-]+\.md)\)', index))
    check('and every link in the index resolves',
          all((root / name).is_file() for name in linked))
    check('there is at least one record to check', len(records) >= 4)

    print()
    if failures:
        print('%d check(s) failed' % len(failures))
        return 1
    print('calibration: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
