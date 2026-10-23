#!/usr/bin/env bash
# Fetch the nine brick repositories beside this one, metadata only.
#
# Why this exists
# ---------------
# Several guards in tests/ can only be written from this repository, because it
# is the only place that sees all nine bricks at once: that a skill's "invoked
# as" sentence names a console script the brick installs; that the `sprezzature`
# driver routes to commands the bricks declare; that a `requirements-dev.txt` is
# one the brick's own workflow reads.
#
# They were running nowhere but a developer's machine. CI cloned one sibling —
# the figures generators, for the release test — so the other eight cases
# skipped, and a skip reads exactly like a pass. The pre-push hook claims that
# "the hook passed" and "CI will pass" mean the same thing; with eight guards
# live on one side and dormant on the other, they did not.
#
# Why not a plain clone
# ---------------------
# Content. `sprezzature-maps` tracks 370 MB and `sprezzature-figures` 112 MB —
# elevation rasters, vector basemaps, fonts, example renders — none of which any
# guard reads. Nine full clones on three matrix jobs would move around 1.5 GB per
# push to answer questions about `pyproject.toml`.
#
# So: `--filter=blob:none` fetches the commit and its trees but no file content,
# and a non-cone sparse checkout then pulls blobs for the listed paths only. The
# whole set lands in a few megabytes. The paths are the ones the guards read,
# plus the package directory, which `scripts/audit_surfaces.py` needs to answer
# "does this brick expose a library surface".
#
# Deliberately NOT fetched: `assets/`. That is where the weight is, and nothing
# that looks across the bricks reads it. A sibling fetched this way is therefore
# a partial checkout — complete for what the guards ask, and not a place to run
# a brick's own suite.
#
# Usage
# -----
#   scripts/fetch_siblings.sh [destination]
#
# `destination` defaults to the directory holding this checkout, which is where
# every guard looks (``REPO_ROOT.parent``). Already-present siblings are left
# alone, so running it on a developer machine with real checkouts is a no-op.
#
# Author
# ------
# Warith HARCHAOUI <warithmetics@deraison.ai>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$(dirname "$REPO_ROOT")}"
REMOTE_BASE="https://github.com/warith-harchaoui/"

# One folder name per line, from the canonical manifest. A brick added to
# SKILLS.txt is fetched here without touching this script. Read with a plain
# loop rather than `mapfile`, which bash 3.2 — what macOS still ships — does
# not have: this script has to run on a developer's machine as well as on a
# runner.
BRICKS=()
while IFS= read -r line; do
    line="$(echo "$line" | tr -d '[:space:]')"
    case "$line" in ''|'#'*) continue ;; esac
    BRICKS+=("$line")
done < "$REPO_ROOT/SKILLS.txt"

if [[ ${#BRICKS[@]} -eq 0 ]]; then
    echo "error: SKILLS.txt is empty or missing at $REPO_ROOT" >&2
    exit 1
fi

# What the cross-brick guards and the surface auditor read. Non-cone sparse
# patterns, gitignore-style: a leading slash anchors at the repository root.
PATHS=(
    '/pyproject.toml'
    '/requirements-dev.txt'
    '/SKILL.md'
    '/Dockerfile'
    '/docker-compose.yml'
    '/.github/'
    '/tests/'
    '/scripts/'
    '/src/'
    '/sprezzature_*/'
    # The ten documents every brick is supposed to carry, because a guard here
    # asserts they are all present — `test_every_brick_carries_the_same_papers`
    # — and a guard that reads a file this script does not fetch fails on the
    # runner and nowhere else. It was written on a machine holding nine real
    # clones, where the question never came up. 717 KB for the nine, which is
    # three per cent of what the fetch already costs.
    #
    # TRIGGERS.md earns its place twice over: the companion check that a
    # brick's trigger tables name real console scripts *skips* when the file
    # is absent, so without it that guard was not red here, it was silent.
    '/README.md'
    '/LISEZMOI.md'
    '/CHANGELOG.md'
    '/CODING.md'
    '/CONTRIBUTING.md'
    '/EXAMPLES.md'
    '/TRIGGERS.md'
    '/LANDSCAPE.md'
    '/PAYSAGE.md'
    '/LICENSE'
    # `scripts/package_skill.py` grafts the extracted figure generators and
    # their faces back into the figures tarball at packaging time, and refuses
    # to package without them — "documentation with nothing behind it". Only
    # the WOFF2 faces go into the archive: the parallel `.ttf` files serve
    # raster backends and are 9.8 MB of figures' 14, so the pattern is what
    # keeps them out where naming the folder would not. The two patterns match
    # in any brick that has faces, which costs a few hundred kilobytes in
    # `sprezzature-ui` and nothing anywhere else.
    '/assets/fonts/**/*.woff2'
    '/assets/fonts/**/*.txt'
)

for brick in "${BRICKS[@]}"; do
    target="$DEST/$brick"
    if [[ -e "$target" ]]; then
        echo "  $brick: already here, left alone"
        continue
    fi
    git clone --quiet --depth 1 --filter=blob:none --no-checkout \
        "$REMOTE_BASE$brick.git" "$target"
    git -C "$target" sparse-checkout set --no-cone "${PATHS[@]}"
    git -C "$target" checkout --quiet
    echo "  $brick: $(du -sh "$target" | cut -f1)"
done
