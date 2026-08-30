#!/usr/bin/env python3
"""An image as a figure: found, numbered, inlined, or refused.

This whole path existed as documentation and nothing else. `![alt](src)` was
matched by the link pattern, which took the bracket half and left the bang
behind as text; the caption under it was consumed by nothing and printed to the
reader with its `{#fig-x}` braces showing; and `@fig-x` still resolved to a
number for a float that was never on the page. Every gate passed.

So the tests here are mostly about what must now *fail*, and about the one
number that has to stay right: a figure's ordinal counts floats, while the
diagram raster index counts diagrams, and an image between two diagrams drew
the wrong one while those were the same counter.
"""
import base64
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docx import Document

from paperforge import docx as docx_mod
from paperforge import images, lint, markdown, profile, typst, verify, xref

failures = []

# an 8x8 PNG; small enough to read in a diff, real enough to be inlined
PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAJUlEQVR42mNkYPhfz0AEYBxV'
    'SF+FjIyM/4nRODwUDr9UM2wUAgB+ZQ8B4c1WcgAAAABJRU5ErkJggg==')
SVG = '<svg viewBox="0 0 10 10" style="max-width:10px"><g/></svg>'


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def rules(found):
    return {(f['rule'], f['severity']) for f in found}


def render(lines, root, svgs=(), prof=None):
    """Drive the HTML emitter the way build() does, without a whole project."""
    prof = prof or profile.load('en')
    markdown.PROF = prof
    markdown.SVGS[:] = list(svgs)
    markdown.SRC['dir'] = Path(root)
    markdown.XREF.clear()
    markdown.XREF.update(xref.resolve(prof, lines))
    markdown.FIG.update(n=0, base=0, dgm=0, label=prof['labels']['figure'])
    return markdown.convert(lines, [])


def document(root, body, name='doc.md'):
    path = Path(root) / name
    path.write_text('\n'.join(body), encoding='utf-8')
    return {'source_path': str(path), 'include_paths': (), 'annex_path': None}


def main():
    print('reading image references out of a source')
    lines = ['text ![one](a.png) more', '', '![two](b/c.svg)', '',
             '```', '![not this](d.png)', '```']
    found = images.refs(lines)
    check('both real references are found, in order',
          [(n, s) for n, _, s in found] == [(1, 'a.png'), (3, 'b/c.svg')])
    check('a reference inside a fence is code, not an image', len(found) == 2)

    print('resolving a path')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'figures').mkdir()
        (root / 'figures' / 'f.png').write_bytes(PNG)
        check('relative to the document, not the working directory',
              images.resolve('figures/f.png', root) == root / 'figures' / 'f.png')
        check('a path with no file resolves to nothing',
              images.resolve('figures/gone.png', root) is None)
        check('a remote src resolves to nothing rather than being fetched',
              images.resolve('https://example.com/f.png', root) is None)
        check('a protocol-relative src is remote too',
              images.resolve('//example.com/f.png', root) is None)
        uri = images.data_uri(root / 'figures' / 'f.png')
        check('the file is carried in the document, not linked',
              uri.startswith('data:image/png;base64,')
              and base64.b64decode(uri.split(',', 1)[1]) == PNG)

    print('an image on its own line is a figure')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'f.png').write_bytes(PNG)
        body = ['## Findings {#sec-f}', '', 'See @fig-photo.', '',
                '![A field](f.png)', '', ': A salinity-affected field. {#fig-photo}']
        html = render(body, root)
        check('it renders as a figure, anchored on its label',
              '<figure class="diagram plate" id="fig-photo">' in html)
        check('the picture is inlined, not linked',
              'src="data:image/png;base64,' in html)
        check('the caption is consumed and numbered',
              '<figcaption>Figure 1. A salinity-affected field.' in html)
        check('the caption does not also print as prose',
              '{#fig-photo}' not in html and '<p>: A' not in html)
        check('no literal bang survives into the page', '!<a href' not in html)
        check('the reference resolves to the figure', 'See Figure 1.' in html)

        print('an image inside a sentence stays inside the sentence')
        html = render(['Some prose ![a mark](f.png) mid-line.'], root)
        check('it renders as an image', '<img src="data:image/png' in html)
        check('and not as a bang and a link', '!<a href' not in html)
        check('and does not become a figure', 'figcaption' not in html)

        print('a float ordinal counts floats; a raster index counts diagrams')
        body = ['![A field](f.png)', '', ': The photograph. {#fig-photo}', '',
                '```mermaid', 'graph TD', 'A-->B', '```', '',
                ': The diagram. {#fig-flow}']
        html = render(body, root, svgs=[SVG])
        check('the image is Figure 1', '<figcaption>Figure 1. The photograph.' in html)
        check('the diagram after it is Figure 2',
              '<figcaption>Figure 2. The diagram.' in html)
        check('the diagram still draws the first rendered SVG', SVG in html)
        check('the diagram count is diagrams, not floats', markdown.FIG['dgm'] == 1)

        print('a missing file leaves a visible gap, never a silent one')
        html = render(['![A field](gone.png)'], root)
        check('the gap says what is missing',
              'image not found: gone.png' in html)
        check('nothing pretends to be an image', '<img' not in html)

    print('lint refuses what the build cannot honour')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'f.png').write_bytes(PNG)
        doc = document(root, ['![here](f.png)', '', ': A caption. {#fig-a}', '',
                              'Text about @fig-a.'])
        check('a resolved image with an attached caption is clean',
              lint.check_images(doc) == [] and lint.check_captions(doc) == [])

        doc = document(root, ['![gone](missing.png)'], 'b.md')
        check('a missing file blocks',
              rules(lint.check_images(doc)) == {('missing-image', 'block')})

        doc = document(root, ['![remote](https://example.com/f.png)'], 'c.md')
        check('a remote image blocks',
              rules(lint.check_images(doc)) == {('remote-image', 'block')})

        doc = document(root, ['Just prose here.', '', ': A caption. {#fig-a}', '',
                              'And @fig-a points at it.'], 'd.md')
        found = lint.check_captions(doc)
        check('a caption under prose blocks',
              rules(found) == {('stray-caption', 'block')})
        check('and it is reported on its own line',
              found and found[0]['line'] == 3)
        check('the older checks cannot see it: the label exists and is used',
              lint.check_references(doc, profile.load('en')) == [])

    print('what may carry a caption')
    slots = xref.attached_captions(
        ['```mermaid', 'graph TD', '```', '', ': one {#fig-a}', '',
         '| a | b |', '|---|---|', '| 1 | 2 |', ': two {#tbl-a}', '',
         '![x](y.png)', '', ': three {#fig-b}', '',
         '- a list item', '', ': four {#fig-c}'])
    check('a diagram may', 4 in slots)
    check('a table may', 9 in slots)
    check('an image may', 13 in slots)
    check('a list may not', 17 not in slots)

    print('coverage does not ask a picture to be text')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'f.png').write_bytes(PNG)
        src = root / 'doc.md'
        src.write_text('![A photograph of a salinity-affected field](f.png)\n',
                       encoding='utf-8')
        html = root / 'doc.html'
        html.write_text('<html><body><figure><img src="data:image/png;base64,x">'
                        '</figure></body></html>', encoding='utf-8')
        check('an image line is not reported as missing content',
              verify.coverage(str(html), str(src)) == [])

    print('the print edition sets the image, rather than deleting it')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'f.png').write_bytes(PNG)
        typst.SRC['dir'] = root
        typst.PLATES.clear()
        typst.FLOATS.clear()
        body = ['![A field](f.png)', '', ': The photograph. {#fig-a}']
        typst.XREF.clear()
        typst.XREF.update(xref.resolve(profile.load('en'), body))
        out = typst.convert(body, {}, [], 'Figure %d')
        check('a block image becomes a Typst figure', '#figure(image("plate-0.png"' in out)
        check('its caption travels with it', 'The photograph' in out)
        check('and the file is registered to be copied beside the source',
              [n for n, _ in typst.PLATES] == ['plate-0.png'])

        (root / 'chart.svg').write_text('<svg viewBox="0 0 10 10"/>', encoding='utf-8')
        typst.PLATES.clear()
        typst.FLOATS.clear()
        typst.convert(['![A chart](chart.svg)'], {}, [], 'Figure %d')
        check('an SVG is rasterised for print, not placed as vector',
              [n for n, _ in typst.PLATES] == ['plate-0-0.png'])

        typst.PLATES.clear()
        typst.FLOATS.clear()
        out = typst.convert(['Prose with ![a mark](f.png) in it.'], {}, [], 'Figure %d')
        check('an inline image is set in the line', '#box(image("plate-0.png"' in out)
        check('and is not counted as a figure', typst.FLOATS == [])

        typst.PLATES.clear()
        typst.FLOATS.clear()
        out = typst.convert(['![A field](gone.png)'], {}, [], 'Figure %d')
        check('a missing file does not reach the Typst source',
              'image(' not in out and 'image not found' in out)

    print('the Word edition places the picture, and not over a diagram')
    calls = []
    real = typst.browser.run
    typst.browser.run = lambda args, **kw: calls.append(
        next(a for a in args if a.startswith('--screenshot=')))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            typst.rasterise(['<svg viewBox="0 0 10 10"/>'], Path(tmp), prefix='mark')
            check('the project mark rasterises under its own name, not fig-0.png',
                  calls and calls[0].endswith('mark-0.png'))
    finally:
        typst.browser.run = real

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'f.png').write_bytes(PNG)
        docx_mod.SRC['dir'] = root
        docx_mod.WORK['dir'] = None
        docx_mod.FLOATS.clear()
        doc = Document()
        figures = []
        docx_mod.convert(doc, ['![A field](f.png)', '', ': The photograph. {#fig-a}'],
                         figures, 'Figure %d', {}, {},
                         table=xref.resolve(profile.load('en'),
                                            ['![A field](f.png)', '',
                                             ': The photograph. {#fig-a}']))
        check('a picture is placed in the .docx',
              any('image' in r.reltype for r in doc.part.rels.values()))
        check('with its caption under it',
              any('The photograph' in p.text for p in doc.paragraphs))
        check('and it is not counted as a diagram', figures == [])

    print()
    if failures:
        print('%d check(s) failed' % len(failures))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
