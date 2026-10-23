#!/usr/bin/env python3
"""
audit_releases
==============

What each repository of the suite *says* its release is, in the four places
that say it, side by side. ``SURFACES.md`` is to ``audit_surfaces.py`` what a
release note is to this: the contract is written down, and this reports the
state from what is on disk.

The four places, and what a disagreement between them means:

``pyproject.toml``
    The version a build would stamp. The source of truth; everything else is
    compared against it.
``CHANGELOG.md``
    The top entry. A newer version in ``pyproject.toml`` than in the changelog
    is a release nobody wrote down.
a git tag
    ``v<version>``, and with ``--remote``, the same question asked of
    ``origin``. Without a tag the commit that produced a published artifact
    cannot be found again. Five repositories of this suite were in that state
    on 2026-10-23, all released on 19 October and none tagged. A tag that
    exists only on the machine that made it is the same gap wearing a
    reassuring label, which is why ``--remote`` is a separate column rather
    than a footnote: on that date the newest tag on ``origin`` was older than
    the version on PyPI in six of the ten repositories, and every local
    column said ``ok``. A *newest* tag that is ahead of ``pyproject.toml`` is
    the other direction: ``sprezzature-maps`` carried a local ``v1.1.0`` from
    August, and the package was renumbered down to 1.0.0 when it became a
    standalone brick in October.
PyPI
    With ``--pypi``. A version in the repository and not on the index is a
    release that was committed and never published: ``sprezzature-accessibility``
    1.2.1 sat there since 21 October while ``pip install`` handed out 1.2.0.

Nothing here writes. Tagging and publishing are deliberate acts.

Usage
-----
::

    python3 scripts/audit_releases.py            # from disk, no network
    python3 scripts/audit_releases.py --remote   # also ask origin for its tags
    python3 scripts/audit_releases.py --pypi     # also ask the index
    python3 scripts/audit_releases.py --strict   # exit 1 on any disagreement

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from skills_manifest import SHIPPED_SKILLS  # noqa: E402

#: ``version = "1.2.3"``. Regex and not ``tomllib``: this repository supports
#: Python 3.10, where that module is not in the standard library.
_VERSION = re.compile(r'^\s*version\s*=\s*["\']([\d.]+)["\']', re.M)

#: A changelog heading naming a version, in either house style: ``## [1.2.1] —``
#: and ``## v1.5.0 (2026-10-21):`` are both in use across the suite.
_CHANGELOG_HEAD = re.compile(r"^#+\s*\[?v?(\d+\.\d+\.\d+)", re.M)

#: ``v1.2.3``. Tags older than the suite's current naming are ignored rather
#: than guessed at.
_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _repo(name: str) -> Path | None:
    path = REPO_ROOT if name == "sprezzature" else REPO_ROOT.parent / name
    return path if (path / "pyproject.toml").is_file() else None


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60
    )
    return done.stdout if done.returncode == 0 else ""


def _pypi_latest(package: str) -> str | None:
    """The newest version on the simple index — the one ``pip`` reads.

    The simple index and not the JSON API: the JSON endpoint has answered for
    a package that ``pip install`` could not then resolve, which is the wrong
    way round for a check meant to tell you whether an install will work.
    """
    url = f"https://pypi.org/simple/{package}/"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    stem = package.replace("-", "[-_]")
    found = re.findall(rf"{stem}-(\d+\.\d+\.\d+)", body)
    return max(found, key=_key) if found else None


def _remote_tags(repo: Path) -> list[str] | None:
    """The versions ``origin`` carries as tags, or ``None`` if it cannot be asked.

    ``^{}`` lines are the commits annotated tags point at; the tag names are
    the lines without them, and counting both doubles every annotated tag.
    """
    out = _git(repo, "ls-remote", "--tags", "origin")
    if not out:
        return None
    found = []
    for line in out.splitlines():
        name = line.rsplit("/", 1)[-1]
        if name.endswith("^{}"):
            continue
        match = _TAG.match(name)
        if match:
            found.append(match.group(1))
    return found


def _state(name: str, ask_pypi: bool, ask_remote: bool = False) -> dict[str, object] | None:
    repo = _repo(name)
    if repo is None:
        return None
    version = _VERSION.search((repo / "pyproject.toml").read_text(encoding="utf-8"))
    changelog = repo / "CHANGELOG.md"
    top = (
        _CHANGELOG_HEAD.search(changelog.read_text(encoding="utf-8"))
        if changelog.is_file()
        else None
    )
    tags = [m.group(1) for m in map(_TAG.match, _git(repo, "tag", "--list").split()) if m]
    current = version.group(1) if version else "?"
    remote = _remote_tags(repo) if ask_remote else None
    return {
        "repo": name,
        "version": current,
        "changelog": top.group(1) if top else "—",
        "tagged": current in tags,
        "newest_tag": max(tags, key=_key) if tags else "—",
        "remote_tag": (max(remote, key=_key) if remote else "—") if remote is not None else None,
        "pypi": _pypi_latest(name) if ask_pypi else None,
    }


def _complaints(row: dict[str, object]) -> list[str]:
    """What disagrees, in words. Empty when the four places agree."""
    out: list[str] = []
    version = str(row["version"])
    if row["changelog"] not in (version, "—"):
        out.append(f"CHANGELOG tops out at {row['changelog']}, pyproject says {version}")
    if not row["tagged"]:
        out.append(f"no v{version} tag: the commit behind the artifact is unfindable")
    newest = str(row["newest_tag"])
    if newest != "—" and _key(newest) > _key(version):
        out.append(f"newest tag v{newest} names a version this repo does not have")
    remote = row.get("remote_tag")
    if remote is not None:
        if remote == "—":
            out.append("origin carries no version tag at all")
        elif _key(str(remote)) < _key(version):
            out.append(
                f"origin's newest tag is v{remote}: the tag for {version} is on "
                f"this machine only"
            )
    pypi = row["pypi"]
    if pypi is not None:
        if _key(str(pypi)) < _key(version):
            out.append(f"PyPI serves {pypi}: {version} is committed and unpublished")
        elif _key(str(pypi)) > _key(version):
            out.append(f"PyPI serves {pypi}, newer than this checkout")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="also ask origin for tags")
    parser.add_argument("--pypi", action="store_true", help="also query the index")
    parser.add_argument("--strict", action="store_true", help="exit 1 on disagreement")
    args = parser.parse_args()

    names = ("sprezzature", *SHIPPED_SKILLS)
    rows = [
        row for row in (_state(n, args.pypi, args.remote) for n in names)
        if row is not None
    ]
    if not rows:
        print("no checkout found — run scripts/fetch_siblings.sh", file=sys.stderr)
        return 2

    head = f'{"repo":28} {"version":9} {"changelog":10} {"tag":5} {"newest tag":11}'
    if args.remote:
        head += f' {"on origin":11}'
    if args.pypi:
        head += " pypi"
    print(head)
    print("-" * len(head))
    for row in rows:
        line = (
            f'{row["repo"]:28} {row["version"]:9} {row["changelog"]:10} '
            f'{"ok" if row["tagged"] else "--":5} {row["newest_tag"]:11}'
        )
        if args.remote:
            line += f' {str(row["remote_tag"]):11}'
        if args.pypi:
            line += f' {row["pypi"] or "?"}'
        print(line)

    trouble = [(row["repo"], _complaints(row)) for row in rows]
    trouble = [(name, said) for name, said in trouble if said]
    if trouble:
        print()
        for name, said in trouble:
            for line in said:
                print(f"  {name}: {line}")
    else:
        print("\nevery repository agrees with itself about what its release is")

    missing = len(names) - len(rows)
    if missing:
        print(f"\n{missing} repo(s) not checked out here; CI fetches all nine.")
    return 1 if (trouble and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
