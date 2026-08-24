"""What a run produced, kept so the next run cannot erase it.

A research corpus in this system was drafted twice. The first pass was poor and
was overwritten in place by the second; the repository had git from the start
and it did not help, because preserving the first pass required somebody to
remember to commit at the right moment and four agent roles all did not. The
drafts are simply gone, so the two passes can never be compared.

So the record is a by-product of running the pipeline rather than an act of
discipline. `all` and `build` write one every time. It holds the sources
themselves, not only their hashes: what was wanted afterwards was the lost
draft, and a fingerprint would not have returned it.

One thing it deliberately does not claim. Hashing an artifact implies a rebuild
reproduces it. The HTML does - byte for byte. The Typst PDF does not reliably:
printed page numbers are *measured*, by printing the document and reading the
page back, so a different machine with different fonts genuinely paginates
differently. The PDF hash is recorded as observed, and `diff` reports a change
in it as a note rather than a discrepancy.
"""
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

RUNS = '.paperforge/runs'


def _sha(path):
    path = Path(path)
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(label):
    return re.sub(r'[^a-z0-9]+', '-', (label or '').lower()).strip('-')[:40]


def write(cfg, docs, stages, label=None, root=None):
    """Record one run. Returns the directory written."""
    root = Path(root or cfg['_root'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = '%s-%s' % (stamp, _slug(label)) if label else stamp
    # two runs inside the same second must not share a directory: the second
    # would overwrite the first, which is the exact failure this exists to stop
    base, n = name, 1
    while (root / RUNS / name / 'record.json').exists():
        n += 1
        name = '%s.%d' % (base, n)
    out = root / RUNS / name
    (out / 'sources').mkdir(parents=True, exist_ok=True)

    entries = []
    for d in docs:
        entry = {'collection': d['collection'], 'language': d.get('language'),
                 'source': d['source'], 'source_sha256': _sha(d['source_path']),
                 'output': d['output'], 'output_sha256': _sha(d['output_path']),
                 'publish': bool(d.get('publish'))}
        pdf = d['output_path'].with_suffix('.pdf')
        if pdf.exists():
            # observed, not a reproducibility claim - see the module docstring
            entry['pdf_sha256_observed'] = _sha(pdf)
        if d.get('annex_path'):
            entry['annex'] = d['annex']
            entry['annex_sha256'] = _sha(d['annex_path'])
        entries.append(entry)
        for path in (d['source_path'], d.get('annex_path')):
            if path and Path(path).exists():
                shutil.copy2(path, out / 'sources' / Path(path).name)

    manifest = Path(cfg.get('_manifest') or (root / 'documents.toml'))
    record = {
        'label': label,
        'recorded': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'manifest_sha256': _sha(manifest),
        'stages': stages,
        'documents': entries,
    }
    (out / 'record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n',
                                     encoding='utf-8')
    return out


def listing(root):
    """Every recorded run, oldest first."""
    base = Path(root) / RUNS
    if not base.is_dir():
        return []
    found = []
    for d in sorted(base.iterdir()):
        record = d / 'record.json'
        if record.is_file():
            found.append((d.name, json.loads(record.read_text(encoding='utf-8'))))
    return found


def load(root, name):
    """One run by directory name, or by a unique prefix of it."""
    runs = listing(root)
    exact = [r for r in runs if r[0] == name]
    if exact:
        return exact[0]
    matches = [r for r in runs if r[0].startswith(name) or _slug(r[1].get('label')) == name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit('no run matches %r; `paperforge runs` lists them' % name)
    raise SystemExit('%r matches %d runs: %s'
                     % (name, len(matches), ', '.join(m[0] for m in matches)))


def diff(before, after):
    """What changed between two runs, in the terms that decide quality."""
    a_docs = {d['source']: d for d in before['documents']}
    b_docs = {d['source']: d for d in after['documents']}
    out = {'added': sorted(set(b_docs) - set(a_docs)),
           'removed': sorted(set(a_docs) - set(b_docs)),
           'rewritten': [], 'unchanged': [], 'pdf_only': [], 'stages': {}}
    for name in sorted(set(a_docs) & set(b_docs)):
        x, y = a_docs[name], b_docs[name]
        if x['source_sha256'] != y['source_sha256'] or x.get('annex_sha256') != y.get('annex_sha256'):
            out['rewritten'].append(name)
        elif x.get('output_sha256') != y.get('output_sha256'):
            out['rewritten'].append(name)          # same source, different render
        elif x.get('pdf_sha256_observed') != y.get('pdf_sha256_observed'):
            out['pdf_only'].append(name)           # measured pagination; not a discrepancy
        else:
            out['unchanged'].append(name)
    for stage in sorted(set(before['stages']) | set(after['stages'])):
        was, now = before['stages'].get(stage), after['stages'].get(stage)
        if was != now:
            out['stages'][stage] = (was, now)
    return out
