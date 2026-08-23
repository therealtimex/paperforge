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
