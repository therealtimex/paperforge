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
SPEC = Path(__file__).resolve().parents[1] / 'specs' / 'calibration.md'

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
    check('and no script is in SCRIPT_FLOOR without a row here',
          {'latin', 'cjk'} == set(verify.SCRIPT_FLOOR)
          and all(("verify.SCRIPT_FLOOR", s) in {(d, k) for d, k, _ in rows}
                  for s in verify.SCRIPT_FLOOR))

    print()
    if failures:
        print('%d check(s) failed' % len(failures))
        return 1
    print('calibration: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
