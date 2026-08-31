"""An authored gist for a claim, and the gate that stops it going stale.

Code has a compiler. Rename a function, miss a call site, and the build fails.
A paper has nothing: change what a paragraph argues, leave its one-line gist
alone, and nothing anywhere complains. A stale gist is worse than no gist,
because whatever reads it - somebody skimming, a model handed the document -
trusts it completely, and the drift is invisible from the output.

So the gist is written by a person and only ever *checked* here. Generating one
would produce a summary that has to be reviewed before it can be trusted, which
is the work it claimed to remove; and by the time the prose has drifted, a
summary of the prose is a summary of the drift.

What is stored is a hash of the prose, taken with the label stripped, so
rewording a gist does not mark it stale and rewriting the paragraph does.
Re-stamping is deliberate - `paperforge claims --accept` - because that is the
moment somebody reread the paragraph and said the gist still holds. Nothing
stamps itself.
"""
import hashlib
import json
import re
from pathlib import Path

from . import xref

LOCK = '.paperforge/claims.json'

GIST_RE = re.compile(r'gist\s*=\s*"([^"]*)"')

# `uses=claim-a,claim-b`. Bare rather than quoted: a label id is [\w-]+ and
# cannot hold a space, a comma or a quote, so quoting would buy nothing and add
# the failure mode `truncated-gist` exists to catch. A gist needs quotes because
# prose does.
USES_RE = re.compile(r'uses\s*=\s*([\w-]+(?:\s*,\s*[\w-]+)*)')
ID_RE = re.compile(r'#[\w-]+')
CLASS_RE = re.compile(r'\.[\w-]+')

# The same condition the emitters' paragraph loops use. A claim's paragraph is
# the run of lines ending on its label, so this has to stop where they stop or
# the hash would cover text the reader sees as a different block.
STOP_RE = re.compile(r'^(?:```|>|\||#)|^\s*(?:[-*+]\s|\d+[.)]\s)|^(?:-{3,}|\*{3,}|_{3,})$')


def parse(attrs):
    """(gist, uses, leftover) for a claim's attribute block.

    `leftover` is everything the parser did not understand. It is returned
    rather than ignored because the quiet failures here all look like success:
    `uses=a b` reads one edge and drops the other, `use=a` reads none, and
    neither says anything. Lint refuses a claim with anything left over.
    """
    rest, gist = attrs, GIST_RE.search(attrs)
    if gist:
        rest = GIST_RE.sub(' ', rest, count=1)
    uses = USES_RE.search(rest)
    names = [u.strip() for u in uses.group(1).split(',') if u.strip()] if uses else []
    if uses:
        rest = USES_RE.sub(' ', rest, count=1)
    rest = CLASS_RE.sub(' ', ID_RE.sub(' ', rest))
    return (gist.group(1) if gist else None, names, rest.strip())


def _prose(text):
    """A paragraph reduced to what it says, so whitespace is not a change."""
    return re.sub(r'\s+', ' ', text).strip()


def fingerprint(text):
    return hashlib.sha256(_prose(text).encode('utf-8')).hexdigest()[:16]


def find(lines):
    """{id: {'gist', 'text', 'line'}} for every labelled paragraph.

    A claim labels itself at the end of its own paragraph, so the paragraph is
    the run of lines ending on the label. Nothing else in the pipeline needs a
    paragraph's boundaries, which is why this walks them here.
    """
    found = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if xref.HEADING_RE.match(stripped):
            continue
        body, ident = xref.take_claim(stripped)
        if not ident:
            continue
        attrs = xref.ATTR_RE.search(stripped)
        gist, uses, leftover = parse(attrs.group(1)) if attrs else (None, [], '')
        start = i
        while start > 0:
            above = lines[start - 1].strip()
            if not above or STOP_RE.match(above):
                break
            start -= 1
        text = ' '.join([l.strip() for l in lines[start:i]] + [body])
        found[ident] = {'gist': gist, 'uses': uses, 'leftover': leftover,
                        'text': _prose(text), 'line': i + 1}
    return found


def edges(rec, table=None):
    """What a claim draws on: what it says, plus what it was told.

    The references and citations inside the paragraph are *in the paragraph* -
    reading them is measurement, the same operation `xref.dangling` does,
    scoped to one block. Only a claim-to-claim edge has to be declared, because
    `@claim-x` is blocked in prose and there is nothing on the page to resolve.
    """
    from . import citations as cite_mod
    drawn = xref.referenced([rec['text']], table)
    drawn |= {'@' + key for key in cite_mod.find(rec['text'])}
    return sorted(drawn | set(rec.get('uses') or []))


def collect(sources):
    """Every claim across a project's sources, with the file it is in."""
    out = {}
    for path in sources:
        lines = Path(path).read_text(encoding='utf-8').split('\n')
        for ident, rec in find(lines).items():
            out[ident] = dict(rec, file=Path(path).name)
    return out


def load(root):
    path = Path(root) / LOCK
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        # a lock nobody can read is a lock that vouches for nothing
        return {}


def save(root, data):
    path = Path(root) / LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return path


def check(sources, root):
    """Findings about the project's claims, worst first.

    `stale` blocks: the paragraph moved under a gist that was once accepted
    against it, which is a demonstrated contradiction. `unaccepted` is manual -
    the answer is not the pipeline's to give, and the finding names the command
    that settles it. The rest warn: a claim with no gist has not promised
    anything, and a lock entry for a claim that is gone is untidy, not wrong.
    """
    present, lock, found = collect(sources), load(root), []
    for ident in sorted(present):
        rec, stamped = present[ident], lock.get(ident)
        if not rec['text'].strip():
            # The gate is the point of a gist, and this one can never fire:
            # the hash covers nothing, so no edit to any prose will ever mark
            # it stale. Six of seven accepted claims in a real dossier were in
            # this state and everything reported them current - a gate that
            # cannot fire is worse than none, because it reads as coverage.
            #
            # It happens when the label stands alone after a list, and a policy
            # document's load-bearing statement is very often a list, so the
            # finding names the forms that work rather than only refusing.
            found.append({'rule': 'empty-claim', 'severity': 'block', 'id': ident,
                          'file': rec['file'], 'line': rec['line'],
                          'why': 'the label is attached to nothing, so its gist '
                                 'is hashed against empty text and can never go stale',
                          'fix': 'put the label at the end of the paragraph it '
                                 'describes, or on the list item it belongs to'})
        elif rec['gist'] is None:
            found.append({'rule': 'no-gist', 'severity': 'warn', 'id': ident,
                          'file': rec['file'], 'line': rec['line'],
                          'why': 'a labelled claim with nothing said about it'})
        elif not stamped:
            # not a warning: nobody has ever vouched for this gist against this
            # paragraph, so the pipeline has no verdict to give - only the
            # person who can reread it does
            found.append({'rule': 'unaccepted', 'severity': 'manual', 'id': ident,
                          'file': rec['file'], 'line': rec['line'],
                          'why': 'a gist never accepted against its paragraph',
                          'fix': 'paperforge claims --accept'})
        elif stamped.get('hash') != fingerprint(rec['text']):
            found.append({'rule': 'stale-gist', 'severity': 'block', 'id': ident,
                          'file': rec['file'], 'line': rec['line'],
                          'why': 'the paragraph changed and the gist was not accepted again'})
    for ident in sorted(set(lock) - set(present)):
        found.append({'rule': 'orphan-gist', 'severity': 'warn', 'id': ident,
                      'file': LOCK, 'line': 0,
                      'why': 'accepted for a claim that no longer exists'})
    order = {'block': 0, 'manual': 1, 'warn': 2, 'skip': 3}
    found.sort(key=lambda f: (order.get(f['severity'], 9), f['id']))
    return found


def accept(sources, root, only=None):
    """Re-stamp claims. `only` names one; without it, all of them.

    Accepting is somebody saying they reread the paragraph, and it is the one
    act here the pipeline cannot verify. It could at least stop making the
    unread version the easiest: this used to re-stamp every claim in the
    project whatever had gone stale, so a build blocked on one paragraph was
    cleared by an action that touched all of them and reported a tally.

    `restamped` carries the prose as well as the gist, so the caller can put
    the two in front of whoever is accepting. Showing the text is not proof it
    was read - nothing is - but a count of two is proof it was not shown.
    """
    present, lock = collect(sources), load(root)
    if only is not None and only not in present:
        raise KeyError(only)
    fresh, changed, restamped = dict(lock), [], []
    for ident, rec in present.items():
        # an empty claim is not stamped, ever: writing the empty hash into the
        # lock is what made six accepted claims read as covered while their
        # gate could not fire. `check` blocks on it; this refuses to record it
        if rec['gist'] is None or not rec['text'].strip():
            continue
        if only is not None and ident != only:
            continue
        digest = fingerprint(rec['text'])
        moved = lock.get(ident, {}).get('hash') != digest
        if moved:
            changed.append(ident)
        # a named claim is shown whether or not it moved: somebody asked to
        # reread that paragraph, and answering with silence because the hash
        # already matched withholds the one thing they asked for
        if moved or only is not None:
            restamped.append({'id': ident, 'gist': rec['gist'], 'text': rec['text'],
                              'was': lock.get(ident, {}).get('gist')})
        fresh[ident] = {'hash': digest, 'gist': rec['gist']}
    if only is None:
        # a claim deleted from the source leaves the lock only on a full pass;
        # accepting one says nothing about the others
        gists = {i for i, r in present.items() if r['gist'] is not None}
        for ident in set(fresh) - gists:
            del fresh[ident]
    dropped = sorted(set(lock) - set(fresh))
    save(root, fresh)
    return {'accepted': sorted(fresh), 'changed': sorted(changed),
            'dropped': dropped, 'restamped': restamped}
