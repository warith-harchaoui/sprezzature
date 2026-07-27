#!/usr/bin/env bash
# release.sh — build per-skill tarballs + a bundle + SHA256SUMS for a tagged release.
#
# Usage:
#   scripts/release.sh <version> [out-dir]
#
# Example:
#   scripts/release.sh 0.3.0                  # writes to dist/
#   scripts/release.sh 0.0.0-test /tmp/r      # writes to /tmp/r/
#
# Output (in <out-dir>):
#   sprezzature-ui-<version>.tar.gz
#   sprezzature-cli-gui-<version>.tar.gz
#   sprezzature-publish-<version>.tar.gz
#   sprezzature-accessibility-<version>.tar.gz
#   sprezzature-colors-<version>.tar.gz
#   sprezzature-vision-<version>.tar.gz
#   sprezzature-audio-<version>.tar.gz
#   sprezzature-ux-laws-<version>.tar.gz
#   sprezzature-skills-<version>.tar.gz        ← bundle of every skill
#   SHA256SUMS                           ← one file, one line per artifact
#
# The tarballs each contain the skill folder at the top level (so
# `tar xzf sprezzature-ui-<version>.tar.gz` extracts to `sprezzature-ui/`).
#
# After the script finishes, publish with:
#   gh release create v<version> dist/*.tar.gz dist/SHA256SUMS --notes-file CHANGELOG.md
#
# Stdlib bash + standard POSIX tools (tar, find). Uses `shasum -a 256`
# on macOS and falls back to `sha256sum` on Linux.
#
# Author: Warith Harchaoui, Ph.D.

set -euo pipefail

# ── Argument parsing ───────────────────────────────────────────────────────

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "usage: $0 <version> [out-dir]" >&2
    echo "  e.g. $0 0.3.0" >&2
    echo "       $0 0.0.0-test /tmp/release-test" >&2
    exit 64
fi

VERSION="$1"
OUT_DIR="${2:-dist}"

# Reject the leading "v" — versions are bare semver here; the tag is "v<version>".
if [[ "$VERSION" == v* ]]; then
    echo "error: pass the bare version (e.g. 0.3.0), not the tag (e.g. v0.3.0)." >&2
    exit 64
fi

# Resolve the repo root from this script's location so the script works
# regardless of the caller's CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# ── Skill list ─────────────────────────────────────────────────────────────

# Read the canonical manifest at SKILLS.txt — single source of truth
# across release.sh, scripts/validate_all.py and the test fixtures.
# Comments and blank lines are stripped; everything else is one skill
# folder name per line.
SKILLS=()
while IFS= read -r line; do
    case "$line" in
        ''|'#'*) continue ;;  # skip blank lines + comment lines
    esac
    SKILLS+=("$(echo "$line" | tr -d '[:space:]')")
done < "$REPO_ROOT/SKILLS.txt"

if [[ ${#SKILLS[@]} -eq 0 ]]; then
    echo "error: SKILLS.txt is empty or missing at $REPO_ROOT" >&2
    exit 1
fi

for skill in "${SKILLS[@]}"; do
    if [[ ! -d "$skill" ]]; then
        echo "error: missing skill folder '$skill' at $REPO_ROOT" >&2
        exit 1
    fi
    if [[ ! -f "$skill/SKILL.md" ]]; then
        echo "error: '$skill' is missing SKILL.md" >&2
        exit 1
    fi
done

# ── Pick the SHA256 binary ─────────────────────────────────────────────────

if command -v shasum >/dev/null 2>&1; then
    SHA_CMD=(shasum -a 256)
elif command -v sha256sum >/dev/null 2>&1; then
    SHA_CMD=(sha256sum)
else
    echo "error: need 'shasum' (macOS) or 'sha256sum' (Linux) on PATH." >&2
    exit 1
fi

# ── Prepare output dir ─────────────────────────────────────────────────────

mkdir -p "$OUT_DIR"
OUT_ABS="$(cd "$OUT_DIR" && pwd)"

echo "→ building release v$VERSION into $OUT_ABS"

# ── Build per-skill tarballs ───────────────────────────────────────────────
#
# Each tarball contains the skill folder at the top level. We exclude
# macOS Finder turds (.DS_Store, __MACOSX), Python caches, and Git noise
# to keep download size honest.

EXCLUDES=(
    --exclude='.DS_Store'
    --exclude='__MACOSX'
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='.pytest_cache'
    --exclude='.mypy_cache'
    --exclude='.ruff_cache'
    # Rendered showcase rasters (the website gallery) are regenerated from the
    # specs and scripts; they belong on the site, not in the shipped skill.
    --exclude='figures-gallery'
)

ARTIFACTS=()

for skill in "${SKILLS[@]}"; do
    tarball="$OUT_ABS/${skill}-${VERSION}.tar.gz"
    echo "  packaging $skill → ${skill}-${VERSION}.tar.gz"
    tar -czf "$tarball" "${EXCLUDES[@]}" "$skill"
    ARTIFACTS+=("$tarball")
done

# ── Bundle tarball (all four skills) ───────────────────────────────────────

bundle="$OUT_ABS/sprezzature-skills-${VERSION}.tar.gz"
echo "  packaging bundle → sprezzature-skills-${VERSION}.tar.gz"
tar -czf "$bundle" "${EXCLUDES[@]}" "${SKILLS[@]}"
ARTIFACTS+=("$bundle")

# ── Emit SHA256SUMS ────────────────────────────────────────────────────────
#
# Note: SHA256SUMS contains *basenames only*, so `shasum -a 256 -c` works
# from the same directory where the artifacts were downloaded.

(
    cd "$OUT_ABS"
    : > SHA256SUMS
    for path in "${ARTIFACTS[@]}"; do
        "${SHA_CMD[@]}" "$(basename "$path")" >> SHA256SUMS
    done
)

echo
echo "→ artifacts:"
ls -la "$OUT_ABS"

echo
echo "→ SHA256SUMS:"
cat "$OUT_ABS/SHA256SUMS"

# ── Verify locally before exiting ──────────────────────────────────────────

echo
echo "→ verifying checksums locally..."
(
    cd "$OUT_ABS"
    "${SHA_CMD[@]}" -c SHA256SUMS
)

# ── Next steps ─────────────────────────────────────────────────────────────

cat <<EOF

✓ release v$VERSION built and verified in $OUT_ABS

next steps:
  1. Inspect the artifacts:
       ls -lh $OUT_ABS
  2. Tag the commit and push:
       git tag -a v$VERSION -m "release v$VERSION"
       git push origin v$VERSION
  3. Publish on GitHub:
       gh release create v$VERSION \\
         $OUT_ABS/*.tar.gz \\
         $OUT_ABS/SHA256SUMS \\
         --title "v$VERSION" \\
         --notes-file CHANGELOG.md
  4. Users install with:
       VERSION=$VERSION
       curl -L -o sprezzature-skills.tar.gz \\
         https://github.com/warith-harchaoui/sprezzature/releases/download/v\${VERSION}/sprezzature-skills-\${VERSION}.tar.gz
       curl -L -o SHA256SUMS \\
         https://github.com/warith-harchaoui/sprezzature/releases/download/v\${VERSION}/SHA256SUMS
       shasum -a 256 -c SHA256SUMS
       tar xzf sprezzature-skills.tar.gz
       cp -r sprezzature-ui ~/.claude/skills/
EOF
