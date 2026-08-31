"""`python3 -m paperforge`, which is how somebody auditing a project reaches it.

`bin/paperforge` was the only entry point, so the obvious invocation failed
with `ModuleNotFoundError: No module named 'paperforge.__main__'` - which is a
poor first contact with a tool you have been asked to check somebody's work
with. A peer reviewer's first command was exactly that, and so was mine.
"""
import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
