"""The authoring brief for a project, generated from what it actually declares.

Written after a real handoff to a research team. The brief was good, and half of
it was the project's own AGENTS.md paraphrased by hand into a loop message - a
second copy of the rules, which goes stale the moment a lint rule changes while
the copy does not. The other half was judgement drawn from a past failure, which
no tool can derive.

So this emits the half that is fact: how to run it here, what is declared, what
the gates will refuse, which values must agree, and where the project stands. It
deliberately does not write the method, the role assignment, or what evidence
should come back - those belong to whoever is running the work, and inventing
them would be the tool pretending to author.
"""
import json
from pathlib import Path

from . import figures as fig_mod, lint, runs

UNSUPPORTED = {
    'unsupported-footnote': 'footnotes `[^1]` and their definitions',
}


def _documents(docs):
    rows = []
    for d in docs:
        bits = [d.get('type') or d.get('layout') or d.get('format') or 'report']
        if d.get('language'):
            bits.append(d['language'])
        if d.get('annex'):
            bits.append('+annex')
        if d.get('pdf'):
            bits.append('pdf:%s' % d['pdf'])
        rows.append((d['source'], ', '.join(bits),
                     'publishable' if d.get('publish') else 'not publishable'))
    return rows


def render(cfg, docs, invocation):
    """The brief, as markdown."""
    out = []
    root = Path(cfg['_root'])
    slug = docs[0]['collection'] if docs else '?'
    out.append('# Authoring brief — %s' % slug)
    out.append('')
    out.append('Generated from `%s`. Everything below is what the project '
               'declares; regenerate it rather than quoting it.'
               % Path(cfg['_manifest']).name)
    out.append('')

    requests = sorted({str(d['request_path']) for d in docs if d.get('request_path')})
    if requests:
        out.append('## What was asked')
        out.append('')
        import os
        for r in requests:
            # a request commonly lives outside the project - a shared intake
            # folder - so relative_to is not enough
            out.append('- `%s`' % os.path.relpath(r, root))
        out.append('')
        out.append('Kept with every run record, so what was asked stays readable '
                   'beside what was produced. If the request is thin, the reading '
                   'of it *is* the specification — write that reading down '
                   'somewhere it can be checked, rather than leaving it in a '
                   'message nobody re-opens.')
        out.append('')

    out.append('## Running it here')
    out.append('')
    out.append('```bash')
    out.append('%s status   # what is built, linked, published' % invocation)
    out.append('%s all      # figures -> lint -> build -> verify -> publish' % invocation)
    out.append('```')
    out.append('')
    out.append('Markdown is the source. Never edit a rendered file: change the '
               'markdown and rebuild.')
    out.append('')

    out.append('## What is declared')
    out.append('')
    out.append('| Source | Kind | Publication |')
    out.append('|---|---|---|')
    for source, kind, publish in _documents(docs):
        out.append('| `%s` | %s | %s |' % (source, kind, publish))
    internal = cfg.get('internal', {}).get('files') or []
    out.append('')
    if internal:
        out.append('Never publishable, whatever anyone edits: %s.'
                   % ', '.join('`%s`' % f for f in internal))
    else:
        out.append('No process records declared yet. Peer review, editorial notes '
                   'and approvals belong under `[internal]` as they appear.')
    out.append('')

    out.append('## What the gates will refuse')
    out.append('')
    packs = (cfg.get('lint') or {}).get('packs') or []
    extra = (cfg.get('lint') or {}).get('rule') or []
    rules = lint.ruleset(packs, extra)
    core_ids = {r[0] for r in lint.CORE}
    unsupported = [(rid, UNSUPPORTED[rid]) for rid, _, _, _ in rules if rid in UNSUPPORTED]
    if unsupported:
        out.append('**Not rendered, and blocked so they cannot print as body text:**')
        for _, what in unsupported:
            out.append('- %s' % what)
        out.append('')
    blocking = [(r[0], r[3]) for r in rules
                if r[1] == 'block' and r[0] not in UNSUPPORTED]
    out.append('**Blocked in any document:**')
    out.append('')
    out.append('| Rule | Refuses |')
    out.append('|---|---|')
    for rid, why in blocking:
        origin = '' if rid in core_ids else ' *(pack)*'
        out.append('| `%s`%s | %s |' % (rid, origin, why))
    warn = [(r[0], r[3]) for r in rules if r[1] == 'warn']
    if warn:
        out.append('')
        out.append('Reported but not blocking: %s.'
                   % ', '.join('`%s` (%s)' % (rid, why) for rid, why in warn))
    out.append('')
    out.append('If a gate blocks, fix the markdown. It is not a formatting '
               'preference; every rule here is something that reached a reader.')
    out.append('')

    out.append('## Values that must agree across documents')
    out.append('')
    path = docs[0].get('figures_path') if docs else None
    declared = fig_mod.load(path) if path and Path(path).exists() else []
    if declared:
        out.append('| Id | About | Accepted forms |')
        out.append('|---|---|---|')
        for f in declared:
            forms = ', '.join('`%s`' % a for a in (f.get('accept') or [])[:4])
            if len(f.get('accept') or []) > 4:
                forms += ', …'
            out.append('| `%s` | %s | %s |' % (f['id'], f.get('label', ''), forms))
        out.append('')
    out.append('Declare a value in `figures.toml` the moment it appears in more '
               'than one place. The gate reports a disagreement, never rewrites '
               'a sentence.')
    out.append('')

    out.append('## Where it stands')
    out.append('')
    recorded = runs.listing(root)
    if recorded:
        name, rec = recorded[-1]
        verdicts = ', '.join('%s %s' % (k, v) for k, v in rec['stages'].items())
        out.append('Last recorded run `%s`%s: %s.'
                   % (name, ' — %s' % rec['label'] if rec.get('label') else '', verdicts))
    else:
        out.append('No run recorded yet.')
    out.append('')
    out.append('Every `build` and `all` records the sources as they stood and the '
               'gate verdicts of the moment, so a draft cannot be lost to the run '
               'that replaces it. Label a run with `--label` to make it findable.')
    out.append('')

    out.append('---')
    out.append('')
    out.append('*This brief states what the project is configured to do. The '
               'research method, who holds which role, and what evidence a handoff '
               'must carry are decisions for whoever is running the work — they are '
               'not derivable from a manifest and are deliberately absent here.*')
    return '\n'.join(out) + '\n'
