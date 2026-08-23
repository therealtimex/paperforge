"""Sync the pipeline and docs into the plugin package.

The plugin ships a copy of the pipeline so it installs standalone, but the repo
stays the single source of truth. `sync()` copies; `check()` reports drift, so a
stale plugin is a visible failure rather than a silent one.
"""
import filecmp
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SKILL = ROOT / 'plugin/skills/paperforge'

# (source, destination inside the skill bundle)
PAYLOAD = [
    (ROOT / 'paperforge', PLUGIN_SKILL / 'pipeline/paperforge'),
    (ROOT / 'bin', PLUGIN_SKILL / 'pipeline/bin'),
    # the fixture travels with the pipeline; a self-test that cannot run is useless
    (ROOT / 'tests', PLUGIN_SKILL / 'pipeline/tests'),
    # the whole reference directory, so adding a feature file is one step and
    # cannot leave the bundle a file behind
    (ROOT / 'docs/reference', PLUGIN_SKILL / 'references'),
]
SKIP = {'__pycache__', '.cache'}
# Built documents are regenerable and must not ship inside the plugin. The theme
# needs its own .html shells, so this applies to the fixtures only.
GENERATED = ('.html', '.pdf')


def _ignore(_dir, names):
    return [n for n in names if n in SKIP or n.endswith('.pyc')]


def _ignore_generated(_dir, names):
    """Fixtures carry build outputs after a test run; those are not payload."""
    return [n for n in names if n in SKIP or n.endswith('.pyc')
            or n.endswith(GENERATED)]


def sync():
    # Rebuild the pipeline tree rather than copying over it: a file removed from
    # the repo would otherwise survive in the bundle indefinitely, which is how
    # a renamed entry point left its old name behind.
    shutil.rmtree(PLUGIN_SKILL / 'pipeline', ignore_errors=True)
    copied = []
    for src, dst in PAYLOAD:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.rmtree(dst, ignore_errors=True)
            ignore = _ignore_generated if src.name == 'tests' else _ignore
            shutil.copytree(src, dst, ignore=ignore)
        else:
            shutil.copy2(src, dst)
        copied.append(dst.relative_to(ROOT))
    # the bundled copy must not carry this repo's manifest: a plugin user has
    # their own project, discovered via --config or the working directory
    return copied


def _differs(src, dst):
    if not dst.exists():
        return True
    if src.is_file():
        return not filecmp.cmp(src, dst, shallow=False)
    for path in src.rglob('*'):
        if any(part in SKIP for part in path.parts) or path.suffix == '.pyc':
            continue
        if src.name == 'tests' and path.suffix in GENERATED:
            continue
        rel = path.relative_to(src)
        other = dst / rel
        if path.is_dir():
            if not other.is_dir():
                return True
        elif not other.exists() or not filecmp.cmp(path, other, shallow=False):
            return True
    return False


def check():
    """Paths whose bundled copy no longer matches the repo."""
    return [str(dst.relative_to(ROOT)) for src, dst in PAYLOAD if _differs(src, dst)]


REFERENCE = ROOT / 'docs/reference'
SKILL = PLUGIN_SKILL / 'SKILL.md'


def check_references():
    """The reference set is one file per feature, cross-linked and routed to
    from SKILL.md. With twenty-odd of them a rename silently breaks navigation,
    and nothing else would notice: a dead pointer still reads like prose.

    Only the "## Related" footer is checked, so an illustrative filename in the
    body ("a link labelled `file.md`") is not mistaken for a pointer.
    """
    present = {p.name for p in REFERENCE.glob('*.md')}
    problems = []
    for path in sorted(REFERENCE.glob('*.md')):
        tail = path.read_text(encoding='utf-8').split('## Related')
        if len(tail) < 2:
            problems.append('%s has no "## Related" footer' % path.name)
            continue
        for name in re.findall(r'`([\w-]+\.md)`', tail[-1]):
            if name not in present:
                problems.append('%s links to missing %s' % (path.name, name))
    routed = set(re.findall(r'\(references/([\w-]+\.md)\)',
                            SKILL.read_text(encoding='utf-8')))
    problems += ['SKILL.md routes to missing %s' % n for n in sorted(routed - present)]
    problems += ['%s is not in the SKILL.md routing table' % n
                 for n in sorted(present - routed)]
    return problems


MANIFEST = ROOT / 'plugin/realtimex.plugin.json'
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')


def version():
    import json
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['version']


def version_problems(tag=None):
    """One shipped thing, one version number.

    The plugin manifest and the skill frontmatter each carry a version, and they
    had already drifted apart (1.0.0 against 2.0) before anything was released.
    A release tag that does not name the version being installed is the same
    class of defect: the artifact and the label disagree, and only the label is
    visible.
    """
    problems = []
    declared = version()
    if not SEMVER.match(declared):
        problems.append('plugin version %r is not MAJOR.MINOR.PATCH' % declared)
    skill = SKILL.read_text(encoding='utf-8')
    front = skill.split('---')[1] if skill.startswith('---') else ''
    m = re.search(r'^\s*version:\s*"?([\w.]+)"?\s*$', front, re.M)
    if not m:
        problems.append('SKILL.md declares no metadata.version')
    elif m.group(1) != declared:
        problems.append('SKILL.md version %s does not match the plugin version %s'
                        % (m.group(1), declared))
    if tag and tag.lstrip('v') != declared:
        problems.append('tag %s does not match the plugin version %s' % (tag, declared))
    return problems


def zip_bundle(into):
    """Write the installable plugin zip, manifest at the root of the archive."""
    import hashlib
    import zipfile
    into = Path(into)
    into.mkdir(parents=True, exist_ok=True)
    dest = into / ('paperforge-plugin-%s.zip' % version())
    plugin = MANIFEST.parent
    files = [p for p in sorted(plugin.rglob('*'))
             if p.is_file()
             and not any(part in SKIP for part in p.parts)
             and p.suffix != '.pyc'
             and not (p.suffix in GENERATED and 'tests' in p.parts)
             and p.name != '.gitignore']
    # deterministic: a fixed timestamp so the same tree always hashes the same,
    # which is what makes the checksum worth publishing
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(plugin)), (1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if path.stat().st_mode & 0o100 else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {'path': dest, 'files': len(files), 'sha256': digest,
            'bytes': dest.stat().st_size}
