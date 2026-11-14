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
    # WebVTT. sprezzature-audio owns timed text in both directions — it
    # transcribes sound into cues and narration turns text back into them —
    # so the format lives there and travels from there. Before this, the
    # suite had four writers of one format and two readers of it, each
    # rounding its own timestamps.
    "_vtt.py": "sprezzature-audio/scripts/_vtt.py",
    # The memoizing wallet. Registered on 2026-11-01, after finding the two
    # copies byte-identical at 311 lines with nothing comparing them — and
    # after very nearly writing a third, divergent one in
    # `sprezzature-accessibility`: a fixed backoff where this has a jittered
    # one, and a raise where this degrades to the JSON ledger. Both wrong, and
    # neither would have been caught.
    #
    # sprezzature-audio holds it for the same reason it holds the others, and
    # for one more: its `tests/test_concurrent_runs_transcribe_once.py` is
    # where the `SqliteLedger` creation race was measured ("two rounds in
    # six"), so the prose that explains the retry lives beside the test that
    # earned it.
    "_wallet.py": "sprezzature-audio/scripts/_wallet.py",
    # The model layer. Three files, 322 lines, with no knowledge of
    # charts or of maps in them: a Protocol every caller depends on instead of a
    # backend, the one wrapper over `best_engine_ai_helper.llm.chat()`, its
    # single schema-repair attempt, and the scriptable fake that lets the whole
    # suite test the model-facing paths with no model installed.
    #
    # Registered the day sprezzature-maps grew a model-facing layer of its own
    # and needed exactly these three. They are keyed by path suffix, not by
    # name, because `repair.py` names two different files in sprezzature-maps —
    # `assistant/` and `ralph/` — and propagating by name would have written
    # one over the other.
    #
    # Why duplicated rather than lifted into best-engine-ai-helper, which is
    # where logic this generic belongs: `client.py` imports that package
    # *lazily*, inside the call, so this layer — and every test of it — works
    # with the package absent. Lifting it upstream would trade that property
    # for a hard import, and would put the schema handling behind a
    # release of a repository outside this suite.
    #
    # sprezzature-figures is canonical: it is where the layer was written, and
    # where the real-model tests (`tests/assistant/test_live_llm.py`) live.
    "assistant/client.py":
        "sprezzature-figures/sprezzature_figures/assistant/client.py",
    "assistant/repair.py":
        "sprezzature-figures/sprezzature_figures/assistant/repair.py",
    "assistant/fake_client.py":
        "sprezzature-figures/sprezzature_figures/assistant/fake_client.py",
    # The inherited-ceiling reader. A package may not promise a Python its
    # dependencies cannot deliver, and `requires-python` is the promise a
    # reader acts on. The check lived in two bricks out of eleven until
    # 2026-11-02, and the single brick where an inherited ceiling actually bit
    # — `sprezzature-accessibility`, claiming 3.14 over a `wallet-helper` that
    # stops at 3.13 — was one of the nine without it.
    #
    # Shared rather than nine times rewritten, and shared *verbatim*: what
    # differs per brick is the measured table, which stays in each brick's own
    # test file. What must not differ is the reading — two cheaper ones were
    # tried first and each produced a confident false accusation, and that
    # reasoning is written into the file itself.
    #
    # `sprezzature-accessibility` is canonical: written there, and there is
    # where the real defect was found.
    "tests/_pywindow.py": "sprezzature-accessibility/tests/_pywindow.py",
    # The skill surface. Until 2026-11-12 the ten skills lived in this hub
    # only, so `pip install sprezzature-maps` carried every surface but the one
    # written for an agent. Each brick now ships its skill inside the package,
    # and these two files -- the install command and the guard that the wheel
    # carries it -- name no brick, so they are shared verbatim.
    # sprezzature-audio is canonical, like the other skill helpers.
    "_skill.py": "sprezzature-audio/sprezzature_audio/_skill.py",
    "tests/test_the_skill_ships_with_the_package.py":
        "sprezzature-audio/tests/test_the_skill_ships_with_the_package.py",
}

#: Shared helpers duplicated across skills, in reporting order.
SHARED_HELPERS = tuple(CANONICAL)

_VERSION_LINE = re.compile(r'^SKILL_VERSION\s*=\s*"[^"]*"', re.M)


def find_copies(helper: str, home: Path) -> list[Path]:
    """
    Every copy of `helper`, across the monorepo and its sibling repositories.

    A key is either a bare file name — ``"_argparse.py"``, which matches at any
    depth — or a path suffix, ``"assistant/client.py"``, which matches
    only where those directories nest in that order. The suffix form exists for
    helpers whose own name is not unique: ``repair.py`` names two different
    files in ``sprezzature-maps``, under ``assistant/`` and ``ralph/``, while
    each path suffix names exactly one. Prefer it for
    anything inside a package, and keep the bare form for the skill helpers,
    whose underscore names are unique by convention.

    Parameters
    ----------
    helper : str
        File name or path suffix, e.g. ``"_argparse.py"`` or
        ``"assistant/client.py"``.
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


def ambiguous_copies(helper: str, home: Path) -> dict[str, list[Path]]:
    """
    Repositories where `helper` names more than one file.

    :func:`find_copies` searches by file name, across a whole checkout. That is
    what lets the script work at all — the copies sit at different depths — and
    it is also its one sharp edge: a helper whose name is not unique suite-wide
    would have an unrelated namesake found as though it were a copy, and
    overwritten by ``--apply``.

    The signal that says so is structural, and needs no knowledge of what the
    files mean: a repository holds *one* copy of a shared helper, because one
    copy is what being in step is about. Two files of that name inside a single
    checkout therefore means the name is ambiguous, not that the repository is
    doubly in step.

    Measured against the registered helpers on 2026-11-01: all six have at most
    one copy per repository, while ``repair.py`` — a name that came within an
    inch of being registered, for the shared model layer — has two in
    ``sprezzature-maps``, under ``assistant/`` and ``ralph/``,
    and they are different files. Registering it would have written one over
    the other, in silence, and the propagation is exactly the step nobody reads
    a diff of.

    The cure for that particular case is a path-suffix key (see
    :func:`find_copies`), which names one file by construction. This check stays
    because the bare form stays too, for the skill helpers, and because nothing
    stops a future suffix from being ambiguous as well.

    Parameters
    ----------
    helper : str
        File name, e.g. ``"_argparse.py"``.
    home : pathlib.Path
        Directory holding the ``sprezzature*`` checkouts.

    Returns
    -------
    dict
        Repository name to its several same-named files. Empty when the name is
        unambiguous everywhere, which is the expected answer.

    Examples
    --------
    >>> ambiguous_copies("_vtt.py", Path.home()) if Path.home().joinpath(
    ...     "sprezzature-audio").is_dir() else {}
    {}
    """
    by_repo: defaultdict[str, list[Path]] = defaultdict(list)
    for path in find_copies(helper, home):
        by_repo[path.relative_to(home).parts[0]].append(path)
    return {repo: paths for repo, paths in sorted(by_repo.items()) if len(paths) > 1}


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
    ambiguous: list[str] = []
    for helper in SHARED_HELPERS:
        clashes = ambiguous_copies(helper, args.home)
        if clashes:
            ambiguous.append(helper)
            print(f"\n{helper}: the name is ambiguous — nothing written")
            for repo, paths in clashes.items():
                print(f"  {repo} holds {len(paths)} files of that name:")
                for path in paths:
                    print(f"                 {path.relative_to(args.home)}")
            print("  A shared helper needs a name no other file in the suite uses. "
                  "Rename it — the house convention is a leading underscore — or "
                  "unregister it. Propagating would overwrite the namesake.")
            continue

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

    if ambiguous:
        print(f"\n{len(ambiguous)} helper(s) share a name with another file in the "
              f"suite: {', '.join(ambiguous)}. Rename or unregister them; --apply "
              "refuses to write over a namesake.")
    if drifted and args.apply:
        print(f"\n{len(drifted)} helper(s) brought back in step. "
              "Review the diff before committing.")
        return 1 if ambiguous else 0
    if drifted:
        sources = ", ".join(CANONICAL[h] for h in drifted if h in CANONICAL)
        print(f"\n{len(drifted)} helper(s) have drifted. Edit {sources} "
              "and run this again with --apply.")
        return 1
    if ambiguous:
        return 1
    print("\nEvery shared helper is in step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
