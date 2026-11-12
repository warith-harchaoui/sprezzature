"""
sprezzature-skills — put the suite's skills where an agent will read them.

An agent reads the skill folder installed under ``~/.claude/skills/`` or
``~/.opencode/skills/``, never the one inside a repository or a site-packages
directory. This command bridges that gap for the ten at once: it reports what
is installed, what differs, and — only when asked — copies the version each
brick ships into place, moving whatever was there aside first. Each brick's
own ``sprezzature-<brick>-skill`` does the same for that brick alone.

Reporting is the default. Writing under ``$HOME`` changes what every future
agent session reads, which is not something to do as a side effect of
installing a package.

Usage
-----
::

    sprezzature-skills                      # what is installed, and what differs
    sprezzature-skills --install            # copy them into ~/.claude/skills
    sprezzature-skills --install --agent opencode
    sprezzature-skills --path               # where each brick's package keeps it

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path

import click

from . import SKILL_NAMES, __version__, skill_path

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


@click.command(
    name="sprezzature-skills",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Report — or, with --install, refresh — the sprezzature skills an agent reads.",
    epilog="Reports by default. --install writes under your home directory, "
    "which changes what every future agent session reads.",
)
@click.option("--install", "do_install", is_flag=True,
              help="Copy the skills the bricks ship into the agent's directory.")
@click.option("--agent", default="claude", show_default=True,
              type=click.Choice(sorted(AGENT_DIRS)),
              help="Which agent's skills directory to use.")
@click.option("--path", "show_path", is_flag=True,
              help="Print where each brick's package keeps its skill, and stop.")
@click.version_option(__version__, "-V", "--version", prog_name="sprezzature-skills")
def _cli(do_install: bool, agent: str, show_path: bool) -> int:
    """Report, or refresh, the installed skills."""
    return _run(do_install, agent, show_path)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    try:
        result = _cli.main(args=argv, prog_name="sprezzature-skills", standalone_mode=False)
    except click.exceptions.UsageError as exc:
        exc.show()
        return 2
    except click.exceptions.Exit as exc:
        return exc.exit_code
    return result if isinstance(result, int) else 0


def _run(do_install: bool, agent: str, show_path: bool) -> int:
    """The body of the command, with its options already parsed."""
    target_dir = Path.home() / AGENT_DIRS[agent]
    if not show_path:
        print(f"{agent}:  {target_dir}\n")

    stale = 0
    for name in SKILL_NAMES:
        try:
            source = skill_path(name)
        except (ImportError, LookupError) as exc:
            print(f"  {name:28} {exc}")
            continue
        if show_path:
            print(f"  {name:28} {source}")
            continue
        if not (source / "SKILL.md").is_file():
            print(f"  {name:28} not shipped in this build")
            continue
        diffs = differences(source, target_dir / name)
        if not diffs:
            print(f"  {name:28} in step")
            continue
        stale += 1
        head = diffs[0] if len(diffs) == 1 else f"{len(diffs)} files differ"
        print(f"  {name:28} {head}")
        if do_install:
            moved = install(source, target_dir / name)
            where = f", previous copy at {moved}" if moved else ""
            print(f"  {'':28} → installed{where}")

    if show_path:
        return 0
    if not stale:
        print("\nEvery skill is in step.")
    elif not do_install:
        print(f"\n{stale} skill(s) differ. Pass --install to refresh them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
