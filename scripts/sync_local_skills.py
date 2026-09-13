"""
sync_local_skills — refresh the installed skills from this repository.

Why this exists
---------------
An agent reads the skill folder installed under ``~/.claude/skills/`` or
``~/.opencode/skills/``, not the one in this repository. Nothing kept the
two in step, so they drifted silently — and a stale skill is worse than a
missing one, because the agent follows it confidently.

The drift this was written for: every charting library was removed from the
stack months ago, and the installed ``sprezzature-figures`` still opened
with *"prefer Vega-Lite over matplotlib"*. An agent reading that produced
Vega specs for a project that had spent a release deleting Vega.

What it does
------------
Compares each ``sprezzature-*`` folder here against its installed copies and
reports what differs. With ``--apply`` it copies the repository version over
the installed one, after moving the old copy aside.

Audit-only by default. Installing under ``$HOME`` changes what every future
agent session reads, which is not something to do as a side effect.

Usage
-----
::

    python3 scripts/sync_local_skills.py              # audit
    python3 scripts/sync_local_skills.py --apply      # refresh
    python3 scripts/sync_local_skills.py --only figures

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

#: Where agent runtimes look for skills. Both read the same SKILL.md, which
#: is why a single source in this repository can serve them.
TARGETS: Dict[str, Path] = {
    "Claude": Path.home() / ".claude" / "skills",
    "OpenCode": Path.home() / ".opencode" / "skills",
}

#: Never copied: build debris and virtual environments that would multiply
#: an already large skill folder for no benefit to the agent reading it.
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".git", ".venv", "build", "dist", "*.egg-info", ".*"
)


def repo_skills(root: Path) -> List[Path]:
    """
    Every ``sprezzature-*`` folder here that carries a SKILL.md.

    Parameters
    ----------
    root : pathlib.Path
        The monorepo root.

    Returns
    -------
    list of pathlib.Path
        Skill folders, sorted by name.
    """
    return sorted(p for p in root.glob("sprezzature-*") if (p / "SKILL.md").is_file())


def compare(source: Path, installed: Path) -> Tuple[str, int]:
    """
    How far the installed copy has drifted.

    Only ``SKILL.md`` is compared line by line: it is the file an agent
    actually reads, and the one whose staleness misleads. The rest of the
    folder is compared by presence, because a byte-diff over 77 MB of
    vendored assets tells nobody anything useful.

    Parameters
    ----------
    source : pathlib.Path
        The repository's skill folder.
    installed : pathlib.Path
        The installed copy, which may not exist.

    Returns
    -------
    tuple of (str, int)
        A verdict, and the number of differing SKILL.md lines.
    """
    if not installed.is_dir():
        return "not installed", 0
    a, b = installed / "SKILL.md", source / "SKILL.md"
    if not a.is_file():
        return "installed without a SKILL.md", 0
    if filecmp.cmp(a, b, shallow=False):
        return "up to date", 0

    import difflib

    old = a.read_text(encoding="utf-8", errors="replace").splitlines()
    new = b.read_text(encoding="utf-8", errors="replace").splitlines()
    changed = sum(
        1 for line in difflib.ndiff(old, new) if line[:1] in ("-", "+")
    )
    return "stale", changed


def refresh(source: Path, installed: Path) -> Path:
    """
    Replace the installed copy, keeping the old one out of the way.

    The backup goes to a sibling of the skills directory, not beside the
    skill. The first version of this put it at ``<skill>.superseded`` in
    place, and the runtime promptly loaded every backup as a skill of its
    own — so an agent saw both the refreshed description and the stale one
    it was meant to replace, which is worse than the drift this fixes.

    Parameters
    ----------
    source : pathlib.Path
        The repository's skill folder.
    installed : pathlib.Path
        Where it goes.

    Returns
    -------
    pathlib.Path
        Where the previous copy was moved, or `installed` when there was none.
    """
    attic = installed.parent.parent / "skills-superseded"
    backup = attic / installed.name
    if installed.is_dir():
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.is_dir():
            shutil.rmtree(backup)
        shutil.move(str(installed), str(backup))
    installed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, installed, ignore=IGNORE)
    return backup if backup.is_dir() else installed


def main(argv: "List[str] | None" = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="sync_local_skills.py",
        description="Refresh the installed skills from this repository.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Copy the repository version over the installed one. Default: audit only.",
    )
    parser.add_argument(
        "--only", action="append",
        help="Limit to this skill, by short name (figures, colors, …). Repeatable.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    skills = repo_skills(root)
    if args.only:
        wanted = {f"sprezzature-{n.removeprefix('sprezzature-')}" for n in args.only}
        skills = [s for s in skills if s.name in wanted]
        if not skills:
            parser.error(f"no skill matched {args.only}")

    stale = 0
    for runtime, base in TARGETS.items():
        if not base.is_dir():
            print(f"\n── {runtime}: {base} does not exist, skipping")
            continue
        print(f"\n── {runtime}  ({base})")
        for source in skills:
            installed = base / source.name
            verdict, lines = compare(source, installed)
            note = f"{verdict}" + (f", {lines} SKILL.md lines differ" if lines else "")
            if verdict == "up to date":
                print(f"  {source.name:28} {note}")
                continue
            stale += 1
            if args.apply:
                kept = refresh(source, installed)
                where = f"previous copy at {kept.name}" if kept != installed else "fresh install"
                print(f"  {source.name:28} refreshed ({note}; {where})")
            else:
                print(f"  {source.name:28} {note}")

    if stale and not args.apply:
        print(f"\n{stale} installed skill(s) differ from this repository.")
        print("An agent reads the installed copy, not this one — a stale skill is")
        print("followed as confidently as a current one. Re-run with --apply to refresh.")
    elif stale:
        print(f"\n{stale} skill(s) refreshed. The superseded copies are kept beside them.")
    else:
        print("\nEverything installed matches this repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
