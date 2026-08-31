"""Paperforge pipeline: build -> lint -> verify -> publish."""
import argparse
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

from . import (assemble, brief, claims, deck, diagrams, editions, figures, lint,
               require,
               markdown, papermap,
               pages, palette, profile, publish as pub, runs, scaffold, typst,
               verify)

def find_config(explicit=None):
    """Locate the manifest: an explicit path, $PAPERFORGE_CONFIG, or the
    nearest documents.toml walking up from the working directory."""
    import os
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get('PAPERFORGE_CONFIG')
    if env:
        return Path(env).resolve()
    for base in [Path.cwd(), *Path.cwd().parents]:
        for candidate in (base / 'documents.toml', base / 'tools/documents.toml'):
            if candidate.exists():
                return candidate
    raise SystemExit('no documents.toml found; pass --config or set PAPERFORGE_CONFIG')


def _doctor_project(explicit=None):
    """Report a project's scaffolded guidance, if there is a project here.

    `init` writes AGENTS.md from a template that keeps changing, so from the
    moment it lands it is a second copy of the pipeline's own instructions -
    and the one nobody can see going stale. A real project was found running
    against guidance from before v3.0.0 against a v3.8.0 pipeline: it named a
    stage that no longer existed and an entry point that was a placeholder.

    Reported, never rewritten. Editing a file in somebody's project is not a
    diagnostic, for the same reason `doctor` does not install a missing tool.
    """
    from . import scaffold
    try:
        config = find_config(explicit)
    except SystemExit:
        return False                      # no project here; nothing to say
    # the manifest may sit in `tools/`, and the project is the directory above
    # it - the same normalisation `load` does, and for the same reason
    root = config.parent.parent if config.parent.name == 'tools' else config.parent
    found = scaffold.drift(root)
    state = {'current': 'ok', 'stale': 'STALE', 'unstamped': 'unknown'}[found['state']]
    print('')
    print('this project:')
    print('  %-18s %-9s %s' % ('scaffold', state, found['why']))
    if found['state'] == 'stale':
        print('  %-18s %-9s %s' % ('', '', 'compare it against a fresh `init`, and '
                                   'copy across what is missing'))
    return found['state'] == 'stale'


# A document type implies how it is rendered, so the manifest names the type
# rather than repeating layout and format mechanics.
# Built-in document types. A project defines its own under [types] in the
# manifest - a due-diligence memo, a board pack, a case study - because the set
# of things research teams publish is not ours to enumerate.
# The order `all` runs its stages in, named once. The scaffolded AGENTS.md
# builds its description of the chain from this rather than restating it: the
# `claims` stage was added and that hand-written line was not, so every project
# scaffolded afterwards carried a wrong account of what the command does.
# unit_gates scans this module and proves the tuple matches the stages that
# actually run, in the order they run.
STAGES = ('figures', 'claims', 'lint', 'build', 'verify', 'publish')

BUILTIN_TYPES = {
    'report': {'layout': 'report'},
    'brief': {'layout': 'brief'},
    'deck': {'format': 'deck'},
    # a map of another document, not a document of its own: it is built from
    # that document's source and says what it declares and what points at what
    'map': {'format': 'map'},
    'note': {'layout': 'brief', 'page_numbers': False},
    # A book is a report that has been made into an object: it is bound, so it
    # has an inside edge and two sides to a leaf, and it is not A4.
    'book': {'layout': 'report', 'page_numbers': True, 'binding': True,
             'trim': 'royal'},
}


def document_types(cfg):
    """Built-in types, plus any the project declares.

    A declared type may extend a built-in one:

        [types.case-study]
        extends = "report"
        page_numbers = true

        [types.board-pack]
        layout = "brief"
    """
    types = {k: dict(v) for k, v in BUILTIN_TYPES.items()}
    for name, spec in (cfg.get('types') or {}).items():
        spec = dict(spec)
        base = spec.pop('extends', None)
        if base and base not in types:
            raise SystemExit('type %r extends unknown type %r' % (name, base))
        merged = dict(types.get(base, {})) if base else {}
        merged.update(spec)
        types[name] = merged
    return types


def editions_of(d):
    """Language sub-tables of a work, e.g. [collection.document.vi].

    A table carrying its own `source` is an edition; anything else is a plain
    setting. A document with `source` at the top level is the flat, single-
    language form and still works unchanged.
    """
    return {k: v for k, v in d.items() if isinstance(v, dict) and 'source' in v}


def columns_of(d):
    """How many columns the print editions set. 1 or 2, and nothing else.

    No journal asks for three, and a third column on A4 is 55mm wide - it
    cannot hold a table, a source URL, or a Vietnamese compound noun. Refusing
    the number is kinder than setting a document nobody can read.
    """
    n = d.get('columns', 1)
    if n not in (1, 2):
        raise SystemExit('document %r sets columns = %r; only 1 or 2 are set'
                         % (d.get('source', '?'), n))
    if n > 1 and d.get('format') == 'map':
        raise SystemExit('document %r is a map and sets columns = %d; a map is a '
                         'description of a document, not a page of one'
                         % (d.get('source', '?'), n))
    if n > 1 and d.get('format') == 'deck':
        raise SystemExit('document %r is a deck and sets columns = %d; a slide is '
                         'not a page and has no measure to divide'
                         % (d.get('source', '?'), n))
    return n


def binding_of(d):
    """Whether the print edition is set for binding, refusing what cannot be.

    Binding is a print instruction, in the same sense as `columns`: it changes
    the bound edition and nothing on screen, because a screen has no verso and
    no gutter.
    """
    trim = d.get('trim', 'a4')
    if trim not in typst.TRIM:
        raise SystemExit('document %r sets trim = %r; the trims set are: %s'
                         % (d.get('source', '?'), trim, ', '.join(sorted(typst.TRIM))))
    if not d.get('binding'):
        return False
    if d.get('format') == 'map':
        raise SystemExit('document %r is a map and is bound; a map is read on a '
                         'screen beside the document and has no leaf to turn'
                         % d.get('source', '?'))
    if d.get('format') == 'deck':
        raise SystemExit('document %r is a deck and is bound; a slide is one side '
                         'of nothing and has no gutter to leave room for'
                         % d.get('source', '?'))
    if d.get('pdf') == 'chrome':
        # measured, not assumed: Chrome honours `@page { size: }` and the
        # `:left`/`:right` margin overrides, so the trim and the margins come
        # out right and the document looks bound. It breaks `recto` to the next
        # page whichever side that is, and renders no running head at all.
        raise SystemExit('document %r is bound and sets pdf = "chrome". Chrome takes '
                         'the trim and the mirrored margins but breaks to the next '
                         'page rather than to a recto, and renders no running head, '
                         'so the chapters would open on left-hand pages under the '
                         'book title. Set pdf = "typst".' % d.get('source', '?'))
    return True


def load(config=None):
    path = find_config(config)
    root = path.parent.parent if path.parent.name == 'tools' else path.parent
    cfg = tomllib.load(open(path, 'rb'))
    cfg['_root'], cfg['_cache'], cfg['_manifest'] = root, path.parent / '.cache', path
    cache, docs = {}, []
    types = document_types(cfg)

    def resolve(name, local, base):
        key = (name, local)
        if key not in cache:
            shipped = profile.load(name) if name and name != 'none' else None
            cache[key] = profile.load_file(base / local, shipped) if local else shipped
        return cache[key]

    for col in cfg['collection']:
        base = root / col['root']
        col_profile = col.get('profile', cfg['defaults'].get('profile', 'vi'))
        col_local = col.get('profile_file')

        for d in col['document']:
            editions = editions_of(d)
            shared = {k: v for k, v in d.items() if k not in editions}
            kind = shared.get('type')
            if kind and kind not in types:
                raise SystemExit('document %r declares unknown type %r; declare it under '
                                 '[types.%s] or use one of: %s'
                                 % (d.get('id', '?'), kind, kind, ', '.join(sorted(types))))
            shared.update(types.get(kind, {}))
            # flat form: the document is its own single edition
            entries = editions or {col_profile: {k: shared.pop(k) for k in
                                                 ('source', 'output', 'annex', 'publish')
                                                 if k in shared}}
            for lang, ed in entries.items():
                name = ed.get('profile', lang if editions else col_profile)
                local = ed.get('profile_file', col_local if not editions else None)
                prof = resolve(name, local, base)
                source = ed['source']
                output = ed.get('output') or Path(source).with_suffix('.html').name
                doc = {**cfg['defaults'], **shared, **ed,
                       'root': base, 'collection': col['slug'], 'language': lang,
                       'figures_path': (base / col['figures']) if col.get('figures') else None,
                       'profile_name': local or name, 'prof': prof,
                       'source': source, 'output': output,
                       'source_path': base / source, 'output_path': base / output,
                       'annex_path': base / ed['annex'] if ed.get('annex') else None,
                       # chapters: body fragments appended in declared order
                       'include_paths': [base / f for f in
                                         ({**cfg['defaults'], **shared, **ed}.get('include') or [])],
                       # what was asked, kept beside what was produced: when the
                       # request is thin the interpretation becomes the real
                       # spec, and an interpretation nobody can re-read is not
                       # one anybody can check the delivery against
                       'logo_path': (base / doc_logo).resolve()
                       if (doc_logo := {**cfg['defaults'], **shared, **ed}.get('logo'))
                       else None,
                       'request_path': (base / doc_request).resolve()
                       if (doc_request := {**cfg['defaults'], **shared, **ed}.get('request'))
                       else None}
                # the contents heading is in every profile; the manifest need not repeat it
                if doc.get('page_numbers') and not doc.get('contents_heading') and prof:
                    doc['contents_heading'] = prof['structure'].get('contents_heading')
                doc.setdefault('publish', False)
                # checked here rather than where it is used: a deck returns
                # from the build before opts() is reached, so a refusal that
                # lived there could never have fired for the one document type
                # it exists to refuse.
                columns_of(doc)
                binding_of(doc)
                docs.append(doc)
    return cfg, docs


def pick(docs, only):
    if not only:
        return docs
    chosen = [d for d in docs if only in (d['source'], d['output'], d['collection'])]
    if not chosen:
        sys.exit('no document matches %r' % only)
    return chosen


def _claim_sources(docs):
    """{root: [source]} - the files a project's claims can live in."""
    roots = {}
    for d in docs:
        root, seen = d['root'], roots.setdefault(d['root'], [])
        for path in [d['source_path'], d.get('annex_path')] + list(d.get('include_paths') or ()):
            if path and Path(path).exists() and Path(path) not in seen:
                seen.append(Path(path))
    return roots


def do_claims(docs, accept=False, quiet=False, only=None):
    """Gists are written by hand. This only ever checks them, except for
    --accept, which is somebody saying they have reread the paragraph."""
    blocking = 0
    for root, sources in sorted(_claim_sources(docs).items()):
        if accept:
            try:
                done = claims.accept(sorted(sources), root, only)
            except KeyError:
                # naming a claim that is not there is a typo, and re-stamping
                # everything because one id was mistyped is the behaviour this
                # option exists to remove
                raise SystemExit('no claim %r in this project; `paperforge claims` '
                                 'lists what is there' % only)
            # the paragraph, not a tally. Showing it is not proof anybody read
            # it - nothing is - but a count is proof they were not shown it
            for item in done['restamped'] if not quiet else []:
                print('  %s' % item['id'])
                if item['was'] and item['was'] != item['gist']:
                    print('      was:  %s' % item['was'])
                print('      gist: %s' % item['gist'])
                print('      says: %s' % _one_line(item['text'], 300))
            print('  %-38s %d accepted, %d restamped, %d dropped'
                  % (claims.LOCK, len(done['accepted']), len(done['changed']),
                     len(done['dropped'])))
            if done['changed']:
                # accepting is somebody saying they reread the paragraph. Left
                # uncommitted that assertion exists on one machine and vouches
                # for nothing to anyone who pulls the repository.
                print('  %-38s commit it: an acceptance nobody else has is not one'
                      % claims.LOCK)
            continue
        found = claims.check(sorted(sources), root)
        blocked = [f for f in found if f['severity'] == 'block']
        blocking += len(blocked)
        total = len(claims.collect(sorted(sources)))
        print('  %-38s %d claim(s), %s'
              % (root.name, total,
                 'all current' if not found else
                 '%d blocking, %d for you, %d to look at'
                 % (len(blocked), sum(1 for f in found if f['severity'] == 'manual'),
                    sum(1 for f in found if f['severity'] == 'warn'))))
        for f in found:
            print('      %-7s %s:%s  %s  %s'
                  % (f['severity'], f['file'], f['line'], f['id'], f['rule']))
            if not quiet:
                print('          %s' % f['why'])
                # a manual finding is only useful if it says what settles it
                if f.get('fix'):
                    print('          -> %s' % f['fix'])
    return blocking


def do_figures(docs, quiet=False):
    """Every document must agree with the project's declared figures."""
    seen, total = set(), 0
    for d in docs:
        path = d.get('figures_path')
        if not path or not path.exists() or str(path) in seen:
            continue
        seen.add(str(path))
        sources = sorted(d['root'].glob('*.md'))
        # every declared edition knows its language; anything else in the folder
        # falls back to the collection's own
        langs = {str(x['source_path']): x.get('language') for x in docs
                 if x.get('figures_path') == path}
        found, declared = figures.check(sources, path, langs)
        total += len(found)
        # declared and stated nowhere: the manifest exists so documents agree,
        # and an entry no document states agrees with nothing. A warning, not a
        # refusal - declaring a figure before writing about it is ordinary.
        unused = sorted({f['id'] for f in declared} - figures.stated(sources, declared))
        print('  %-38s %d figure(s) declared, %d document(s) checked, %s'
              % (path.name, len(declared), len(sources),
                 'consistent' if not found else '%d DISAGREEMENT(S)' % len(found)))
        for f in found:
            print('      %s:%s  %s' % (f['file'], f['line'], f['label']))
            print('          found %r, expected %r' % (f['found'], f['expected']))
            if not quiet:
                print('          %s' % f['context'])
        for ident in unused:
            print('      %-8s %-16s %s' % ('warn', ident, 'declared, stated in no document'))
    return total


def _one_line(text, width):
    """A paragraph as one line, so a gist and its prose can sit next to each
    other. Truncated with a marker: a silent cut reads as the whole thing."""
    flat = ' '.join(text.split())
    return flat if len(flat) <= width else flat[:width - 1] + '…'


def active_rules(cfg):
    section = cfg.get('lint') or {}
    return lint.ruleset(section.get('packs', []), section.get('rule', []))


def gate_inputs(cfg, docs):
    """What every gate needs to know about the project, not the document.

    Derived once and passed to `lint.check_all`, so the two commands that run
    the gates cannot be given different ideas of what is declared.
    """
    return {'rules': active_rules(cfg),
            'allowed': {d['source'] for d in docs},   # declared, drafts included
            'blocked': set(cfg['internal']['files']),
            'embedded': {d['annex'] for d in docs if d.get('annex')}}


def do_lint(cfg, docs, quiet=False):
    """Report gate findings; returns {source: blocking count}."""
    gate = gate_inputs(cfg, docs)
    result = {}
    for d in docs:
        findings = lint.check_all(d, **gate)
        s = lint.summarise(findings)
        result[d['output']] = s['blocking']
        state = next((name for name, key in (('BLOCKED', 'block'), ('manual', 'manual'),
                                             ('warn', 'warn'), ('skip', 'skip'))
                      if s['counts'][key]), 'ok')
        print('  %-38s %s' % (d['source'], state))
        if not quiet:
            for f in findings:
                print('      %-8s L%-5s %-16s %s' %
                      (f['severity'], f['line'] or '-', f['rule'], f['context'][:76] or f['why']))
                if f.get('fix'):
                    print('      %-8s %-6s %-16s -> %s' % ('', '', '', f['fix']))
    return result


def opts(d):
    """Render options for one document, shared by every build call so the
    first pass and the page-number rebuild cannot drift apart."""
    return {'contents_heading': d.get('contents_heading'),
            'kind_fallback': d.get('title_kind'), 'prof': d['prof'],
            'organisation': d.get('organisation'), 'publisher': d.get('publisher'),
            'footer_note': d.get('footer_note'), 'annex_label': d.get('annex_label'),
            'brand': d.get('brand'), 'logo': d.get('logo_path'),
            'review': bool(d.get('review')),
            'includes': d.get('include_paths') or (),
            'bibliography': (d['root'] / d['bibliography']) if d.get('bibliography') else None,
            'citation_style': d.get('citation_style', 'apa'),
            'layout': d.get('layout', 'report'),
            'columns': columns_of(d)}


def record_run(cfg, docs, stages, label=None):
    out = runs.write(cfg, docs, stages, label)
    print('  recorded %s' % out.relative_to(cfg['_root']))
    return out


def do_runs(cfg, pair, only, sources=False):
    """List recorded runs, or compare two of them."""
    root = cfg['_root']
    if pair:
        names = [n.strip() for n in pair.split(',') if n.strip()]
        if len(names) != 2:
            raise SystemExit('--diff takes two run names, comma separated')
        (an, a), (bn, b) = runs.load(root, names[0]), runs.load(root, names[1])
        d = runs.diff(a, b)
        print('%s -> %s' % (an, bn))
        for stage, (was, now) in d['stages'].items():
            print('  %-10s %s -> %s' % (stage, was or '-', now or '-'))
        for kind in ('added', 'removed', 'rewritten', 'unchanged'):
            if d[kind]:
                print('  %-10s %s' % (kind, ', '.join(d[kind])))
        if d['pdf_only']:
            # measured pagination differs between machines; see runs.py
            print('  %-10s %s (print edition only; page numbers are measured)'
                  % 'repaginated', ', '.join(d['pdf_only']))
        if sources:
            lines, missing = runs.source_diff(root, an, bn, only)
            if missing:
                print('  no stored sources for %s' % ', '.join(missing))
            elif not lines:
                print('  sources identical')
            else:
                print('')
                print(''.join(lines), end='')
        return 0
    found = runs.listing(root)
    if not found:
        print('  no runs recorded yet')
        return 0
    for name, rec in found:
        if only and only not in name and only not in (rec.get('label') or ''):
            continue
        verdict = ', '.join('%s %s' % (k, v) for k, v in rec['stages'].items())
        print('  %-32s %-28s %d document(s)  %s'
              % (name, (rec.get('label') or '-')[:28], len(rec['documents']), verdict))
    return 0


def structure_warnings(d, stats):
    """A declaration that matches nothing is the failure this pipeline exists to
    prevent: no part banners, no page breaks, no printed page numbers, and not a
    word said about it. Now it is said."""
    out = []
    st = stats.get('structure', {})
    h2, found = st.get('h2', 0), st.get('inferred_parts', 0) + st.get('explicit_parts', 0)
    # Parts are a long-report concept. A brief is continuous by design and a
    # short internal note has no parts to find, so only a document that asked
    # for a contents section and page numbers is expected to have them.
    expects_parts = d.get('layout', 'report') == 'report' and d.get('page_numbers')
    if expects_parts and h2 >= 3 and not found:
        out.append('no part headings detected in %d top-level headings — profile %r '
                   'part_banner matched nothing; mark them with {.part} or fix the pattern'
                   % (h2, d.get('profile_name')))
    if d.get('contents_heading') and d.get('page_numbers') and not stats.get('numbered'):
        out.append('no contents entry was numbered — check that %r names the contents '
                   'section and that its entries match the headings'
                   % d['contents_heading'])
    return out


def do_build(docs, cache, measure=True):
    cache.mkdir(exist_ok=True)
    failures = []
    for d in docs:
        # every file the document is made of, not just the first: the
        # emitters read the assembled text, so a diagram in an included
        # section was allocated a figure number and a raster nobody had been
        # asked to render - see assemble.sources()
        if d.get('format') == 'map':
            # built from the source, so it needs no diagrams rendered and no
            # page numbers measured; it describes the document, it is not one
            stats = papermap.emit(d, d['output_path'], prof=d['prof'],
                                  brand=d.get('brand'),
                                  subtitle=d.get('organisation') or '',
                                  footer=d.get('footer_note') or '')
            print('  %-38s %s' % (d['output'], json.dumps(stats, ensure_ascii=False)))
            continue
        srcs = diagrams.sources(*assemble.sources(d))
        # the document's own palette and font stack, so a diagram is drawn in
        # the same colours as the page around it; the cache keys on both
        svgs = diagrams.render(srcs, cache=cache / ('%s.diagrams.json' % d['source']),
                               tokens=palette.resolve(d['prof'], d.get('brand')))
        if d.get('format') == 'deck':
            stats = deck.build(d['source_path'], d['output_path'], svgs=svgs,
                               brand=d.get('brand'), logo=d.get('logo_path'),
                               kind_fallback=d.get('title_kind'), prof=d['prof'])
            warnings = stats.pop('warnings', [])
            print('  %-38s %s' % (d['output'], json.dumps(stats, ensure_ascii=False)))
            for w in warnings:
                print('      slide check: %s' % w)
            continue
        pages_map = None
        try:
            stats = markdown.build(d['source_path'], d['output_path'], svgs=svgs,
                                   annex=d['annex_path'], pages=None, **opts(d))
        except RuntimeError as err:
            # a missing tool the reading edition cannot do without - maths or a
            # bibliography, both of which go through typst. The other documents
            # in the project are not affected by this one's needs, so report and
            # carry on rather than ending the run in a traceback.
            print('  %-38s REFUSED: %s' % (d['output'], str(err).splitlines()[0]))
            failures.append(d['output'])
            continue
        if measure and d.get('page_numbers'):
            from . import browser
            pdf = cache / (d['output'] + '.pdf')
            try:
                browser.print_pdf(d['output_path'], pdf)
            except RuntimeError as err:
                # the document is fine; the measurement is not available. Page
                # numbers are already an optional edition-level extra, and there
                # is a path for declining them - this joins it rather than
                # ending the run in a traceback.
                print('  %-38s skip  page numbers: %s' % (d['output'], err))
                d['page_numbers'] = False
                d['_text_unreadable'] = True
            body = ''.join(p.read_text(encoding='utf-8')
                           for p in [d['source_path']] + ([d['annex_path']] if d['annex_path'] else []))
            quality = pages.extractable(
                pdf, body, fold_diacritics=d['prof'].get('fold_diacritics', True),
                rtl=d['prof'].get('direction') == 'rtl')
            if not quality['usable']:
                # the cause is not always a missing ToUnicode map: Arabic comes
                # back complete, shaped into presentation forms and in visual
                # order, so all of the text is there and none of it matches
                print('  %-38s printed page numbers skipped: %d of %d sampled words '
                      'are findable in the PDF (%s)'
                      % (d['output'], quality['found'], quality['checked'], quality['why']))
                d['page_numbers'] = False
                d['_text_unreadable'] = True
        if measure and d.get('page_numbers'):
            # measure the printed pagination, bake it in, and repeat until stable
            for _ in range(3):
                pdf = cache / (d['output'] + '.pdf')
                from . import browser
                try:
                    browser.print_pdf(d['output_path'], pdf)
                except RuntimeError as err:
                    print('  %-38s skip  page numbers: %s' % (d['output'], err))
                    info = {'pages': 0}
                    break
                fold = d['prof'].get('fold_diacritics', True)
                found, info = pages.measure(
                    str(d['output_path']), str(pdf),
                    markdown.slugify(d['contents_heading'], fold),
                    # a right-to-left page is extracted in visual order, so the
                    # matching compares token sets rather than substrings
                    rtl=d['prof'].get('direction') == 'rtl',
                    fold=fold)
                if found == pages_map:
                    break
                pages_map = found
                stats = markdown.build(d['source_path'], d['output_path'], svgs=svgs,
                                       annex=d['annex_path'], pages=pages_map, **opts(d))
            stats['printed_pages'] = info['pages']
        bib_warnings = stats.pop('bib_warnings', [])
        print('  %-38s %s' % (d['output'], json.dumps(stats, ensure_ascii=False)))
        for key, kind in bib_warnings:
            print('      bibliography: %r is @%s with a year but no month; APA emits a stray '
                  'comma. Use @report, or give a full date.' % (key, kind))
        for w in structure_warnings(d, stats):
            print('      structure: %s' % w)

        # Typst produces the print edition the browser cannot: footnotes at the
        # foot of the page, running heads, and markedly denser typesetting
        if d.get('pdf') == 'typst' and not require.found('typst'):
            # optional work, so the run continues without it - loudly. A green
            # `all` on this machine means less than one on a machine that has
            # every tool, and saying so is the whole point of the skip.
            print('      skip  %s'
                  % require.why('typst', 'the print edition was not built'))
        elif d.get('pdf') == 'typst':
            pdf_out = d['output_path'].with_suffix('.pdf')
            try:
                info = typst.build(d['source_path'], pdf_out, d['prof'], svgs=svgs,
                                   annex=d['annex_path'], title_kind=d.get('title_kind'),
                                   organisation=d.get('organisation', ''),
                                   brand=d.get('brand'), cache=cache, logo=d.get('logo_path'),
                                   review=bool(d.get('review')),
                                   includes=d.get('include_paths') or (),
                                   contents_heading=d.get('contents_heading'),
                                   bibliography=(d['root'] / d['bibliography'])
                                   if d.get('bibliography') else None,
                                   citation_style=d.get('citation_style', 'apa'),
                                   columns=columns_of(d), binding=binding_of(d),
                                   trim=d.get('trim', 'a4'))
                print('  %-38s %s' % (pdf_out.name, json.dumps(info, ensure_ascii=False)))
            except (RuntimeError, FileNotFoundError) as err:
                print('  %-38s typst FAILED: %s' % (pdf_out.name, str(err).splitlines()[0][:90]))
                failures.append(pdf_out.name)

        # Word, for the reader who has to work on the document rather than read
        # it: lift a section into a submission, comment, track changes.
        if d.get('docx'):
            # imported here, not at module scope: python-docx is only needed by
            # a project that asks for a Word edition, and the version check runs
            # on a job that installs nothing else
            from . import docx as docx_mod
            docx_out = d['output_path'].with_suffix('.docx')
            try:
                info = docx_mod.build(d['source_path'], docx_out, d['prof'], svgs=svgs,
                                      annex=d['annex_path'], title_kind=d.get('title_kind'),
                                      organisation=d.get('organisation', ''),
                                      brand=d.get('brand'), cache=cache, logo=d.get('logo_path'),
                                      review=bool(d.get('review')),
                                      includes=d.get('include_paths') or (),
                                      bibliography=(d['root'] / d['bibliography'])
                                      if d.get('bibliography') else None,
                                      citation_style=d.get('citation_style', 'apa'),
                                      contents_heading=d.get('contents_heading'),
                                      columns=columns_of(d))
                print('  %-38s %s' % (docx_out.name, json.dumps(info, ensure_ascii=False)))
            except Exception as err:
                print('  %-38s docx FAILED: %s' % (docx_out.name, str(err).splitlines()[0][:90]))
                failures.append(docx_out.name)

        # The browser already prints the document to measure its pagination, but
        # that copy is a cache by-product. `pdf = "chrome"` promotes it to a
        # named deliverable, so a print edition from the reading edition's own
        # layout is something the manifest asks for rather than something a
        # person links out of .cache by hand.
        # `if`, not `elif`: this used to be chained to the Typst branch, and
        # inserting the Word branch between them silently re-chained it to
        # `docx`. A document declaring both `docx = true` and `pdf = "chrome"`
        # then got no PDF at all, and nothing said so - the stale one from the
        # previous build was still sitting beside the HTML.
        if d.get('pdf') == 'chrome':
            pdf_out = d['output_path'].with_suffix('.pdf')
            measured = cache / (d['output'] + '.pdf')
            if not measured.exists():
                try:
                    browser.print_pdf(d['output_path'], measured)
                except RuntimeError as err:
                    print('  %-38s chrome print FAILED: %s' % (pdf_out.name, err))
            if measured.exists():
                shutil.copyfile(measured, pdf_out)
                print('  %-38s {"bytes": %d, "from": "chrome"}'
                      % (pdf_out.name, pdf_out.stat().st_size))
            else:
                print('  %-38s chrome print FAILED' % pdf_out.name)
                failures.append(pdf_out.name)
    return failures


def do_verify(docs, cache, quiet=False):
    failed = 0
    for d in docs:
        if not d['output_path'].exists():
            print('  %-38s NOT BUILT' % d['output']); failed += 1; continue
        r = verify.check(d['output_path'], *assemble.sources(d))
        if d.get('format') == 'map':
            # a map is not the document's prose, so the coverage check does not
            # apply: every line would read as missing. What must hold is that it
            # opens offline, like every other artefact here.
            problems = (['external assets %s' % r['external_assets'][:2]]
                        if r['external_assets'] else [])
            claims_on_it = Path(d['output_path']).read_text(
                encoding='utf-8').count('class="claim"')
            print('  %-38s %s (%d claim(s) mapped)' %
                  (d['output'], 'ok' if not problems else 'FAIL: ' + '; '.join(problems),
                   claims_on_it))
            failed += bool(problems)
            continue
        if d.get('format') == 'deck':
            problems = []
            if r['external_assets']:
                problems.append('external assets %s' % r['external_assets'][:2])
            if r['missing_content']:
                problems.append('%d missing lines %s' % (len(r['missing_content']),
                                                         r['missing_content'][:2]))
            slides = Path(d['output_path']).read_text(encoding='utf-8').count('<section')
            print('  %-38s %s (%d slides)' %
                  (d['output'], 'ok' if not problems else 'FAIL: ' + '; '.join(problems), slides))
            failed += bool(problems)
            continue
        problems = []
        if r['unclosed'] or r['markup_errors']:
            problems.append('markup %s' % (r['markup_errors'][:2] or r['unclosed'][:2]))
        if r['missing_content']:
            problems.append('%d missing lines %s' % (len(r['missing_content']), r['missing_content'][:2]))
        if r['broken_anchors']:
            problems.append('%d broken anchors' % len(r['broken_anchors']))
        if r['external_assets']:
            problems.append('external assets %s' % r['external_assets'][:2])
        if r['external_links']:
            # reported, never blocking: a citation the reader may follow is not
            # a dependency - the page renders identically offline - and a
            # reference list without retrieval URLs is the worse document
            print('      %d external link(s); the page loads none of them'
                  % len(r['external_links']))
        if r['leaks']:
            problems.append('%d raw markup leak(s): %s'
                            % (len(r['leaks']), [l['match'] for l in r['leaks'][:3]]))
        # The comparison is only meaningful against a second, independent
        # emitter. `pdf = "chrome"` prints the reading edition's own layout, so
        # there is nothing to disagree with - and its diagrams stay vector,
        # which the figure count reads as zero.
        pdf_edition = d['output_path'].with_suffix('.pdf')
        if pdf_edition.exists():
            pl = verify.print_leaks(pdf_edition)
            if pl:
                problems.append('%d raw markup leak(s) in the PDF: %s'
                                % (len(pl), ['%s %s' % (l['where'], l['match'])
                                             for l in pl[:3]]))
        word_edition = d['output_path'].with_suffix('.docx')
        if word_edition.exists() and d.get('docx'):
            wd = editions.compare_docx(d['output_path'], word_edition)
            for kind, label in (('missing', 'in the reading edition but not the .docx'),
                                ('extra', 'in the .docx but not the reading edition')):
                if wd[kind]:
                    problems.append('%d heading(s) %s: %s'
                                    % (len(wd[kind]), label, [h[:34] for h in wd[kind]][:2]))
            for what in ('figures', 'tables'):
                if wd['%s_html' % what] != wd['%s_docx' % what]:
                    problems.append('%s differ: html %d, docx %d'
                                    % (what, wd['%s_html' % what], wd['%s_docx' % what]))
            if not any(wd[k] for k in ('missing', 'extra')):
                print('      docx: %d headings, %d figures, %d tables agree with the '
                      'reading edition'
                      % (wd['headings_docx'], wd['figures_docx'], wd['tables_docx']))

        if pdf_edition.exists() and d.get('pdf') == 'typst':
            ed = editions.compare(d['output_path'], pdf_edition,
                                  columns=columns_of(d),
                                  header=typst.HEADER_BAND if binding_of(d) else 0)
            if ed['mid_page']:
                problems.append('%d heading(s) open a page in HTML but not in the PDF: %s'
                                % (len(ed['mid_page']), [h[:30] for h, _ in ed['mid_page']][:3]))
            if ed['unlocated']:
                problems.append('%d heading(s) not found in the PDF: %s'
                                % (len(ed['unlocated']), [h[:30] for h in ed['unlocated']][:3]))
            if not ed['figures_agree']:
                problems.append('figure counts differ: html %d, pdf %d'
                                % (ed['figures_html'], ed['figures_pdf']))
            else:
                print('      editions: %d page-opening headings agree, %d figures in both'
                      % (ed['expected_openers'], ed['figures_html']))

        try:
            lay = verify.layout(d['output_path'])
        except RuntimeError as err:
            # the layout probe renders the page at four widths; if the browser
            # will not come back, that check has no answer. Untestable is never
            # passed, so it says so rather than reporting no overflow.
            print('      skip  layout: %s' % err)
            lay = {}
        over = [w for w, v in lay.items() if v.get('over')]
        clip = [w for w, v in lay.items() if v.get('clip')]
        if over:
            problems.append('horizontal overflow at %s' % over)
        if clip:
            problems.append('clipped content at %s' % clip)
        pdf = cache / (d['output'] + '.pdf')
        # verify runs independently of build, so re-establish whether the PDF's
        # text can be read back at all before trusting anything derived from it
        readable = True
        if pdf.exists():
            body = ''.join(p.read_text(encoding='utf-8') for p in assemble.sources(d))
            quality = pages.extractable(
                pdf, body, fold_diacritics=d['prof'].get('fold_diacritics', True),
                rtl=d['prof'].get('direction') == 'rtl')
            readable = quality['usable']
            if not readable:
                print('      skip  print checks: %d of %d sampled words are findable in '
                      'the PDF (%s)'
                      % (quality['found'], quality['checked'], quality['why']))
        if pdf.exists() and readable:
            # The cover is sparse by design - a badge, a title, a metadata grid -
            # and the near-empty check looks for stranded headings and orphaned
            # frames, neither of which a cover can be. A scaffolded project with
            # a short title failed on it, which quietly contradicted the promise
            # that a fresh project passes clean; the CI scaffold only passed
            # because its title happened to be long enough.
            exempt = {1}
            if d.get('contents_heading'):
                import pdfplumber
                with pdfplumber.open(pdf) as doc:
                    texts = [pages.norm(p.extract_text() or '') for p in doc.pages]
                html = d['output_path'].read_text(encoding='utf-8')
                anchor = markdown.slugify(d['contents_heading'],
                                          d['prof'].get('fold_diacritics', True))
                if ('<h2 id="%s"' % anchor) in html:
                    # contents_pages is 0-based; pagination reports 1-based
                    exempt |= {i + 1 for i in pages.contents_pages(texts, html, anchor)}
            # a citation that did not survive into print is not a formatting
            # nit: it is the difference between an annex and a list of claims
            # Reported, not blocking: a row taller than the page splits a URL
            # across the break and no reconstruction here rejoins it, so some
            # of these are intact. It points at pages to look at.
            cut = verify.print_truncation(pdf, *assemble.sources(d))
            if cut['unlocated']:
                print('      print: %d of %d source URL(s) not found whole - check whether '
                      'a table row spans a page break: %s'
                      % (len(cut['unlocated']), cut['checked'],
                         ', '.join(u[:38] for u in cut['unlocated'][:2])))
            elif cut['checked']:
                print('      print: all %d source URL(s) survive the page' % cut['checked'])
            # the colophon is not a page either - see verify.colophon()
            tail = verify.colophon(pdf, d['output_path'].read_text(encoding='utf-8'))
            if tail:
                exempt |= {tail}
            pg = verify.pagination(pdf, exempt=exempt,
                                  script=d['prof'].get('script', 'latin'))
            if pg.get('skipped'):
                print('      skip  near-empty pages: %s' % pg['skipped'])
            elif pg['thin']:
                problems.append('%d near-empty printed page(s): %s'
                                % (len(pg['thin']), [t['page'] for t in pg['thin']]))
        if d.get('page_numbers') and readable:
            if pdf.exists():
                st = d['prof']['structure']
                a = pages.audit(
                    str(d['output_path']), str(pdf),
                    markdown.slugify(d['contents_heading'],
                                     d['prof'].get('fold_diacritics', True)),
                    st.get('part_pattern') or r'^%s\s+[ivx]+' % st['part_word'],
                    st.get('section_pattern') or r'^%s\s+(\d+)' % st['section_word'],
                    profile.normalise(d['prof']['labels']['annex_divider'],
                                      d['prof'].get('fold_diacritics', True)),
                    rtl=d['prof'].get('direction') == 'rtl',
                    fold=d['prof'].get('fold_diacritics', True))
                if a['wrong']:
                    problems.append('%d wrong page numbers %s' % (len(a['wrong']), a['wrong'][:2]))
                else:
                    print('      page numbers: %d confirmed, %d untestable, 0 wrong'
                          % (a['confirmed'], len(a['untestable'])))
                    if not quiet:
                        for label, why in a['untestable']:
                            print('          skip  %-46s %s' % (label, why))
                # An entry with no number is neither confirmed nor wrong, so the
                # line above reported a contents where five of six entries were
                # blank as a clean sweep. A warning, not a refusal: the document
                # is correct, its contents is just less useful than it looks.
                if a['unnumbered'] and not quiet:
                    print('      warn  %d contents entr%s could not be numbered - no '
                          'unambiguous heading in the printed pages; see print.md'
                          % (len(a['unnumbered']),
                             'y' if len(a['unnumbered']) == 1 else 'ies'))
                    for label in a['unnumbered'][:4]:
                        print('          warn  %s' % label)
        print('  %-38s %s' % (d['output'], 'ok' if not problems else 'FAIL: ' + '; '.join(problems)))
        failed += bool(problems)
    return failed


def do_publish(cfg, docs, expires=None):
    """Publish only what the gate clears. The allowlist says what *may* be
    published; lint says whether it is *fit* to be.

    Returns the number of documents the gate refused, so a refusal reaches the
    exit status. It used to print REFUSED and exit 0, which reads to anything
    automated - a release job, a scheduled rebuild - as a successful publish.
    A target declining one artefact is not counted: that is the host's policy,
    reported per artefact, and not this gate's verdict on the document.
    """
    refused = 0
    gate = gate_inputs(cfg, docs)
    for d in docs:
        if not d['publish']:
            print('  %-38s skipped (not publishable)' % d['output']); continue
        # every gate, not the two this used to run. `all` lints first and holds
        # a blocking document back, so the subset decided nothing there and
        # everything in a standalone `publish` against an artifact built earlier
        findings = lint.check_all(d, **gate)
        blocking = [f for f in findings if f['severity'] == 'block']
        if blocking:
            print('  %-38s REFUSED: %d blocking finding(s): %s' %
                  (d['output'], len(blocking), ', '.join(sorted({f['rule'] for f in blocking}))))
            refused += 1
            continue
        if not d['output_path'].exists():
            # a refusal like any other: a document declared publishable and
            # never built is not a publication that succeeded quietly
            print('  %-38s REFUSED: not built' % d['output'])
            refused += 1
            continue
        # the reading edition and the print edition are both deliverables
        editions = [d['output_path']]
        # Only a declared print edition ships. Publishing whatever .pdf happened
        # to be lying beside the HTML let a file appear on disk and reach a
        # public URL without anyone deciding - which is the one thing the
        # manifest exists to prevent.
        pdf = d['output_path'].with_suffix('.pdf')
        if d.get('pdf') and pdf.exists():
            editions.append(pdf)
        word = d['output_path'].with_suffix('.docx')
        if d.get('docx') and word.exists():
            editions.append(word)
        elif pdf.exists():
            print('  %-38s not published: no `pdf =` in the manifest' % pdf.name)

        target = d.get('target', 'realtimex')
        if target == 'realtimex' and not require.found('realtimex-pp-cli'):
            # optional in the same sense as the print edition: everything built
            # and verified, and the one step that needs a tool this machine does
            # not have is reported rather than crashing the run
            print('  %-38s skip  %s'
                  % (d['output'], require.why('realtimex-pp-cli',
                                              'nothing was published')))
            continue
        for artefact in editions:
            if target == 'directory':
                dest, how = pub.to_directory(artefact, cfg['_root'] / d.get('directory', 'dist'))
                print('  %-38s %s' % (artefact.name, how))
                continue
            # A target may refuse an edition: the RealTimeX artifact server
            # serves browser-viewable entry files, so it declines a .docx. That
            # is the host's policy and not ours to encode - encoding it here
            # would go stale the moment the host changed, and silently. So the
            # attempt is made and the refusal is reported per artefact.
            #
            # Per artefact, and not per run: this used to raise, which killed
            # the stage on the first refusal. Every later document went
            # unpublished and `record_run` never ran, so a run that had in fact
            # published two artefacts left no evidence that it had.
            try:
                dest, how = pub.link(artefact, d['workspace'])
                existing = pub.find(d['workspace'], artefact.name)
                art = existing or pub.publish(d['workspace'], artefact.name,
                                              expires_at=expires)
            except RuntimeError as err:
                reason = str(err).strip().splitlines()[-1][:120]
                print('  %-38s REFUSED by the target: %s' % (artefact.name, reason))
                continue
            print('  %-38s %s -> %s' % (artefact.name, how, art['publicUrl']))
    return refused


def main(argv=None):
    ap = argparse.ArgumentParser(prog='paperforge', description='Paperforge document pipeline')
    ap.add_argument('--label', help='name this run in the record')
    ap.add_argument('--out', help='brief, map: write to this file instead of stdout')
    ap.add_argument('--diff', help='runs: compare two runs, comma separated')
    ap.add_argument('--draft', action='store_true',
                    help='report every finding and refuse nothing; cannot publish')
    ap.add_argument('--sources', action='store_true',
                    help='runs --diff: show what changed in the sources, not only which')
    ap.add_argument('command', choices=['build', 'lint', 'verify', 'publish', 'all',
                                        'status', 'selftest', 'plugin', 'figures', 'init', 'runs',
                                     'brief', 'claims', 'map', 'doctor'])
    ap.add_argument('--json', action='store_true',
                    help='map: emit the map as JSON rather than for a reader')
    # optional value: `--accept` is every claim, `--accept claim-x` is one.
    # A build blocked on one paragraph used to be cleared by an action that
    # touched all of them
    ap.add_argument('--accept', nargs='?', const=True, metavar='CLAIM',
                    help='claims: re-stamp a gist against its paragraph, '
                         'or every gist if no claim is named')
    ap.add_argument('--only', help='limit to one document or collection')
    ap.add_argument('--expires-at', help='ISO timestamp for artifact expiry')
    ap.add_argument('--no-measure', action='store_true', help='skip printed page numbering')
    ap.add_argument('--config', help='path to documents.toml')
    ap.add_argument('--into', help='init: directory to prepare')
    ap.add_argument('--title', help='init: project title')
    ap.add_argument('--slug', help='init: short project name used for filenames')
    ap.add_argument('--profile', help='init: language profile (vi, en, zh, ar, ...)')
    ap.add_argument('--languages', help='init: comma-separated editions, e.g. vi,en')
    ap.add_argument('--publications', default='report',
                    help='init: comma-separated from report,book,brief,deck,annex')
    ap.add_argument('--organisation', default='Paperforge', help='init: short name')
    ap.add_argument('--publisher', help='init: full publisher line')
    ap.add_argument('--workspace', help='init: RealTimeX workspace for publishing')
    ap.add_argument('--no-git', action='store_true', help='init: skip git init')
    ap.add_argument('--check', action='store_true', help='report drift instead of syncing')
    ap.add_argument('--package', metavar='DIR',
                    help='plugin: write the installable zip into DIR')
    ap.add_argument('--tag', help='plugin: assert this release tag matches the version')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)
    if a.command == 'init':
        if not a.into:
            sys.exit('init needs --into <directory>')
        target = Path(a.into).resolve()
        slug = a.slug or target.name
        title = a.title or slug.replace('-', ' ').title()
        languages = [x.strip() for x in (a.languages or a.profile or 'en').split(',') if x.strip()]
        profiles = {lang: profile.load(lang) for lang in languages}
        kinds = [k.strip() for k in a.publications.split(',') if k.strip()]
        unknown = [k for k in kinds if k not in scaffold.BUILDERS]
        if unknown:
            sys.exit('unknown publication type(s): %s; choose from %s'
                     % (', '.join(unknown), ', '.join(scaffold.BUILDERS)))
        # an annex is embedded in its parent and never published alone, so it
        # needs one: a report or a book, both of which carry an appendix
        if 'annex' in kinds and not {'report', 'book'} & set(kinds):
            sys.exit('an annex is embedded in a report or a book; add one of them '
                     'to --publications')
        written = scaffold.create(target, slug, title, languages, profiles, kinds,
                                  a.organisation, a.publisher or a.organisation,
                                  a.workspace, git=not a.no_git)
        print('prepared %s' % target)
        for w in written:
            print('  %s' % w)
        print('\nnext: paperforge all --config %s/documents.toml' % target)
        return 0

    if a.command == 'plugin':
        from . import package_plugin
        # a reference that points nowhere still reads like prose, so the link
        # check runs on both paths rather than only on --check
        broken = ['reference: %s' % r for r in package_plugin.check_references()]
        broken += package_plugin.version_problems(a.tag)
        for problem in broken:
            print('  %s' % problem)
        if a.package:
            drift = package_plugin.check()
            if drift or broken:
                print('plugin package: REFUSED (%s)'
                      % ('stale bundle: ' + ', '.join(drift) if drift else 'see above'))
                return 1
            out = package_plugin.zip_bundle(a.package)
            print('  packaged %s' % out['path'])
            print('  %d files, %d bytes, sha256 %s'
                  % (out['files'], out['bytes'], out['sha256']))
            return 0
        if a.check:
            drift = package_plugin.check()
            print('plugin package: %s' % ('in sync' if not drift else 'STALE: ' + ', '.join(drift)))
            return 1 if (drift or broken) else 0
        for path in package_plugin.sync():
            print('  synced %s' % path)
        return 1 if broken else 0

    if a.command == 'doctor':
        # the tools are documented in SKILL.md and were never checked against
        # the machine; discovering typst is missing used to mean running
        # selftest, which builds a whole fixture and crashes
        print('external tools:')
        missing = 0
        for name, path, what in require.report():
            print('  %-18s %-9s %-52s %s'
                  % (name, 'ok' if path else 'MISSING', what, path or ''))
            missing += not path
        # chrome is found by probing application paths rather than by name, so
        # it is asked rather than looked up. Reporting it without asking would
        # be a check that says ok without checking.
        from . import browser
        try:
            found = browser.chrome()
        except RuntimeError:
            found = None
        print('  %-18s %-9s %-52s %s'
              % ('chrome', 'ok' if found else 'MISSING',
                 'diagrams, page measurement, layout checks', found or ''))
        missing += not found
        # what the machine has is half the answer; the other half is whether
        # this project's own guidance still describes the pipeline it names
        stale = _doctor_project(a.config)
        if not missing:
            # the scaffold section above has already said what to do about
            # drift; the advice below is about tools, and printing it under an
            # empty list of them said nothing to install and named nobody
            if not stale:
                print('\nnothing is missing.')
        else:
            print('')
            for name, path, _ in require.report():
                if not path:
                    print('  %s' % require.why(name))
            if not found:
                print('  headless Chrome is not installed. Needed for diagrams, page '
                      'measurement and layout checks. See https://www.google.com/chrome/')
            print('\nInstalling these is not the pipeline\'s to do. Ask whoever '
                  'owns this machine.')
        return 0

    if a.command == 'selftest':
        fixture = Path(__file__).resolve().parents[1] / 'tests/fixtures/en-sample/documents.toml'
        print('selftest: building the English fixture (%s)' % fixture.parent.name)
        return main(['all', '--config', str(fixture), '--quiet'])

    cfg, docs = load(a.config)
    # Say which project is being acted on. Without --config the manifest is
    # found by walking up, and a run started from a repository root that holds
    # one silently targets whatever it finds: on this pipeline's first real
    # project, a run labelled as peer review for one report rebuilt and
    # republished a different, already-approved corpus. The run record made it
    # visible afterwards; one line makes it visible before.
    # printed however the manifest was resolved: a wrapper that supplies
    # --config hides the choice just as effectively as the walk-up does
    print('project: %s' % cfg['_manifest'])
    cache = cfg['_cache']
    docs = pick(docs, a.only)

    if a.command == 'status':
        for d in docs:
            for artefact in [d['output_path'], d['output_path'].with_suffix('.pdf')]:
                if artefact.suffix == '.pdf' and not artefact.exists():
                    continue
                state = 'not built' if not artefact.exists() else (
                    'stale link' if pub.stale(artefact, d['workspace']) else 'linked')
                art = pub.find(d['workspace'], artefact.name) if d['publish'] else None
                print('  %-38s %-11s %s' % (artefact.name, state, art['publicUrl'] if art else '-'))
        return 0

    if a.command == 'brief':
        # the invocation as it actually happened, not a placeholder: whoever
        # reads this brief has to be able to paste the command
        text = brief.render(cfg, docs, sys.argv[0])
        if a.out:
            out = Path(a.out)
            out.write_text(text, encoding='utf-8')
            print('  wrote %s' % out)
        else:
            print(text)
        return 0

    if a.command == 'map':
        # what the document declares and what points at what. A report, not a
        # gate: some of what it shows is only a defect a reader can recognise.
        maps = [papermap.build(d, d['prof']) for d in docs]
        text = papermap.as_json(maps) if a.json else papermap.render(maps)
        if a.out:
            Path(a.out).write_text(text, encoding='utf-8')
            print('  wrote %s' % a.out)
        else:
            print(text, end='')
        return 0

    if a.command == 'runs':
        return do_runs(cfg, a.diff, a.only, a.sources)

    # A draft run reports every finding and refuses nothing, because every gate
    # here fires at the end and that is the worst moment to learn something.
    # `todo` blocks, every draft has TODOs, so `all` is unusable while a
    # document is being written - which is why it is not run until somebody
    # believes they are finished, exactly when a refusal costs most.
    #
    # It is only defensible because a draft run cannot publish. A mode that
    # turns refusals off is otherwise a documented way around the gates, and the
    # scaffolded AGENTS.md tells agents in as many words not to take one.
    draft = getattr(a, 'draft', False)
    if draft and a.command == 'publish':
        raise SystemExit('a draft run does not publish; that is what makes the '
                         'mode safe. Run `publish` without --draft when the '
                         'gates pass.')
    failed, stages, would_block = 0, {}, []
    if a.command in ('figures', 'all'):
        print('figures:')
        disagreements = do_figures(docs, a.quiet)
        stages['figures'] = 'disagreements' if disagreements else 'ok'
        if a.command == 'figures':
            return 1 if disagreements else 0
        if disagreements and draft:
            would_block.append('%d figure disagreement(s)' % disagreements)
        elif disagreements:
            failed = 1

    if a.command in ('claims', 'all'):
        print('claims:')
        stale = do_claims(docs, bool(a.accept), a.quiet,
                          a.accept if isinstance(a.accept, str) else None)
        stages['claims'] = 'stale' if stale else 'ok'
        if a.command == 'claims':
            return 1 if stale else 0
        if stale and draft:
            would_block.append('%d stale gist(s)' % stale)
        elif stale:
            failed = 1

    if a.command in ('lint', 'all'):
        print('lint:')
        blocking = do_lint(cfg, docs, a.quiet)
        stages['lint'] = 'blocked' if any(blocking.values()) else 'ok'
        if a.command == 'lint':
            return 1 if any(blocking.values()) else 0
        # carry on with the documents that passed; a blocked one must not stop the rest
        held = [d['output'] for d in docs if blocking.get(d['output'])]
        if draft:
            # a draft builds the document it is about to tell you is unfinished:
            # holding it back would leave nothing to look at, which is the whole
            # reason the gates were being avoided until the end
            if held:
                would_block.append('%d document(s) with blocking lint findings: %s'
                                   % (len(held), ', '.join(held)))
        else:
            docs = [d for d in docs if not blocking.get(d['output'])]
            if held:
                failed = 1
                print('  held back: %s' % ', '.join(held))

    if a.command in ('build', 'all'):
        print('build:')
        built = do_build(docs, cache, measure=not a.no_measure)
        stages['build'] = 'failed' if built else 'ok'
        if built:
            failed = 1

    if a.command in ('verify', 'all'):
        print('verify:')
        problems = do_verify(docs, cache, a.quiet)
        stages['verify'] = 'failed' if problems else 'ok'
        if problems:
            record_run(cfg, docs, stages, a.label)
            return 1

    if a.command == 'all' and draft:
        print('publish:')
        print('  a draft run does not publish. Nothing here has passed the gates.')
        stages['publish'] = 'draft'
    elif a.command in ('publish', 'all'):
        print('publish:')
        refused = do_publish(cfg, docs, a.expires_at)
        stages['publish'] = 'refused' if refused else 'ran'
        # a refusal is the gate working, and it has to reach the exit status:
        # a release job reading only that saw a refused publish as a done one
        failed = failed or bool(refused)

    # written for build and all, pass or fail: a run that went badly is exactly
    # the one worth being able to look at again
    if a.command in ('build', 'all'):
        record_run(cfg, docs, stages, a.label)

    if draft:
        # the inventory, which is what a draft run is for: not "you may not
        # ship this" but "here is what is left". Findings were printed by the
        # stages above; this says which of them publication would refuse.
        print('')
        if would_block:
            print('draft: nothing was held back. Publication would refuse:')
            for item in would_block:
                print('  %s' % item)
        else:
            print('draft: nothing would block publication.')
    return failed


if __name__ == '__main__':
    sys.exit(main())
