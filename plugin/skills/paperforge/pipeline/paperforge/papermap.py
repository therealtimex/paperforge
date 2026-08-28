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
import json
from pathlib import Path

from . import assemble, citations as cite_mod, claims as claims_mod, xref


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
