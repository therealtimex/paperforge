#!/usr/bin/env python3
"""The cross-edition check, against a document built to disagree.

Two independent emitters render the same source and they have drifted: parts
opened a page in the HTML and ran on mid-page in the PDF, the annex likewise.
Every other gate looks at one edition at a time and each was individually
valid, so this comparison is the only thing that would have caught it.

Proving it does not false-alarm is what CI already does on every fixture.
This proves it fires, by typesetting a PDF in which one heading deliberately
starts mid-page.

Needs typst and pdfplumber.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import editions

failures = []

HTML = """<html><body><main>
<h2 class="part" id="alpha">Alpha Section One<a class="anchor" href="#alpha"></a></h2>
<p>Body.</p>
<h2 class="part" id="beta">Beta Section Two<a class="anchor" href="#beta"></a></h2>
<p>Body.</p>
<h2 id="plain">Plain Subsection<a class="anchor" href="#plain"></a></h2>
<p>Body.</p>
</main></body></html>"""

# page 1 opens on Alpha; page 2 opens on prose and reaches Beta halfway down
TYP = """#set page(width: 210mm, height: 297mm, margin: 20mm)
#set text(size: 11pt)
= Alpha Section One
#lorem(90)
#pagebreak()
#lorem(120)
= Beta Section Two
#lorem(40)
== Plain Subsection
#lorem(30)
"""


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    print('reading the reading edition')
    openers = editions.page_openers_html(HTML)
    check('a heading marked as a part is expected to open a page',
          any(o.startswith('alpha') for o in openers))
    check('an unmarked heading is not', not any('plain' in o for o in openers))
    check('exactly the two parts are expected', len(openers) == 2)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / 'doc.typ').write_text(TYP, encoding='utf-8')
        built = subprocess.run(['typst', 'compile', 'doc.typ', 'doc.pdf'],
                               cwd=work, capture_output=True, text=True)
        if built.returncode != 0:
            print('  typst failed:\n%s' % built.stderr.strip()[:300])
            return 1
        (work / 'doc.html').write_text(HTML, encoding='utf-8')

        print('comparing it with the print edition')
        result = editions.compare(work / 'doc.html', work / 'doc.pdf')
        check('both parts are located in the PDF', result['unlocated'] == [])
        mid = [h for h, _ in result['mid_page']]
        check('the heading that starts mid-page is reported',
              any(h.startswith('beta') for h in mid))
        check('the heading that opens its page is not reported',
              not any(h.startswith('alpha') for h in mid))
        check('the page it landed on is reported',
              all(isinstance(p, int) and p > 0 for _, p in result['mid_page']))
        check('a document with no figures agrees about having none',
              result['figures_agree'] and result['figures_html'] == 0)

        print('a heading the print edition never received')
        extra = HTML.replace('</main>',
                             '<h2 class="part" id="gamma">Gamma Section Missing'
                             '<a class="anchor" href="#gamma"></a></h2></main>')
        (work / 'extra.html').write_text(extra, encoding='utf-8')
        result = editions.compare(work / 'extra.html', work / 'doc.pdf')
        check('a heading absent from the PDF is reported as unlocated',
              any('gamma' in h for h in result['unlocated']))

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\neditions: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
