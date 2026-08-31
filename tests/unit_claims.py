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
from paperforge import claims, xref

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
        # not a warning: nobody has vouched for this gist against this paragraph,
        # so there is no verdict to give - only a person who can reread it
        check('a gist never accepted is manual, not a warning',
              ('claim-c', 'unaccepted') in rules(found)
              and [f['severity'] for f in found if f['id'] == 'claim-c'] == ['manual'])
        check('and it names the act that settles it',
              [f['fix'] for f in found if f['rule'] == 'unaccepted']
              == ['paperforge claims --accept'])
        # the form, not the instance: any manual finding is useless without one
        check('every manual finding names an act',
              all(f.get('fix') for f in found if f['severity'] == 'manual'))
        check('nothing here blocks', not any(f['severity'] == 'block' for f in found))
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
        check('and the worst thing found is reported first',
              found[0]['severity'] == 'block')

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

    print('what a claim draws on')
    # resolved defensively so a regression reads as failing checks rather than
    # a traceback that stops the rest of the suite
    edges = getattr(claims, 'edges', lambda r: [])
    rec = claims.find(['Consistent, as @fig-s shows [@w2019].',
                       '{#claim-mle gist="c" uses=claim-lik, claim-reg}'])['claim-mle']
    check('a declared edge list is read, spaces and all',
          rec.get('uses') == ['claim-lik', 'claim-reg'])
    # the references and citations are *in* the paragraph; reading them is
    # measurement, not inference, so they need no syntax of their own
    check('references and citations in the paragraph are edges too',
          edges(rec) == ['@w2019', 'claim-lik', 'claim-reg', 'fig-s'])
    check('a claim with no uses has only what its prose says',
          edges(claims.find(['Says @fig-a. {#claim-p}'])['claim-p']) == ['fig-a'])

    # the quiet failures here all look like success
    check('uses=a b reads one edge and leaves the other over',
          claims.find(['T. {#claim-b uses=a b}'])['claim-b'].get('leftover') == 'b')
    check('a misspelled key is left over rather than ignored',
          claims.find(['T. {#claim-c use=a}'])['claim-c'].get('leftover') == 'use=a')
    check('a well-formed attribute leaves nothing over',
          claims.find(['T. {#claim-d gist="g" uses=claim-a}'])['claim-d'].get('leftover') == '')

    print('edges that point nowhere, and arguments that rest on themselves')
    from paperforge import lint, profile
    checker = getattr(lint, 'check_uses', lambda *a, **k: [])
    with tempfile.TemporaryDirectory() as tmp:
        u = Path(tmp) / 'r.md'
        u.write_text('```mermaid\ngraph LR\nA-->B\n```\n\n: Chart {#fig-s}\n\n'
                     '## Methods {#sec-m}\n\nBase. {#claim-a}\n\n'
                     'On a figure and a section. {#claim-b uses=fig-s,sec-m,claim-a}\n\n'
                     'Nowhere. {#claim-c uses=claim-zz}\n\n'
                     'Loop one. {#claim-x uses=claim-y}\n\n'
                     'Loop two. {#claim-y uses=claim-x}\n\n'
                     'Self. {#claim-s uses=claim-s}\n', encoding='utf-8')
        found = checker({'source_path': u, 'annex_path': None}, profile.load('en'))
        by = {(f['match'], f['rule']) for f in found}
        check('an edge naming no label blocks', ('claim-zz', 'dangling-uses') in by)
        check('a two-claim cycle blocks',
              ('claim-x', 'circular-uses') in by and ('claim-y', 'circular-uses') in by)
        check('a claim that uses itself blocks', ('claim-s', 'circular-uses') in by)
        # a claim may rest on a figure or a section, not only on another claim
        check('edges to a figure and a section are not dangling',
              not any(m in ('fig-s', 'sec-m') for m, _ in by))
        check('a valid chain is not reported',
              not any(m in ('claim-a', 'claim-b') for m, _ in by))
        check('every one of these blocks rather than warns',
              all(f['severity'] == 'block' for f in found))

        # a long chain is not a cycle, and must not exhaust the stack
        deep = Path(tmp) / 'deep.md'
        deep.write_text('Base. {#claim-n0}\n\n' + ''.join(
            'Step %d. {#claim-n%d uses=claim-n%d}\n\n' % (i, i, i - 1)
            for i in range(1, 400)), encoding='utf-8')
        check('a 400-deep chain of claims is not a cycle',
              checker({'source_path': deep, 'annex_path': None}, profile.load('en')) == [])

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

    print('accepting one claim, and being shown it')
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _d:
        root = Path(_d)
        src = root / 'doc.md'
        src.write_text(
            'Yields fell 18%. {#claim-a gist="Salinity costs yield."}\n\n'
            'Timing beats breeding. {#claim-b gist="Timing beats breeding."}\n',
            encoding='utf-8')
        claims.accept([str(src)], root)
        # BOTH paragraphs move. With only one of them accepted, the other must
        # still be stale afterwards - which is the whole point, and what a
        # check on `changed` alone does not test: an untouched claim is absent
        # from `changed` whether it was filtered out or simply had not moved
        src.write_text(
            'Yields fell 31%. {#claim-a gist="Salinity costs yield."}\n\n'
            'Timing loses to breeding. {#claim-b gist="Timing beats breeding."}\n',
            encoding='utf-8')
        one = claims.accept([str(src)], root, 'claim-a')
        check('accepting one re-stamps only that one', one['changed'] == ['claim-a'])
        stale = {f['id'] for f in claims.check([str(src)], root)
                 if f['severity'] == 'block'}
        check('and the paragraph nobody accepted is still stale',
              stale == {'claim-b'})
        check('the others keep their record', 'claim-b' in one['accepted'])
        check('the paragraph comes back with the gist, not a tally',
              bool(one['restamped']) and '31%' in one['restamped'][0]['text']
              and one['restamped'][0]['gist'] == 'Salinity costs yield.')

        # re-stamping every claim because one id was mistyped is exactly what
        # naming a claim is meant to remove
        try:
            claims.accept([str(src)], root, 'claim-typo')
            check('a claim that does not exist is refused', False)
        except KeyError:
            check('a claim that does not exist is refused', True)

        src.write_text('Only one now. {#claim-a gist="Salinity costs yield."}\n',
                       encoding='utf-8')
        kept = claims.accept([str(src)], root, 'claim-a')
        check('accepting one says nothing about a claim that is gone',
              'claim-b' in kept['accepted'])
        swept = claims.accept([str(src)], root)
        check('a full pass is what drops it', 'claim-b' in swept['dropped'])

    print('a label is not the reader\'s business, wherever it sits')
    para = ('First sentence. {#claim-a gist="a summary"}\n'
            'Second sentence, same paragraph because no blank line.')
    check('a label that ends a line but not a paragraph is stripped',
          '#claim-a' not in xref.strip_claims(para))
    check('and the sentences stay separate',
          xref.strip_claims(para).split('\n') ==
          ['First sentence.', 'Second sentence, same paragraph because no blank line.'])
    # Typst and Word join a paragraph's lines with a space, markdown with a
    # newline, so a rule keyed to the end of a line fixed one edition of three
    joined = 'First sentence. {#claim-a gist="a summary"} Second sentence.'
    check('and the same label in a space-joined paragraph',
          xref.strip_claims(joined) == 'First sentence. Second sentence.')
    check('a paragraph entitled to end in braces keeps them',
          xref.strip_claims('the set {a, b}') == 'the set {a, b}')
    check('and an attribute that is not a claim is left alone',
          xref.strip_claims('A heading {.part}') == 'A heading {.part}')
    # a report that explains the syntax had its own example deleted before the
    # emitter could set it as code; `verify.leaks` already excludes code from
    # the artifact scan, so backticks are how one is written deliberately
    shown = 'Write `{#claim-x gist="y"}` to label a paragraph.'
    check('syntax shown in a code span is not a label being used',
          xref.strip_claims(shown) == shown)
    check('punctuation belonging to the sentence keeps its place',
          xref.strip_claims('First {#claim-a gist="x"}, next') == 'First, next')

    print('every edition strips it, and the artifact is checked for one')
    from paperforge import verify
    found = verify.leaks('concessions. {#claim-exec gist="a summary"} Thanh Hoa mirrors')
    check('a label that survived into a built document is a leak',
          [f['kind'] for f in found] == ['label'])
    check('and ordinary prose with braces is not',
          verify.leaks('an ordinary sentence about {a, b} sets') == [])
    # an id may sit behind other attributes, as every attribute parser here
    # allows, so a pattern that demanded `{#` would have missed `{.part #sec-x}`
    check('an id behind another attribute is still a leak',
          [f['kind'] for f in verify.leaks('a heading {.part #sec-x} leaked')] == ['label'])

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nclaims: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
