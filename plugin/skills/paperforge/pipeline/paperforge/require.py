"""External tools the pipeline shells out to, and what to do when one is absent.

Four binaries are invoked. Chrome was guarded and named what it was for; the
other three failed with a `FileNotFoundError` traceback, and one of them failed
*after* `init` had written five files. A tool that is not installed is an
ordinary condition on somebody else's machine, not an internal error.

Two rules are deliberate.

**A URL, never a runnable command.** The command differs per platform, so a
hardcoded `brew install ...` would be wrong most places - and a copy-pasteable
command invites an agent with shell access to run it, while a URL invites it to
ask. Installing software changes the machine, which is not the pipeline's call
to make.

**Optional means skipped, loudly.** A run on a machine that cannot produce every
edition should produce the ones it can and say plainly what it did not do.
Refusing work that would have succeeded is its own kind of wrong; a skip nobody
notices is worse than both, so the message names the tool, what was lost, and
where to get it.
"""
import shutil

TOOLS = {
    'typst': {
        'for': 'print editions, rendered maths and formatted citations',
        'from': 'https://github.com/typst/typst#installation',
    },
    'git': {
        'for': 'creating a repository for a new project',
        'from': 'https://git-scm.com/downloads',
    },
    'realtimex-pp-cli': {
        'for': 'publishing to a RealtimeX workspace',
        'from': 'https://www.npmjs.com/package/@realtimex/pp-cli',
    },
}


def found(name):
    """The resolved path, or None. Chrome is not here: it is found by probing a
    list of application paths rather than by name - see browser.find()."""
    return shutil.which(name)


def why(name, lost=None):
    """One line saying what is missing, what it was for, and where it comes from.

    `lost` names what this particular run could not do, which is the part a
    reader needs: "typst is not installed" is a fact, "the print edition was not
    built" is the consequence.
    """
    tool = TOOLS.get(name, {})
    said = '%s is not installed' % name
    if lost:
        said += '; %s' % lost
    return '%s. Needed for %s. See %s' % (said, tool.get('for', '?'),
                                          tool.get('from', '?'))


def demand(name, lost):
    """Raise for a tool this run cannot do without, saying so in the same terms.

    Used where the work is not optional: a document with maths cannot render its
    reading edition without typst, so building it anyway would publish a
    document with the equations missing.
    """
    if not found(name):
        raise RuntimeError(why(name, lost))
    return name


def report():
    """(name, path or None, what it is for) for every tool, for `doctor`."""
    return [(name, found(name), TOOLS[name]['for']) for name in sorted(TOOLS)]
