"""Language and document-convention profiles.

Keeps structural vocabulary out of the code: which headings open a part, what a
figure is called, how a cross-reference to an annex section reads. A research
project picks a profile in its manifest; nothing in the pipeline hard-codes a
language.
"""
import re
import tomllib
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent / 'profiles'


def normalise(text, fold_diacritics=True):
    """Case-folded form used for structural matching.

    Keeps letters of every script. The previous ASCII-only filter erased
    Chinese, Arabic, Thai, Cyrillic and Devanagari entirely, which made
    structural matching impossible outside Latin script.

    `fold_diacritics` strips combining marks, which is what Vietnamese wants
    (PHẦN -> phan) but is destructive where marks carry meaning, as in Arabic,
    Thai and Devanagari - those profiles turn it off.
    """
    text = text.replace('Đ', 'D').replace('đ', 'd').replace('Ð', 'D')
    if fold_diacritics:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
    else:
        text = unicodedata.normalize('NFC', text)
    text = text.casefold()
    # Keep letters and digits of any script, plus combining marks: Python's \w
    # excludes marks, which silently gutted Thai and Devanagari vowel signs.
    text = ''.join(c if (c.isalnum() or unicodedata.category(c).startswith('M')
                         or c in ' .:') else ' ' for c in text)
    return re.sub(r'\s+', ' ', text).strip()


def available():
    return sorted(p.stem for p in DIR.glob('*.toml'))


def merge(base, override):
    """Deep-merge a project's own declarations over a shipped profile."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def load_file(path, base=None):
    """A project-local profile.

    Lets a research team declare their own conventions - what a part heading
    looks like, what a figure is called - without a pipeline release. Layered
    over a shipped profile when one is named, so a team overrides only what
    differs, and a language nobody has shipped a profile for still works.
    """
    data = tomllib.load(open(path, 'rb'))
    profile = merge(base, data) if base else data
    for section in ('labels', 'ui', 'structure'):
        profile.setdefault(section, {})
    profile.setdefault('name', Path(path).stem)
    return profile


def load(name='vi'):
    path = DIR / ('%s.toml' % name)
    if not path.exists():
        raise ValueError('unknown profile %r; available: %s' % (name, ', '.join(available())))
    data = tomllib.load(open(path, 'rb'))
    for section in ('labels', 'ui', 'structure'):
        data.setdefault(section, {})
    data['name'] = name
    return data
