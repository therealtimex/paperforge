#!/usr/bin/env python3
"""One document from several files.

A report is one file; a thesis is chapters. The pieces are concatenated before
anything parses them, because cross-references, figure numbers and the contents
have to see the whole work - and they can only do that if there is only ever one
text.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import assemble

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'main.md').write_text('# T\n## Title\n', encoding='utf-8')
        (root / 'a.md').write_text('## Chapter A\n', encoding='utf-8')
        (root / 'b.md').write_text('## Chapter B\n', encoding='utf-8')

        print('assembling')
        text = assemble.read(root / 'main.md', [root / 'a.md', root / 'b.md'])
        check('the source comes first', text.startswith('# T'))
        check('includes follow in declared order',
              text.index('Chapter A') < text.index('Chapter B'))
        check('a blank line separates them, so blocks do not merge',
              '\n\n## Chapter A' in text)
        check('no includes is just the source',
              assemble.read(root / 'main.md') == (root / 'main.md').read_text(encoding='utf-8'))

        print('what makes up a document')
        doc = {'source_path': root / 'main.md',
               'include_paths': [root / 'a.md', root / 'b.md'],
               'annex_path': root / 'x.md'}
        names = [p.name for p in assemble.sources(doc)]
        check('every file is listed, in order, annex last',
              names == ['main.md', 'a.md', 'b.md', 'x.md'])
        check('a document with neither is just its source',
              [p.name for p in assemble.sources({'source_path': root / 'main.md'})]
              == ['main.md'])

        print('refusing what cannot work')
        check('a correct set has no problems',
              assemble.problems(root / 'main.md', [root / 'a.md']) == [])
        check('an include that is not there is reported',
              any('not found' in p for p in
                  assemble.problems(root / 'main.md', [root / 'gone.md'])))
        (root / 'own.md').write_text('+++\nabstract = "x"\n+++\n\n## C\n', encoding='utf-8')
        check('an include carrying its own front matter is reported, because a '
              'fragment is not a document',
              any('front matter' in p for p in
                  assemble.problems(root / 'main.md', [root / 'own.md'])))
        check('the source listed as its own include is reported',
              any('assembled twice' in p for p in
                  assemble.problems(root / 'main.md', [root / 'main.md'])))

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nassemble: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
