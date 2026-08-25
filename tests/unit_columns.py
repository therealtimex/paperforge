#!/usr/bin/env python3
"""Two columns: the setting, the things that must cross the gutter, and the
reader that has to make sense of the result.

A journal asks for a two-column manuscript. Three things then stop being true
at once. A wide table cannot live in an 88mm column - it already needed the
long edge of the paper. A title block broken over a gutter is not a title
block. And the print edition can no longer be read a page at a time, because
both columns share one leading, so their baselines coincide and a whole-page
flatten reads straight across the gutter.

The third is the one worth a test of its own: it is invisible, it corrupts
every text probe that looks at a printed page, and nothing else in the suite
would notice.

Needs typst, pdfplumber and python-docx.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import cli, editions, typst, verify

failures = []


def check(label, condition):
    print('  %-64s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


# Two columns of flowing prose with nothing to offset one against the other:
# the case where the baselines line up exactly. The banner is set across the
# full measure, as a part banner is.
TYP = """#set page(width: 210mm, height: 297mm, margin: 15mm, columns: 2)
#set text(size: 10.5pt)
#set par(justify: true)
#place(top + center, scope: "parent", float: true)[
  #text(size: 18pt, weight: "bold")[Robot Density and the Closing Window]
]
#lorem(700)
"""

# A body that ends on a page boundary, then the colophon alone on the last one.
COLOPHON_TYP = """#set page(width: 210mm, height: 297mm, margin: 15mm)
#set text(size: 10.5pt)
#lorem(320)
#pagebreak()
#align(center)[© 2026 Paperforge \\ Circulated for policy planning.]
"""
FOOTER_HTML = ('<html><body><main><p>Body.</p></main>'
               '<footer><p>© 2026 Paperforge<br>Circulated for policy planning.</p>'
               '</footer></body></html>')


def main():
    # --- what the manifest is allowed to ask for --------------------------
    check('columns = 1 is the default', cli.columns_of({}) == 1)
    check('columns = 2 is accepted', cli.columns_of({'columns': 2}) == 2)
    for bad in (3, 0, '2'):
        try:
            cli.columns_of({'source': 'x.md', 'columns': bad})
            check('columns = %r is refused' % bad, False)
        except SystemExit as err:
            check('columns = %r is refused' % bad, 'only 1 or 2' in str(err))
    try:
        cli.columns_of({'source': 'x.md', 'columns': 2, 'format': 'deck'})
        check('a deck cannot be set in columns', False)
    except SystemExit as err:
        check('a deck cannot be set in columns', 'slide is not a page' in str(err))

    # --- what crosses the gutter ------------------------------------------
    check('one column leaves content alone', typst.span('= Part One', 1) == '= Part One')
    two = typst.span('= Part One', 2)
    check('two columns place it in the parent scope',
          'scope: "parent"' in two and 'float: true' in two and '= Part One' in two)

    # --- the Word section that carries the count --------------------------
    from docx import Document
    from docx.oxml.ns import qn
    from paperforge import docx as docx_mod
    doc = Document()
    docx_mod._columns(doc.sections[0], 2)         # the body
    docx_mod._landscape(doc, True, columns=2)     # a wide table takes its own
    docx_mod._landscape(doc, False, columns=2)    # and the body resumes
    # python-docx hands back the trailing sentinel rather than the section just
    # written, so the sections are read in document order instead.
    body, wide, resumed = doc.sections[0], doc.sections[1], doc.sections[2]

    def count(section):
        cols = section._sectPr.find(qn('w:cols'))
        return cols.get(qn('w:num')) if cols is not None else None

    check('the body section is set in two columns', count(body) == '2')
    check('a wide table leaves the columns behind', count(wide) == '1')
    check('and the body returns to two after it', count(resumed) == '2')
    check('the wide section is landscape', wide.page_width > wide.page_height)
    check('and the one after it is not', resumed.page_width < resumed.page_height)

    if not shutil.which('typst'):
        print('\ntypst not on PATH: the page-reading checks need it')
        return 1 if failures else 0

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / 'two.typ').write_text(TYP, encoding='utf-8')
        pdf = work / 'two.pdf'
        r = subprocess.run(['typst', 'compile', 'two.typ', str(pdf)],
                           cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            print('typst failed:\n%s' % r.stderr[:400])
            return 1

        import pdfplumber
        import logging
        import warnings
        warnings.filterwarnings('ignore')
        logging.getLogger('pdfminer').setLevel(logging.ERROR)
        with pdfplumber.open(pdf) as doc:
            page = doc.pages[0]
            measure = page.width - 30              # the text measure, less margins
            flat = [l for l in (page.extract_text() or '').split('\n') if l.strip()]
            read = [l for l in editions.page_text(page, 2).split('\n') if l.strip()]
            longest_flat = max(len(l) for l in flat)
            longest_read = max(len(l) for l in read)
            spanning = [l for l in read if l.startswith('Robot Density and the Closing')]
            plain = editions.page_text(page, 1)
            flat_text = page.extract_text() or ''

        # The defect this exists for: a whole-page flatten joins the two
        # columns line by line, so a probe for anything on the page is being
        # matched against text that was never a sentence.
        # The two numbers are compared against each other rather than against a
        # constant: a merged line is one column's line plus another's, so it
        # runs about twice as long, whatever the paper, face or language.
        check('a whole-page flatten merges the two columns',
              longest_flat > 1.6 * longest_read)
        check('reading it as columns recovers the lines it merged',
              len(read) > len(flat))
        # ...without cutting in half the blocks that are meant to span, which
        # is what a plain crop down the middle of the page does.
        check('a block that spans the measure is kept whole', len(spanning) == 1)
        check('one column is read exactly as before', plain == flat_text)
        check('the measure is wider than any column line', longest_read < measure)

    # --- the colophon is not a page --------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / 'c.typ').write_text(COLOPHON_TYP, encoding='utf-8')
        pdf = work / 'c.pdf'
        subprocess.run(['typst', 'compile', 'c.typ', str(pdf)], cwd=work,
                       capture_output=True, text=True, check=True)
        check('a last page carrying only the colophon is named',
              verify.colophon(pdf, FOOTER_HTML) == 2)
        check('and the near-empty check passes once it is exempted',
              not verify.pagination(pdf, exempt={verify.colophon(pdf, FOOTER_HTML)})['thin'])
        check('a last page with body text on it is not',
              verify.colophon(pdf, FOOTER_HTML.replace('Circulated for policy planning.',
                                                       'Something else entirely.')) is None)
        check('a document with no footer is not either',
              verify.colophon(pdf, '<html><body><main><p>Body.</p></main></body></html>') is None)

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\ncolumns: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
