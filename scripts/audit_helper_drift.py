"""
audit_helper_drift — report shared helpers that have drifted apart.

Why this exists
---------------
Four small helpers (``_argparse.py``, ``_click.py``, ``_lang.py``,
``_vocab.py``) are copied into every skill on purpose, so each repository
stays installable on its own. Every copy's docstring says to change the
others at the same time, and ``tests/test_helper_sync.py`` asserts they are
byte-identical.

That test now skips. It globs inside the monorepo, and the skills moved out
to standalone repositories, so it finds fewer than two copies and reports —
honestly — that there is nothing left to cross-check. The invariant is still
written in ten files and nothing enforces it any more.

They have drifted: ``_argparse.py`` ranges from four to thirty-nine lines
apart, and some copies were modernised (``str | None``) while others were
not (``Optional[str]``).

What this does
--------------
Looks across the sibling repositories, groups the copies of each helper by
content, and reports the groups. It does not converge them: a repository is
free to have moved on for a reason, and picking a winner is a judgement
about which reason was better.

Usage
-----
::

    python3 scripts/audit_helper_drift.py
    python3 scripts/audit_helper_drift.py --diff _argparse.py

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

#: Copied into every skill on purpose, so each repository installs alone.
SHARED_HELPERS = ("_argparse.py", "_click.py", "_lang.py", "_vocab.py")


def find_copies(helper: str, home: Path) -> List[Path]:
    """
    Every copy of `helper`, across the monorepo and its sibling repositories.

    Parameters
    ----------
    helper : str
        File name, e.g. ``"_argparse.py"``.
    home : pathlib.Path
        Directory holding the ``sprezzature*`` checkouts.

    Returns
    -------
    list of pathlib.Path
        Sorted paths, build and virtual-environment copies excluded.
    """
    skip = {".venv", "build", "dist", "__pycache__", "node_modules"}
    out: List[Path] = []
    for repo in sorted(home.glob("sprezzature*")):
        if not repo.is_dir():
            continue
        for path in repo.rglob(helper):
            if any(part in skip or part.endswith(".egg-info") for part in path.parts):
                continue
            out.append(path)
    return sorted(out)


def group_by_content(paths: List[Path]) -> Dict[str, List[Path]]:
    """
    Bucket copies by their bytes.

    Returns
    -------
    dict
        Short digest to the paths sharing it, largest group first.
    """
    groups: Dict[str, List[Path]] = defaultdict(list)
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        groups[digest].append(path)
    return dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))


def main(argv: "List[str] | None" = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="audit_helper_drift.py",
        description="Report shared helpers whose copies have drifted apart.",
    )
    parser.add_argument("--diff", help="Show the diff for this helper against the majority copy.")
    parser.add_argument(
        "--home", type=Path, default=Path.home(),
        help="Directory holding the sprezzature* checkouts. Defaults to $HOME.",
    )
    args = parser.parse_args(argv)

    drifted = 0
    for helper in SHARED_HELPERS:
        copies = find_copies(helper, args.home)
        if len(copies) < 2:
            print(f"\n{helper}: {len(copies)} copy — nothing to compare")
            continue
        groups = group_by_content(copies)
        if len(groups) == 1:
            print(f"\n{helper}: {len(copies)} copies, all identical")
            continue

        drifted += 1
        print(f"\n{helper}: {len(copies)} copies in {len(groups)} versions")
        for digest, paths in groups.items():
            marker = "majority" if paths is next(iter(groups.values())) else "        "
            print(f"  {digest}  {marker}  {len(paths)} cop{'y' if len(paths) == 1 else 'ies'}")
            for path in paths:
                print(f"              {path.relative_to(args.home)}")

        if args.diff == helper:
            reference = next(iter(groups.values()))[0]
            for paths in list(groups.values())[1:]:
                other = paths[0]
                print(f"\n  ── {other.relative_to(args.home)} against the majority")
                diff = difflib.unified_diff(
                    reference.read_text(encoding="utf-8").splitlines(),
                    other.read_text(encoding="utf-8").splitlines(),
                    fromfile=str(reference.name), tofile=str(other), lineterm="",
                )
                for line in list(diff)[:40]:
                    print(f"  {line}")

    if drifted:
        print(
            f"\n{drifted} helper(s) have drifted. Each copy's docstring still says to "
            "change the others at the same time, and the test that enforced it now "
            "skips: it globs inside the monorepo, and the skills moved out."
        )
        print("Nothing is converged here — a repository may have moved on for a reason.")
    else:
        print("\nEvery shared helper is in step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
