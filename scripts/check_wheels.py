"""
check_wheels — build each package and prove the artefact works on its own.

Why this exists
---------------
A test suite run inside a checkout cannot see the difference between a module
the wheel ships and a module that merely sits next to it. Three of the seven
packages imported their own command-line modules by bare name, which worked in
the repository (``scripts/`` was on ``sys.path``) and raised
``ModuleNotFoundError`` the moment anyone installed the wheel — with 190 green
tests in each of them. Two more mounted an MCP surface that raised
``TypeError`` on import, because an unpinned dependency resolved to a version
their wrapper cannot call.

None of that is visible from inside the repository. This builds each package,
installs the wheel into a throwaway virtual environment with nothing else on
the path, and imports what it claims to offer. It is the only check here that
tests what a reader of PyPI would actually receive.

Usage
-----
::

    python3 scripts/check_wheels.py              # every package
    python3 scripts/check_wheels.py --only sprezzature-maps
    python3 scripts/check_wheels.py --keep       # leave the venvs for poking at

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

#: Every checkout that publishes a package, and its import name. This
#: repository is in the list: it publishes ``sprezzature``, the distribution
#: that carries the skills, and leaving it out meant the one package whose
#: wheel nobody had ever installed from a clean venv was the flagship.
PACKAGES: dict[str, str] = {
    "sprezzature": "sprezzature",
    "sprezzature-figures": "sprezzature_figures",
    "sprezzature-colors": "sprezzature_colors",
    "sprezzature-accessibility": "sprezzature_accessibility",
    "sprezzature-audio": "sprezzature_audio",
    "sprezzature-cli-gui": "sprezzature_cli_gui",
    "sprezzature-ux-laws": "sprezzature_ux_laws",
    "sprezzature-maps": "sprezzature_maps",
}

#: Imported with the [api,mcp] extras: the two surfaces that broke silently.
#: A package that declares neither (``sprezzature`` is skills and a copier,
#: not a server) is checked on its top-level import and its commands alone.
SURFACES = ("api", "mcp")

#: A command refusing because an optional extra is missing, and naming it.
_REFUSAL = re.compile(r"pip install '[^']+\[[a-z,]+\]'")


def build(repo: Path) -> Path:
    """Build `repo` and return the wheel. Raises if the build fails."""
    dist = repo / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    subprocess.run([sys.executable, "-m", "build"], cwd=repo, check=True,
                   capture_output=True)
    wheels = list(dist.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"{repo.name}: expected one wheel, found {len(wheels)}")
    return wheels[0]


def scripts_of(repo: Path) -> list[str]:
    """The console scripts `repo` declares."""
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    return list(data["project"].get("scripts", {}))


def surfaces_of(repo: Path) -> tuple[str, ...]:
    """Which of `SURFACES` this package actually declares an extra for."""
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    declared = data["project"].get("optional-dependencies", {})
    return tuple(s for s in SURFACES if s in declared)


def _missing_skills(py: Path) -> list[str]:
    """Skill folders `sprezzature` advertises but did not ship, if any."""
    probe = (
        "import sprezzature as s;"
        "print(' '.join(n for n in s.SKILL_NAMES "
        "if not (s.skill_path(n) / 'SKILL.md').is_file()))"
    )
    r = subprocess.run([str(py), "-c", probe], cwd="/", capture_output=True,
                       text=True, timeout=60)
    if r.returncode != 0:
        last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "?"
        return [f"sprezzature: could not enumerate the shipped skills — {last[:120]}"]
    absent = r.stdout.split()
    if absent:
        return [f"sprezzature: the wheel names {len(absent)} skill(s) it does not "
                f"carry — {', '.join(absent)}"]
    return []

def check(repo_name: str, package: str, keep: bool) -> list[str]:
    """
    Install `repo_name`'s wheel alone and exercise it. Returns the failures.

    The virtual environment is built with no system packages and the import
    runs from ``/``, so nothing in the checkout can stand in for something the
    wheel forgot to ship.
    """
    repo = Path.home() / repo_name
    problems: list[str] = []
    surfaces = surfaces_of(repo)
    wheel = build(repo)
    venv = Path(tempfile.mkdtemp(prefix=f"wheelcheck-{repo_name}-"))
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                       capture_output=True)
        py = venv / "bin" / "python"
        target = f"{wheel}[{','.join(surfaces)}]" if surfaces else str(wheel)
        pip = subprocess.run([str(venv / "bin" / "pip"), "install", "-q", target],
                             capture_output=True, text=True)
        if pip.returncode != 0:
            return [f"{repo_name}: install failed: {pip.stderr.strip()[-300:]}"]

        # A package with no server surface still has to import at all.
        r = subprocess.run([str(py), "-c", f"import {package}"],
                           cwd="/", capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "?"
            problems.append(f"{repo_name}: import {package} — {last[:120]}")
        elif repo_name == "sprezzature":
            # This package's whole payload is folders, not modules: importing
            # it proves nothing about whether the skills came with it. The
            # three hand-kept tables in pyproject.toml decide that, and when
            # SKILL_NAMES grows and they do not, the wheel names a skill whose
            # files are absent — invisible from a checkout, where the folder
            # sits in the source tree.
            problems += _missing_skills(py)

        for surface in surfaces:
            r = subprocess.run([str(py), "-c", f"import {package}.{surface}"],
                               cwd="/", capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "?"
                problems.append(f"{repo_name}: {package}.{surface} — {last[:120]}")

        for command in scripts_of(repo):
            exe = venv / "bin" / command
            try:
                # A command that does not answer --help is a finding, not a
                # reason to hang the check: every MCP entry point used to go
                # straight to uvicorn.run and serve forever.
                r = subprocess.run([str(exe), "--help"], cwd="/", capture_output=True,
                                   text=True, timeout=30)
            except subprocess.TimeoutExpired:
                problems.append(f"{repo_name}: {command} --help did not answer "
                                f"in 30s — it probably starts something instead")
                continue
            if r.returncode != 0:
                lines = (r.stderr or r.stdout).strip().splitlines()
                message = lines[-1] if lines else "?"
                if _REFUSAL.search(message):
                    # A command that needs an optional extra this check did
                    # not install, and says which one, is behaving. Only the
                    # [api,mcp] extras are installed here: pulling the rest
                    # would mean downloading a speech model to find out
                    # whether --help prints.
                    continue
                problems.append(f"{repo_name}: {command} --help — {message[:120]}")
    finally:
        if keep:
            print(f"  venv kept at {venv}")
        else:
            shutil.rmtree(venv, ignore_errors=True)
    return problems


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="check_wheels.py",
        description="Build each package and import it from a clean install.",
    )
    parser.add_argument("--only", nargs="*", help="Check only these repositories.")
    parser.add_argument("--keep", action="store_true",
                        help="Leave the virtual environments in place.")
    args = parser.parse_args(argv)

    names = args.only or list(PACKAGES)
    problems: list[str] = []
    for name in names:
        if name not in PACKAGES:
            print(f"{name}: not a published package, skipped")
            continue
        print(f"{name} …", flush=True)
        problems += check(name, PACKAGES[name], args.keep)

    if problems:
        print(f"\n{len(problems)} problem(s) a checkout cannot see:")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"\n{len(names)} package(s): every surface imports, every command answers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
