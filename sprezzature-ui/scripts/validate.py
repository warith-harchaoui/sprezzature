#!/usr/bin/env python3
"""
validate
========

Pre-ship quality gate for the ``sprezzature`` Claude skill.

The script enforces the seven hard rules the skill is built around:

1. ``SKILL.md`` exists and has a valid YAML frontmatter block.
2. ``description`` in the frontmatter is between 50 and 1024 characters
   (the Anthropic skill spec caps it at 1024).
3. No forbidden framework imports anywhere in the skill source
   (``react``, ``vue``, ``svelte``, ``solid-js``, ``next``, ``nuxt``,
   ``@angular``).
4. No trademarked UI-platform terms in user-facing docs (``Apple``,
   ``iOS``, ``macOS``, ``HIG``, ``SF Pro``, …). Install-context references
   are exempt — see the allow-list in :func:`_is_user_facing_doc`.
5. No LLM-marketing phrases (``production-grade``, ``non-negotiable``,
   ``seamlessly``, ``leverages``, …). The anti-patterns reference is
   itself exempt because it defines them as refusal targets.
6. No ``README.md`` inside the skill folder (Anthropic spec forbids it).
7. Every reference path declared by ``references/ui-guidelines/INDEX.md``
   resolves on disk.

Exit code is non-zero on any failure. The script reports each check on
its own line and lists offending file:line excerpts when a check fails.

Usage
-----
::

    # Run from anywhere; the script resolves the skill root from __file__.
    python scripts/validate.py

    # Typical CI invocation
    python3 scripts/validate.py && echo "shippable"

Notes
-----
* Python 3.10+, stdlib only.
* The script intentionally avoids importing anything from the skill so it
  can run in a minimal CI container.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# ── Resolution + state ──────────────────────────────────────────────────────

#: Root of the skill folder (``sprezzature-ui/`` in this repo since the 0.2.0
#: split). The validator walks this tree exclusively.
SKILL_ROOT: Path = Path(__file__).resolve().parent.parent

#: Running failure count. Incremented by :func:`bad`; non-zero at end → exit 1.
FAIL: int = 0


# ── Tiny logging helpers ────────────────────────────────────────────────────

def ok(msg: str) -> None:
    """
    Print a success line for one check.

    Parameters
    ----------
    msg : str
        Human-readable description of the passing check.
    """
    print(f"✓ {msg}")


def bad(msg: str, lines: list[str] | None = None) -> None:
    """
    Print a failure line and (up to ten) offending excerpts.

    Increments the module-level :data:`FAIL` counter so the eventual exit
    code reflects the failure.

    Parameters
    ----------
    msg : str
        Top-level failure description, e.g. "framework import detected".
    lines : list of str or None, optional
        Offending ``path:line:content`` excerpts. Only the first ten are
        printed to keep the output legible.
    """
    global FAIL
    print(f"✗ {msg}", file=sys.stderr)
    for ln in (lines or [])[:10]:
        print(f"  → {ln}", file=sys.stderr)
    FAIL += 1


# ── File discovery ─────────────────────────────────────────────────────────

def all_files(*globs: str) -> list[Path]:
    """
    Recursively collect every file under :data:`SKILL_ROOT` matching any glob.

    The ``node_modules`` folder is excluded — the skill itself ships no
    Node modules, but a user might temporarily install some.

    Parameters
    ----------
    *globs : str
        File-name glob patterns (e.g. ``"*.md"``, ``"*.py"``).

    Returns
    -------
    list of Path
        Matching files in iteration order.
    """
    out: list[Path] = []
    for g in globs:
        out.extend(SKILL_ROOT.rglob(g))
    # Defensive filter: skip any ``node_modules`` subtree the user may have
    # created during testing.
    return [p for p in out if "node_modules" not in p.parts]


# ── Check 4 exemption rules (factored out for readability) ─────────────────

def _is_user_facing_doc(path: Path, line: str) -> bool:
    """
    Decide whether the trademark check applies to a given file/line.

    A handful of files legitimately mention platform names because they
    describe install steps that require them (the local Ollama alt-text
    helper, for instance, documents brew / winget / apt install steps).
    Those are exempt. So is the Material Design reference, which compares Material
    tokens to the skill's tokens.

    Parameters
    ----------
    path : Path
        File being checked, relative to :data:`SKILL_ROOT`.
    line : str
        Specific line containing the suspect term.

    Returns
    -------
    bool
        ``True`` when the term should fail the check, ``False`` when it is
        explicitly allowed.
    """
    rel: str = path.relative_to(SKILL_ROOT).as_posix()

    # Whole-file allow-list: the alt-text reference talks about the helper's
    # install path, which legitimately names the hardware platform.
    if rel == "references/alt-text-ai.md":
        return False
    # The captions reference documents whisper.cpp install per OS; same shape
    # as alt-text-ai.md, exempt for the same reason.
    if rel == "references/captions-ai.md":
        return False
    # The site-indexes reference cites Apple Podcasts as the canonical reason
    # to ship RSS 2.0 instead of Atom — naming the platform is the point.
    if rel == "references/site-indexes.md":
        return False
    # The Material Design reference compares tokens by name; the file's whole
    # purpose is to map third-party design-system vocabulary to the skill.
    if rel == "references/material-design.md":
        return False

    # Per-line allow-list: the images foundation references the alt-text
    # helper's install path, which mentions MLX-capable hardware.
    if rel == "references/ui-guidelines/foundations/images.md" and (
        "install_alt_ai" in line or "alt_from_ollama" in line or "MLX" in line
    ):
        return False

    # SKILL.md cites the helpers by name in the scripts section / decision tree.
    if rel == "SKILL.md" and (
        "alt-text-ai.md" in line
        or "alt_from_ollama" in line
        or "install_alt_ai" in line
    ):
        return False

    return True


# ── Check 1 — frontmatter shape ─────────────────────────────────────────────

skill_md: Path = SKILL_ROOT / "SKILL.md"
frontmatter_text: str = ""

if not skill_md.is_file():
    bad(f"SKILL.md missing at {skill_md}")
else:
    body: str = skill_md.read_text(encoding="utf-8")
    # Match an opening ``---\n``, the YAML body, and a closing ``---\n``.
    m = re.match(r"^---\n(.*?)\n---\n", body, re.S)
    if not m:
        bad("SKILL.md does not start with a valid '---\\n…\\n---\\n' frontmatter block")
    else:
        ok("SKILL.md frontmatter is well-formed")
        frontmatter_text = m.group(1)


# ── Check 2 — description length ────────────────────────────────────────────

# Match ``description: ...`` followed by either the next top-level YAML key or
# end-of-string. The non-greedy ``(.*?)`` captures the value across line wraps.
desc_match = re.search(
    r"^description:\s*(.*?)(?=^[a-z][a-z_]*:\s|\Z)",
    frontmatter_text,
    re.M | re.S,
)

if not desc_match:
    bad("SKILL.md frontmatter missing 'description:' field")
else:
    desc: str = " ".join(desc_match.group(1).split())
    if len(desc) < 50:
        bad(f"SKILL.md description too short ({len(desc)} chars; need ≥ 50)")
    elif len(desc) > 1024:
        bad(f"SKILL.md description exceeds 1024 chars ({len(desc)})")
    else:
        ok(f"SKILL.md description length OK ({len(desc)} / 1024 chars)")


# ── Check 3 — forbidden framework imports ──────────────────────────────────

#: Single compiled regex matching the import shapes most likely to leak into
#: the skill (ES module ``from`` and CommonJS ``require``).
framework_pat: re.Pattern[str] = re.compile(
    r"""(?x)
    (?: from \s+ ["']
      | require \s* \( \s* ["']
    )
    (?: react | vue | svelte | solid-js | next | nuxt | @angular )
    """,
)

hits: list[str] = []
for f in all_files("*.md", "*.html", "*.mjs", "*.js"):
    for i, line in enumerate(
        f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        if framework_pat.search(line):
            hits.append(f"{f.relative_to(SKILL_ROOT)}:{i}:{line.strip()}")

if hits:
    bad("Framework import detected:", hits)
else:
    ok("No framework imports")


# ── Check 4 — trademarked UI-platform terms in user-facing docs ────────────

trademark_pat: re.Pattern[str] = re.compile(
    r"\b(Apple|Apple Silicon|iOS|iPadOS|macOS|watchOS|tvOS|visionOS|HIG)\b"
    r"|SF\s*(Pro|Mono|Symbol)\b"
    r"|San\s*Francisco\b",
)

hits = []
for f in all_files("*.md", "*.html"):
    for i, line in enumerate(
        f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        if trademark_pat.search(line) and _is_user_facing_doc(f, line):
            hits.append(f"{f.relative_to(SKILL_ROOT)}:{i}:{line.strip()}")

if hits:
    bad("Trademarked UI-platform term in user-facing docs:", hits)
else:
    ok("No trademarked UI-platform terms in user-facing docs")


# ── Check 5 — LLM-marketing phrases ────────────────────────────────────────

#: Words that mark text as model-default marketing voice. The list is curated
#: from real LLM output, not from a generic ban-list.
MARKETING_WORDS: list[str] = [
    "production-grade", "non-negotiable", "world-class",
    "cutting-edge", "state-of-the-art", "seamlessly",
    "effortlessly", "gracefully", "leverages", "leverage",
    "empowers", "empower", "robust", "comprehensive", "turnkey",
]

marketing_pat: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(MARKETING_WORDS) + r")\b",
    re.I,
)

hits = []

#: Files that intentionally contain banned marketing words as
#: examples / refusal targets, not as the doc's own voice.
MARKETING_EXEMPT: frozenset[str] = frozenset({
    "references/anti-patterns.md",
    "references/plain-language.md",
})

for f in all_files("*.md"):
    if f.relative_to(SKILL_ROOT).as_posix() in MARKETING_EXEMPT:
        continue
    for i, line in enumerate(
        f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        if marketing_pat.search(line):
            hits.append(f"{f.relative_to(SKILL_ROOT)}:{i}:{line.strip()}")

if hits:
    bad("LLM-marketing phrase detected:", hits)
else:
    ok("No LLM-marketing phrases")


# ── Check 6 — no README.md anywhere inside the skill folder ────────────────

# The Anthropic spec is explicit: "Don't include README.md inside your
# skill folder. All documentation goes in SKILL.md or references/."
# That covers nested paths too (e.g. ``assets/fonts/README.md``), so we
# walk the whole tree, not just the top level. ``rglob`` is case-
# sensitive on POSIX, which matches the spec's "case-sensitive" rule on
# SKILL.md / README.md filenames.
nested_readmes: list[Path] = sorted(SKILL_ROOT.rglob("README.md"))
if nested_readmes:
    bad(
        "README.md exists inside the skill folder (Anthropic spec forbids it)",
        [str(p.relative_to(SKILL_ROOT)) for p in nested_readmes],
    )
else:
    ok("No README.md anywhere inside the skill folder")


# ── Check 7 — every INDEX.md reference resolves ────────────────────────────

idx: Path = SKILL_ROOT / "references" / "ui-guidelines" / "INDEX.md"
missing: list[str] = []

if idx.is_file():
    # The index uses three path shapes:
    #   foo/bar.md           → relative to references/ui-guidelines/
    #   references/foo.md    → relative to the skill root (cross-references)
    #   foo.md (bare)        → cross-reference up one level (references/)
    refs = sorted(set(re.findall(r"`([a-z][a-z0-9_/\-]*\.md)`", idx.read_text(encoding="utf-8"))))
    for rel in refs:
        if rel.startswith("references/"):
            target = SKILL_ROOT / rel
        elif "/" in rel:
            target = SKILL_ROOT / "references" / "ui-guidelines" / rel
        else:
            target = SKILL_ROOT / "references" / rel
        if not target.exists():
            missing.append(rel)
    if missing:
        bad("INDEX.md references missing files:", missing)
    else:
        ok("All ui-guidelines/INDEX.md paths exist")


# ── Summary + exit code ────────────────────────────────────────────────────

print()
if FAIL == 0:
    print("PASS — skill is shippable.")
    sys.exit(0)
else:
    print(f"FAIL — {FAIL} check(s) failed.")
    sys.exit(1)
