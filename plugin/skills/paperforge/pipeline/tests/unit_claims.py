#!/usr/bin/env python3
"""Gists, and the gate that stops one going stale.

The point of this module is a refusal that fires on a document nobody
noticed changing, so most of what is worth testing is the difference between
an edit that should mark a gist stale and one that should not. Rewording the
summary is not drift. Rewrapping the paragraph is not drift. Changing what the
paragraph says is.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import claims

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def rules(found):
    return {(f['id'], f['rule']) for f in found}


def main():
    print('reading a claim out of its paragraph')
    lines = ['## Heading {#sec-h}', '',
             'The estimator is consistent', 'under A1-A3. {#claim-c gist="consistent"}', '',
             '- a list item', 'Bare. {#claim-b}', '',
             '> a quote', 'After a quote. {#claim-q}']
    found = claims.find(lines)
    check('the gist is read off the attribute',
          found['claim-c']['gist'] == 'consistent')
    check('the paragraph is joined across its lines, without the label',
          found['claim-c']['text'] == 'The estimator is consistent under A1-A3.')
    check('a claim with no gist is found, and says so',
          found['claim-b']['gist'] is None)
    # the hash covers what the reader sees as one block, so it has to stop
    # where the emitters' paragraph loops stop
    check('a list item above is a boundary, not part of the paragraph',
          found['claim-b']['text'] == 'Bare.')
    check('so is a blockquote', found['claim-q']['text'] == 'After a quote.')
    check('a heading is never read as a claim',
          all(not k.startswith('sec-') for k in found))

    print('what counts as a change')
    base = claims.fingerprint('The estimator is consistent under A1-A3.')
    check('whitespace is not a change',
          claims.fingerprint('The  estimator is\nconsistent under A1-A3.') == base)
    check('rewriting the paragraph is',
          claims.fingerprint('The estimator is consistent under A1-A4.') != base)
    # the hash is taken with the label stripped, so improving the wording of a
    # gist cannot mark the gist it describes stale
    one = claims.find(['Text here. {#claim-x gist="first wording"}'])['claim-x']
    two = claims.find(['Text here. {#claim-x gist="a better wording"}'])['claim-x']
    check('rewording the gist alone is not a change to the paragraph',
          claims.fingerprint(one['text']) == claims.fingerprint(two['text']))

    print('the gate')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src = root / 'r.md'
        src.write_text('The estimator is consistent under A1-A3. '
                       '{#claim-c gist="consistent"}\n\n'
                       'Nothing said about this one. {#claim-b}\n', encoding='utf-8')

        found = claims.check([src], root)
        check('a gist never accepted is reported, and does not block',
              ('claim-c', 'unaccepted') in rules(found)
              and all(f['severity'] == 'warn' for f in found))
        check('a claim with no gist is a hole, reported as one',
              ('claim-b', 'no-gist') in rules(found))

        claims.accept([src], root)
        check('accepting writes the lock', (root / claims.LOCK).exists())
        check('and the accepted claim is then current',
              not any(f['id'] == 'claim-c' for f in claims.check([src], root)))
        # accepting is not a way to make a hole go away
        check('while the claim with no gist is still reported',
              ('claim-b', 'no-gist') in rules(claims.check([src], root)))
        check('a claim with no gist is not stamped',
              'claim-b' not in claims.load(root))

        # the whole point: the paragraph moves and the gist does not
        src.write_text(src.read_text(encoding='utf-8')
                       .replace('under A1-A3.', 'only under A1 and A2.'), encoding='utf-8')
        found = claims.check([src], root)
        check('moving the paragraph under an accepted gist blocks',
              ('claim-c', 'stale-gist') in rules(found)
              and any(f['severity'] == 'block' for f in found))

        # rewrapping is the edit an author makes without meaning anything by it
        src.write_text('The estimator is consistent\nonly under A1 and A2. '
                       '{#claim-c gist="consistent"}\n', encoding='utf-8')
        claims.accept([src], root)
        src.write_text('The estimator is\nconsistent only under   A1 and A2. '
                       '{#claim-c gist="consistent"}\n', encoding='utf-8')
        check('rewrapping the same words does not block',
              claims.check([src], root) == [])

        src.write_text('Different claim entirely. {#claim-z gist="z"}\n', encoding='utf-8')
        check('a lock entry for a claim that no longer exists is reported',
              ('claim-c', 'orphan-gist') in rules(claims.check([src], root)))
        claims.accept([src], root)
        check('and accepting drops it', 'claim-c' not in claims.load(root))

        (root / claims.LOCK).write_text('{ not json', encoding='utf-8')
        check('a lock nobody can read vouches for nothing, rather than crashing',
              claims.load(root) == {})

    print('labels that would reach a reader')
    from paperforge import lint
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'r.md'
        src.write_text('Fine. {#claim-a gist="fine"}\n\n'
                       'Braced. {#claim-y gist="the set {a,b}"}\n\n'
                       'Quoted. {#claim-q gist="says \\"maybe\\""}\n', encoding='utf-8')
        found = lint.check_claims({'source_path': src})
        by = {f['rule'] for f in found}
        # a brace defeats the attribute pattern entirely, so nothing strips the
        # label and it prints - the defect take_equation records for {#eq-x}
        check('a brace inside a gist is blocked, not silently unlabelled',
              'malformed-claim' in by)
        check('a quote inside a gist is blocked, not silently truncated',
              'truncated-gist' in by)
        check('a well-formed claim is not reported', len(found) == 2)
        check('and both block rather than warn',
              all(f['severity'] == 'block' for f in found))

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nclaims: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
