# Paperforge 4.0.3: guidance that can be refreshed, and knows where it points

Design brief from System Design, 2026-09-06. Delivery target: a branch `init-refresh` on `/Users/realtimex/github/paperforge` (GitHub `therealtimex/paperforge`) from `main` at 034ca78 (v4.0.2). No forge: delivery is the pushed branch at a named SHA, per `CONTRIBUTING.md`; do not tag or release, System Design tags `v4.0.3` after QA.

## Context

A QSPEC project's `documents/AGENTS.md`, scaffolded by `paperforge init` from a source checkout on 4 September, names `/Users/realtimex/github/paperforge/bin/paperforge` in every command line. Agents followed it and kept reaching for the checkout and its venv instead of the deployed skill. `paperforge doctor` reports the guidance as current, because the stamp's fingerprint covers the template and deliberately excludes the invocation path; that is right for "is the guidance current" and blind to "does it point somewhere sensible". `init` cannot be re-run on a project because `scaffold.create()` rewrites `documents.toml` and `AGENTS.md` unconditionally. Two smaller defects were logged alongside: `narrow_layout` scoping from 4.0.2 shows on the console line and not in `record.json`; and `status` raises `KeyError: 'workspace'` (`cli.py:1227`) on a manifest with no `workspace` key. QSPEC met the same refresh gap after copying paperforge's stamp and solved it with `init --refresh`; the design comes back here with its tests known.

## Decisions

- **ADR-4.0.3-1 `init --refresh --into <dir>`.** Rewrites only what `init` wrote: `AGENTS.md` from the current template, the `CLAUDE.md` link or import, and the stamp. Never touches `documents.toml`, `figures.toml`, `.gitignore`, sources, or git. Refuses when `.paperforge/scaffold.json` is absent and says to run `init` without `--refresh`. Keeps the stamp's `created`, adds `refreshed`, and re-records the fingerprint. The title is read back from the manifest so the heading is preserved. Output lists what was rewritten, in the shape of `init`'s.
- **ADR-4.0.3-2 The stamp records the invocation, and doctor reads it.** `scaffold.stamp()` gains `invocation`, the absolute entry point `init` or `--refresh` was run from, which is already what the template receives. `doctor` prints a second `this project:` line: `invocation`, `ok` when it equals the running entry point, `moved` when it differs, `missing` when the path no longer exists, with `init --refresh` named as the remedy for the last two. The template fingerprint stays path-free; a project stamped before 4.0.3 reports `invocation unknown` rather than an error.
- **ADR-4.0.3-3 A deployed invocation that is one token.** The plugin's `pipeline/bin/paperforge` runs correctly only under an interpreter that has the pipeline's dependencies; in RealTimeX that is the app's bundled python, and the shebang's `python3` is not it. The launcher gains a resolution step: honour `PAPERFORGE_PYTHON` when set; otherwise, if the current interpreter cannot import `pdfplumber`, re-exec under the first candidate that can from a short documented list, including the RealTimeX bundled interpreter path under `/Applications/RealTimeX.AI.app/…/compat/<os>/python3`; otherwise fail with a message naming what was tried and what was missing. The skill text says the launcher does this and drops the `PYTHONPATH` advice. `init` and `--refresh` then record the launcher path alone.
- **ADR-4.0.3-4 The run record shows the probe scope.** `runs.write()` records, per document, `layout_probe: "full" | "wide only"` from the verify stage, so a reader of `record.json` sees when the narrow widths were skipped. `runs --diff` reports a change in it as `probe` next to the existing stage lines.
- **ADR-4.0.3-5 `status` tolerates a manifest with no workspace.** `d['workspace']` at `cli.py:1227` and its siblings read the key through `.get`; a document with no workspace reports `unlinked` rather than raising. A fixture manifest without the key is added to the unit checks.
- **ADR-4.0.3-6 Versioning and gates.** Patch release 4.0.3, consistent with 4.0.2 adding a manifest key as a patch. Version in `plugin/realtimex.plugin.json` and the skill frontmatter; `bin/paperforge plugin` re-run; `plugin --check`; `node scripts/node-runtime-contract.mjs` and `scripts/check-plugin-manifest.mjs`; every `tests/unit_*.py` including new checks that fail on the pre-fix code (`--refresh` leaves `documents.toml` byte-identical; stamp carries `invocation`; doctor says `moved` for a stamp pointing at a nonexistent path; a record from a scoped verify carries `wide only`; `status` on a workspace-less manifest exits 0); fixtures and backtest build. `references/starting-a-project.md`, `commands.md`, `provenance.md` updated.

## Acceptance criteria

1. All unit scripts pass, and the five new checks fail when run against a `git archive` of 034ca78.
2. `bin/paperforge plugin --check` in sync; both node scripts ok; fixtures and backtest build.
3. Proof in the Dev handoff: on a temp copy of `policyforge/vietnam/vn-procurement/documents`, `init --refresh` rewrites `AGENTS.md` to name the invocation it was run from, `documents.toml` is byte-identical before and after, `doctor` reports scaffold ok and invocation ok, and a second doctor run after moving the recorded path reports `moved`. Then from the deployed skill directory, the launcher runs `status` on that copy under the bundled interpreter without `PYTHONPATH` and exits 0.
4. Nothing under `policyforge/vietnam/vn-procurement` itself is modified.

## Non-goals

- No template or lint change; no QSPEC-specific behaviour.
- No change to what the fingerprint covers.

## Where things are

- `paperforge/scaffold.py` (`STAMP`, `stamp()`, `drift()`, `create()`, `AGENTS` template with `{invocation}`), `paperforge/cli.py` (`init` handler near line 1035, `_doctor_project`, `status` near line 1227, `record_run`), `paperforge/runs.py` (`write()`, `diff()`), `bin/paperforge` and `plugin/skills/paperforge/pipeline/bin/paperforge` (generated by `plugin`), `paperforge/package_plugin.py`, `tests/unit_gates.py`, `tests/unit_cli.py`.
- The QSPEC reference implementation of refresh: `/Users/realtimex/github/qspec/lib/scaffold.js` (`refresh()`, `stamp()`, `drift()`, `doctor()`), read-only.
- The stale file that motivated this: `/Users/realtimex/github/policyforge/vietnam/vn-procurement/documents/AGENTS.md` and its stamp, read-only; work on a copy.
