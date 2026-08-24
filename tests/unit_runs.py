#!/usr/bin/env python3
"""The run record: what a run produced, kept where the next run cannot erase it.

This exists because a corpus was drafted twice, the second pass overwrote the
first in place, and the drafts of the first are simply gone. The repository had
git the whole time. So the checks here are about the record being written
without anyone remembering to ask for it, holding the sources rather than only
their fingerprints, and surviving a run that failed.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import runs

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def project(root, body, annex=None):
    """A throwaway cfg/docs pair shaped like the pipeline's."""
    (root / 'documents.toml').write_text('[defaults]\n', encoding='utf-8')
    src = root / 'report.md'
    src.write_text(body, encoding='utf-8')
    out = root / 'report.html'
    out.write_text('<html>%s</html>' % body, encoding='utf-8')
    doc = {'collection': 'c', 'language': 'en', 'source': 'report.md', 'source_path': src,
           'output': 'report.html', 'output_path': out, 'annex_path': None, 'publish': True}
    if annex is not None:
        ann = root / 'annex.md'
        ann.write_text(annex, encoding='utf-8')
        doc['annex'], doc['annex_path'] = 'annex.md', ann
    return {'_root': root, '_manifest': root / 'documents.toml'}, [doc]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg, docs = project(root, 'First draft.\n', annex='Annex one.\n')

        print('writing a record')
        out = runs.write(cfg, docs, {'lint': 'ok', 'verify': 'failed'}, label='Run 1 antigravity')
        rec = json.loads((out / 'record.json').read_text(encoding='utf-8'))
        check('the directory is named for the run', 'run-1-antigravity' in out.name)
        check('the label is kept verbatim too', rec['label'] == 'Run 1 antigravity')
        check('a failed stage is recorded, not suppressed', rec['stages']['verify'] == 'failed')
        check('the manifest is fingerprinted', len(rec['manifest_sha256']) == 64)
        check('the source is fingerprinted', len(rec['documents'][0]['source_sha256']) == 64)
        check('the annex is fingerprinted too', 'annex_sha256' in rec['documents'][0])
        check('the source itself is kept, not only its hash',
              (out / 'sources' / 'report.md').read_text(encoding='utf-8') == 'First draft.\n')
        check('the annex is kept as well', (out / 'sources' / 'annex.md').exists())
        check('a PDF that does not exist is not claimed',
              'pdf_sha256_observed' not in rec['documents'][0])

        print('a second run overwrites the working copy, not the record')
        (root / 'report.md').write_text('Second draft, much better.\n', encoding='utf-8')
        (root / 'report.html').write_text('<html>Second draft, much better.</html>',
                                          encoding='utf-8')
        two = runs.write(cfg, docs, {'lint': 'ok', 'verify': 'ok'}, label='Run 2 opus')
        check('the first draft is still readable after being overwritten',
              (out / 'sources' / 'report.md').read_text(encoding='utf-8') == 'First draft.\n')
        check('the second is recorded separately',
              (two / 'sources' / 'report.md').read_text(encoding='utf-8').startswith('Second'))

        print('finding runs again')
        found = runs.listing(root)
        check('both runs are listed, oldest first',
              len(found) == 2 and found[0][1]['label'] == 'Run 1 antigravity')
        check('a run can be found by its label slug',
              runs.load(root, 'run-2-opus')[1]['label'] == 'Run 2 opus')
        check('a run can be found by a prefix of its directory',
              runs.load(root, found[0][0][:24])[0] == found[0][0])
        try:
            runs.load(root, found[0][0][:12])       # shared timestamp prefix
            check('an ambiguous prefix is an error, not an arbitrary pick', False)
        except SystemExit:
            check('an ambiguous prefix is an error, not an arbitrary pick', True)
        try:
            runs.load(root, 'no-such-run')
            check('an unknown run is an error, not an empty result', False)
        except SystemExit:
            check('an unknown run is an error, not an empty result', True)

        print('two runs in the same second')
        one = runs.write(cfg, docs, {'build': 'ok'})
        two_same = runs.write(cfg, docs, {'build': 'ok'})
        check('the second does not overwrite the first', one != two_same)
        check('both records survive',
              (one / 'record.json').exists() and (two_same / 'record.json').exists())

        print('comparing two runs')
        d = runs.diff(found[0][1], found[1][1])
        check('a rewritten document is reported as rewritten', d['rewritten'] == ['report.md'])
        check('the verdict change is reported',
              d['stages'].get('verify') == ('failed', 'ok'))
        same = runs.diff(found[1][1], found[1][1])
        check('a run compared with itself reports no change',
              same['unchanged'] == ['report.md'] and not same['rewritten'])

        print('the same source, a different tool')
        # the case the record has to be able to tell apart: nothing was rewritten,
        # the pipeline changed underneath it
        a = dict(found[1][1])
        b = json.loads(json.dumps(a))
        b['stages'] = {'lint': 'ok', 'verify': 'failed'}
        d = runs.diff(a, b)
        check('an unchanged source with a changed verdict is not called a rewrite',
              d['unchanged'] == ['report.md'] and d['rewritten'] == [])
        check('and the verdict change is what is reported',
              d['stages'].get('verify') == ('ok', 'failed'))

        b = json.loads(json.dumps(a))
        b['documents'][0]['pdf_sha256_observed'] = 'f' * 64
        a2 = json.loads(json.dumps(a))
        a2['documents'][0]['pdf_sha256_observed'] = '0' * 64
        d = runs.diff(a2, b)
        check('a print edition that merely repaginated is held apart from a rewrite',
              d['pdf_only'] == ['report.md'] and d['rewritten'] == [])

        print('the request travels with the run')
        req = root / 'request.md'
        req.write_text('Answer this, roughly.\n', encoding='utf-8')
        docs[0]['request_path'] = req
        three = runs.write(cfg, docs, {'build': 'ok'}, label='with request')
        rec3 = json.loads((three / 'record.json').read_text(encoding='utf-8'))
        check('the request is fingerprinted',
              len(rec3['documents'][0].get('request_sha256', '')) == 64)
        check('and kept, so what was asked survives with what was produced',
              (three / 'sources' / 'request.md').read_text(encoding='utf-8')
              == 'Answer this, roughly.\n')
        docs[0]['request_path'] = None
        four = runs.write(cfg, docs, {'build': 'ok'}, label='no request')
        rec4 = json.loads((four / 'record.json').read_text(encoding='utf-8'))
        check('a project that declares none is recorded without one',
              'request' not in rec4['documents'][0])

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nruns: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
