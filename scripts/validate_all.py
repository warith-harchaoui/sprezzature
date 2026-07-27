#!/usr/bin/env python3
"""
validate_all
============

Run every validator the repo ships, in one command. The maintainer
invokes this before tagging a release; CI invokes it on every push.

What this runs
--------------
1. Strict YAML frontmatter validation (``validate_skill``) against every
   shipped skill (the nine ``front-*`` folders). This is the cross-skill
   foundation: if a SKILL.md has invalid YAML, the runtime silently
   rejects it.
2. Content-quality gate (``sprezzature-ui/scripts/validate.py``). This adds
   sprezzature-ui-specific checks the cross-skill module deliberately stays
   out of: forbidden framework imports, trademarked platform terms,
   LLM-marketing voice, etc.

The exit code is non-zero on any failure in either stage, so CI fails
the way users expect: one red light covers both layers.

Usage
-----
::

    # From the repo root
    python3 scripts/validate_all.py

    # Equivalent invocations on CI
    python3 scripts/validate_all.py && echo "shippable"

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Import the shared validator from the sibling script so the two stay
# in lock-step. ``sys.path`` is amended in-process so this script can be
# run directly from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import validate_skill  # noqa: E402


# ── Module-level configuration ──────────────────────────────────────────────

#: Repo root resolved from this file's location so the script works
#: regardless of the caller's cwd.
REPO_ROOT: Path = Path(__file__).resolve().parents[1]

#: The shipped skills, sourced from ``SKILLS.txt`` at repo root — one
#: source of truth across release.sh and the test fixtures. Adding a
#: new skill is a one-line edit *there*, not here.
from skills_manifest import SHIPPED_SKILLS as SKILLS  # noqa: E402


# ── Stage runners ──────────────────────────────────────────────────────────

def stage_yaml() -> int:
    """
    Run the strict YAML validator against every shipped skill.

    Returns
    -------
    int
        Number of skills that failed validation.
    """
    print("[1/2] YAML frontmatter validation", flush=True)
    failed: int = 0
    for name in SKILLS:
        errors = validate_skill(REPO_ROOT / name)
        if errors:
            failed += 1
            for err in errors:
                print(f"  FAIL {err}", file=sys.stderr, flush=True)
        else:
            print(f"  PASS {name}", flush=True)
    return failed


def stage_sprezzature_ui_content() -> int:
    """
    Run the sprezzature-ui content-quality gate as a subprocess.

    Returns
    -------
    int
        ``0`` when the gate passes, ``1`` otherwise.
    """
    print("\n[2/2] sprezzature-ui content quality gate", flush=True)
    sys.stdout.flush()  # ensure header appears before subprocess output
    script: Path = REPO_ROOT / "sprezzature-ui" / "scripts" / "validate.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        check=False,
    )
    return 0 if proc.returncode == 0 else 1


# ── Orchestrator ───────────────────────────────────────────────────────────

def main() -> int:
    """
    Run both stages and return a single aggregated exit code.

    Returns
    -------
    int
        ``0`` when every stage passes; ``1`` otherwise.
    """
    yaml_failures: int = stage_yaml()
    content_failure: int = stage_sprezzature_ui_content()
    total: int = yaml_failures + content_failure
    print()
    if total:
        print(f"FAIL — {total} validator stage(s) failed.", file=sys.stderr)
        return 1
    print(f"PASS — all {len(SKILLS)} skill(s) pass YAML + content gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
