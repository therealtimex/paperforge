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


# A project that actually publishes, to a directory, so the gate can be run
# without a host. The document is publishable and refers to a label that is
# not there: `lint` has always blocked it, `publish` used not to look.
PUBLISH_MANIFEST = """[defaults]
profile = "en"
target = "directory"
directory = "published"

[[collection]]
slug = "p"
root = "."

  [[collection.document]]
  id = "report"
  type = "report"
  source = "report.md"
  publish = true

[internal]
files = []
reason = "unit"
"""

DANGLING_DOC = """# DOCUMENT
## A report that points at nothing

---
**Prepared by:** Paperforge

---

## CONTENTS

1. **Findings**

---

## Findings

The shape of it is set out in @fig-nowhere, which is a label this document
never declares, and every edition prints the reference as its own source.
"""


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

        print('a draft run')
        # The mode reports every finding and refuses nothing, which is only
        # defensible because it cannot publish: otherwise it is a documented way
        # around the gates, and the scaffolded AGENTS.md tells agents not to
        # take one. That property is the gate.
        raises('publishing a draft is refused, in those terms',
               lambda: cli.main(['publish', '--draft',
                                 '--config', str(root / 'documents.toml')]))
        # a check that cannot fail reads as coverage: assert argparse actually
        # knows the flag rather than that a docstring mentions it
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            knows = cli.main(['doctor', '--draft']) == 0
        check('and argparse knows the flag, so the refusal is reachable', knows)

        print('publishing runs the whole gate, not the part it used to')
        # `all` lints first and holds a blocking document back, so the subset
        # publish re-ran decided nothing there - and everything in a standalone
        # `publish` against an artifact built earlier, which is how a document
        # is published a second time.
        import contextlib as _c, io as _io
        pub = root / 'pub'
        pub.mkdir()
        (pub / 'documents.toml').write_text(PUBLISH_MANIFEST, encoding='utf-8')
        (pub / 'report.md').write_text(DANGLING_DOC, encoding='utf-8')
        out = _io.StringIO()
        with _c.redirect_stdout(out):
            cli.main(['build', '--config', str(pub / 'documents.toml')])
        built = (pub / 'report.html').is_file()
        check('the document builds; nothing here is about the build', built)
        out = _io.StringIO()
        with _c.redirect_stdout(out):
            code = cli.main(['publish', '--config', str(pub / 'documents.toml')])
        said = out.getvalue()
        check('a dangling reference refuses publication on its own',
              'REFUSED' in said and 'dangling-reference' in said)
        # a refusal that exits 0 reads to a release job as a done publish
        check('and the refusal reaches the exit status', code == 1)
        check('and nothing reached the directory',
              not (pub / 'published').exists()
              or not list((pub / 'published').glob('*.html')))

        print('a document that cannot be assembled')
        # `check_all` reads the assembled document, and a missing include
        # cannot be read: the include finding was recorded and then buried
        # under a FileNotFoundError traceback
        gone = root / 'gone'
        gone.mkdir()
        (gone / 'documents.toml').write_text(
            PUBLISH_MANIFEST.replace('  source = "report.md"',
                                     '  source = "report.md"\n  include = ["missing.md"]'),
            encoding='utf-8')
        (gone / 'report.md').write_text(DANGLING_DOC, encoding='utf-8')
        out = _io.StringIO()
        with _c.redirect_stdout(out):
            cli.main(['lint', '--config', str(gone / 'documents.toml')])
        said = out.getvalue()
        check('a missing include is reported, not raised',
              'include' in said and 'missing.md' in said)

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
