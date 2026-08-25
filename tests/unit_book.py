#!/usr/bin/env python3
"""A book is a report that has been made into an object.

Four conventions separate the two, and none of them is visible in a one-page
test: a chapter opens on the right-hand leaf, the leaf skipped to put it there
is bare, the running head names the book on the left and the chapter on the
right, and the front matter numbers in roman while the book proper restarts at
arabic one.

The fourth thing this covers is the check that guards the first. A running head
puts the chapter title at the top of every recto in the chapter, and the gate
comparing the two editions asks which headings open a page by reading the top of
each page. It cannot tell an opening from a running head, so it goes on
reporting success over text that says nothing about what it was written to
guard - the recurring defect in this pipeline, in a new place.

Needs typst and pdfplumber.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import cli, editions, profile, typst

failures = []


def check(label, condition):
    print('  %-64s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


# Built through typst.build, not through a hand-written preamble: the crop that
# separates a running head from the body is a claim about where the emitter puts
# them, and a stripped-down test document with none of the real heading styling
# would prove it about a layout Paperforge never produces.
FILLER = (
    'A page in a bound book is one side of a leaf, and the leaf has another '
    'side, and the two are held together at an edge that vanishes into the '
    'binding. Every decision about the page follows from that physical fact. '
    'A renderer treating the page as a rectangle of text produces something '
    'that reads correctly and looks wrong to anybody holding it. ')


def book_project(root, chapter_one_pages=3):
    """A minimal book: cover, contents, two chapters marked as parts."""
    body = '\n\n'.join([FILLER * 6] * (4 * chapter_one_pages))
    (root / 'book.md').write_text('\n'.join([
        '# A PAPERFORGE MONOGRAPH',
        '## Setting a Book',
        '',
        '---',
        '**Author:** Paperforge Press',
        '',
        '---',
        '',
        '## CONTENTS',
        '',
        '1. **Chapter One**',
        '2. **Chapter Two**',
        '',
        '## Chapter One {.part}',
        '',
        body,
        '',
        '## Chapter Two {.part}',
        '',
        FILLER,
        '']), encoding='utf-8')
    return root / 'book.md'


# The folio and the running head sit inside the top and bottom margins; the
# body's first baseline sits just below the top one. Classifying at exactly the
# margin therefore reads the first line of body text as a running head, so the
# bands used to *read* the page are drawn a little inside the ones used to
# *crop* it.
HEAD = typst.HEADER_BAND - 6
FOOT = 45


def read(pdf_path):
    """Each leaf as head, folio, body words and inside margin, in order."""
    import pdfplumber
    leaves = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            body = [w for w in words if HEAD <= w['top'] <= page.height - FOOT]
            leaves.append({
                'head': ' '.join(w['text'] for w in words if w['top'] < HEAD),
                'folio': ' '.join(w['text'] for w in words
                                  if w['top'] > page.height - FOOT),
                'body': [w['text'] for w in body],
                'inside': min([w['x0'] for w in body], default=None),
                'width': page.width, 'height': page.height})
    return leaves


def main():
    # --- what the manifest is allowed to ask for --------------------------
    check('a document is unbound by default', cli.binding_of({}) is False)
    check('binding = true is accepted', cli.binding_of({'binding': True}) is True)
    check('the book type is bound and not A4',
          cli.BUILTIN_TYPES['book']['binding'] is True
          and cli.BUILTIN_TYPES['book']['trim'] == 'royal')
    check('a book prints page numbers and lays out as a report',
          cli.BUILTIN_TYPES['book']['page_numbers'] is True
          and cli.BUILTIN_TYPES['book']['layout'] == 'report')

    for bad in ('letter', 'A4', '', 'royal-octavo'):
        try:
            cli.binding_of({'source': 'x.md', 'trim': bad})
            check('trim = %r is refused' % bad, False)
        except SystemExit as err:
            check('trim = %r is refused, and the message lists the trims' % bad,
                  'royal' in str(err) and 'b5' in str(err))
    try:
        cli.binding_of({'source': 'x.md', 'binding': True, 'format': 'deck'})
        check('a bound deck is refused', False)
    except SystemExit as err:
        check('a bound deck is refused', 'slide' in str(err))
    try:
        cli.binding_of({'source': 'x.md', 'binding': True, 'pdf': 'chrome'})
        check('a bound document printed by Chrome is refused', False)
    except SystemExit as err:
        # the refusal has to say which half Chrome fails, because it does the
        # other half convincingly - the trim and the mirrored margins come out
        check('the Chrome refusal names recto and the running head',
              'recto' in str(err) and 'running head' in str(err))
    check('an unbound document may still be printed by Chrome',
          cli.binding_of({'pdf': 'chrome'}) is False)

    # --- the markup the emitter produces ----------------------------------
    bound = typst.running_head('T', 'Org', True)
    loose = typst.running_head('T', 'Org', False)
    check('a bound running head takes parity from the physical leaf',
          'here().page()' in bound and 'calc.even(leaf)' in bound)
    check('a bound running head is suppressed where a chapter opens',
          'not opens' in bound)
    check('a bound recto names the chapter, not the document',
          'seen.last().body' in bound)
    check('an unbound running head is the document title throughout',
          'seen.last().body' not in loose and 'counter(page)' in loose)

    figures = []
    part = ['## Chapter One {.part}', '', 'Text.']
    check('bound, a part opens a recto',
          '#pf-recto()' in typst.convert(part, {}, figures, 'Figure %d', binding=True))
    check('unbound, a part opens a page',
          '#pagebreak(weak: true)' in typst.convert(part, {}, figures, 'Figure %d'))
    # inside an annex every section is a part; six of them would cost six blank
    # leaves to say nothing at all
    check('a section of an appendix opens a page, not a recto',
          '#pf-recto()' not in typst.convert(
              part, {}, figures, 'Figure %d', force_parts=True, binding=True))

    if not shutil.which('typst'):
        print('  typst not installed; skipping the measured half')
        return 1 if failures else 0

    work = Path(tempfile.mkdtemp())
    source = book_project(work)
    typst.build(source, work / 'book.pdf', profile.load('en'),
                organisation='Paperforge Press', contents_heading='CONTENTS',
                cache=work, binding=True, trim='royal')

    leaves = read(work / 'book.pdf')
    check('the trim is royal octavo, not A4',
          round(leaves[0]['width'] / 72 * 25.4) == 156
          and round(leaves[0]['height'] / 72 * 25.4) == 234)

    # --- the four conventions ---------------------------------------------
    blanks = [i for i, p in enumerate(leaves, 1) if not p['body']]
    check('a leaf is skipped to put a chapter on a recto', bool(blanks))
    check('every skipped leaf is a verso', all(i % 2 == 0 for i in blanks))
    check('a skipped leaf carries no folio',
          all(not leaves[i - 1]['folio'] for i in blanks))
    check('a skipped leaf carries no running head',
          all(not leaves[i - 1]['head'] for i in blanks))

    opens = [i for i, p in enumerate(leaves, 1)
             if p['body'][:1] == ['Chapter']]
    check('every chapter opens on a recto', bool(opens) and all(i % 2 for i in opens))
    check('a chapter opening carries no running head above its title',
          all(not leaves[i - 1]['head'] for i in opens))

    heads = {i: p['head'] for i, p in enumerate(leaves, 1) if p['head']}
    versos = [h for i, h in heads.items() if i % 2 == 0]
    rectos = [h for i, h in heads.items() if i % 2]
    check('every verso running head names the book',
          bool(versos) and all(h.startswith('Setting a Book') for h in versos))
    check('every recto running head names the chapter',
          bool(rectos) and all(h.startswith('Chapter') for h in rectos))

    folios = [p['folio'] for p in leaves if p['folio']]
    check('the front matter numbers in roman', folios[0] == 'i')
    check('the book proper restarts at arabic one', '1' in folios)
    check('the restart lands on a recto',
          next(i for i, p in enumerate(leaves, 1) if p['folio'] == '1') % 2 == 1)
    check('a skipped leaf still counts in the pagination',
          [f for f in folios if f.isdigit()] != [str(n) for n in
                                                 range(1, len(folios) + 1)])

    # the inside edge disappears into the gutter, so it gets the wider margin
    insides = {i % 2: round(p['inside'] / 72 * 25.4)
               for i, p in enumerate(leaves, 1) if p['inside'] and i > 1}
    check('the margins are mirrored, wider on the inside edge',
          insides.get(1, 0) > insides.get(0, 99))

    # --- and the check that would have missed all of it -------------------
    # "Chapter One" is at the top of the page it opens, and at the top of every
    # later recto of that chapter, because that is what a running head is. A
    # gate reading the first words of each page cannot tell those apart, so a
    # chapter that opened no page at all would still be found - and reported as
    # opening one.
    # --- a top-level heading that is not a chapter ------------------------
    # `{.no-part}` says "this ## does not open a page". Suppressing the running
    # head wherever a level-1 heading falls on the leaf - the obvious proxy for
    # "a chapter opens here" - then strips the head from a page whose text
    # merely runs on past one, and promotes the interlude to a chapter in every
    # later running head. The emitter marks the headings that open a page.
    aside = Path(tempfile.mkdtemp())
    src = book_project(aside)
    src.write_text(src.read_text().replace(
        '## Chapter Two {.part}',
        '## An interlude {.no-part}\n\n' + FILLER * 8 + '\n\n## Chapter Two {.part}'),
        encoding='utf-8')
    typst.build(src, aside / 'book.pdf', profile.load('en'),
                organisation='Paperforge Press', contents_heading='CONTENTS',
                cache=aside, binding=True, trim='royal')
    mixed = read(aside / 'book.pdf')
    # the cover and the pages a division opens carry no head by design
    bare = [i for i, p in enumerate(mixed, 1)
            if i > 1 and p['body'] and not p['head']
            and p['body'][0] not in ('Chapter', 'CONTENTS')]
    check('a leaf running on past a {.no-part} heading keeps its running head',
          not bare)
    check('a {.no-part} heading never becomes the running head',
          not any('interlude' in p['head'].lower() for p in mixed))
    shutil.rmtree(aside, ignore_errors=True)

    # The contents page lists every chapter and so answers to every probe; the
    # real gate drops such pages by counting how many candidates they carry,
    # and with two chapters that rule cannot fire, so it is dropped by name.
    contents = next(i for i, p in enumerate(leaves, 1) if p['body'][:1] == ['CONTENTS'])
    import pdfplumber
    with pdfplumber.open(work / 'book.pdf') as pdf:
        pages = list(pdf.pages)

        def tops(header):
            return [i for i, page in enumerate(pages, 1)
                    if i != contents and 'chapter one' in ' '.join(
                        editions.page_text(page, 1, header).lower().split()[:26])]
        uncropped, cropped = tops(0), tops(typst.HEADER_BAND)
    check('uncropped, the chapter is found at the top of more than one page',
          len(uncropped) > 1)
    check('dropping the running head leaves exactly the page it opens',
          len(cropped) == 1 and cropped[0] == min(uncropped))
    check('the crop keeps the body: the opening is still found',
          bool(cropped))

    shutil.rmtree(work, ignore_errors=True)
    return 1 if failures else 0


if __name__ == '__main__':
    print(__doc__.strip().split('\n')[0])
    code = main()
    if failures:
        print('\n%d check(s) failed:' % len(failures))
        for f in failures:
            print('  - %s' % f)
    sys.exit(code)
