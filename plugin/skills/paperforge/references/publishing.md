# Publishing

```bash
paperforge publish              # ship every declared, publishable document
paperforge status               # what is built, linked and published
```

`publish` re-runs the lint gate and refuses anything blocking, so the manifest
says what *may* ship and lint says whether it is *fit* to.

## Targets

```toml
target = "realtimex"             # default: into a workspace artifacts dir
workspace = "editor"

target = "directory"             # or a plain folder for any static host
directory = "dist"
```

A document declaring `pdf = "typst"` ships **both** editions as separate
artifacts, each with its own URL and content type.

## Hard links, not copies

The artifact server refuses symlinks that leave the artifact root
(`entryFile must stay inside the workspace artifact root`), so the served copy
is a **hard link**: one inode, two names. Rebuild in the repo and the public URL
reflects it immediately, with no copy step and no re-publish.

> **Caveat.** Git *replaces* files rather than writing into them, so `checkout`,
> `pull`, `stash` or a fresh clone detaches the link and the artifact keeps
> serving the old content **silently**. `paperforge status` reports
> `stale link`; `paperforge publish` re-establishes it. Rebuilds are safe — the
> build writes in place and preserves the inode.

## Access

Published documents are reachable by anyone holding the URL: unguessable, but
**not authenticated**. Treat the URL as the credential.

```bash
realtimex-pp-cli pause-artifact <id>     # stop serving, keep the entry
realtimex-pp-cli revoke-artifact <id>    # end it
paperforge publish --expires-at <ISO>   # publish with an expiry
```

Confirm with the user before publishing anything outward-facing for the first
time. Republishing an already-linked document is not a new disclosure; a new
document is.

## Related

`lint.md` · `manifest.md` · `commands.md` · `print.md`
