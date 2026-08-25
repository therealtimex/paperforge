"""One document from several files.

A report is one file. A thesis is chapters, and a 200-page markdown file is
neither editable by a human nor reviewable in a diff. The annex mechanism was
already a limited form of this - one extra file, appended, with its own title
and its own figure numbering - so generalising it costs little.

An included file is **body markdown**: a fragment of one document, not a
document. It carries no front matter and no title of its own, and the pieces
are concatenated in declared order before anything parses them. That matters
more than it sounds: cross-references, figure numbers and the contents have to
see the whole work, and they can only do that if there is only ever one text.
"""
from pathlib import Path

SEPARATOR = '\n\n'


def read(source, includes=()):
    """The document body: `source`, then each include in declared order."""
    text = Path(source).read_text(encoding='utf-8').replace('\r\n', '\n')
    for path in includes or ():
        part = Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')
        text = text.rstrip('\n') + SEPARATOR + part.lstrip('\n')
    return text


def sources(document):
    """Every file that makes up a document, in order, annex last.

    Used by everything that reads "the source": lint, the coverage check, the
    reference and front-matter gates, and the run record. A document assembled
    from five files whose provenance records one of them is a record that lies.
    """
    found = [document['source_path']]
    found += list(document.get('include_paths') or [])
    if document.get('annex_path'):
        found.append(document['annex_path'])
    return [p for p in found if p]


def problems(source, includes=()):
    """Includes that cannot be read, or that carry their own front matter."""
    found = []
    for path in includes or ():
        path = Path(path)
        if not path.exists():
            found.append('included file not found: %s' % path.name)
            continue
        head = path.read_text(encoding='utf-8').lstrip().split('\n', 1)[0].strip()
        if head == '+++':
            found.append('%s opens with front matter; an included file is a '
                         'fragment of one document, and only the source carries '
                         'the head' % path.name)
    if Path(source) in [Path(p) for p in includes or ()]:
        found.append('the source is also listed as an include, so it would be '
                     'assembled twice')
    return found
