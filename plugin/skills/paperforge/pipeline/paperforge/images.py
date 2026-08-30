"""An illustration from a file: found, inlined, or refused.

A diagram is written in the document and drawn at build time, so it cannot go
missing. An image is the other kind of figure - a photograph, a chart exported
from an analysis, a scanned trace - and it is a *reference to a file*, which is
the only thing in a document that can be true when it is written and false when
it is built. Someone renames a directory and the paper still says "see Figure
1"; nothing in the prose changed, so nothing in the prose looks wrong.

So the file is resolved here, once, and a reference that resolves to nothing is
a demonstrated contradiction between the markdown and the disk - a `block`, not
a warning. There is no reading of a missing file under which the document is
correct.

What is found is inlined as a data URI rather than linked. `layout.md` says it
plainly - no CDN, no runtime library, no external image - and a published
document is one file that has to open on a machine that has never seen the
project. A relative `src=` survives `verify`, which only refuses `http(s)://`,
and then breaks the moment the file travels alone.
"""
import base64
import mimetypes
import re
from pathlib import Path

# `![alt](src)`. The alt is optional and may be empty; the src may not contain
# whitespace, matching the link pattern the emitters already use.
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)\)')

# A line that is nothing but an image is a float. One inside a sentence is an
# inline image and stays where the author put it.
ONLY_RE = re.compile(r'^\s*!\[([^\]]*)\]\(([^)\s]+)\)\s*$')

REMOTE_RE = re.compile(r'^(?:https?:)?//', re.I)


def refs(lines):
    """(line number, alt, src) for every image reference, in order."""
    out = []
    fenced = False
    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            fenced = not fenced
        if fenced:
            continue
        for m in IMAGE_RE.finditer(line):
            out.append((i + 1, m.group(1), m.group(2)))
    return out


def resolve(src, root):
    """The file an image reference names, or None.

    Relative to the document's own directory, which is where an author is
    looking when they type the path. A remote src resolves to nothing here on
    purpose: it is refused by lint rather than fetched, because a build that
    reaches the network produces a different document on a different day.
    """
    if REMOTE_RE.match(src) or src.startswith('data:'):
        return None
    path = Path(src)
    if not path.is_absolute():
        path = Path(root) / path
    return path if path.is_file() else None


def data_uri(path):
    """The file as a data URI, so the document carries its own illustrations."""
    path = Path(path)
    mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    if path.suffix.lower() == '.svg':
        mime = 'image/svg+xml'
    data = base64.b64encode(path.read_bytes()).decode('ascii')
    return 'data:%s;base64,%s' % (mime, data)
