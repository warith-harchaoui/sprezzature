#!/usr/bin/env python3
"""
package_skill
=============

Build a Claude-uploadable ``.zip`` for each shipped sprezzature-* skill,
and refuse to write one that the upload form would reject.

Why this exists
---------------

``scripts/release.sh`` builds ``.tar.gz`` archives for GitHub releases.
The Claude skill-import form wants a ``.zip`` and enforces a hard limit:
**30 MB uncompressed**. The two constraints are unrelated enough that a
tarball that uploads fine to a release page can still be refused by the
import form — which is exactly what happened to ``sprezzature-figures``:
a 30.5 MB zip whose payload was 74 MB of rendered showcase PNGs and SVGs
that no line of ``SKILL.md``, ``FIGURES.md`` or ``references/`` ever
reads, alongside *zero* generator code.

So this module encodes two rules the tarball path does not:

1. **A skill ships its inputs, not its outputs.** Rendered galleries are
   website material (``web/img/figures/`` already carries its own copy).
   They are excluded here by directory name — see :data:`SHOWCASE_DIRS`.
2. **A skill ships the code it documents.** When the monorepo split
   (see ``SPLIT.md``), some skills' generators moved to a standalone
   repo and the monorepo kept only the prose. Uploading the prose alone
   produces a skill that describes 127 chart generators and cannot draw
   one. :data:`EXTRACTED_CODE` grafts that code back in at packaging
   time, and :func:`build` fails loudly when it cannot find it.

The 30 MB check runs on the *uncompressed* total, before the zip is
written, and reports a per-directory breakdown so an over-budget skill
says which folder to cut rather than just "too big".

Fonts
-----

``sprezzature-figures`` embeds its faces into every generated SVG as
base64 WOFF2, so the WOFF2 files are a genuine runtime input. The
parallel ``.ttf`` files serve raster backends only and are 9.8 MB, so
they stay out of the zip — see :data:`FONT_SUFFIXES`.

Usage
-----
::

    # Every skill in SKILLS.txt, into dist/skills/
    python3 scripts/package_skill.py

    # One skill, custom destination
    python3 scripts/package_skill.py sprezzature-figures --out-dir /tmp

    # Generators live somewhere other than the sibling default
    python3 scripts/package_skill.py sprezzature-figures \\
        --code-from ~/work/sprezzature-figures

    # Report sizes without writing anything
    python3 scripts/package_skill.py --dry-run

Exit codes: ``0`` on success, ``1`` when a skill is over budget or its
extracted code is missing, ``64`` on bad arguments.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import io
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterator, NamedTuple, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skills_manifest import SHIPPED_SKILLS  # noqa: E402


#: The Claude skill-import form's ceiling, applied to the sum of the
#: payload's uncompressed file sizes. Stated in the form's own error
#: message ("Zip file uncompressed size exceeds 30MB"), so it is a
#: decimal 30 MB rather than 30 MiB — the stricter reading of the two.
MAX_UNCOMPRESSED_BYTES: int = 30_000_000

#: Directory and file names that never belong in a distributed skill:
#: editor/tooling caches, Finder turds, and local scratch space.
EXCLUDED_NAMES: frozenset[str] = frozenset(
    {
        ".DS_Store",
        ".git",
        ".mypy_cache",
        ".private",
        ".pytest_cache",
        ".ruff_cache",
        "__MACOSX",
        "__pycache__",
    }
)

#: File suffixes that are build artefacts of the files beside them.
EXCLUDED_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})

#: Directories holding *rendered* figures — the website gallery. They are
#: the skill's output, regenerable by running the generators, and they
#: are what pushed the figures zip past the limit (69 MB of the 74 MB).
#: ``web/img/figures/`` is the copy the site actually serves.
SHOWCASE_DIRS: frozenset[str] = frozenset(
    {"figures-gallery", "situation-maps", "svg-examples"}
)

#: Font file suffixes worth shipping. WOFF2 is embedded into every
#: generated SVG, so it is a runtime input; TTF duplicates it for raster
#: backends at 2.3x the bytes and is dropped.
FONT_SUFFIXES: frozenset[str] = frozenset({".woff2", ".txt", ".py"})

#: Directory names whose contents are filtered by :data:`FONT_SUFFIXES`.
FONT_DIRS: frozenset[str] = frozenset({"fonts", "sprezzature_figures_fonts"})

#: Skills whose code was extracted to a standalone repo, as
#: ``archive path -> path in the standalone repo``. Both may be a file
#: or a directory; archive paths are relative to the skill folder.
#:
#: The figures layout is not a straight copy, and the reason is worth
#: stating. Every generator opens with
#: ``sys.path.insert(0, <its own folder>)`` and then imports
#: ``sprezzature_figures.fonts``. Landing the font module *inside*
#: ``scripts/`` therefore makes ``python <skill>/scripts/make_bar.py``
#: work from any working directory with no ``PYTHONPATH`` and no install
#: step — and, because that folder goes on the front of ``sys.path``, it
#: also shadows any stale copy of the package the user happens to have
#: installed. ``fonts.py`` resolves its font folder two levels up from
#: itself, which is why the WOFF2 files land in
#: ``scripts/sprezzature_figures_fonts/`` — one of the two layouts the
#: module already looks in.
EXTRACTED_CODE: dict[str, dict[str, str]] = {
    "sprezzature-figures": {
        "scripts": "scripts",
        "scripts/sprezzature_figures/fonts.py": "sprezzature_figures/fonts.py",
        "scripts/sprezzature_figures_fonts": "assets/fonts",
    },
}

#: Files written into the archive that exist in no repo, as
#: ``skill -> {archive path: contents}``.
#:
#: The shim below deliberately does *not* reuse the standalone repo's
#: ``sprezzature_figures/__init__.py``: that one re-exports
#: ``make_figure``, dragging in the whole library to satisfy an import
#: that only ever wanted a font stack.
GENERATED_FILES: dict[str, dict[str, str]] = {
    "sprezzature-figures": {
        "scripts/sprezzature_figures/__init__.py": (
            '"""Font access for the bundled generators.\n\n'
            "Packaging shim. The skill ships the generators and the font\n"
            "module they need, not the whole ``sprezzature_figures``\n"
            "library, so this package stays empty on purpose: importing\n"
            "``sprezzature_figures.fonts`` must not pull in a figure\n"
            "factory, a catalog and a CLI to return a CSS font stack.\n"
            '"""\n'
        ),
    },
}


class Entry(NamedTuple):
    """
    One file in the archive: where it goes, and where its bytes come from.

    Exactly one of `disk` and `text` is set — a file copied off disk, or
    one synthesised at packaging time (see :data:`GENERATED_FILES`).
    """

    arc: Path
    disk: Path | None = None
    text: str | None = None

    @property
    def size(self) -> int:
        """Uncompressed size in bytes, which is what the limit counts."""
        if self.disk is not None:
            return self.disk.stat().st_size
        return len((self.text or "").encode("utf-8"))


def _is_excluded(relative: Path) -> bool:
    """
    Decide whether a path is dropped from every skill zip.

    Parameters
    ----------
    relative : Path
        Path relative to the skill folder, e.g.
        ``assets/figures-gallery/bar.png``.

    Returns
    -------
    bool
        True when any path segment is a cache/scratch name or a
        showcase directory, or the file is a compiled-Python artefact.
    """
    if relative.suffix in EXCLUDED_SUFFIXES:
        return True
    return any(
        part in EXCLUDED_NAMES or part in SHOWCASE_DIRS for part in relative.parts
    )


def _walk(source: Path, arc_prefix: Path) -> Iterator[Entry]:
    """
    Yield an :class:`Entry` for one file, or for every file in a tree.

    Parameters
    ----------
    source : Path
        A file or directory on disk.
    arc_prefix : Path
        Where `source` lands inside the archive. For a directory, its
        children are laid out underneath this prefix.

    Yields
    ------
    Entry
        One per file that survives the exclusion rules.
    """
    if source.is_file():
        if not _is_excluded(arc_prefix):
            yield Entry(arc_prefix, disk=source)
        return
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        arc: Path = arc_prefix / path.relative_to(source)
        if _is_excluded(arc):
            continue
        # The font folder is the one place we ship a subset of a
        # directory rather than all of it; see FONT_SUFFIXES.
        if arc.parts[-2] in FONT_DIRS and path.suffix not in FONT_SUFFIXES:
            continue
        yield Entry(arc, disk=path)


def plan_payload(skill: str, repo_root: Path, code_root: Path | None) -> list[Entry]:
    """
    Resolve everything that goes into one skill's zip.

    Parameters
    ----------
    skill : str
        Skill folder name, e.g. ``sprezzature-figures``.
    repo_root : Path
        This monorepo's root — where the skill folder lives.
    code_root : Path or None
        Standalone repo holding the skill's extracted generators, or
        None when the skill has none to graft.

    Returns
    -------
    list of Entry
        The skill folder first, grafted code next, synthesised files
        last, so a later entry wins a name clash by being written last.

    Raises
    ------
    FileNotFoundError
        If the skill folder, or a declared extracted-code path, is
        missing. A silent skip here is how a skill ships with no code.
    """
    skill_dir: Path = repo_root / skill
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"no such skill folder: {skill_dir}")

    entries: list[Entry] = list(_walk(skill_dir, Path(skill)))

    for arc_relative, code_relative in EXTRACTED_CODE.get(skill, {}).items():
        if code_root is None:
            raise FileNotFoundError(
                f"{skill} declares extracted code at '{code_relative}' but no "
                f"source repo was found; pass --code-from <path>"
            )
        source: Path = code_root / code_relative
        if not source.exists():
            raise FileNotFoundError(
                f"{skill}: extracted code missing at {source}. Packaging would "
                f"ship documentation with nothing behind it."
            )
        entries.extend(_walk(source, Path(skill) / arc_relative))

    for arc_relative, text in GENERATED_FILES.get(skill, {}).items():
        entries.append(Entry(Path(skill) / arc_relative, text=text))

    return entries


def breakdown(entries: Sequence[Entry]) -> list[tuple[str, int]]:
    """
    Total the payload by top-level folder inside the skill.

    Parameters
    ----------
    entries : sequence of Entry
        As returned by :func:`plan_payload`.

    Returns
    -------
    list of (str, int)
        ``(folder, bytes)`` sorted heaviest first. Files sitting
        directly in the skill root are grouped under ``"."``.
    """
    totals: dict[str, int] = {}
    for entry in entries:
        parts: tuple[str, ...] = entry.arc.parts[1:]
        key: str = "/".join(parts[:2]) if len(parts) > 1 else "."
        totals[key] = totals.get(key, 0) + entry.size
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def _mb(size: int) -> str:
    """Format a byte count as a short decimal-MB string."""
    return f"{size / 1_000_000:.1f} MB"


def build(
    skill: str,
    repo_root: Path,
    out_dir: Path,
    code_root: Path | None,
    dry_run: bool = False,
    fmt: str = "zip",
    suffix: str = "",
) -> tuple[Path | None, int]:
    """
    Package one skill, enforcing the uncompressed-size ceiling.

    Parameters
    ----------
    skill : str
        Skill folder name.
    repo_root : Path
        Monorepo root.
    out_dir : Path
        Destination folder for ``<skill>.zip``. Created if absent.
    code_root : Path or None
        Standalone repo for grafted generators.
    dry_run : bool, optional
        Report the size and skip writing the archive.
    fmt : str, optional
        ``"zip"`` for the Claude import form, ``"tar.gz"`` for a GitHub
        release. Same payload either way — which is the point: the release
        tarballs used to be a plain ``tar`` of the skill folder, so the
        figures one shipped the prose without the generators, exactly the
        way the import zip did.
    suffix : str, optional
        Appended to the archive stem, for a release's ``-<version>`` naming.

    Returns
    -------
    tuple of (Path or None, int)
        The written archive (None on a dry run) and the payload's
        uncompressed size in bytes.

    Raises
    ------
    ValueError
        If the payload exceeds :data:`MAX_UNCOMPRESSED_BYTES`. The
        message carries the per-folder breakdown, so the caller sees
        what to cut without re-running anything.
    """
    entries: list[Entry] = plan_payload(skill, repo_root, code_root)
    total: int = sum(entry.size for entry in entries)

    if total > MAX_UNCOMPRESSED_BYTES:
        lines: list[str] = [
            f"{skill}: {_mb(total)} uncompressed, over the "
            f"{_mb(MAX_UNCOMPRESSED_BYTES)} skill-import limit.",
            "Heaviest folders:",
        ]
        lines += [f"  {_mb(size):>9}  {name}" for name, size in breakdown(entries)[:8]]
        raise ValueError("\n".join(lines))

    if dry_run:
        return None, total

    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "zip":
        archive: Path = out_dir / f"{skill}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in entries:
                if entry.disk is not None:
                    zf.write(entry.disk, entry.arc.as_posix())
                else:
                    zf.writestr(entry.arc.as_posix(), entry.text or "")
        return archive, total

    archive = out_dir / f"{skill}{suffix}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        for entry in entries:
            if entry.disk is not None:
                tf.add(entry.disk, arcname=entry.arc.as_posix())
            else:
                payload = (entry.text or "").encode("utf-8")
                info = tarfile.TarInfo(entry.arc.as_posix())
                info.size = len(payload)
                info.mode = 0o644
                tf.addfile(info, io.BytesIO(payload))
    return archive, total


def _default_code_root(skill: str, repo_root: Path) -> Path | None:
    """
    Guess where a skill's extracted generators live.

    The split put each standalone repo beside the monorepo
    (``~/sprezzature`` and ``~/sprezzature-figures``), so the sibling
    folder named after the skill is the convention.

    Parameters
    ----------
    skill : str
        Skill folder name.
    repo_root : Path
        Monorepo root.

    Returns
    -------
    Path or None
        The sibling repo if it exists, else None.
    """
    candidate: Path = repo_root.parent / skill
    return candidate if candidate.is_dir() else None


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. See the module docstring for usage."""
    parser = argparse.ArgumentParser(
        description="Build Claude-uploadable .zip archives for sprezzature-* skills.",
    )
    parser.add_argument(
        "skills",
        nargs="*",
        metavar="SKILL",
        help="skill folders to package (default: every skill in SKILLS.txt)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("dist/skills"),
        help="where to write the archives (default: dist/skills)",
    )
    parser.add_argument(
        "--code-from",
        type=Path,
        default=None,
        help="standalone repo holding extracted generators "
        "(default: the sibling folder named after the skill)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report sizes without writing archives",
    )
    parser.add_argument(
        "--format",
        choices=("zip", "tar.gz"),
        default="zip",
        help="zip for the Claude import form, tar.gz for a GitHub release",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="appended to each archive stem, e.g. -1.1.0",
    )
    args = parser.parse_args(argv)

    repo_root: Path = Path(__file__).resolve().parent.parent
    skills: tuple[str, ...] = tuple(args.skills) or SHIPPED_SKILLS

    unknown: list[str] = [s for s in skills if not (repo_root / s).is_dir()]
    if unknown:
        print(f"error: no such skill folder: {', '.join(unknown)}", file=sys.stderr)
        return 64

    failures: int = 0
    for skill in skills:
        code_root: Path | None = args.code_from or _default_code_root(skill, repo_root)
        try:
            archive, total = build(
                skill, repo_root, args.out_dir, code_root, args.dry_run,
                fmt=args.format, suffix=args.suffix,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"FAIL {exc}", file=sys.stderr)
            failures += 1
            continue
        headroom: str = f"{100 * total / MAX_UNCOMPRESSED_BYTES:.0f}% of limit"
        target: str = "(dry run)" if archive is None else str(archive)
        print(f"  {skill:<28} {_mb(total):>9} uncompressed, {headroom:<15} {target}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
