#!/usr/bin/env python3
"""The packager's own guarantees.

`plugin --check` is what stands between the repo and a plugin that ships stale
code, a dead documentation pointer or a version that disagrees with its tag.
Every one of those has happened here. CI runs the command against a tree that
is correct, which proves it does not false-alarm; this proves it fires.
"""
import os
import shlex
import shutil
import subprocess
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

    print('the deployed launcher finds the pipeline runtime')
    launcher = root / 'bin/paperforge'
    with tempfile.TemporaryDirectory() as tmp:
        candidates = [sys.executable,
                      '/Applications/RealTimeX.AI.app/Contents/Resources/app/src/'
                      'electron/features/pty/compat/macos/python3']
        capable = next((p for p in candidates if Path(p).is_file() and
                        subprocess.run([p, '-c', 'import pdfplumber'],
                                       capture_output=True).returncode == 0), None)
        marker = Path(tmp) / 'chosen'
        chooser = Path(tmp) / 'paperforge-python'
        chooser.write_text(
            '#!/bin/sh\n'
            'printf chosen > %s\n'
            'exec %s "$@"\n' % (shlex.quote(str(marker)), shlex.quote(capable or 'missing')),
            encoding='utf-8')
        chooser.chmod(0o755)
        env = dict(os.environ, PAPERFORGE_PYTHON=str(chooser))
        selected = subprocess.run([str(launcher), '--help'], env=env,
                                  capture_output=True, text=True)
        check('PAPERFORGE_PYTHON selects the interpreter explicitly',
              selected.returncode == 0 and marker.is_file())

        missing = subprocess.run(
            [str(launcher), '--help'],
            env=dict(os.environ, PAPERFORGE_PYTHON=str(Path(tmp) / 'missing-python')),
            capture_output=True, text=True)
        check('an unusable override names the missing dependency clearly',
              missing.returncode != 0 and 'pdfplumber' in missing.stderr)

        liar = Path(tmp) / 'lying-python'
        liar.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = "-c" ]; then exit 0; fi\n'
            'PYTHONPATH= exec %s -S "$@"\n' % shlex.quote(capable or sys.executable),
            encoding='utf-8')
        liar.chmod(0o755)
        try:
            one_hop = subprocess.run(
                [str(launcher), '--help'],
                env=dict(os.environ, PAPERFORGE_PYTHON=str(liar)),
                capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            one_hop = None
        check('a lying explicit capability probe stops after one re-exec',
              one_hop is not None and one_hop.returncode != 0
              and 'pdfplumber' in one_hop.stderr)

        # Run the real launcher under an isolated stdlib-only interpreter. The
        # installed-app candidate is suppressed so this remains a check of the
        # launcher's fallback on developer machines that happen to have it.
        isolated = (
            'import pathlib, runpy, sys; '
            'real_is_file = pathlib.Path.is_file; '
            'pathlib.Path.is_file = lambda p: False if '
            'str(p).startswith("/Applications/RealTimeX.AI.app/") '
            'else real_is_file(p); '
            'runpy.run_path(sys.argv.pop(1), run_name="__main__")'
        )

        def without_pdfplumber(*args, extra_env=None):
            clean = dict(os.environ, PATH='/usr/bin:/bin')
            for name in ('PAPERFORGE_PYTHON', 'PAPERFORGE_LAUNCHER_REEXEC',
                         'REALTIMEX_MANAGED_PYTHON_BIN'):
                clean.pop(name, None)
            clean.update(extra_env or {})
            return subprocess.run(
                [sys.executable, '-S', '-c', isolated, str(launcher), *args],
                cwd=root, env=clean, capture_output=True, text=True)

        fallback = without_pdfplumber('plugin', '--check')
        warning = [line for line in fallback.stderr.splitlines() if line.strip()]
        check('a non-PDF command runs when no candidate has pdfplumber',
              fallback.returncode == 0 and len(warning) == 1
              and 'pdfplumber' in warning[0] and 'tried' in warning[0])

        needs_pdf = without_pdfplumber(
            'verify', '--config', str(root / 'tests/fixtures/publishing/documents.toml'))
        check('a PDF command reaches its own missing-dependency error',
              needs_pdf.returncode != 0
              and "No module named 'pdfplumber'" in needs_pdf.stderr
              and 'paperforge needs a Python interpreter' not in needs_pdf.stderr)

        managed_marker = Path(tmp) / 'managed'
        managed = Path(tmp) / 'managed-python'
        managed.write_text(
            '#!/bin/sh\n'
            'printf managed > %s\n'
            'exec %s "$@"\n'
            % (shlex.quote(str(managed_marker)), shlex.quote(capable or 'missing')),
            encoding='utf-8')
        managed.chmod(0o755)
        selected = without_pdfplumber(
            '--help', extra_env={'REALTIMEX_MANAGED_PYTHON_BIN': str(managed)})
        check('the managed RealtimeX Python is an automatic candidate',
              selected.returncode == 0 and managed_marker.is_file())

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\npackager: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
