"""
sprezzature-skills — put the suite's skills where an agent will read them.

An agent reads the skill folder installed under ``~/.claude/skills/`` or
``~/.opencode/skills/``, never the one inside a repository or a site-packages
directory. This command bridges that gap: it reports what is installed, what
differs, and — only when asked — copies this package's version into place,
moving whatever was there aside first.

Reporting is the default. Writing under ``$HOME`` changes what every future
agent session reads, which is not something to do as a side effect of
installing a package.

Usage
-----
::

    sprezzature-skills                      # what is installed, and what differs
    sprezzature-skills --install            # copy them into ~/.claude/skills
    sprezzature-skills --install --agent opencode
    sprezzature-skills --path               # where pip put them

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

from . import SKILL_NAMES, __version__, skill_path, skills_path

#: Where each agent looks for skills, relative to the user's home directory.
AGENT_DIRS: dict[str, str] = {
    "claude": ".claude/skills",
    "opencode": ".opencode/skills",
}


def differences(source: Path, installed: Path) -> list[str]:
    """
    Files that differ between a shipped skill and its installed copy.

    Parameters
    ----------
    source : pathlib.Path
        The skill folder inside this package.
    installed : pathlib.Path
        The folder under the agent's skills directory.

    Returns
    -------
    list of str
        Relative paths that differ, are missing, or are extra. Empty when
        the two folders hold the same bytes.
    """
    if not installed.is_dir():
        return ["(not installed)"]
    out: list[str] = []
    for path in sorted(source.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(source)
        other = installed / rel
        if not other.is_file():
            out.append(f"missing: {rel}")
        elif not filecmp.cmp(path, other, shallow=False):
            out.append(f"differs: {rel}")
    return out


def install(source: Path, target: Path) -> Path | None:
    """
    Copy `source` over `target`, moving any existing copy aside first.

    Returns
    -------
    pathlib.Path or None
        Where the previous copy was moved, or None if there was none. The
        backup lands beside the skills directory rather than inside it: a
        folder left within it is itself read as a skill, which is how a
        superseded copy comes back to life.
    """
    moved: Path | None = None
    if target.exists():
        backups = target.parent.parent / "skills-superseded"
        backups.mkdir(parents=True, exist_ok=True)
        moved = backups / target.name
        if moved.exists():
            shutil.rmtree(moved)
        shutil.move(str(target), str(moved))
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return moved


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="sprezzature-skills",
        description="Report — or, with --install, refresh — the sprezzature "
                    "skills an agent reads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Reports by default. --install writes under your home directory, "
               "which changes what every future agent session reads.",
    )
    parser.add_argument("--install", action="store_true",
                        help="Copy the shipped skills into the agent's directory.")
    parser.add_argument("--agent", default="claude", choices=sorted(AGENT_DIRS),
                        help="Which agent's skills directory to use (default: %(default)s).")
    parser.add_argument("--path", action="store_true",
                        help="Print where pip installed the skills, and stop.")
    parser.add_argument("-V", "--version", action="version",
                        version=f"sprezzature-skills {__version__}")
    args = parser.parse_args(argv)

    shipped = skills_path()
    if args.path:
        print(shipped)
        return 0

    target_dir = Path.home() / AGENT_DIRS[args.agent]
    print(f"shipped: {shipped}")
    print(f"{args.agent}:  {target_dir}\n")

    stale = 0
    for name in SKILL_NAMES:
        source = skill_path(name)
        if not source.is_dir():
            print(f"  {name:28} not shipped in this build")
            continue
        diffs = differences(source, target_dir / name)
        if not diffs:
            print(f"  {name:28} in step")
            continue
        stale += 1
        head = diffs[0] if len(diffs) == 1 else f"{len(diffs)} files differ"
        print(f"  {name:28} {head}")
        if args.install:
            moved = install(source, target_dir / name)
            where = f", previous copy at {moved}" if moved else ""
            print(f"  {'':28} → installed{where}")

    if not stale:
        print("\nEvery skill is in step.")
    elif not args.install:
        print(f"\n{stale} skill(s) differ. Pass --install to refresh them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
