"""
sync_helpers — keep the duplicated helpers in step, from one canonical copy.

Why this exists
---------------
Four small helpers (``_argparse.py``, ``_click.py``, ``_lang.py``,
``_vocab.py``) are copied into every skill on purpose: a skill has to install
and run on its own, including from a downloaded zip with nothing but the
standard library available, so it cannot import a shared package from a
sibling repository.

That duplication is a deliberate exception to "don't repeat yourself", and it
is only safe while the copies stay identical. What must not be repeated is the
*editing*: one copy is declared canonical in :data:`CANONICAL` below, that is
the one to change, and this script propagates it everywhere else. Editing a
copy by hand, in ten places, is the repetition worth removing.

``SKILL_VERSION`` is the one line that legitimately differs: it names the
release of the repository the copy sits in, not of the helper. It is preserved
on propagation, and ignored when comparing.

Usage
-----
::

    python3 scripts/sync_helpers.py                 # report, change nothing
    python3 scripts/sync_helpers.py --diff _lang.py # show what differs
    python3 scripts/sync_helpers.py --apply         # propagate the canonical copy

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
from collections import defaultdict
from pathlib import Path

#: Copy to propagate from, per helper, relative to the directory holding the
#: checkouts. sprezzature-audio holds the most recently revised prose for all
#: four: its docstrings gloss what argparse, Click and langdetect are on first
#: mention, which is what the writing charter asks for.
CANONICAL: dict[str, str] = {
    "_argparse.py": "sprezzature-audio/scripts/_argparse.py",
    "_click.py": "sprezzature-audio/scripts/_click.py",
    "_lang.py": "sprezzature-audio/scripts/_lang.py",
    "_vocab.py": "sprezzature-audio/scripts/_vocab.py",
}

#: Shared helpers duplicated across skills, in reporting order.
SHARED_HELPERS = tuple(CANONICAL)

_VERSION_LINE = re.compile(r'^SKILL_VERSION\s*=\s*"[^"]*"', re.M)


def find_copies(helper: str, home: Path) -> list[Path]:
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
    out: list[Path] = []
    for repo in sorted(home.glob("sprezzature*")):
        if not repo.is_dir():
            continue
        for path in repo.rglob(helper):
            if any(part in skip or part.endswith(".egg-info") for part in path.parts):
                continue
            out.append(path)
    return sorted(out)


def comparable(text: str) -> str:
    """
    `text` with its ``SKILL_VERSION`` blanked out.

    Each repository sets that line to its own released version, so two copies
    that differ only there are in step, not drifted.
    """
    return _VERSION_LINE.sub('SKILL_VERSION = "—"', text)


def group_by_content(paths: list[Path]) -> dict[str, list[Path]]:
    """
    Bucket copies by their bytes, ``SKILL_VERSION`` aside.

    Returns
    -------
    dict
        Short digest to the paths sharing it, largest group first.
    """
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        body = comparable(path.read_text(encoding="utf-8"))
        groups[hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]].append(path)
    return dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))


def rendered_for(canonical_text: str, target: Path) -> str:
    """
    `canonical_text`, carrying `target`'s own ``SKILL_VERSION``.

    Raises
    ------
    ValueError
        If one file declares a ``SKILL_VERSION`` and the other does not: that
        is a real difference, and silently dropping or inventing the line
        would either re-version a package or lose its version entirely.
    """
    current = _VERSION_LINE.search(target.read_text(encoding="utf-8"))
    wanted = _VERSION_LINE.search(canonical_text)
    if (current is None) != (wanted is None):
        raise ValueError(f"{target}: SKILL_VERSION on one side only")
    if current is None:
        return canonical_text
    return _VERSION_LINE.sub(current.group(0), canonical_text, count=1)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="sync_helpers.py",
        description="Report — or, with --apply, repair — drift between the "
                    "duplicated copies of the shared helpers.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write the canonical copy over every other one, keeping each "
             "file's own SKILL_VERSION.",
    )
    parser.add_argument("--diff", help="Show the diff for this helper against the canonical copy.")
    parser.add_argument(
        "--home", type=Path, default=Path.home(),
        help="Directory holding the sprezzature* checkouts. Defaults to $HOME.",
    )
    args = parser.parse_args(argv)

    drifted: list[str] = []
    for helper in SHARED_HELPERS:
        copies = find_copies(helper, args.home)
        if len(copies) < 2:
            print(f"\n{helper}: {len(copies)} copy — nothing to compare")
            continue

        source = args.home / CANONICAL[helper]
        if not source.is_file():
            print(f"\n{helper}: canonical copy missing at {CANONICAL[helper]}")
            drifted.append(helper)
            continue
        canonical_text = source.read_text(encoding="utf-8")

        stale = [p for p in copies
                 if p != source and p.read_text(encoding="utf-8") != rendered_for(canonical_text, p)]
        if not stale:
            print(f"\n{helper}: {len(copies)} copies, all in step")
            continue

        drifted.append(helper)
        groups = group_by_content(copies)
        print(f"\n{helper}: {len(copies)} copies in {len(groups)} versions "
              f"— canonical is {CANONICAL[helper]}")
        for digest, paths in groups.items():
            mark = "canonical" if source in paths else "         "
            print(f"  {digest}  {mark}  {len(paths)} cop{'y' if len(paths) == 1 else 'ies'}")
            for path in paths:
                print(f"                 {path.relative_to(args.home)}")

        if args.diff == helper:
            for path in stale:
                print(f"\n  ── {path.relative_to(args.home)} against the canonical copy")
                diff = difflib.unified_diff(
                    canonical_text.splitlines(),
                    path.read_text(encoding="utf-8").splitlines(),
                    fromfile=CANONICAL[helper], tofile=str(path.relative_to(args.home)),
                    lineterm="",
                )
                for line in list(diff)[:40]:
                    print(f"  {line}")

        if args.apply:
            for path in stale:
                path.write_text(rendered_for(canonical_text, path), encoding="utf-8")
                print(f"  → wrote {path.relative_to(args.home)}")

    if drifted and args.apply:
        print(f"\n{len(drifted)} helper(s) brought back in step. "
              "Review the diff before committing.")
        return 0
    if drifted:
        sources = ", ".join(CANONICAL[h] for h in drifted if h in CANONICAL)
        print(f"\n{len(drifted)} helper(s) have drifted. Edit {sources} "
              "and run this again with --apply.")
        return 1
    print("\nEvery shared helper is in step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
