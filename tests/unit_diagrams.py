#!/usr/bin/env python3
"""How the diagram stage responds to what the renderer hands back.

Mermaid is driven through headless Chrome, so a fixture only ever exercises the
happy path. The interesting behaviour is the refusals - and one of them exists
because of a defect that shipped: with startOnLoad the library reused a single
SVG id across diagrams and emitted several with no viewBox, which drew them on
top of each other. A diagram without a viewBox must stop the build.

The browser is stubbed. What is under test is this module's reading of the
output, not Chrome.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import browser, diagrams, palette

failures = []
GOOD = '<svg viewBox="0 0 100 50" style="max-width:100px"><g/></svg>'
RECOLOURED = '<svg viewBox="0 0 100 50"><g fill="#5b2333"/></svg>'
HOUSE = {'navy': '#5b2333', 'navy-soft': '#efe2e6'}


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def raises(label, fn, fragment):
    try:
        fn()
    except RuntimeError as e:
        ok = fragment in str(e)
        print('  %-58s %s (%s)' % (label, 'ok' if ok else 'FAIL', str(e)[:34]))
        if not ok:
            failures.append(label)
        return
    print('  %-58s FAIL (no error)' % label)
    failures.append(label)


def _stale(cache, srcs):
    """Rewrite the cache in the old shape - sources and svgs, no theme - and
    return what a build would serve from it, which must be nothing."""
    cache.write_text(json.dumps({'sources': srcs, 'svgs': ['STALE', 'STALE']}),
                     encoding='utf-8')
    stub(json.dumps([GOOD, GOOD]))
    served = diagrams.render(srcs, cache=cache)
    return served if 'STALE' in served else None


def stub(payload):
    """Replace the browser with a canned DOM containing `payload`."""
    def dump_dom(url, budget=40000, extra=()):
        return '<pre id="out">%s</pre>' % payload
    browser.dump_dom = dump_dom


def main():
    real = browser.dump_dom
    try:
        print('finding diagram sources')
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / 'a.md'
            doc.write_text('Text.\n\n```mermaid\ngraph TD\n A-->B\n```\n\n'
                           '```bash\nnot a diagram\n```\n\n'
                           '```mermaid\nflowchart LR\n C-->D\n```\n', encoding='utf-8')
            srcs = diagrams.sources(doc)
            check('every mermaid block is found, in reading order',
                  len(srcs) == 2 and srcs[0].startswith('graph TD'))
            check('a fence in another language is not a diagram',
                  not any('not a diagram' in s for s in srcs))
            check('a missing companion file is skipped, not an error',
                  diagrams.sources(doc, None) == srcs)

            print('rendering')
            check('nothing to render needs no browser at all', diagrams.render([]) == [])

            cache = Path(tmp) / 'diagrams.json'
            stub(json.dumps([GOOD, GOOD]))
            out = diagrams.render(srcs, cache=cache)
            check('two diagrams render to two SVGs', len(out) == 2)
            check('the result is cached', cache.exists())

            stub('THIS SHOULD NOT BE READ')
            check('an unchanged source list is served from the cache',
                  diagrams.render(srcs, cache=cache) == out)
            stub(json.dumps([GOOD]))
            check('a changed source list re-renders rather than reusing the cache',
                  len(diagrams.render(srcs[:1], cache=cache)) == 1)

            print('the palette is part of the cache key')
            stub(json.dumps([GOOD, GOOD]))
            plain = diagrams.render(srcs, cache=cache)
            stub(json.dumps([RECOLOURED, RECOLOURED]))
            # The key was the sources alone. Changing a palette and rebuilding
            # served the diagrams back in the old colours, on a machine where
            # everything else had changed, with the build reporting success.
            branded = diagrams.render(srcs, cache=cache,
                                      tokens=palette.resolve(None, HOUSE))
            check('a changed palette re-renders rather than serving old colours',
                  branded != plain and branded[0] == RECOLOURED)
            stub('THIS SHOULD NOT BE READ EITHER')
            check('and the branded result is itself cached',
                  diagrams.render(srcs, cache=cache,
                                  tokens=palette.resolve(None, HOUSE)) == branded)
            check('a cache written before the theme was keyed is not trusted',
                  _stale(cache, srcs) is None)

            print('refusals')
            stub('')
            raises('an empty result stops the build',
                   lambda: diagrams.render(srcs[:1]), 'produced nothing')
            stub(json.dumps(['ERROR: bad shape in line 2']))
            raises('a diagram the renderer rejected stops the build',
                   lambda: diagrams.render(srcs[:1]), 'failed')
            stub(json.dumps(['<svg style="max-width:100px"><g/></svg>']))
            raises('a diagram with no viewBox stops the build, because it would overlap',
                   lambda: diagrams.render(srcs[:1]), 'viewBox')
    finally:
        browser.dump_dom = real

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\ndiagrams: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
