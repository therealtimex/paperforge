"""The map of a document: what it declares, and what points at what.

Nobody reads a repository into a model's context. It is parsed, and what gets
sent is a map of symbols - files, functions, signatures, and which calls which.
A paper has structure too, and most of it is already declared: sections,
figures, tables, equations, citations. What it usually lacks is a map of the
paragraph-level claims that behave like functions, stated in one place and
drawn on in another.

Everything here is read from the source. Sections and floats come from the
label table; a claim's edges come from the references and citations inside its
own paragraph, plus whatever `uses=` its author declared. Nothing is inferred
and nothing is summarised: a gist is the one thing on this page written by a
person, and it is stored, checked and printed, never generated.

Some of what it reports is deliberately not a gate. A claim nothing uses is
usually the finding - resting on everything below it, supporting nothing above
- so a refusal for it would fire on every correct paper. It is a line in a
report instead, where a reader decides what it means.
"""
import html as ihtml
import json
from pathlib import Path

from . import assemble, citations as cite_mod, claims as claims_mod, palette, xref

THEME = Path(__file__).parent / 'theme'


def _headings(lines):
    """(line, depth, title, id or None) for every heading, in order."""
    out = []
    for i, line in enumerate(lines):
        m = xref.HEADING_RE.match(line.strip())
        if not m:
            continue
        title, ident = m.group(2), None
        attrs = xref.ATTR_RE.search(title)
        if attrs:
            found = xref.SEC_ID_RE.search(attrs.group(1))
            ident = found.group(1) if found else None
            title = title[:attrs.start()].rstrip()
        out.append((i + 1, len(m.group(1)), title, ident))
    return out


def _section_at(heads, line):
    """The heading a line sits under, by its id if it has one, else its words."""
    here = [h for h in heads if h[0] <= line]
    return (here[-1][3] or here[-1][2]) if here else None


def build(document, prof=None):
    """The map of one document, as data."""
    body = assemble.read(document['source_path'],
                         document.get('include_paths')).split('\n')
    annex = document.get('annex_path')
    annex_lines = Path(annex).read_text(encoding='utf-8').split('\n') if annex else []
    table = xref.resolve(prof or {}, body, annex_lines)

    referenced = set()
    for lines in (body, annex_lines):
        for line in lines:
            referenced.update(m.group(1) for m in xref.REF_RE.finditer(line))

    heads = _headings(body) + [(n + len(body), d, t, i)
                               for n, d, t, i in _headings(annex_lines)]
    sections = [{'id': ident, 'title': title, 'line': n, 'depth': depth}
                for n, depth, title, ident in heads]

    floats = [{'id': ident, 'kind': e['kind'], 'label': e['label'],
               'caption': e.get('caption') or '', 'line': e['line'] + 1,
               'used_by': []}
              for ident, e in sorted(table.items()) if e['kind'] in xref.NUMBERED]

    claims, offset = {}, 0
    for lines in (body, annex_lines):
        for ident, rec in claims_mod.find(lines).items():
            line = rec['line'] + offset
            claims[ident] = {'id': ident, 'gist': rec['gist'], 'line': line,
                             'section': _section_at(heads, line),
                             'uses': claims_mod.edges(rec), 'used_by': []}
        offset = len(body)

    by_id = {f['id']: f for f in floats}
    for ident, claim in sorted(claims.items()):
        for target in claim['uses']:
            if target in claims:
                claims[target]['used_by'].append(ident)
            elif target in by_id:
                by_id[target]['used_by'].append(ident)

    notes = []
    for ident, claim in sorted(claims.items()):
        if claim['gist'] is None:
            notes.append({'rule': 'no-gist', 'id': ident,
                          'why': 'nothing said about what this paragraph is for'})
        if not claim['used_by']:
            # not a defect: the paper's finding rests on everything and
            # supports nothing, which is why this is a note and not a gate
            notes.append({'rule': 'nothing-uses-it', 'id': ident,
                          'why': 'nothing draws on this; the finding, or a leftover'})
    for entry in floats:
        if entry['id'] not in referenced:
            notes.append({'rule': 'never-referred-to', 'id': entry['id'],
                          'why': 'declared and printed, mentioned in no prose'})

    return {'document': Path(document['source_path']).name,
            'sections': sections, 'floats': floats,
            'claims': [claims[k] for k in sorted(claims)],
            'citations': sorted(set(cite_mod.find('\n'.join(body + annex_lines)))),
            'notes': notes}


def render(maps):
    """The map as something a person reads, one block per document."""
    out = []
    for m in maps:
        out.append(m['document'])
        for section in m['sections']:
            # a labelled heading is named by its id, with the words after it;
            # an unlabelled one has only its words, and no trailing gap
            name = section['id'] or section['title']
            said = ('  ' + section['title']) if section['id'] else ''
            out.append('%s%s%s' % ('  ' * (section['depth'] - 1), name, said))
            for claim in m['claims']:
                if (claim['section'] or '') != (section['id'] or section['title']):
                    continue
                out.append('  ' * section['depth'] + claim['id'])
                out.append('  ' * (section['depth'] + 1) + 'gist:    %s'
                           % (claim['gist'] or '-'))
                if claim['uses']:
                    out.append('  ' * (section['depth'] + 1) + 'uses:    %s'
                               % ', '.join(claim['uses']))
                if claim['used_by']:
                    out.append('  ' * (section['depth'] + 1) + 'used-by: %s'
                               % ', '.join(claim['used_by']))
        for entry in m['floats']:
            out.append('%s  %s' % (entry['id'],
                                   entry['caption'] or entry['label']))
            if entry['used_by']:
                out.append('  used-by: %s' % ', '.join(entry['used_by']))
        if m['citations']:
            out.append('cites: %s' % ', '.join(m['citations']))
        for note in m['notes']:
            out.append('note: %-20s %s  (%s)' % (note['rule'], note['id'], note['why']))
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def as_json(maps):
    return json.dumps(maps, indent=2, ensure_ascii=False) + '\n'


def _link(ident):
    """An edge as something a reader can follow. A citation key has no anchor
    on this page - there is no entry here to jump to - so it stays plain."""
    if ident.startswith('@'):
        return '<span class="cite">%s</span>' % ihtml.escape(ident)
    return '<a class="ref" href="#%s">%s</a>' % (ihtml.escape(ident), ihtml.escape(ident))


def _edges(claim):
    out = []
    for key, name in (('uses', 'uses'), ('used_by', 'used by')):
        if claim[key]:
            out.append('<span class="edge"><b>%s</b> %s</span>'
                       % (name, ', '.join(_link(i) for i in claim[key])))
    return ''.join(out)


def _claim(claim):
    """One claim, wherever it sits. Both callers go through here: the first
    version rendered the gist only for claims under a heading, so a claim
    written before the first one silently lost the sentence a person wrote."""
    gist = ('<span class="gist">%s</span>' % ihtml.escape(claim['gist'])
            if claim['gist'] else
            '<span class="gist absent">nothing said about this one</span>')
    return ('<div class="claim" id="%s"><span class="id">%s</span>%s%s</div>'
            % (ihtml.escape(claim['id']), ihtml.escape(claim['id']),
               gist, _edges(claim)))


def page(m, prof=None, brand=None, subtitle='', footer=''):
    """The map as a self-contained page.

    Structure is rendered whether or not the document has any claims. Most do
    not yet, and a map of sections, floats and citations is still a map of the
    document's machinery - what it would not be is a reason to publish one.
    """
    from . import markdown as md
    prof = prof or {}
    body, by_section = [], {}
    for claim in m['claims']:
        by_section.setdefault(claim['section'], []).append(claim)

    body.append('<h2>Structure</h2>')
    for section in m['sections']:
        key = section['id'] or section['title']
        ident = ' id="%s"' % ihtml.escape(section['id']) if section['id'] else ''
        name = ihtml.escape(section['id'] or section['title'])
        said = ('<span class="words">%s</span>' % ihtml.escape(section['title'])
                if section['id'] else '')
        body.append('<p class="section depth-%d"%s><a href="#%s">%s</a> %s</p>'
                    % (min(section['depth'], 4), ident, ihtml.escape(key), name, said))
        for claim in by_section.get(key, ()):
            body.append(_claim(claim))

    orphaned = by_section.get(None, [])
    if orphaned:
        body.append('<h2>Before any heading</h2>')
        for claim in orphaned:
            body.append(_claim(claim))

    if m['floats']:
        body.append('<h2>Figures, tables and equations</h2>')
        for entry in m['floats']:
            used = ('<span class="edge">used by %s</span>'
                    % ', '.join(_link(i) for i in entry['used_by'])) if entry['used_by'] else ''
            body.append('<div class="float" id="%s"><span class="label">%s</span>'
                        '<span class="caption">%s</span>%s</div>'
                        % (ihtml.escape(entry['id']), ihtml.escape(entry['label']),
                           ihtml.escape(entry['caption']), used))

    if m['citations']:
        body.append('<h2>Cited</h2><p class="cites">%s</p>'
                    % ', '.join(ihtml.escape(c) for c in m['citations']))

    if m['notes']:
        body.append('<h2>Worth a look</h2>')
        for note in m['notes']:
            body.append('<div class="note"><span class="rule">%s</span> %s '
                        '<span class="why">%s</span></div>'
                        % (ihtml.escape(note['rule']), _link(note['id']),
                           ihtml.escape(note['why'])))

    shell = (THEME / 'map.html').read_text(encoding='utf-8')
    filled = {
        'LANG': prof.get('lang', 'en'),
        'DIR': prof.get('direction', 'ltr'),
        'TITLE': ihtml.escape(m['document']),
        'SUBTITLE': ihtml.escape(subtitle),
        'FOOTER': ihtml.escape(footer),
        'THEME_CSS': (palette.stylesheet(THEME / 'map.css')
                      + '\n' + md.theme_override(prof, brand)),
        'BODY': '\n'.join(body),
    }
    for key, value in filled.items():
        shell = shell.replace('{{%s}}' % key, value)
    return shell


def emit(document, output, prof=None, brand=None, subtitle='', footer=''):
    """Build the map and write it. Returns what it put on the page."""
    m = build(document, prof)
    Path(output).write_text(page(m, prof, brand, subtitle, footer), encoding='utf-8')
    return {'sections': len(m['sections']), 'floats': len(m['floats']),
            'claims': len(m['claims']), 'notes': len(m['notes'])}
