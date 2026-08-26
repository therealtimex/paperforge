"""The design tokens, declared once.

Every edition draws on the same palette, and until this module existed each one
carried its own copy: two stylesheet `:root` blocks, a `DEFAULTS` dict in the
Word emitter, and eight colour literals scattered through the Typst emitter. The
copies agreed on the shipped defaults, which is why nothing looked wrong - and
disagreed the moment a project declared a palette of its own. Measured on the
English fixture with all thirteen colour tokens overridden, three reached the
print edition and two reached Word; the most frequent non-black colour on the
printed page, at 818 occurrences, was one the project had overridden and could
not change.

A colour written as a literal in an emitter is correct by default and
unbrandable forever, and it reads as finished code either way. That is the trap
this module closes: `tests/unit_palette.py` fails on a colour literal appearing
in either emitter, rather than on any particular colour going missing.
"""

# The shipped defaults. Both stylesheets open with this block, filled in at
# build time rather than typed into each of them, so `deck.css` cannot drift
# from `paperforge.css` again. A project's palette is still layered *after* the
# theme by markdown.theme_override, which is what lets it win.
TOKENS = {
    'navy': '#243b53', 'navy-2': '#334e68', 'navy-3': '#486581',
    'navy-soft': '#e8eef8',
    'amber': '#8a6d1f', 'amber-soft': '#faf6ec', 'amber-line': '#f0dcbb',
    'red': '#a4262c', 'red-soft': '#fdf0f0', 'red-line': '#f0c9c9',
    'green': '#1f7a4d', 'green-soft': '#eefaf3', 'green-line': '#c6e9d6',
    'ink': '#1b2430', 'ink-soft': '#4a5568', 'muted': '#6b7789',
    'bg': '#eef1f6', 'paper': '#ffffff', 'line': '#dfe4ec', 'line-soft': '#eef1f6',
    'shadow': '0 1px 3px rgba(11,37,69,.06),0 12px 32px rgba(11,37,69,.08)',
    'sans': '"Be Vietnam Pro","Segoe UI",-apple-system,BlinkMacSystemFont,Roboto,'
            '"Helvetica Neue",Arial,sans-serif',
    'serif': 'Georgia,"Noto Serif","Times New Roman",Times,serif',
}

# The tokens an emitter can put on a page. `shadow` is a CSS shadow, and the two
# font stacks are resolved separately by each emitter: Word takes a single face
# rather than a fallback list, and a profile's stack is a glyph-coverage
# constraint rather than a preference - see docs/reference/languages.md.
COLOURS = frozenset(k for k, v in TOKENS.items() if v.startswith('#'))

# Screen-only by nature rather than by omission, and every one of them is about
# the sheet rather than about anything printed on it:
#   bg      the colour behind the sheet, and paper has no behind
#   paper   the sheet itself, which a printer supplies and cannot full-bleed
#   shadow  the lift under the sheet, which is the same absence
# `red` and `line-soft` were here too, each justified by a feature that did not
# exist yet rather than by the paper: the print emitter could not tell a warning
# callout from a note, and drew no soft rules. Both do now.
SCREEN_ONLY = frozenset(['bg', 'paper', 'shadow'])

# A callout's three colours: the rule down its edge, the fill behind it, and the
# hairline around it. The reading edition takes the type from `> [!WARNING]` and
# turns it into a class; the print and Word editions matched it, dropped it and
# drew a note. An unknown type is a note in every edition - which is what the
# stylesheet already did, having rules for two variants and a base.
CALLOUTS = {'note': ('amber', 'amber-soft', 'amber-line'),
            'warning': ('red', 'red-soft', 'red-line'),
            'tip': ('green', 'green-soft', 'green-line')}


def variant(kind):
    """The (rule, fill, hairline) tokens for a callout type."""
    return CALLOUTS.get((kind or 'note').lower(), CALLOUTS['note'])


# Mermaid names its theme in its own vocabulary, so the mapping onto these
# tokens is written down once here rather than inferred at each use. A node fill
# is `navy-soft` and not `navy`: a flowchart node filled with a structural
# colour at full strength has unreadable text on it.
MERMAID = {'primaryColor': 'navy-soft', 'primaryTextColor': 'navy',
           'primaryBorderColor': 'navy-3', 'lineColor': 'navy-3',
           'secondaryColor': 'amber-soft', 'tertiaryColor': 'line-soft',
           'clusterBkg': 'line-soft', 'clusterBorder': 'line',
           'titleColor': 'navy',
           'cScale0': 'navy', 'cScale1': 'navy-3', 'cScale2': 'amber'}


def resolve(prof=None, brand=None):
    """The palette this document is set in.

    Defaults, then the profile's faces, then the project's own - the same order
    the reading edition has always applied, so the editions cannot disagree
    about type. A brand key the table does not know is carried through: the
    stylesheet consumes a fixed set, but nothing is gained by dropping the rest
    on the floor.
    """
    tokens = dict(TOKENS)
    tokens.update((prof or {}).get('fonts') or {})
    tokens.update(brand or {})
    return tokens


def root(tokens):
    """The `:root` block both stylesheets open with."""
    return ':root {\n%s}' % ''.join('  --%s: %s;\n' % (k, tokens[k])
                                    for k in sorted(tokens))


def stylesheet(path):
    """A theme stylesheet with its `:root` filled in from the table above.

    The shipped defaults only: a project's own palette is layered after the
    theme by markdown.theme_override, so that it wins over anything the
    stylesheet declares for itself.
    """
    from pathlib import Path
    text = Path(path).read_text(encoding='utf-8')
    if '{{TOKENS}}' not in text:
        raise ValueError('%s has no {{TOKENS}} block to fill' % Path(path).name)
    return text.replace('{{TOKENS}}', root(TOKENS))


def channels(value):
    """A `#rrggbb` token as three 0-255 integers, for emitters that want them."""
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
