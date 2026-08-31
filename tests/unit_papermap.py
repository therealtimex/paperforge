#!/usr/bin/env python3
"""The map of a document, and the line between what it reports and what gates.

The map is built entirely from what the source says, so most of what is worth
testing is that an edge appears where an edge was written and nowhere else. The
rest is the deliberate omission: a claim nothing uses is reported here and
refused nowhere, because it is usually the paper's finding.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import lint, papermap, profile

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


SOURCE = '''## Methods {#sec-methods}

```mermaid
graph LR
A-->B
```

: bias vs n for the two estimators {#fig-sim-bias}

The estimator is consistent given @fig-sim-bias [@white2019].
{#claim-mle gist="MLE is consistent under A1-A3"}

## Results {#sec-results}

The finite-sample bias is small. {#claim-finite uses=claim-mle}

| a |
| - |
| 1 |

: A table nobody mentions {#tbl-lonely}
'''


def main():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'r.md'
        src.write_text(SOURCE, encoding='utf-8')
        doc = {'source_path': src, 'annex_path': None}
        m = papermap.build(doc, profile.load('en'))
        claims = {c['id']: c for c in m['claims']}
        floats = {f['id']: f for f in m['floats']}
        notes = {(n['rule'], n['id']) for n in m['notes']}

        print('what the document declares')
        check('sections are listed by id, in order',
              [s['id'] for s in m['sections']] == ['sec-methods', 'sec-results'])
        check('a float carries its caption and its number',
              floats['fig-sim-bias']['caption'] == 'bias vs n for the two estimators'
              and floats['fig-sim-bias']['label'] == 'Figure 1')
        check('a claim carries the gist a person wrote',
              claims['claim-mle']['gist'] == 'MLE is consistent under A1-A3')
        check('and the section it sits in',
              claims['claim-mle']['section'] == 'sec-methods'
              and claims['claim-finite']['section'] == 'sec-results')
        check('citations are collected', m['citations'] == ['white2019'])

        print('what points at what')
        # the reference and the citation are in the paragraph; only the
        # claim-to-claim edge was written down
        check('a claim draws on what its own prose names',
              claims['claim-mle']['uses'] == ['@white2019', 'fig-sim-bias'])
        check('and on what its author declared',
              claims['claim-finite']['uses'] == ['claim-mle'])
        check('used-by is the inverse, not something written',
              claims['claim-mle']['used_by'] == ['claim-finite'])
        check('a float knows which claims rest on it',
              floats['fig-sim-bias']['used_by'] == ['claim-mle'])
        check('a claim nothing draws on has an empty used-by',
              claims['claim-finite']['used_by'] == [])

        print('reported here, refused nowhere')
        check('a claim nothing uses is a note',
              ('nothing-uses-it', 'claim-finite') in notes)
        # it is the paper's finding as often as it is a leftover, so a gate for
        # it would fire on every correct paper
        check('and lint does not refuse it',
              not any('claim-finite' in str(f) for f in
                      lint.check_uses(doc, profile.load('en'))))
        check('a claim with no gist is a note', ('no-gist', 'claim-finite') in notes)
        check('a float nobody mentions is a note',
              ('never-referred-to', 'tbl-lonely') in notes)
        check('one that is mentioned is not',
              ('never-referred-to', 'fig-sim-bias') not in notes)

        print('the two ways out')
        text = papermap.render([m])
        check('the reader form names the claim under its section',
              'sec-methods  Methods' in text and 'claim-mle' in text)
        check('and shows the gist and both directions',
              'gist:    MLE is consistent under A1-A3' in text
              and 'used-by: claim-finite' in text)
        check('an unlabelled heading leaves no trailing gap',
              not any(l.rstrip() != l for l in text.split('\n')))
        loaded = json.loads(papermap.as_json([m]))
        check('the machine form is the same map', loaded == [m])

        print('the map as a published page')
        html = papermap.page(m, profile.load('en'))
        check('it opens offline, like every other artefact here',
              not re.search(r'(?:src|href)="https?://', html))
        check('it is filled from the palette, not from literals',
              '--navy:' in html and '--amber:' in html)
        check('a claim is an anchor, and an edge is a link to it',
              'id="claim-mle"' in html and 'href="#claim-mle"' in html)
        check('the gist a person wrote is on the page',
              'MLE is consistent under A1-A3' in html)
        check('and a claim with none says so rather than showing nothing',
              'nothing said about this one' in html)
        check('a float carries its number and caption',
              'Figure 1' in html and 'bias vs n for the two estimators' in html)
        check('citations and notes are on it',
              'white2019' in html and 'nothing-uses-it' in html)

        # a gist is prose a person wrote, so it can contain anything
        sharp = Path(tmp) / 'sharp.md'
        sharp.write_text('A claim. {#claim-x gist="a < b & <script>alert(1)</script>"}\n',
                         encoding='utf-8')
        page = papermap.page(papermap.build({'source_path': sharp, 'annex_path': None},
                                            profile.load('en')), profile.load('en'))
        check('a gist is escaped, not injected',
              '<script>' not in page and '&lt;script&gt;' in page)

        # most documents have no claims yet, and a map of sections and floats is
        # still a map of the document's machinery
        plain = Path(tmp) / 'plain.md'
        plain.write_text('## Only headings {#sec-only}\n\nSome prose.\n', encoding='utf-8')
        bare = papermap.build({'source_path': plain, 'annex_path': None}, profile.load('en'))
        rendered = papermap.page(bare, profile.load('en'))
        check('a document with no claims still gets its structure',
              bare['claims'] == [] and 'sec-only' in rendered)

        print('what a map cannot be')
        from paperforge import cli
        for label, fn, doc in (
                ('a map has no page to divide into columns', cli.columns_of,
                 {'source': 'r.md', 'format': 'map', 'columns': 2}),
                ('and no leaf to bind', cli.binding_of,
                 {'source': 'r.md', 'format': 'map', 'binding': True})):
            try:
                fn(doc)
                check(label, False)
            except SystemExit as e:
                check(label, 'map' in str(e))

        print('an annex is part of the same work')
        body, annex = Path(tmp) / 'b.md', Path(tmp) / 'a.md'
        body.write_text('## Body {#sec-b}\n\nA claim. {#claim-b}\n', encoding='utf-8')
        annex.write_text('## Annex {#sec-a}\n\nRests on it. {#claim-a uses=claim-b}\n',
                         encoding='utf-8')
        m2 = papermap.build({'source_path': body, 'annex_path': annex},
                            profile.load('en'))
        ids = {c['id'] for c in m2['claims']}
        check('claims in the annex are on the map', ids == {'claim-a', 'claim-b'})
        check('and an edge crosses from the annex into the body',
              [c for c in m2['claims'] if c['id'] == 'claim-b'][0]['used_by'] == ['claim-a'])

    print('a map with nothing on it says so')
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _d:
        bare = Path(_d) / 'bare.md'
        bare.write_text('## A heading\n\nProse with no labels at all.\n\n'
                        '## Another heading\n\nMore prose.\n', encoding='utf-8')
        m = papermap.build({'source_path': str(bare), 'include_paths': (),
                            'annex_path': None})
        # every other note here is per claim or per float, so a document with
        # neither produced none - and a 95-page dossier mapped to 163 lines of
        # headings with nothing said about that
        check('an undeclared document is noted, once',
              [n['rule'] for n in m['notes']] == ['nothing-declared'])

        some = Path(_d) / 'some.md'
        some.write_text('## A heading {#sec-a}\n\nProse pointing at @sec-a.\n',
                        encoding='utf-8')
        m = papermap.build({'source_path': str(some), 'include_paths': (),
                            'annex_path': None})
        check('a document with labels and no claims is partial, not empty',
              'nothing-declared' not in [n['rule'] for n in m['notes']])

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\npapermap: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
