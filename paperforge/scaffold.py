"""Prepare a new research project.

Every artefact that makes an existing project work - the manifest, the figures
list, the profile choice, the internal-document list - was written after the
documents existed in the one project that predates this command. Three real
failures came from that ordering: internal metadata reached a ministry-facing
draft, a rendered file drifted from its source, and a brief was typeset as a
report. All three are decisions best made in an empty folder.

The interview belongs to the agent, not here: this writes what it is told, so
the result is deterministic and reviewable.
"""
import subprocess
from datetime import date
from pathlib import Path

GITIGNORE = """# built artefacts are reproducible from the sources
.cache/
*.pdf

# .paperforge/runs is deliberately NOT ignored: it is the record of what each
# run produced, and the reason it exists is that a previous corpus lost its
# first draft to a second run that overwrote it in place.
"""

AGENTS = """# {title}

Research project. Markdown is the source; every rendered artefact is **built**
from it and must never be hand-edited.

## Working here

The pipeline is not on PATH by default. Invoke it by path, or put it on PATH
once as `paperforge`:

```bash
<paperforge>/bin/paperforge status   # what is built, linked, published
<paperforge>/bin/paperforge all      # figures -> lint -> build -> verify -> publish
<paperforge>/bin/paperforge all --only <source.md>
```

- `documents.toml` decides what may be published. Process records — peer review,
  editorial notes, approvals — belong under `[internal]` and never ship.
- `figures.toml` holds values the documents must agree on. Add a figure the
  moment it appears in more than one place.
- A document becomes publishable by a deliberate edit to `publish`, which is
  also the moment someone decides it is ready.
- If lint blocks, fix the markdown. Do not bypass the gate.

Skeleton sections are marked `{{.part}}` so structure is explicit and does not
depend on matching a heading pattern. Keep the marker when you rewrite them.
"""


def _meta_block(prof, publisher, when):
    s = prof.get('scaffold', {})
    return '**%s:** %s\n**%s:** %s\n' % (
        s.get('prepared_by', 'Prepared by'), publisher,
        s.get('completed', 'Completed'), when)


def report(prof, title, publisher, when):
    s = prof.get('scaffold', {})
    contents = prof['structure'].get('contents_heading', 'CONTENTS')
    parts = [s.get('summary', 'Executive summary'),
             s.get('section_one', 'Context'),
             s.get('section_two', 'Findings'),
             s.get('conclusion', 'Conclusion')]
    prose = s.get('prose', 'Replace this paragraph with the substance of the section.')
    out = ['# %s' % prof['labels'].get('document', 'DOCUMENT'), '## %s' % title, '',
           '---', _meta_block(prof, publisher, when), '---', '',
           '## %s' % contents, '']
    out += ['%d. **%s**' % (i, p) for i, p in enumerate(parts, 1)]
    out += ['', '---', '']
    for p in parts:
        out += ['## %s {.part}' % p, '', prose, '', prose, '']
    return '\n'.join(out)


def brief(prof, title, publisher, when):
    s = prof.get('scaffold', {})
    prose = s.get('prose', 'Replace this paragraph with the substance of the section.')
    out = ['# %s' % title, '', '---', _meta_block(prof, publisher, when), '---', '']
    for heading in (s.get('summary', 'Executive summary'), s.get('section_two', 'Findings')):
        out += ['## %s' % heading, '', prose, '']
    return '\n'.join(out)


def deck(prof, title, publisher, when):
    s = prof.get('scaffold', {})
    prose = s.get('prose', 'Replace this paragraph with the substance of the section.')
    out = ['# %s' % prof['labels'].get('deck', 'PRESENTATION'), '## %s' % title, '',
           '---', _meta_block(prof, publisher, when), '---', '']
    for heading in (s.get('summary', 'Executive summary'), s.get('section_two', 'Findings')):
        out += ['## %s' % heading, '', '- %s' % prose, '']
    return '\n'.join(out)


def annex(prof, title, publisher, when):
    s = prof.get('scaffold', {})
    prose = s.get('prose', 'Replace this paragraph with the substance of the section.')
    return '\n'.join(['# %s' % prof['labels'].get('annex_badge', 'Annex'),
                      '## %s' % title, '', _meta_block(prof, publisher, when), '---', '',
                      '## 1. %s' % s.get('sources', 'Sources'), '', prose, ''])


BUILDERS = {'report': report, 'brief': brief, 'deck': deck, 'annex': annex}


def manifest(slug, title, languages, publications, organisation, publisher,
             workspace, has_annex):
    """The manifest is written already correct rather than as a placeholder:
    a placeholder to edit later never gets edited.

    One language yields the flat form. Several yield the edition form, where a
    work carries a language sub-table each - which is also what gives the
    figures check the language context it needs.
    """
    multi = len(languages) > 1
    lines = [
        '# Publication manifest for %s.' % title,
        '#',
        '# A document ships only if it appears here with publish = true.',
        '# Process records belong under [internal] and can never be published.',
        '',
        '[defaults]',
        'organisation = "%s"' % organisation,
        'publisher = "%s"' % publisher,
        'paper = "A4"',
        '# footer_note = "..."     # overrides the profile default on every document',
    ]
    if not multi:
        lines.insert(6, 'profile = "%s"' % languages[0])
    if workspace:
        lines.append('workspace = "%s"        # RealTimeX workspace serving the artifacts' % workspace)
    lines += ['', '[[collection]]', 'slug = "%s"' % slug, 'root = "."',
              'figures = "figures.toml"']
    if not multi:
        lines.append('profile = "%s"' % languages[0])
    lines.append('')

    for kind in [k for k in publications if k != 'annex']:
        lines += ['  [[collection.document]]',
                  '  id = "%s"' % kind,
                  '  type = "%s"' % kind]
        if kind == 'report':
            lines.append('  page_numbers = true')
            lines.append('  # contents_heading comes from the profile; override only if it differs')
        else:
            lines.append('  page_numbers = false')
        if multi:
            lines.append('')
            for lang in languages:
                lines += ['    [collection.document.%s]' % lang,
                          '    source = "%s"' % source_name(slug, kind, lang, multi)]
                if kind == 'report' and has_annex:
                    lines.append('    annex = "%s"      # embedded inline, not published alone'
                                 % source_name(slug, 'annex', lang, multi))
                lines += ['    publish = false        # flip to true when this edition is ready', '']
        else:
            lines.append('  source = "%s"' % source_name(slug, kind, languages[0], multi))
            if kind == 'report' and has_annex:
                lines.append('  annex = "%s"      # embedded inline, not published alone'
                             % source_name(slug, 'annex', languages[0], multi))
            lines += ['  publish = false           # flip to true when the document is ready', '']

    lines += ['[internal]',
              '# Never publishable. Add process records here as they appear.',
              'files = []',
              'reason = "process records: review, editorial notes, approvals"', '']
    return '\n'.join(lines)


def source_name(slug, kind, language, multi):
    """Systematic names so an edition is identifiable from its filename."""
    return '%s-%s.%s.md' % (slug, kind, language) if multi else '%s-%s.md' % (slug, kind)


FIGURES = '''# Canonical figures for this project.
#
# The same value gets restated across documents; correcting one leaves the
# others silently disagreeing. Declare a value here the moment it appears in
# more than one place, and every document is checked against it.
#
# Values are checked, never substituted, so the prose stays natural.
#
# [[figure]]
# id      = "growth-target"
# label   = "Headline growth target"
# context = "growth|GDP"                  # a line about this fact matches this
# pattern = '(?:>=|at least)\\s*\\d+\\s*%'   # what a stated value looks like
# accept  = [">= 10%", "at least 10%"]    # the forms that are correct
'''


def create(directory, slug, title, languages, profiles, publications,
           organisation, publisher, workspace=None, git=True):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    multi = len(languages) > 1
    # %B is the C-locale month name, which put "August 2026" in a Vietnamese
    # document; the format belongs to the profile
    written = []
    text = manifest(slug, title, languages, publications, organisation,
                    publisher, workspace, 'annex' in publications)
    (root / 'documents.toml').write_text(text, encoding='utf-8')
    written.append('documents.toml')

    (root / 'figures.toml').write_text(FIGURES, encoding='utf-8')
    (root / '.gitignore').write_text(GITIGNORE, encoding='utf-8')
    (root / 'AGENTS.md').write_text(AGENTS.format(title=title), encoding='utf-8')
    written += ['figures.toml', '.gitignore', 'AGENTS.md']

    for language in languages:
        prof = profiles[language]
        when = date.today().strftime(prof.get('scaffold', {}).get('date_format', '%m/%Y'))
        for kind in publications:
            name = source_name(slug, kind, language, multi)
            (root / name).write_text(BUILDERS[kind](prof, title, publisher, when),
                                     encoding='utf-8')
            written.append(name)

    if git and not (root / '.git').exists() and not _inside_work_tree(root):
        subprocess.run(['git', 'init', '-q'], cwd=root, capture_output=True)
        written.append('.git/')
    return written


def _inside_work_tree(path):
    """A project created inside an existing repository must not nest a second
    one: git refuses to add the directory, and the surrounding repo cannot track
    its contents."""
    r = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'],
                       cwd=path, capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == 'true'
