#!/usr/bin/env python3
"""Combine the suite's coverage and hold it to a floor.

Two numbers, not one. A single combined figure lets branch coverage rot while
line coverage carries the average - and the defects in this pipeline have been
branch-shaped: a threshold no short heading could clear, a tag that matched
nothing, an emitter that handled the explicit case and not the inferred one.

The floors sit just under what the suite actually achieves, so they ratchet
against regression rather than describing an ambition. Raise them when the
suite improves; lowering one is a decision that should be visible in a diff.

They are deliberately not the same number. Branch coverage is harder to earn
honestly: past a point the remaining exits are error paths that need a
contrived input to reach, and a floor that forces those into existence buys
tests written to move a number rather than to catch anything. Signals sets
branches at 48 against lines at 80 for the same reason.
"""
import subprocess
import sys
from pathlib import Path

FLOORS = {'line': 88.0, 'branch': 78.0}
ROOT = Path(__file__).resolve().parents[1]


def main():
    # combine sweeps every .coverage.* file, so anything else named that way -
    # including this script's own JSON output, once - is fed to it as a database
    (ROOT / 'coverage-report.json').unlink(missing_ok=True)
    combine = subprocess.run([sys.executable, '-m', 'coverage', 'combine'],
                             cwd=ROOT, capture_output=True, text=True)
    combined = (ROOT / '.coverage').exists()
    # combine deletes the parallel files it consumes, so a second run finds
    # nothing to combine and exits non-zero with the message on stdout. That is
    # only a failure if there is no combined data either - which CI would never
    # have shown, because there it runs exactly once.
    output = (combine.stderr + combine.stdout).strip()
    if combine.returncode != 0 and not combined:
        print(output or 'coverage combine failed')
        return 1
    if not combined:
        print('no coverage data; run the suite under `coverage run` first')
        return 1

    subprocess.run([sys.executable, '-m', 'coverage', 'json', '-o', 'coverage-report.json', '-q'],
                   cwd=ROOT, check=True)
    import json
    data = json.loads((ROOT / 'coverage-report.json').read_text(encoding='utf-8'))
    totals = data['totals']
    actual = {
        'line': 100.0 * totals['covered_lines'] / totals['num_statements'],
        'branch': 100.0 * totals['covered_branches'] / totals['num_branches'],
    }

    print('%-22s %7s %8s' % ('module', 'line', 'branch'))
    rows = []
    for name, entry in data['files'].items():
        s = entry['summary']
        if not s['num_statements']:
            continue
        rows.append((100.0 * s['covered_lines'] / s['num_statements'],
                     name.replace('paperforge/', ''),
                     100.0 * s['covered_branches'] / s['num_branches']
                     if s['num_branches'] else None))
    for line, name, branch in sorted(rows):
        print('%-22s %6.0f%% %8s' % (name, line, '%.0f%%' % branch if branch is not None else 'n/a'))

    print()
    failed = []
    for metric, floor in FLOORS.items():
        got = actual[metric]
        ok = got >= floor
        print('%-7s %5.1f%%   floor %4.1f%%   %s'
              % (metric, got, floor, 'ok' if ok else 'BELOW FLOOR'))
        if not ok:
            failed.append('%s %.1f%% < %.1f%%' % (metric, got, floor))

    if failed:
        print('\ncoverage gate: %s' % '; '.join(failed))
        return 1
    print('\ncoverage gate: passed (%d statements, %d branch exits)'
          % (totals['num_statements'], totals['num_branches']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
