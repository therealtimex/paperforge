"""How many of a line's words must be found before a match counts.

Both readers of a printed artifact ask a page the same question. The source
says this line is here; some of its words are; is that enough? Both answered it
with `max(floor, len(words) - 1)`, and that expression can ask for more matches
than there are words to make them: a two-word line faces a threshold of three
and can never be confirmed, however correctly the document rendered.

That has been found three times now, in three places, each time as a correct
document reported as missing a line it had printed - `verify.py` in #44,
`pages.py` twice. One of the three was fixed locally, with a comment explaining
the arithmetic perfectly, twelve lines above the copy that was not.

So the rule lives here once, and the gate is over its shape rather than over any
of the three instances: a threshold may never exceed the pool it draws from.
"""


def quorum(pool, floor):
    """How many of `pool` words must appear. Never more than `pool` itself.

    `floor` is what a caller considers convincing when there are plenty of
    words to choose from - two for prose, three for a contents entry, which is
    shorter and more repetitive.

    A pool of zero returns zero, which no caller should read as agreement: it
    is the absence of evidence, and the caller has to say what that means. Both
    callers here refuse rather than pass.
    """
    return min(pool, max(floor, pool - 1))
