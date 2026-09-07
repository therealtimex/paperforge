#!/usr/bin/env python3
"""What wrote a project, and whether that is still what we would write.

`init` copies this pipeline's guidance into a project, and from that moment it
is a second copy of something that keeps changing here. The first copy of that
mistake was caught by `plugin --check`, which fails when the generated bundle
drifts from the repository. This is the same check for the copy that leaves the
repository, and the reason it is needed is a real project found running against
an AGENTS.md from before v3.0.0 against a v3.8.0 pipeline: it named a stage
that no longer existed and an entry point that was a placeholder.

The interesting case is the third one. A project scaffolded before stamping
existed has no record of what wrote it, and reporting nothing would read as
current. Untestable is never passed.
"""
import json
import io
import contextlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paperforge
from paperforge import cli, package_plugin, scaffold

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def project(root):
    """A scaffolded project, the way `init` makes one."""
    from paperforge import profile
    scaffold.create(root, 't', 'T', ['en'], {'en': profile.load('en')},
                    ['report'], 'Org', 'Publisher', None, git=False)


def main():
    print('one shipped thing, one version number')
    check('the package carries a version', bool(paperforge.__version__))
    # the bundle ships neither the manifest nor SKILL.md, which is the whole
    # reason the package carries a version at all; there is nothing to compare
    # it against there, and a check that cannot run says so
    if package_plugin.MANIFEST.is_file():
        check('and it agrees with the plugin and the skill',
              package_plugin.version_problems() == [])
    else:
        print('  %-58s skip (no plugin manifest here)'
              % 'and it agrees with the plugin and the skill')

    print('a fingerprint of the guidance, not of the project')
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        scaffold.stamp(a)
        scaffold.stamp(b)
        one = json.loads((Path(a) / scaffold.STAMP).read_text(encoding='utf-8'))
        two = json.loads((Path(b) / scaffold.STAMP).read_text(encoding='utf-8'))
        # the rendered AGENTS.md carries a title and an absolute path, so
        # hashing the output would give every project its own answer to a
        # question about Paperforge
        check('two projects scaffolded now agree', one['agents'] == two['agents'])
        check('and the stamp records the version that wrote them',
              one['version'] == paperforge.__version__)
        check('and records the one-token invocation that wrote them',
              one.get('invocation') == str(Path(sys.argv[0]).resolve()))

    print('everything init fills in is in the fingerprint')
    from paperforge.cli import STAGES
    import paperforge.cli as _cli
    before = fingerprint_now = scaffold.fingerprint()
    _cli.STAGES = STAGES + ('nonsense',)
    try:
        # the stage chain is filled into the template from cli.STAGES, so a new
        # stage changes what `init` writes without touching the template. The
        # field project's AGENTS.md was stale in exactly this way: a chain with
        # no `claims` in it
        check('adding a stage changes what a project would be told',
              scaffold.fingerprint() != before)
    finally:
        _cli.STAGES = STAGES
    check('and restoring it restores the fingerprint',
          scaffold.fingerprint() == before)

    print('a stamp that is JSON but not a record')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / '.paperforge').mkdir()
        (root / scaffold.STAMP).write_text('[]', encoding='utf-8')
        check('parses, and is still unknown rather than a traceback',
              scaffold.drift(root)['state'] == 'unstamped')

    print('what doctor is told about a project')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        check('a project with no stamp is unknown, not current',
              scaffold.drift(root)['state'] == 'unstamped')
        check('and it says why',
              'no record' in scaffold.drift(root)['why'])

        scaffold.stamp(root)
        check('a project stamped by this pipeline is current',
              scaffold.drift(root)['state'] == 'current')

        path = root / scaffold.STAMP
        found = json.loads(path.read_text(encoding='utf-8'))
        found['agents'] = 'deadbeefdeadbeef'
        found['version'] = '2.9.0'
        path.write_text(json.dumps(found), encoding='utf-8')
        stale = scaffold.drift(root)
        check('guidance we would no longer write is stale',
              stale['state'] == 'stale')
        check('and the report names both versions',
              '2.9.0' in stale['why'] and paperforge.__version__ in stale['why'])

        path.write_text('{not json', encoding='utf-8')
        check('an unreadable stamp is unknown, not current',
              scaffold.drift(root)['state'] == 'unstamped')

    print('the drift is a property of the template, not of the version')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        scaffold.stamp(root)
        path = root / scaffold.STAMP
        found = json.loads(path.read_text(encoding='utf-8'))
        found['version'] = '0.0.1'          # older, but the guidance is the same
        path.write_text(json.dumps(found), encoding='utf-8')
        # a version bump that does not change what `init` writes leaves a
        # project's guidance correct, and saying otherwise would train people
        # to ignore the report
        check('an old version with current guidance is not stale',
              scaffold.drift(root)['state'] == 'current')

    print('init leaves the stamp behind')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'p'
        project(root)
        check('a scaffolded project is stamped',
              (root / scaffold.STAMP).is_file())
        check('and reports itself current',
              scaffold.drift(root)['state'] == 'current')

        manifest = root / 'documents.toml'
        manifest.write_text(
            '# QSPEC: this hand-built comment predates the manifest body\n'
            + manifest.read_text(encoding='utf-8').split('\n', 1)[1],
            encoding='utf-8')
        agents = root / 'AGENTS.md'
        agents.write_text(
            '# Writer-owned heading\n'
            + agents.read_text(encoding='utf-8').split('\n', 1)[1],
            encoding='utf-8')
        claude = root / 'CLAUDE.md'
        claude.unlink()
        own_claude = b'# My own Claude notes\n\nKeep this byte-for-byte.\n'
        claude.write_bytes(own_claude)

        before = manifest.read_bytes()
        old = json.loads((root / scaffold.STAMP).read_text(encoding='utf-8'))
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                refreshed = cli.main(['init', '--refresh', '--into', str(root)]) == 0
        except SystemExit:
            refreshed = False
        after = json.loads((root / scaffold.STAMP).read_text(encoding='utf-8'))
        check('refresh leaves the manifest byte-identical',
              refreshed and manifest.read_bytes() == before)
        check('refresh preserves created and records when it ran',
              after['created'] == old['created'] and bool(after.get('refreshed')))
        check('refresh rewrites the guidance with the current invocation',
              after.get('invocation', '<not recorded>')
              in agents.read_text(encoding='utf-8'))
        check('refresh preserves the existing guidance heading',
              agents.read_text(encoding='utf-8').splitlines()[0]
              == '# Writer-owned heading')
        check('refresh leaves a customised CLAUDE.md byte-identical',
              claude.is_file() and not claude.is_symlink()
              and claude.read_bytes() == own_claude)
        check('and reports that the customised pointer was left alone',
              "CLAUDE.md (left alone: not Paperforge's pointer)"
              in output.getvalue())

        after['invocation'] = str(root / 'a-launcher-that-moved')
        (root / scaffold.STAMP).write_text(json.dumps(after), encoding='utf-8')
        check('a recorded invocation that itself vanished is missing',
              scaffold.invocation_drift(
                  root, current=after['invocation'])['state'] == 'missing')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli._doctor_project(str(root / 'documents.toml'))
        check('doctor calls a different recorded invocation moved',
              'invocation' in out.getvalue() and 'moved' in out.getvalue())

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        scaffold.stamp(root)
        path = root / scaffold.STAMP
        legacy = json.loads(path.read_text(encoding='utf-8'))
        legacy.pop('invocation')
        path.write_text(json.dumps(legacy), encoding='utf-8')
        unknown = scaffold.invocation_drift(root)
        check('an unknown invocation names refresh as the remedy',
              unknown['state'] == 'unknown'
              and 'init --refresh' in unknown['why'])

    with tempfile.TemporaryDirectory() as tmp:
        try:
            cli.main(['init', '--refresh', '--into', tmp])
            check('refresh refuses a directory init did not stamp', False)
        except SystemExit as err:
            check('refresh refuses a directory init did not stamp',
                  'without `--refresh`' in str(err))

    print()
    if failures:
        print('%d check(s) failed' % len(failures))
        return 1
    print('scaffold: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
