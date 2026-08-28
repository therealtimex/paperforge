"""Headless Chrome helpers.

Chrome is a build-time dependency only: it pre-renders diagrams and measures
printed pagination. Nothing it produces is needed at view time - published
documents carry no scripts or network dependencies from it.
"""
import shutil
import subprocess
from pathlib import Path

CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
]


def chrome():
    for name in ('google-chrome', 'chromium', 'chromium-browser'):
        found = shutil.which(name)
        if found:
            return found
    for path in CANDIDATES:
        if Path(path).exists():
            return path
    raise RuntimeError('headless Chrome not found; needed to render diagrams and measure pages')


# CI runners have no usable user namespace for Chrome's sandbox, and the failure
# is a silent blank render rather than an error - every diagram would come out
# empty with a green build. Opt in explicitly rather than always disabling it.
CI_FLAGS = ['--no-sandbox', '--disable-dev-shm-usage']


def run(args, timeout=180):
    """One headless invocation.

    A print that never returns used to surface as a `TimeoutExpired` traceback
    and end the run - observed twice, both times on a document that had built
    in half a minute on the previous attempt. Whatever the cause, a tool that
    does not come back is the same class as one that is not installed: the
    pipeline cannot do that piece of work and should say so, not stack-trace.
    Callers that can proceed without it skip; the ones that cannot refuse.
    """
    import os
    extra = CI_FLAGS if os.environ.get('PAPERFORGE_CHROME_NO_SANDBOX') else []
    cmd = [chrome(), '--headless=new', '--disable-gpu', '--no-first-run'] + extra + args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        target = next((a.split('=', 1)[1] for a in args if a.startswith('--print-to-pdf=')),
                      args[-1] if args else '?')
        raise RuntimeError('headless Chrome did not finish within %gs on %s'
                           % (timeout, Path(target).name))


def dump_dom(url, budget=40000, extra=()):
    """Load a page, let it settle, and return the rendered DOM."""
    r = run(['--virtual-time-budget=%d' % budget, '--dump-dom', *extra, url])
    return r.stdout


def print_pdf(html_path, pdf_path, budget=25000):
    run(['--virtual-time-budget=%d' % budget, '--no-pdf-header-footer',
         '--print-to-pdf=%s' % pdf_path, Path(html_path).absolute().as_uri()])
    return Path(pdf_path)
