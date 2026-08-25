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
from paperforge import editions, profile, typst

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

    print('the Word edition against the reading edition')
    from paperforge import docx as docx_mod, profile
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        src = work / 'r.md'
        src.write_text('# KIND\n## Title\n\n---\n\n## CONTENTS\n\n'
                       '## Alpha Section One {.part}\n\nBody text here.\n\n'
                       '| A | B |\n|---|---|\n| 1 | 2 |\n\n'
                       '## Beta Section Two {.part}\n\nMore body text.\n',
                       encoding='utf-8')
        prof = profile.load('en')
        out = work / 'r.docx'
        info = docx_mod.build(src, out, prof, contents_heading='CONTENTS')
        check('the Word file is written', out.exists() and info['bytes'] > 0)
        check('its tables come across', info['tables'] == 1)
        built = docx_mod.structure(out)
        check('both parts are headings in Word',
              any(h.startswith('Alpha') for h in built['headings'])
              and any(h.startswith('Beta') for h in built['headings']))

        (work / 'r.html').write_text(
            '<html><body><main>'
            '<h2 id="c">CONTENTS<a class="anchor" href="#c"></a></h2>'
            '<h2 class="part" id="a">Alpha Section One<a class="anchor" href="#a"></a></h2>'
            '<table><tr><td>1</td></tr></table>'
            '<h2 class="part" id="b">Beta Section Two<a class="anchor" href="#b"></a></h2>'
            '</main></body></html>', encoding='utf-8')
        cmp = editions.compare_docx(work / 'r.html', out)
        check('a document built from the same source agrees',
              not cmp['missing'] and not cmp['extra'])
        check('tables are counted on both sides',
              cmp['tables_html'] == cmp['tables_docx'] == 1)

        (work / 'drifted.html').write_text(
            '<html><body><main>'
            '<h2 id="c">CONTENTS<a class="anchor" href="#c"></a></h2>'
            '<h2 class="part" id="a">Alpha Section One<a class="anchor" href="#a"></a></h2>'
            '<h2 class="part" id="g">Gamma Section Missing<a class="anchor" href="#g"></a></h2>'
            '</main></body></html>', encoding='utf-8')
        drift = editions.compare_docx(work / 'drifted.html', out)
        check('a heading the Word file never received is reported',
              any('Gamma' in h for h in drift['missing']))
        check('a heading only Word carries is reported too',
              any('Beta' in h for h in drift['extra']))

    # --- where the annex head ends, in both editions ----------------------
    # The reading edition sets everything above the annex's first rule as one
    # title block: badge, title, meta. The print edition converted the whole
    # file with force_parts, which made that `##` title an annex *section*, so
    # it opened a page of its own and the badge was left alone on the page
    # before. `verify` reported the annex head unlocated in the PDF - correctly,
    # since the two editions disagreed about where the annex began.
    import shutil
    if shutil.which('typst'):
        work = Path(tempfile.mkdtemp())
        # Every string here is distinct from the document title, because the
        # title is printed as a running head on every page from the second and
        # a probe it satisfies proves nothing. The first version of this test
        # gave the annex the same title as the document and passed against the
        # defect it was written for.
        (work / 'doc.md').write_text(
            '# REPORT\n## Critical Minerals\n\n---\n**Prepared by:** Paperforge\n\n'
            '---\n\n## CONTENTS\n\n1. **Context**\n\n---\n\n'
            '## Context {.part}\n\nBody.\n', encoding='utf-8')
        (work / 'annex.md').write_text(
            '# Annex\n## Provenance Of Every Figure\n\n**Prepared by:** Paperforge\n\n'
            '---\n\n## 1. Sources and method\n\nBody.\n', encoding='utf-8')
        typst.build(work / 'doc.md', work / 'doc.pdf', profile.load('en'),
                    annex=work / 'annex.md', organisation='Paperforge',
                    contents_heading='CONTENTS', cache=work)
        import pdfplumber
        with pdfplumber.open(work / 'doc.pdf') as pdf:
            pages = [' '.join((p.extract_text() or '').split()) for p in pdf.pages]
        badge = next((i for i, pg in enumerate(pages) if 'Annex' in pg), None)
        check('the annex head is set on one page, badge and title together',
              badge is not None and 'Provenance Of Every Figure' in pages[badge])
        # the reading edition sets `**Prepared by:** X` as a two-column grid and
        # drops the colon with the key; letting it fall through as body prose
        # keeps it, and the two editions then disagree about the head's text
        check('the annex metadata is a grid, as the document head is',
              badge is not None and 'Prepared by' in pages[badge]
              and 'Prepared by:' not in pages[badge])
        # not `startswith`: an unbound edition prints the running head above
        # every page from the second, so no page text starts with its heading
        section = next((i for i, pg in enumerate(pages)
                        if '1. Sources and method' in pg), None)
        check('the annex section still opens a page of its own',
              section is not None and section != badge)
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\neditions: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
