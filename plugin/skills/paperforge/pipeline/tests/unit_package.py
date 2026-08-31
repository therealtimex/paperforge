#!/usr/bin/env python3
"""The packager's own guarantees.

`plugin --check` is what stands between the repo and a plugin that ships stale
code, a dead documentation pointer or a version that disagrees with its tag.
Every one of those has happened here. CI runs the command against a tree that
is correct, which proves it does not false-alarm; this proves it fires.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import package_plugin as pp

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    print('drift detection')
    # measured against whatever the tree reports now, not against zero: a
    # working copy mid-change is legitimately out of sync, and a test that
    # demands a clean tree is testing the developer, not the packager
    baseline = pp.check()
    dst = pp.PLUGIN_SKILL / 'pipeline/paperforge/lint.py'
    original = dst.read_bytes()
    try:
        dst.write_bytes(original + b'\n# drift\n')
        check('an edited file in the bundle is reported',
              any('pipeline/paperforge' in d for d in pp.check()))
        dst.unlink()
        check('a file missing from the bundle is reported',
              any('pipeline/paperforge' in d for d in pp.check()))
    finally:
        dst.write_bytes(original)
    check('restoring the file returns the report to where it started',
          pp.check() == baseline)

    print('reference links')
    check('every "## Related" pointer resolves today', pp.check_references() == [])
    victim = pp.REFERENCE / 'tables.md'
    moved = pp.REFERENCE / 'tables.md.moved'
    try:
        victim.rename(moved)
        broken = pp.check_references()
        check('a renamed reference is reported by the files pointing at it',
              any('links to missing tables.md' in b for b in broken))
        check('and by the routing table in SKILL.md',
              any('SKILL.md routes to missing tables.md' in b for b in broken))
    finally:
        moved.rename(victim)
    check('restoring it clears the report', pp.check_references() == [])

    print('one version across the manifest, the skill and the tag')
    declared = pp.version()
    check('the repo agrees with itself', pp.version_problems() == [])
    check('a matching tag passes', pp.version_problems('v%s' % declared) == [])
    check('a tag naming another version is refused',
          any('does not match' in p for p in pp.version_problems('v9.9.9')))
    check('the leading v is optional', pp.version_problems(declared) == [])

    print('a manifest that disagrees with itself')
    import tempfile as _tf
    real_manifest, real_skill = pp.MANIFEST, pp.SKILL
    with _tf.TemporaryDirectory() as tmp:
        m, k = Path(tmp) / 'plugin.json', Path(tmp) / 'SKILL.md'
        pp.MANIFEST, pp.SKILL = m, k
        try:
            m.write_text('{"id": "ai.realtimex.x", "name": "x", "version": "2.0"}', encoding='utf-8')
            k.write_text('---\nname: x\nmetadata:\n  version: "2.0"\n---\n', encoding='utf-8')
            check('a version that is not MAJOR.MINOR.PATCH is refused',
                  any('MAJOR.MINOR.PATCH' in p for p in pp.version_problems()))
            m.write_text('{"id": "ai.realtimex.x", "name": "x", "version": "2.0.0"}', encoding='utf-8')
            check('a skill frontmatter naming another version is refused',
                  any('does not match' in p for p in pp.version_problems()))
            k.write_text('---\nname: x\n---\n', encoding='utf-8')
            check('a skill with no version at all is refused',
                  any('no metadata.version' in p for p in pp.version_problems()))
        finally:
            pp.MANIFEST, pp.SKILL = real_manifest, real_skill

    print('the installable zip')
    with tempfile.TemporaryDirectory() as tmp:
        first = pp.zip_bundle(tmp)
        check('the archive is named for the version',
              first['path'].name == 'paperforge-plugin-%s.zip' % declared)
        check('it carries files', first['files'] > 10)
        import zipfile
        with zipfile.ZipFile(first['path']) as z:
            names = z.namelist()
        check('the manifest sits at the root of the archive',
              'realtimex.plugin.json' in names)
        check('the skill travels with it', 'skills/paperforge/SKILL.md' in names)
        check('no bytecode is shipped', not any(n.endswith('.pyc') for n in names))
        check('no built fixture output is shipped',
              not any(n.endswith('.html') and '/tests/' in n for n in names))

        second_dir = Path(tmp) / 'again'
        second = pp.zip_bundle(second_dir)
        # fixed timestamps: the same tree must produce the same archive, or the
        # checksum published beside a release means nothing
        check('the same tree produces the same checksum',
              second['sha256'] == first['sha256'])
        shutil.rmtree(second_dir, ignore_errors=True)

    print('a project can say `paperforge` without knowing where it lives')
    import tomllib
    root = Path(__file__).resolve().parents[1]
    meta = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
    check('there is packaging metadata at all',
          meta['project']['name'] == 'paperforge')
    check('and a console script, so PYTHONPATH is not the answer',
          meta['project']['scripts'].get('paperforge') == 'paperforge.cli:main')
    # one version, and this is the fourth place it could have been written
    check('the version is read from the package, not repeated here',
          'version' not in meta['project']
          and meta['tool']['setuptools']['dynamic']['version']['attr']
          == 'paperforge.__version__')

    print('what the pipeline imports is declared and reported')
    from paperforge import require
    declared = set(meta['project']['dependencies'])
    check('the runtime dependencies are declared',
          any(d.startswith('pdfplumber') for d in declared)
          and any(d.startswith('python-docx') for d in declared))
    # doctor reported the external programs and said nothing about these, so a
    # machine without them failed inside a stage instead of being told
    reported = {name for name, _, _, _ in require.libraries()}
    check('and doctor reports every one of them',
          reported == {'pdfplumber', 'docx'})
    check('a library that is not installed is seen as missing',
          require.imported('definitely_not_installed') is False)
    check('every library says where it comes from',
          all(src.startswith('pip install') for _, _, _, src in require.libraries()))

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\npackager: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
