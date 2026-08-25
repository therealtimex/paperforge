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
{invocation} status   # what is built, linked, published
{invocation} all      # figures -> lint -> build -> verify -> publish
{invocation} all --only <source.md>
{invocation} brief    # what this project declares, regenerated from the manifest
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


# A book is chapters, in files. Scaffolding one as a single markdown file
# would teach the opposite of what assembling.md exists to say - and the first
# thing anyone does with a scaffold is copy its shape.
#
# The file name and the heading travel together because the contents entry and
# the chapter heading have to be the same string: if they diverge, nothing in
# the contents gets numbered and `all` says so.
CHAPTERS = (('ch01', 'section_one', 'Context'),
            ('ch02', 'section_two', 'Findings'),
            ('ch03', 'conclusion', 'Conclusion'))


def chapter_titles(prof):
    """(file kind, heading) for each chapter a scaffolded book opens with."""
    s = prof.get('scaffold', {})
    return [(kind, s.get(key, fallback)) for kind, key, fallback in CHAPTERS]


def book(prof, title, publisher, when):
    """The cover and the contents. Every chapter is a file of its own."""
    contents = prof['structure'].get('contents_heading', 'CONTENTS')
    out = ['# %s' % prof['labels'].get('document', 'DOCUMENT'), '## %s' % title, '',
           '---', _meta_block(prof, publisher, when), '---', '',
           '## %s' % contents, '']
    out += ['%d. **%s**' % (i, heading)
            for i, (_, heading) in enumerate(chapter_titles(prof), 1)]
    out += ['', '---', '']
    return '\n'.join(out)


def chapter(prof, heading):
    """One chapter: body markdown, carrying no front matter and no title page.

    `{.part}` explicitly rather than by pattern, for the reason structure.md
    gives - a scaffolded project should not depend on a profile's part_banner
    matching headings the project chose.
    """
    prose = prof.get('scaffold', {}).get('prose',
                                         'Replace this paragraph with the substance of the section.')
    return '\n'.join(['## %s {.part}' % heading, '', prose, '', prose, ''])


def annex(prof, title, publisher, when):
    s = prof.get('scaffold', {})
    prose = s.get('prose', 'Replace this paragraph with the substance of the section.')
    return '\n'.join(['# %s' % prof['labels'].get('annex_badge', 'Annex'),
                      '## %s' % title, '', _meta_block(prof, publisher, when), '---', '',
                      '## 1. %s' % s.get('sources', 'Sources'), '', prose, ''])


# chapters are deliberately absent: they are part of a book, not a
# publication type anyone can ask for
BUILDERS = {'report': report, 'book': book, 'brief': brief, 'deck': deck,
            'annex': annex}


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
        if kind == 'book':
            # the type already carries page_numbers, the trim and the binding;
            # repeating them would be a generated file arguing with itself,
            # because a type overrides the document that declares it
            lines.append('  pdf = "typst"             # a bound edition: Chrome '
                         'cannot open a chapter on a recto')
        elif kind == 'report':
            lines.append('  page_numbers = true')
            lines.append('  # contents_heading comes from the profile; override only if it differs')
        else:
            lines.append('  page_numbers = false')
        if multi:
            lines.append('')
            for lang in languages:
                lines += ['    [collection.document.%s]' % lang,
                          '    source = "%s"' % source_name(slug, kind, lang, multi)]
                if kind == 'book':
                    lines.append(_include_list(slug, lang, multi, '    '))
                if kind in ('report', 'book') and has_annex:
                    lines.append('    annex = "%s"      # embedded inline, not published alone'
                                 % source_name(slug, 'annex', lang, multi))
                lines += ['    publish = false        # flip to true when this edition is ready', '']
        else:
            lines.append('  source = "%s"' % source_name(slug, kind, languages[0], multi))
            if kind == 'book':
                lines.append(_include_list(slug, languages[0], multi, '  '))
            if kind in ('report', 'book') and has_annex:
                lines.append('  annex = "%s"      # embedded inline, not published alone'
                             % source_name(slug, 'annex', languages[0], multi))
            lines += ['  publish = false           # flip to true when the document is ready', '']

    lines += ['[internal]',
              '# Never publishable. Add process records here as they appear.',
              'files = []',
              'reason = "process records: review, editorial notes, approvals"', '']
    return '\n'.join(lines)


def _include_list(slug, language, multi, indent):
    """The chapters, in reading order. Order is the whole meaning of the key:
    the pieces are concatenated before anything parses them."""
    names = [source_name(slug, kind, language, multi) for kind, _, _ in CHAPTERS]
    pad = ' ' * (len(indent) + len('include = ['))
    return indent + 'include = [' + (',\n' + pad).join('"%s"' % n for n in names) + ']'


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
    # the real entry point, not a placeholder: a scaffolded project that
    # tells you to run `<paperforge>/bin/paperforge` tells you nothing
    import sys
    # absolute: a relative entry point is only valid from wherever the
    # scaffolding happened to be run, which is not where the project lives
    invocation = str(Path(sys.argv[0]).resolve()) if sys.argv and sys.argv[0] else 'paperforge'
    (root / 'AGENTS.md').write_text(AGENTS.format(title=title, invocation=invocation),
                                    encoding='utf-8')
    written += ['figures.toml', '.gitignore', 'AGENTS.md']

    for language in languages:
        prof = profiles[language]
        when = date.today().strftime(prof.get('scaffold', {}).get('date_format', '%m/%Y'))
        for kind in publications:
            name = source_name(slug, kind, language, multi)
            (root / name).write_text(BUILDERS[kind](prof, title, publisher, when),
                                     encoding='utf-8')
            written.append(name)
            if kind != 'book':
                continue
            for chapter_kind, heading in chapter_titles(prof):
                chapter_name = source_name(slug, chapter_kind, language, multi)
                (root / chapter_name).write_text(chapter(prof, heading), encoding='utf-8')
                written.append(chapter_name)

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
