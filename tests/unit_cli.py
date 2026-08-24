#!/usr/bin/env python3
"""Manifest resolution and the errors it is documented to raise.

These are guarantees the reference docs state - "an undeclared type is an error
rather than silence", "the nearest documents.toml above the working directory",
"--only limits to one document or collection" - and no fixture reaches them,
because CI always passes an explicit --config and never mistypes a type name.
A documented promise nothing exercises is exactly what this repo gates against.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import cli

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def raises(label, fn):
    try:
        fn()
    except SystemExit as e:
        print('  %-58s ok (%s)' % (label, str(e)[:28]))
        return
    print('  %-58s FAIL (no error)' % label)
    failures.append(label)


MANIFEST = """[defaults]
profile = "en"

[types.case-study]
extends = "report"
page_numbers = true

[[collection]]
slug = "sample"
root = "."

  [[collection.document]]
  id = "main"
  type = "case-study"
    [collection.document.en]
    source = "report.en.md"
    [collection.document.vi]
    source = "report.vi.md"

  [[collection.document]]
  source = "note.md"

[internal]
files = []
reason = "unit"
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'documents.toml').write_text(MANIFEST, encoding='utf-8')
        for name in ('report.en.md', 'report.vi.md', 'note.md'):
            (root / name).write_text('# T\n## Title\n\n---\n\nBody text here.\n', encoding='utf-8')

        print('finding the manifest')
        # find_config resolves symlinks, and on macOS /var is one, so both
        # sides have to be resolved before they can be compared
        manifest = (root / 'documents.toml').resolve()
        check('an explicit path wins',
              cli.find_config(str(root / 'documents.toml')) == manifest)
        os.environ['PAPERFORGE_CONFIG'] = str(root / 'documents.toml')
        check('$PAPERFORGE_CONFIG is used when no path is given',
              cli.find_config() == manifest)
        del os.environ['PAPERFORGE_CONFIG']

        nested = root / 'a' / 'b'
        nested.mkdir(parents=True)
        cwd = Path.cwd()
        try:
            os.chdir(nested)
            check('the nearest manifest above the working directory is found',
                  cli.find_config().resolve() == manifest)
        finally:
            os.chdir(cwd)

        with tempfile.TemporaryDirectory() as empty:
            try:
                os.chdir(empty)
                raises('no manifest anywhere is an error, not a default',
                       lambda: cli.find_config())
            finally:
                os.chdir(cwd)

        print('document types')
        types = cli.document_types({'types': {'board-pack': {'layout': 'brief'}}})
        check('a project type is added to the built-ins', 'board-pack' in types)
        check('the built-ins survive', types['report']['layout'] == 'report')
        inherited = cli.document_types({'types': {'x': {'extends': 'brief', 'page_numbers': True}}})
        check('extends inherits and the override wins',
              inherited['x'] == {'layout': 'brief', 'page_numbers': True})
        raises('extending an unknown type is an error',
               lambda: cli.document_types({'types': {'x': {'extends': 'nope'}}}))

        print('loading')
        cfg, docs = cli.load(str(root / 'documents.toml'))
        check('two language editions become two documents',
              sum(1 for d in docs if d['collection'] == 'sample' and d['source'].startswith('report')) == 2)
        check('an edition carries its own language',
              {d['language'] for d in docs if d['source'].startswith('report')} == {'en', 'vi'})
        check('the declared type is applied to every edition',
              all(d.get('page_numbers') for d in docs if d['source'].startswith('report')))
        check('the flat single-document form still works',
              any(d['source'] == 'note.md' for d in docs))
        check('a document defaults to not publishable', not any(d['publish'] for d in docs))

        bad = root / 'bad.toml'
        bad.write_text(MANIFEST.replace('type = "case-study"', 'type = "case-stdy"'),
                       encoding='utf-8')
        raises('a mistyped type is an error rather than a silent report',
               lambda: cli.load(str(bad)))

        print('scoping with --only')
        check('--only matches a source', len(cli.pick(docs, 'note.md')) == 1)
        check('--only matches an output', len(cli.pick(docs, 'note.html')) == 1)
        check('--only matches a collection', len(cli.pick(docs, 'sample')) == len(docs))
        check('no --only means everything', len(cli.pick(docs, None)) == len(docs))
        raises('--only matching nothing is an error, not an empty run',
               lambda: cli.pick(docs, 'no-such-document.md'))

        print('structure warnings')
        report = {'layout': 'report', 'page_numbers': True, 'profile_name': 'en',
                  'contents_heading': 'CONTENTS'}
        silent = {'structure': {'h2': 8}, 'numbered': 4}
        warned = cli.structure_warnings(report, silent)
        check('a profile matching no part heading is reported, not ignored',
              any('part_banner matched nothing' in w for w in warned))
        check('the report says how many headings it looked at',
              any('8 top-level headings' in w for w in warned))
        check('a document that found its parts is quiet',
              cli.structure_warnings(report, {'structure': {'h2': 8, 'inferred_parts': 5},
                                              'numbered': 4}) == [])
        check('an unnumbered contents is reported',
              any('no contents entry was numbered' in w
                  for w in cli.structure_warnings(report,
                                                  {'structure': {'h2': 8, 'inferred_parts': 5},
                                                   'numbered': 0})))
        brief = {'layout': 'brief', 'page_numbers': False, 'profile_name': 'en'}
        check('a brief is continuous by design and is not nagged about parts',
              cli.structure_warnings(brief, silent) == [])
        check('a document with too few headings to judge is not nagged',
              cli.structure_warnings(report, {'structure': {'h2': 2}, 'numbered': 1}) == [])

        print('editions')
        check('a sub-table with a source is an edition',
              set(cli.editions_of({'type': 'report', 'en': {'source': 'a.md'}})) == {'en'})
        check('a sub-table without one is a plain setting',
              cli.editions_of({'brand': {'navy': '#000'}}) == {})

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\ncli: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
