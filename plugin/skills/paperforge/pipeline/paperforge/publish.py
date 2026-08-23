"""Publish built documents as RealTimeX artifacts.

The artifact server refuses symlinks that leave the artifact root
("entryFile must stay inside the workspace artifact root"), so the served copy
is a hard link: one inode, two names, edits visible immediately with no copy
step. The catch is that git replaces files rather than writing into them, so a
checkout or pull silently detaches the link and the artifact would keep serving
the old content - `link()` re-establishes it and `stale()` detects it.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

STORAGE = Path.home() / '.realtimex.ai/desktop-user-data/app/users'


def artifacts_dir(workspace, user=None):
    """Resolve <user>/storage/working-data/<workspace>/artifacts.

    Several user directories can exist (including an empty `_anon`), so choose
    by which one actually holds the workspace rather than by name order.
    """
    if user:
        return STORAGE / user / 'storage/working-data' / workspace / 'artifacts'
    if not STORAGE.exists():
        raise RuntimeError('no RealTimeX user storage found under %s' % STORAGE)
    owning = [p for p in sorted(STORAGE.iterdir()) if p.is_dir()
              and (p / 'storage/working-data' / workspace).is_dir()]
    if not owning:
        raise RuntimeError('workspace %r not found in any user storage under %s'
                           % (workspace, STORAGE))
    if len(owning) > 1:                      # prefer the most recently used
        owning.sort(key=lambda p: (p / 'storage/working-data' / workspace).stat().st_mtime,
                    reverse=True)
    return owning[0] / 'storage/working-data' / workspace / 'artifacts'


def link(built, workspace, user=None):
    """Hard-link a built file into the workspace artifacts directory."""
    target = artifacts_dir(workspace, user)
    target.mkdir(parents=True, exist_ok=True)
    dest = target / Path(built).name
    src = Path(built).resolve()
    if dest.exists():
        if dest.stat().st_ino == src.stat().st_ino:
            return dest, 'already linked'
        dest.unlink()
    try:
        os.link(src, dest)
        return dest, 'hard-linked'
    except OSError:                       # different filesystem: fall back to a copy
        shutil.copy2(src, dest)
        return dest, 'copied (cross-device; re-run publish after each rebuild)'


def stale(built, workspace, user=None):
    """True when the served copy has become detached from the built file."""
    dest = artifacts_dir(workspace, user) / Path(built).name
    if not dest.exists():
        return True
    s, d = Path(built).resolve().stat(), dest.stat()
    return s.st_ino != d.st_ino and (s.st_size, s.st_mtime) != (d.st_size, d.st_mtime)


def to_directory(built, directory):
    """Copy a built document into a plain output directory.

    The default target serves from a RealTimeX workspace; this one lets the
    same pipeline publish to any static host, or to nothing at all.
    """
    dest = Path(directory)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / Path(built).name
    shutil.copy2(built, target)
    return target, 'copied to %s' % dest


def _cli(*args):
    r = subprocess.run(['realtimex-pp-cli', *args, '--agent'],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:400])
    return json.loads(r.stdout)


def publish(workspace, artifact_path, entry_file=None, expires_at=None):
    args = ['publish-artifact', workspace, '--artifact-path', artifact_path]
    if entry_file:
        args += ['--entry-file', entry_file]
    if expires_at:
        args += ['--expires-at', expires_at]
    d = _cli(*args)
    return d.get('results', d).get('artifact', d.get('results', d))


def listing(workspace):
    d = _cli('list-artifacts', workspace)
    return d['results']['artifacts']


def find(workspace, artifact_path):
    return next((a for a in listing(workspace)
                 if a.get('artifactPath') == artifact_path and a.get('active')), None)
