#!/usr/bin/env python3
"""The gates' own rules, exercised directly.

A fixture proves the pipeline runs; it does not prove a rule refuses what it
claims to refuse. Everything here is documented behaviour - an unknown lint
pack is an error, a project profile layers over a shipped one, a deck warns
about a table nobody can read from the back of a room - reachable only by
feeding it the input a fixture never contains.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import browser, citations, deck, lint, pages, profile, verify

failures = []


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def raises(label, fn, kind=Exception):
    try:
        fn()
    except kind as e:
        print('  %-58s ok (%s)' % (label, str(e)[:26]))
        return
    print('  %-58s FAIL (no error)' % label)
    failures.append(label)


def rules_fired(text, **kw):
    return {f['rule'] for f in lint.check_text(text, **kw)}


def main():
    print('lint rules')
    core = lint.ruleset()
    check('the core applies with no packs enabled', len(core) == len(lint.CORE))
    check('a pack adds its rules',
          len(lint.ruleset(['realtimex-loops'])) == len(lint.CORE) + len(lint.PACKS['realtimex-loops']))
    raises('an unknown pack is an error, not silently ignored',
           lambda: lint.ruleset(['no-such-pack']), ValueError)
    project = lint.ruleset([], [{'id': 'codename', 'pattern': 'PROJECT BLUEBIRD',
                                 'why': 'internal codename'}])
    check('a project rule is added', any(r[0] == 'codename' for r in project))
    check('a project rule blocks by default',
          next(r[1] for r in project if r[0] == 'codename') == 'block')

    check('an unfinished marker is caught', 'todo' in rules_fired('This is a TODO item'))
    check('placeholder text is caught', 'lorem' in rules_fired('Lorem ipsum dolor'))
    check('a filename shown to a reader is caught',
          'filename-label' in rules_fired('See [`REPORT.md`](./REPORT.md)'))
    check('an unrendered footnote is caught',
          'unsupported-footnote' in rules_fired('A claim.[^1]'))
    check('a caption is a supported construct now, not a blocked one',
          'unsupported-caption' not in rules_fired(': A caption {#fig-1}'))
    check('a project rule fires',
          'codename' in rules_fired('Regarding PROJECT BLUEBIRD.', rules=project))

    fenced = 'Text.\n```\nTODO fix this sample\n```\n'
    check('a rule cannot fire inside a code sample', 'todo' not in rules_fired(fenced))
    check('the same text outside a fence does fire',
          'todo' in rules_fired(fenced, skip_code=False))
    check('a finding reports its line',
          lint.check_text('ok\nok\nTODO here')[0]['line'] == 3)

    print('cross-references')
    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / 'r.md'
        doc.write_text('Drawn in @fig-flow.\n\n```mermaid\ngraph LR\nA-->B\n```\n\n'
                       ': How it flows {#fig-flow}\n\nAnd @fig-absent is nothing.\n',
                       encoding='utf-8')
        found = lint.check_references(doc, None, profile.load('en'))
        check('a reference to a label that does not exist is blocked',
              any(f['rule'] == 'dangling-reference' and f['match'] == '@fig-absent'
                  for f in found))
        check('a reference that resolves is not reported',
              not any(f['match'] == '@fig-flow' for f in found))
        check('the finding carries the line it is on',
              all(f['line'] > 0 for f in found if f['rule'] == 'dangling-reference'))

        twice = Path(tmp) / 'twice.md'
        twice.write_text(': One {#fig-a}\n\n: Two {#fig-a}\n', encoding='utf-8')
        found = lint.check_references(twice, None, profile.load('en'))
        check('a label declared twice is blocked, because every reference '
              'would mean the first',
              any(f['rule'] == 'duplicate-label' for f in found))

    print('the publication allowlist')
    declared, blocked, embedded = {'report.md'}, {'REVIEW.md'}, {'annex.md'}
    check('a declared document passes',
          lint.check_publishable('/x/report.md', declared, blocked, embedded) == [])
    check('an embedded annex is neither publishable nor an error',
          lint.check_publishable('/x/annex.md', declared, blocked, embedded) == [])
    check('an internal file is refused',
          lint.check_publishable('/x/REVIEW.md', declared, blocked, embedded)[0]['rule']
          == 'not-publishable')
    check('an undeclared file is refused',
          lint.check_publishable('/x/stray.md', declared, blocked, embedded)[0]['rule']
          == 'undeclared')

    print('profiles')
    check('every shipped profile loads',
          all(profile.load(n).get('lang') for n in profile.available()))
    check('Vietnamese folds to a matchable form',
          profile.normalise('PHẦN III: BỐI CẢNH') == 'phan iii: boi canh')
    check('folding can be refused, because some marks are letters',
          profile.normalise('PHẦN', fold_diacritics=False) != 'phan')
    merged = profile.merge({'labels': {'figure': 'Figure %d', 'annex_badge': 'Annex'}},
                           {'labels': {'figure': 'Diagram %d'}})
    check('an override merges into a nested table, it does not replace it',
          merged['labels'] == {'figure': 'Diagram %d', 'annex_badge': 'Annex'})
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / 'profile.toml'
        local.write_text('[labels]\nfigure = "Rajah %d"\n', encoding='utf-8')
        layered = profile.load_file(local, profile.load('en'))
        check('a project profile layers over a shipped one',
              layered['labels']['figure'] == 'Rajah %d'
              and layered['structure']['contents_heading'] == 'CONTENTS')
        raises('a missing profile file is an error, not a default',
               lambda: profile.load_file(Path(tmp) / 'absent.toml', None))

    print('decks')
    source = ['## First slide', 'Body.', '', '---', '', '## Second slide',
              '> notes: say this out loud', 'More body.']
    cut = deck.slides(source)
    check('a ## heading and an explicit rule both start a slide', len(cut) == 2)
    check('a slide keeps its own body', 'Body.' in cut[0])
    body, notes = deck._notes(cut[1])
    check('speaker notes are pulled out of the slide body',
          notes == ['say this out loud'])
    check('the note is not left in the visible text',
          not any('notes:' in l for l in body))
    check('words are counted by spaces for Latin', deck.count_words('one two three') == 3)
    # ~2.2 characters carry a word, so a dense Chinese slide does not register
    # as three "words" and slip past the length check
    check('CJK is counted by character, having no word spaces',
          deck.count_words('关键矿产供应链', units='characters') == 3)
    check('the same string counted by spaces looks like one word',
          deck.count_words('关键矿产供应链') == 1)

    dense = '<section><table>%s</table></section>' % ('<tr><td>x</td></tr>' * 9)
    check('a table nobody could read from the back of a room is reported',
          any('table' in w for w in deck.audit(dense)))
    wordy = '<section><p>%s</p></section>' % ('word ' * 140)
    check('an overfull slide is reported', any('word' in w for w in deck.audit(wordy)))
    check('a reasonable slide is not reported',
          deck.audit('<section><p>Three short words</p></section>') == [])

    print('citations')
    check('a single key is found', citations.find('A claim [@nq57].') == ['nq57'])
    check('several keys in one marker are found',
          citations.find('Both [@a; @b] agree.') == ['a', 'b'])
    check('a repeated key is reported once',
          citations.find('[@a] and again [@a]') == ['a'])
    check('an email address is not a citation', citations.find('write to a@b.com') == [])
    with tempfile.TemporaryDirectory() as tmp:
        bib = Path(tmp) / 'refs.bib'
        bib.write_text('@legislation{nq57,\n  title = {A decree},\n  year = {2026},\n}\n'
                       '@report{ok,\n  title = {A report},\n  year = {2026},\n}\n',
                       encoding='utf-8')
        warned = dict(citations.dangling_dates(bib))
        check('a year-only @legislation entry is flagged for the stray comma',
              warned.get('nq57') == 'legislation')
        check('@report with the same year is not flagged', 'ok' not in warned)
        check('the warning can be limited to the keys actually cited',
              citations.dangling_dates(bib, {'ok'}) == [])

    print('structural checks on a document built to be broken')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'report.md'
        src.write_text('# T\n## Title\n\n---\n\n'
                       'A sentence that reaches the rendered page unchanged.\n\n'
                       'A second sentence that the renderer will lose entirely.\n',
                       encoding='utf-8')
        page = Path(tmp) / 'report.html'
        page.write_text(
            '<html><body><main>'
            '<h2 id="one">Title</h2>'
            '<p>A sentence that reaches the rendered page unchanged.</p>'
            '<a href="#nowhere">a reference to nothing</a>'
            '<img src="https://example.com/logo.png">'
            '<b><i>crossed</b></i>'
            '</main></body></html>', encoding='utf-8')
        r = verify.check(page, src)
        check('crossed tags are reported',
              any('expected </i>, got </b>' in e for e in r['markup_errors']))
        check('an anchor pointing nowhere is reported', r['broken_anchors'] == ['nowhere'])
        check('a network reference is reported', r['external_refs'] == ['https://example.com/logo.png'])
        check('a source line that never reached the page is reported',
              any('second sentence' in m[2] for m in r['missing_content']))
        check('a line that did reach the page is not reported',
              not any('reaches the rendered page' in m[2] for m in r['missing_content']))

        page.write_text('</p><html><body><main><p>text</p></main></body></html>',
                        encoding='utf-8')
        check('a closing tag with nothing open is reported as stray',
              any('stray' in e for e in verify.check(page, src)['markup_errors']))
        page.write_text('<html><body><main><div><p>text', encoding='utf-8')
        left = verify.check(page, src)['unclosed']
        check('tags left open at the end of the file are reported',
              {'div', 'p'} <= set(left))
        page.write_text('<html><body><main><p>text</p></main></body></html>', encoding='utf-8')
        clean = verify.check(page, src)
        check('a well-formed document reports nothing',
              not clean['markup_errors'] and not clean['unclosed'])

    print('raw markup that reached the page')
    check('an unrendered tag is a leak',
          any(l['match'] == '<br>' for l in verify.leaks('a TRỊ<br>(Verified)')))
    check('a real HTML entity is a leak',
          any(l['match'] == '&nbsp;' for l in verify.leaks('a&nbsp;b')))
    check('a numeric entity is a leak', any(l['kind'] == 'entity' for l in verify.leaks('a&#160;b')))
    check('"KH&CN;" is prose, not an entity', verify.leaks('KH&CN; and R&D; costs') == [])
    check('"<10%" and ">55" are prose, not tags', verify.leaks('Nhóm 2: <10% and >55–60%') == [])
    check('unrendered emphasis is a leak', any(l['kind'] == 'emphasis' for l in verify.leaks('a **b**')))

    print('branding')
    from paperforge import markdown as md
    prof = profile.load('en')
    plain = md.theme_override(prof, None)
    check('an unbranded project gets the profile fonts and no palette',
          '--serif' in plain and '--navy' not in plain)
    branded = md.theme_override(prof, {'navy': '#5b2333', 'bg': '#f7f4ef'})
    check('a declared palette is emitted as tokens',
          '--navy: #5b2333' in branded and '--bg: #f7f4ef' in branded)
    housed = md.theme_override(prof, {'serif': 'Palatino, serif'})
    check('a project may name its own face, overriding the profile',
          '--serif: Palatino, serif' in housed)
    check('and the profile still supplies the one it did not name',
          '--sans' in housed)

    with tempfile.TemporaryDirectory() as tmp:
        mark = Path(tmp) / 'mark.svg'
        mark.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                        '<rect width="10" height="10"/></svg>', encoding='utf-8')
        tag = md.logo_tag(mark)
        check('an SVG mark is inlined as markup, not linked',
              '<svg' in tag and 'src=' not in tag)
        raster = Path(tmp) / 'mark.png'
        raster.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0' * 40)
        check('any other format is inlined as a data URI',
              'data:image/png;base64,' in md.logo_tag(raster))
        check('a mark that is not there is not a broken image',
              md.logo_tag(Path(tmp) / 'absent.svg') == '')

    print('locating the contents in a printed PDF')
    # These two guards were added after a real defect: with every contents entry
    # shorter than the length filter, the search scored every page zero and
    # returned the cover, exempting the wrong page from the near-empty check.
    toc = '<h2 id="contents">CONTENTS</h2><ol><li>1. Context</li>' \
          '<li>2. Sources and method</li><li>3. Conclusions drawn</li></ol><h2 id="x">X</h2>'
    body = ['cover page only', 'contents 1. context 2. sources and method 3. conclusions drawn',
            'context the body of the report begins here']
    check('the contents page is found, not the cover',
          pages.contents_pages([pages.norm(t) for t in body], toc, 'contents') == {1})
    short = '<h2 id="contents">CONTENTS</h2><ol><li>1. A</li><li>2. B</li></ol><h2 id="x">X</h2>'
    found = pages.contents_pages([pages.norm(t) for t in
                                  ['cover', 'contents 1. a 2. b', 'a the body']], short, 'contents')
    check('entries too short for the length filter still locate the contents', found == {1})
    empty = '<h2 id="contents">CONTENTS</h2><ol></ol><h2 id="x">X</h2>'
    check('a contents with no entries exempts nothing rather than guessing',
          pages.contents_pages([pages.norm(t) for t in body], empty, 'contents') == set())
    check('a contents that cannot be located exempts nothing',
          pages.contents_pages([pages.norm('unrelated text'), pages.norm('more prose')],
                               toc, 'contents') == set())

    print('finding a browser')
    real_which = browser.shutil.which
    try:
        browser.shutil.which = lambda name: '/usr/bin/%s' % name if name == 'chromium' else None
        check('a browser on PATH is used', browser.chrome() == '/usr/bin/chromium')
        browser.shutil.which = lambda name: None
        real_candidates = browser.CANDIDATES
        browser.CANDIDATES = []
        try:
            browser.chrome()
            check('no browser anywhere is an error, not a silent blank render', False)
        except RuntimeError:
            check('no browser anywhere is an error, not a silent blank render', True)
        finally:
            browser.CANDIDATES = real_candidates
    finally:
        browser.shutil.which = real_which

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\ngates: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
