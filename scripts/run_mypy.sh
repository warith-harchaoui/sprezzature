#!/usr/bin/env bash
#
# run_mypy.sh — type-check every skill's scripts/ dir (CODING_ALL.md rule 3,
# type half; the AUDIT counterpart to `ruff check`).
#
# Inputs : none (checks sprezzature-*/scripts and scripts/ from the repo root).
# Output : mypy diagnostics on stdout; a one-line summary on stderr.
# Exit   : 0 if every dir type-checks clean, 1 if any dir has errors.
#
# Why per-dir: several skills ship private helper modules with the SAME name
# (_click, _argparse, _lang, _vocab), and the scripts import siblings by bare
# name via a runtime sys.path.insert. A single `mypy .` rejects the duplicate
# module names; checking one scripts/ dir at a time resolves the siblings and
# avoids the collision. Config (ignore_missing_imports, etc.) lives in mypy.ini.
#
# `--list` prints the directories this run would check and exits. It exists so
# a test can read which branch of the loop is live without paying for mypy:
# the loop named `sprezzature-cli/src` and skipped it for months, because the
# "is there anything here" probe was `find -maxdepth 1 -name '*.py'` and that
# package keeps its modules one level down, in src/sprezzature_cli/. The gate
# said "1 dir(s) type-check clean" and a reader heard "everything is clean".
# The summary below now names what it skipped, for the same reason.

set -euo pipefail

# Resolve the repo root from this script's location so it runs from anywhere.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$here"

# Diagnostics to stderr; stdout stays reserved for mypy's own report.
log() { printf '%s\n' "$*" >&2; }

list_only=0
[ "${1:-}" = "--list" ] && list_only=1

fail=0
checked=0
skipped=""
for dir in sprezzature-*/scripts scripts sprezzature-cli/src; do
    # An unmatched glob would expand to the literal pattern — skip non-dirs.
    [ -d "$dir" ] || continue
    # A skill whose deterministic tools moved to a standalone package leaves an
    # empty scripts/ (only a __pycache__). mypy would report "no .py[i] files"
    # and fail; there is nothing to type-check, so skip it. No -maxdepth: a
    # package laid out under src/ keeps its modules one level down, and the
    # depth-limited probe read that as empty.
    case "$(find "$dir" -name '*.py' -print -quit)" in
        "") skipped="${skipped}${skipped:+ }$dir" ; continue ;;
    esac
    checked=$((checked + 1))
    if [ "$list_only" -eq 1 ]; then
        printf '%s\n' "$dir"
        continue
    fi
    # Keep going after a failing dir so the report covers every skill in one run.
    if ! python -m mypy "$dir"; then
        fail=1
    fi
done

[ "$list_only" -eq 1 ] && exit 0

if [ "$fail" -eq 0 ]; then
    log "run_mypy: ${checked} dir(s) type-check clean"
else
    log "run_mypy: type errors found (see above)"
fi
# Named, not counted: "1 of 10" invites the reader to assume the other nine were
# fine. The nine are empty directories left behind by the monorepo split.
[ -n "$skipped" ] && log "run_mypy: no Python to check in: $skipped"
exit "$fail"
