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

# The six colours a project actually chooses. Everything else is a shade of one
# of them, computed below.
BASE = {
    'navy': '#243b53',      # structure: parts, table headers, links, the cover
    'amber': '#8a6d1f',     # emphasis, annex material, note callouts
    'red': '#a4262c',       # warning callouts
    'green': '#1f7a4d',     # tip callouts
    'ink': '#1b2430',       # body text, and every grey derived from it
    'paper': '#ffffff',     # the sheet, which has no hue to shade
    'sans': '"Be Vietnam Pro","Segoe UI",-apple-system,BlinkMacSystemFont,Roboto,'
            '"Helvetica Neue",Arial,sans-serif',
    'serif': 'Georgia,"Noto Serif","Times New Roman",Times,serif',
}

# Every other token, as (base, lightness %, saturation factor, hue turn°).
#
# These numbers are *fitted from the palette as it was shipped*, not invented:
# each one reproduces its hand-picked value to the byte, which is the finding
# that produced this table. The design was already a shade system - a hue held
# steady, a lightness ramp, saturation lifted in the darks - and nobody had
# written the system down, so twenty-four values were maintained by eye and ten
# more like them were loose in the stylesheets where no project could reach them.
#
# The hue turns are small and deliberate. The amber ramp warms as it darkens,
# -12° by the deepest step, which is why fitting it on lightness and saturation
# alone left it 26/255 out; the navy ramp holds its hue to within 7°.
SHADES = {
    'navy-2':       ('navy',   30.4, 0.87,  -1.2),   # h3 headings
    'navy-3':       ('navy',   39.4, 0.72,  -1.2),   # h2 headings, links
    'navy-strong':  ('navy',   18.8, 1.79,  +3.8),   # bold body text
    'navy-deep':    ('navy',   12.0, 1.95,  +3.8),   # cover gradient start, code
    'navy-dark':    ('navy',   15.7, 1.84,  +2.5),   # cover gradient middle
    'navy-mid':     ('navy',   21.8, 1.67,  +4.7),   # cover gradient end
    'navy-glow':    ('navy',   30.6, 1.62,  +1.8),   # the light over the cover
    'navy-pale':    ('navy',   68.0, 0.95,  +3.8),   # metadata keys on the cover
    'navy-wash':    ('navy',   85.7, 1.08,  +4.2),   # lede and topbar text
    'navy-soft':    ('navy',   94.1, 1.35,  +6.9),   # diagram nodes, code text
    'navy-tint':    ('navy',   98.2, 1.41,  +5.4),   # banded table rows
    'amber-bright': ('amber',  72.0, 1.34,  -6.1),   # on the dark cover
    'amber-lift':   ('amber',  36.1, 1.17, -10.7),   # annex banner, progress
    'amber-deep':   ('amber',  28.8, 1.39, -12.1),   # links on light ground
    'amber-line':   ('amber',  83.7, 1.01,  -6.4),   # note callout hairline
    'amber-soft':   ('amber',  95.3, 0.92,  -0.9),   # note callout fill
    'red-line':     ('red',    86.5, 0.91,  +2.9),   # warning callout hairline
    'red-soft':     ('red',    96.7, 1.23,  +2.9),   # warning callout fill
    'green-line':   ('green',  84.5, 0.74,  -2.9),   # tip callout hairline
    'green-soft':   ('green',  95.7, 0.92,  -5.3),   # tip callout fill
    'ink-soft':     ('ink',    34.9, 0.60,  +3.7),   # captions, affiliations
    'muted':        ('ink',    47.8, 0.44,  +1.7),   # running heads, meta labels
    'line':         ('ink',    90.0, 0.91,  +2.6),   # rules and table strokes
    'line-soft':    ('ink',    94.9, 1.10,  +3.2),   # the softest rule
    'bg':           ('ink',    94.9, 1.10,  +3.2),   # behind the sheet, on screen
}


def shade(value, light, sat=1.0, turn=0.0):
    """A base colour at another lightness, on the same hue.

    HSL rather than a perceptual space on purpose: HSL is what the values were
    picked in, so it is what reproduces them, and a rule that cannot reproduce
    the design it claims to describe is a different design.
    """
    import colorsys
    r, g, b = (int(value.lstrip('#')[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hue, _, saturation = colorsys.rgb_to_hls(r, g, b)
    hue = ((hue * 360 + turn) % 360) / 360.0
    saturation = max(0.0, min(1.0, saturation * sat))
    return '#%02x%02x%02x' % tuple(
        round(c * 255) for c in colorsys.hls_to_rgb(hue, light / 100.0, saturation))



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

    Bases, then the profile's faces, then the project's own - the same order the
    reading edition has always applied, so the editions cannot disagree about
    type. Then every shade the project did not name for itself is recomputed
    from whichever base it hangs off, so a project that declares `navy` gets a
    cover, a code block and a set of diagram nodes in its own colour without
    having to know that those exist.

    A shade the project *did* name wins outright: a house style with a specific
    cover is not obliged to accept one derived from its structural navy.

    A brand key the table does not know is carried through. The stylesheet
    consumes a fixed set, but nothing is gained by dropping the rest.
    """
    brand = brand or {}
    tokens = dict(BASE)
    tokens.update((prof or {}).get('fonts') or {})
    tokens.update(brand)
    for name, (base, light, sat, turn) in SHADES.items():
        if name not in brand:
            tokens[name] = shade(tokens[base], light, sat, turn)
    return tokens


# The palette as shipped: what the stylesheets are filled with, and what stands
# in for the emitters until a document is built.
TOKENS = resolve()

COLOURS = frozenset(k for k, v in TOKENS.items() if v.startswith('#'))


# The translucent tokens: a base shown through, at a fixed strength.
#
# The strengths are structural rather than editorial - a topbar at 97% is a
# topbar, not a decision - so a veil is not overridable on its own. Change its
# base and it follows.
VEILS = {
    'navy-veil':    ('navy-dark', 97),      # the topbar over scrolling content
    'navy-screen':  ('navy-dark', 75),      # a deck's slide number
    'navy-shade':   ('navy-dark', 28),      # the lift under a raised card
    'navy-film':    ('navy-dark', 13),      # the fade at a scrollable edge
    'navy-ghost':   ('navy-dark',  4),      # the rest state of the same card
    'navy-mark':    ('navy-glow', 35),      # the underline beneath a link
    'amber-veil':   ('amber-bright', 50),   # the cover badge's edge
    'amber-film':   ('amber-bright', 10),   # the cover badge's ground
    'amber-shade':  ('amber-lift', 35),     # the annex badge's edge
    'amber-wash':   ('amber-lift', 14),     # the annex badge's ground
    'paper-film':   ('paper', 12),          # a hairline reversed out of navy
}


def alpha(value, percent):
    """A token at a percentage, as eight-digit hex."""
    return '%s%02x' % (value, round(percent * 255 / 100.0))


def veil_rules(tokens, names=None):
    """Each veil twice: a resolved value, then the same thing as a color-mix.

    The fallback is not a compromise here and the color-mix is not load-bearing.
    This stylesheet is *generated*, so the build already knows what `navy-dark`
    resolved to for this project and can write the eight-digit hex itself -
    correct under any brand, on any browser back to 2016. The color-mix line
    restates it against the live custom property, which is what keeps the two
    from parting company if a token is ever overridden after the sheet is
    written. A browser that does not know color-mix drops that line and is left
    holding the right colour rather than a fallback for one.
    """
    out = []
    for name, (base, percent) in sorted(VEILS.items()):
        if names is not None and base not in names:
            continue
        out.append('  --%s: %s;' % (name, alpha(tokens[base], percent)))
        out.append('  --%s: color-mix(in oklab, var(--%s) %d%%, transparent);'
                   % (name, base, percent))
    return out


def shadow(tokens):
    """The lift under the sheet: the cover navy, twice, very faint."""
    return '0 1px 3px %s,0 12px 32px %s' % (alpha(tokens['navy-dark'], 6),
                                            alpha(tokens['navy-dark'], 8))


def root(tokens):
    """The `:root` block both stylesheets open with."""
    lines = ['  --%s: %s;' % (k, tokens[k]) for k in sorted(tokens)]
    lines.append('  --shadow: %s;' % shadow(tokens))
    return ':root {\n%s\n}' % '\n'.join(lines + veil_rules(tokens))


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
