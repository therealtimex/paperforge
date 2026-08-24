"""Paperforge pipeline: build -> lint -> verify -> publish."""
import argparse
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

from . import (brief, deck, diagrams, docx as docx_mod, editions, figures, lint,
               markdown, pages, profile, publish as pub, runs, scaffold, typst,
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


# A document type implies how it is rendered, so the manifest names the type
# rather than repeating layout and format mechanics.
# Built-in document types. A project defines its own under [types] in the
# manifest - a due-diligence memo, a board pack, a case study - because the set
# of things research teams publish is not ours to enumerate.
BUILTIN_TYPES = {
    'report': {'layout': 'report'},
    'brief': {'layout': 'brief'},
    'deck': {'format': 'deck'},
    'note': {'layout': 'brief', 'page_numbers': False},
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
                docs.append(doc)
    return cfg, docs


def pick(docs, only):
    if not only:
        return docs
    chosen = [d for d in docs if only in (d['source'], d['output'], d['collection'])]
    if not chosen:
        sys.exit('no document matches %r' % only)
    return chosen


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
        print('  %-38s %d figure(s) declared, %d document(s) checked, %s'
              % (path.name, len(declared), len(sources),
                 'consistent' if not found else '%d DISAGREEMENT(S)' % len(found)))
        for f in found:
            print('      %s:%s  %s' % (f['file'], f['line'], f['label']))
            print('          found %r, expected %r' % (f['found'], f['expected']))
            if not quiet:
                print('          %s' % f['context'])
    return total


def active_rules(cfg):
    section = cfg.get('lint') or {}
    return lint.ruleset(section.get('packs', []), section.get('rule', []))


def do_lint(cfg, docs, quiet=False):
    """Report gate findings; returns {source: blocking count}."""
    rules = active_rules(cfg)
    allowed = {d['source'] for d in docs}          # declared, drafts included
    embedded = {d['annex'] for d in docs if d.get('annex')}
    blocked = set(cfg['internal']['files'])
    result = {}
    for d in docs:
        findings = lint.check_document(d['source_path'], rules)
        findings += lint.check_publishable(d['source_path'], allowed, blocked, embedded)
        if d['annex_path']:
            findings += lint.check_document(d['annex_path'], rules)
        s = lint.summarise(findings)
        result[d['source']] = s['blocking']
        state = 'BLOCKED' if s['blocking'] else ('warn' if s['total'] else 'ok')
        print('  %-38s %s' % (d['source'], state))
        if not quiet:
            for f in findings:
                print('      %-8s L%-5s %-16s %s' %
                      (f['severity'], f['line'] or '-', f['rule'], f['context'][:76] or f['why']))
    return result


def opts(d):
    """Render options for one document, shared by every build call so the
    first pass and the page-number rebuild cannot drift apart."""
    return {'contents_heading': d.get('contents_heading'),
            'kind_fallback': d.get('title_kind'), 'prof': d['prof'],
            'organisation': d.get('organisation'), 'publisher': d.get('publisher'),
            'footer_note': d.get('footer_note'), 'annex_label': d.get('annex_label'),
            'brand': d.get('brand'), 'logo': d.get('logo_path'),
            'bibliography': (d['root'] / d['bibliography']) if d.get('bibliography') else None,
            'citation_style': d.get('citation_style', 'apa'),
            'layout': d.get('layout', 'report')}


def record_run(cfg, docs, stages, label=None):
    out = runs.write(cfg, docs, stages, label)
    print('  recorded %s' % out.relative_to(cfg['_root']))
    return out


def do_runs(cfg, pair, only):
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
        srcs = diagrams.sources(d['source_path'], d['annex_path'])
        svgs = diagrams.render(srcs, cache=cache / ('%s.diagrams.json' % d['source']))
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
        stats = markdown.build(d['source_path'], d['output_path'], svgs=svgs,
                               annex=d['annex_path'], pages=None, **opts(d))
        if measure and d.get('page_numbers'):
            from . import browser
            pdf = cache / (d['output'] + '.pdf')
            browser.print_pdf(d['output_path'], pdf)
            body = ''.join(p.read_text(encoding='utf-8')
                           for p in [d['source_path']] + ([d['annex_path']] if d['annex_path'] else []))
            quality = pages.extractable(pdf, len(re.sub(r'\s|[|#*`>-]', '', body)))
            if not quality['usable']:
                print('  %-38s printed page numbers skipped: only %.0f%% of the text is '
                      'readable back from the PDF (font has no usable ToUnicode map)'
                      % (d['output'], 100 * quality['ratio']))
                d['page_numbers'] = False
                d['_text_unreadable'] = True
        if measure and d.get('page_numbers'):
            # measure the printed pagination, bake it in, and repeat until stable
            for _ in range(3):
                pdf = cache / (d['output'] + '.pdf')
                from . import browser
                browser.print_pdf(d['output_path'], pdf)
                found, info = pages.measure(str(d['output_path']), str(pdf),
                                            markdown.slugify(d['contents_heading'],
                                                             d['prof'].get('fold_diacritics', True)))
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
        if d.get('pdf') == 'typst':
            pdf_out = d['output_path'].with_suffix('.pdf')
            try:
                info = typst.build(d['source_path'], pdf_out, d['prof'], svgs=svgs,
                                   annex=d['annex_path'], title_kind=d.get('title_kind'),
                                   organisation=d.get('organisation', ''),
                                   brand=d.get('brand'), cache=cache, logo=d.get('logo_path'),
                                   contents_heading=d.get('contents_heading'),
                                   bibliography=(d['root'] / d['bibliography'])
                                   if d.get('bibliography') else None,
                                   citation_style=d.get('citation_style', 'apa'))
                print('  %-38s %s' % (pdf_out.name, json.dumps(info, ensure_ascii=False)))
            except (RuntimeError, FileNotFoundError) as err:
                print('  %-38s typst FAILED: %s' % (pdf_out.name, str(err).splitlines()[0][:90]))
                failures.append(pdf_out.name)

        # Word, for the reader who has to work on the document rather than read
        # it: lift a section into a submission, comment, track changes.
        if d.get('docx'):
            docx_out = d['output_path'].with_suffix('.docx')
            try:
                info = docx_mod.build(d['source_path'], docx_out, d['prof'], svgs=svgs,
                                      annex=d['annex_path'], title_kind=d.get('title_kind'),
                                      organisation=d.get('organisation', ''),
                                      brand=d.get('brand'), cache=cache, logo=d.get('logo_path'),
                                      contents_heading=d.get('contents_heading'))
                print('  %-38s %s' % (docx_out.name, json.dumps(info, ensure_ascii=False)))
            except Exception as err:
                print('  %-38s docx FAILED: %s' % (docx_out.name, str(err).splitlines()[0][:90]))
                failures.append(docx_out.name)

        # The browser already prints the document to measure its pagination, but
        # that copy is a cache by-product. `pdf = "chrome"` promotes it to a
        # named deliverable, so a print edition from the reading edition's own
        # layout is something the manifest asks for rather than something a
        # person links out of .cache by hand.
        elif d.get('pdf') == 'chrome':
            pdf_out = d['output_path'].with_suffix('.pdf')
            measured = cache / (d['output'] + '.pdf')
            if not measured.exists():
                browser.print_pdf(d['output_path'], measured)
            if measured.exists():
                shutil.copyfile(measured, pdf_out)
                print('  %-38s {"bytes": %d, "from": "chrome"}'
                      % (pdf_out.name, pdf_out.stat().st_size))
            else:
                print('  %-38s chrome print FAILED' % pdf_out.name)
                failures.append(pdf_out.name)
    return failures


def do_verify(docs, cache):
    failed = 0
    for d in docs:
        if not d['output_path'].exists():
            print('  %-38s NOT BUILT' % d['output']); failed += 1; continue
        r = verify.check(d['output_path'], d['source_path'], d['annex_path'])
        if d.get('format') == 'deck':
            problems = []
            if r['external_refs']:
                problems.append('external refs %s' % r['external_refs'][:2])
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
        if r['external_refs']:
            problems.append('external refs %s' % r['external_refs'][:2])
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
            ed = editions.compare(d['output_path'], pdf_edition)
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

        lay = verify.layout(d['output_path'])
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
            body = ''.join(p.read_text(encoding='utf-8') for p in
                           [d['source_path']] + ([d['annex_path']] if d['annex_path'] else []))
            quality = pages.extractable(pdf, len(re.sub(r'\s|[|#*`>-]', '', body)))
            readable = quality['usable']
            if not readable:
                print('      print checks skipped: only %.0f%% of the text is readable back '
                      'from the PDF' % (100 * quality['ratio']))
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
            cut = verify.print_truncation(pdf, d['source_path'], d['annex_path'])
            if cut['unlocated']:
                print('      print: %d of %d source URL(s) not found whole - check whether '
                      'a table row spans a page break: %s'
                      % (len(cut['unlocated']), cut['checked'],
                         ', '.join(u[:38] for u in cut['unlocated'][:2])))
            elif cut['checked']:
                print('      print: all %d source URL(s) survive the page' % cut['checked'])
            pg = verify.pagination(pdf, exempt=exempt,
                                  script=d['prof'].get('script', 'latin'))
            if pg['thin']:
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
                                      d['prof'].get('fold_diacritics', True)))
                if a['wrong']:
                    problems.append('%d wrong page numbers %s' % (len(a['wrong']), a['wrong'][:2]))
                else:
                    print('      page numbers: %d confirmed, %d untestable, 0 wrong'
                          % (a['confirmed'], a['untestable']))
        print('  %-38s %s' % (d['output'], 'ok' if not problems else 'FAIL: ' + '; '.join(problems)))
        failed += bool(problems)
    return failed


def do_publish(cfg, docs, expires=None):
    """Publish only what the gate clears. The allowlist says what *may* be
    published; lint says whether it is *fit* to be."""
    allowed = {x['source'] for x in docs}
    embedded = {x['annex'] for x in docs if x.get('annex')}
    blocked_files = set(cfg['internal']['files'])
    for d in docs:
        if not d['publish']:
            print('  %-38s skipped (not publishable)' % d['output']); continue
        rules = active_rules(cfg)
        findings = lint.check_document(d['source_path'], rules)
        findings += lint.check_publishable(d['source_path'], allowed, blocked_files, embedded)
        if d['annex_path']:
            findings += lint.check_document(d['annex_path'], rules)
        blocking = [f for f in findings if f['severity'] == 'block']
        if blocking:
            print('  %-38s REFUSED: %d blocking finding(s): %s' %
                  (d['output'], len(blocking), ', '.join(sorted({f['rule'] for f in blocking}))))
            continue
        if not d['output_path'].exists():
            print('  %-38s REFUSED: not built' % d['output']); continue
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
        for artefact in editions:
            if target == 'directory':
                dest, how = pub.to_directory(artefact, cfg['_root'] / d.get('directory', 'dist'))
                print('  %-38s %s' % (artefact.name, how))
                continue
            dest, how = pub.link(artefact, d['workspace'])
            existing = pub.find(d['workspace'], artefact.name)
            art = existing or pub.publish(d['workspace'], artefact.name, expires_at=expires)
            print('  %-38s %s -> %s' % (artefact.name, how, art['publicUrl']))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='paperforge', description='Paperforge document pipeline')
    ap.add_argument('--label', help='name this run in the record')
    ap.add_argument('--out', help='brief: write to this file instead of stdout')
    ap.add_argument('--diff', help='runs: compare two runs, comma separated')
    ap.add_argument('command', choices=['build', 'lint', 'verify', 'publish', 'all',
                                        'status', 'selftest', 'plugin', 'figures', 'init', 'runs',
                                     'brief'])
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
                    help='init: comma-separated from report,brief,deck,annex')
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
        if 'annex' in kinds and 'report' not in kinds:
            sys.exit('an annex is embedded in a report; add report to --publications')
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

    if a.command == 'runs':
        return do_runs(cfg, a.diff, a.only)

    failed, stages = 0, {}
    if a.command in ('figures', 'all'):
        print('figures:')
        disagreements = do_figures(docs, a.quiet)
        stages['figures'] = 'disagreements' if disagreements else 'ok'
        if a.command == 'figures':
            return 1 if disagreements else 0
        if disagreements:
            failed = 1

    if a.command in ('lint', 'all'):
        print('lint:')
        blocking = do_lint(cfg, docs, a.quiet)
        stages['lint'] = 'blocked' if any(blocking.values()) else 'ok'
        if a.command == 'lint':
            return 1 if any(blocking.values()) else 0
        # carry on with the documents that passed; a blocked one must not stop the rest
        held = [d['output'] for d in docs if blocking.get(d['source'])]
        docs = [d for d in docs if not blocking.get(d['source'])]
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
        problems = do_verify(docs, cache)
        stages['verify'] = 'failed' if problems else 'ok'
        if problems:
            record_run(cfg, docs, stages, a.label)
            return 1

    if a.command in ('publish', 'all'):
        print('publish:')
        do_publish(cfg, docs, a.expires_at)
        stages['publish'] = 'ran'

    # written for build and all, pass or fail: a run that went badly is exactly
    # the one worth being able to look at again
    if a.command in ('build', 'all'):
        record_run(cfg, docs, stages, a.label)
    return failed


if __name__ == '__main__':
    sys.exit(main())
