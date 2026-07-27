#!/usr/bin/env bash
#
# run_mypy.sh — type-check every skill's scripts/ dir (CODING_ALL.md rule 3,
# type half; the AUDIT counterpart to `ruff check`).
#
# Inputs : none (checks front-*/scripts and scripts/ from the repo root).
# Output : mypy diagnostics on stdout; a one-line summary on stderr.
# Exit   : 0 if every dir type-checks clean, 1 if any dir has errors.
#
# Why per-dir: several skills ship private helper modules with the SAME name
# (_click, _argparse, _lang, _vocab), and the scripts import siblings by bare
# name via a runtime sys.path.insert. A single `mypy .` rejects the duplicate
# module names; checking one scripts/ dir at a time resolves the siblings and
# avoids the collision. Config (ignore_missing_imports, etc.) lives in mypy.ini.

set -euo pipefail

# Resolve the repo root from this script's location so it runs from anywhere.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$here"

# Diagnostics to stderr; stdout stays reserved for mypy's own report.
log() { printf '%s\n' "$*" >&2; }

fail=0
checked=0
for dir in front-*/scripts scripts sprezzature-cli/src; do
    # An unmatched glob would expand to the literal pattern — skip non-dirs.
    [ -d "$dir" ] || continue
    checked=$((checked + 1))
    # Keep going after a failing dir so the report covers every skill in one run.
    if ! python -m mypy "$dir"; then
        fail=1
    fi
done

if [ "$fail" -eq 0 ]; then
    log "run_mypy: ${checked} dir(s) type-check clean"
else
    log "run_mypy: type errors found (see above)"
fi
exit "$fail"
