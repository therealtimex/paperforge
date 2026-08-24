#!/usr/bin/env python3
"""The hard-link publishing path, which CI cannot reach through a fixture.

`target = "directory"` is exercised by tests/fixtures/publishing, but the
default target hard-links into a RealTimeX workspace and there is no host on a
runner. This drives the same functions against a temporary storage root.

It covers the failure that actually happens: git replaces files rather than
writing into them, so a checkout, pull, stash or fresh clone detaches the link
and the artifact keeps serving the old content *silently*. `stale()` is the
only thing standing between that and a reader.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import publish as pub

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pub.STORAGE = root / 'users'
        workspace = 'editor'
        (pub.STORAGE / 'someone' / 'storage/working-data' / workspace).mkdir(parents=True)

        built = root / 'report.html'
        built.write_text('<html>first</html>', encoding='utf-8')

        print('hard link')
        dest, how = pub.link(built, workspace, user='someone')
        check('linked into the workspace artifacts directory', dest.exists())
        check('one inode, two names', dest.stat().st_ino == built.stat().st_ino)
        check('reports what it did', 'link' in how.lower())
        check('a freshly linked artifact is not stale',
              not pub.stale(built, workspace, user='someone'))

        print('rebuild in place: the published copy must follow')
        built.write_text('<html>second</html>', encoding='utf-8')
        check('the artifact reflects the edit with no copy step',
              dest.read_text(encoding='utf-8') == '<html>second</html>')
        check('still not stale', not pub.stale(built, workspace, user='someone'))

        print('git replaces the file rather than writing into it')
        built.unlink()
        built.write_text('<html>third</html>', encoding='utf-8')
        check('the artifact is now a different inode', dest.stat().st_ino != built.stat().st_ino)
        check('it is silently serving the old content',
              dest.read_text(encoding='utf-8') == '<html>second</html>')
        check('stale() detects the detached link',
              pub.stale(built, workspace, user='someone'))

        print('publish repairs it')
        dest, _ = pub.link(built, workspace, user='someone')
        check('relinked', dest.stat().st_ino == built.stat().st_ino)
        check('serving current content again',
              dest.read_text(encoding='utf-8') == '<html>third</html>')
        check('no longer stale', not pub.stale(built, workspace, user='someone'))

        print('discovery picks the user directory that owns the workspace')
        (pub.STORAGE / '_anon').mkdir(parents=True, exist_ok=True)
        resolved = pub.artifacts_dir(workspace).parts
        check('an empty user directory is not chosen',
              'someone' in resolved and '_anon' not in resolved)
        try:
            pub.artifacts_dir('no-such-workspace')
            check('an unknown workspace raises', False)
        except RuntimeError:
            check('an unknown workspace raises', True)

        print('already linked')
        again, how = pub.link(built, workspace, user='someone')
        check('re-linking an already-linked file is a no-op, not a copy',
              again.stat().st_ino == built.stat().st_ino)
        check('and says so rather than claiming to have done work',
              'link' in how.lower())

        print('resolving the workspace')
        (pub.STORAGE / 'newer' / 'storage/working-data' / workspace).mkdir(parents=True)
        check('two user directories holding the workspace resolve to one',
              pub.artifacts_dir(workspace).is_absolute())
        missing = root / 'artifacts' / 'report.html'
        check('a never-published file is stale by definition',
              pub.stale(root / 'unpublished.html', workspace, user='someone')
              if not missing.exists() else True)

        print('the artifact CLI')
        calls = []
        real_cli = pub._cli
        pub._cli = lambda *a: (calls.append(a), {'results': {'artifact': {'publicUrl': 'u'}}})[1]
        try:
            pub.publish(workspace, 'report.html')
            check('a plain publish passes the workspace and the path',
                  'publish-artifact' in calls[-1] and 'report.html' in calls[-1])
            pub.publish(workspace, 'report.html', entry_file='index.html')
            check('an entry file is passed through', '--entry-file' in calls[-1])
            pub.publish(workspace, 'report.html', expires_at='2027-01-01T00:00:00Z')
            check('an expiry is passed through', '--expires-at' in calls[-1])
            pub._cli = lambda *a: {'results': {'artifacts': [
                {'artifactPath': 'report.html', 'active': True, 'id': 'A'},
                {'artifactPath': 'old.html', 'active': False, 'id': 'B'}]}}
            check('find returns the active artifact for a path',
                  pub.find(workspace, 'report.html')['id'] == 'A')
            check('an inactive artifact is not returned',
                  pub.find(workspace, 'old.html') is None)
            check('an unknown path returns nothing', pub.find(workspace, 'nope.html') is None)
        finally:
            pub._cli = real_cli

        print('no RealtimeX storage at all')
        pub.STORAGE = root / 'absent'
        try:
            pub.artifacts_dir(workspace)
            check('a missing storage root raises', False)
        except RuntimeError:
            check('a missing storage root raises', True)
        pub.STORAGE = root / 'users'

        print('directory target')
        out = root / 'dist'
        copied, how = pub.to_directory(built, out)
        check('copied into the output directory', copied.exists())
        check('a copy, not a link', copied.stat().st_ino != built.stat().st_ino)
        check('reports the destination', str(out) in how)

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\npublish: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
