"""Check that documents agree on the project's canonical figures.

Policy prose states the same number many ways, and the same number appears in
many documents: in this corpus one target is written out eight times across four
files. Substituting a template into the sentence would ruin the prose, so the
figures are declared once and every statement of them is checked instead.

A finding is a *disagreement*, not a style note: a line that talks about a
declared fact and states a value that is not one of its accepted forms.
"""
import re
import tomllib
from pathlib import Path

FENCE = re.compile(r'```.*?```', re.S)


def load(path):
    """Declared figures.

    `accept` lists the correct surface forms. A value written differently in
    each language - Vietnamese "50.000", English "50,000" - declares them under
    [figure.surface] per language, so a correct translation is never reported as
    a disagreement.
    """
    data = tomllib.load(open(path, 'rb'))
    figures = []
    for f in data.get('figure', []):
        surface = {lang: forms for lang, forms in (f.get('surface') or {}).items()}
        figures.append({**f, 'surface': surface,
                        'context_re': re.compile(f['context'], re.I),
                        'value_re': re.compile(f['pattern'])})
    return figures


def _normalise(text):
    """Compare on shape, not spacing: "55 - 60 %" and "55-60%" are one value."""
    return re.sub(r'\s+', '', text).replace('–', '-').replace('—', '-')


def check_file(path, figures, language=None):
    text = FENCE.sub(lambda m: '\n' * m.group(0).count('\n'),
                     Path(path).read_text(encoding='utf-8'))
    accepted = {}
    for f in figures:
        forms = list(f.get('accept', []))
        if language and f['surface']:
            # a declared language uses its own forms; other languages' forms are
            # not acceptable here, which is the point of declaring them
            forms = list(f['surface'].get(language, forms))
        accepted[f['id']] = {_normalise(a) for a in forms}
    findings = []
    for line_no, line in enumerate(text.split('\n'), 1):
        for f in figures:
            if not f['context_re'].search(line):
                continue
            for m in f['value_re'].finditer(line):
                if _normalise(m.group(0)) not in accepted[f['id']]:
                    expected = (f['surface'].get(language) or f.get('accept') or ['?'])[0]
                    findings.append({'file': Path(path).name, 'line': line_no,
                                     'figure': f['id'], 'found': m.group(0),
                                     'expected': expected, 'language': language,
                                     'label': f['label'],
                                     'context': line.strip()[:88]})
    return findings


def stated(paths, figures):
    """The ids some document actually states, however it states them.

    A disagreement is still a statement. A figure written wrongly somewhere is
    in use, and reporting it as unused as well would be two findings about one
    fact, the second of them false.
    """
    seen = set()
    for path in paths:
        text = FENCE.sub(lambda m: '\n' * m.group(0).count('\n'),
                         Path(path).read_text(encoding='utf-8'))
        for line in text.split('\n'):
            for f in figures:
                if f['id'] not in seen and f['context_re'].search(line) \
                        and f['value_re'].search(line):
                    seen.add(f['id'])
    return seen


def check(paths, figures_file, languages=None):
    """`languages` maps a source path to the language it is written in, so each
    document is checked against its own edition's surface forms."""
    figures = load(figures_file)
    languages = languages or {}
    findings = []
    for p in paths:
        findings += check_file(p, figures, languages.get(str(p)))
    return findings, figures
