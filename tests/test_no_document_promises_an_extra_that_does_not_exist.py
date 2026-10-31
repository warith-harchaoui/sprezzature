"""
A ``pip install`` line must not name an extra the manifest does not declare.

pip, handed an extra a distribution does not have, prints a warning and
installs the rest. It does not fail. So a document can tell a reader, for
weeks, to install a ``[cli]`` extra of ``sprezzature-maps`` that is declared
nowhere; the reader can run that line, and nothing reports that the bracket
did nothing — not the reader's
terminal, which looks like a success, and not this repository, which never
reads its own instructions.

Found on 2026-10-31, after ``[click]`` and ``[cli]`` were folded into the base
install when the argparse front doors were dropped on 2026-10-25. Eleven
shipped places still sold them: three install blocks in sprezzature-figures's
README and LISEZMOI each, five in sprezzature-maps (including the module
docstring of its own command line), one in sprezzature-video's, the
``[click]`` block in sprezzature-cli-gui's README, LISEZMOI, EXAMPLES, CODING
and CONTRIBUTING — and, in this repository, the SKILL.md sentence telling a
reader that the figures commands "all need the ``[cli]`` extra".

Three CI workflows asked for it too: their editable-install lines listed
``cli`` among the extras, in sprezzature-maps, sprezzature-video and
sprezzature-figures. Those are the ones worth pausing on. The workflow was green, every test passed, and the
install line had been wrong for a week — the warning scrolled past in a log
nobody reads when the job is green.

Why it lives here
-----------------
Because the promise and the manifest are frequently in different
repositories: this repository's ``sprezzature-<brick>/SKILL.md`` sells extras
that only the brick's ``pyproject.toml`` can confirm. A copy of this check
inside each brick would be blind to exactly that case, which is the one that
shipped.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

#: Read with regexes rather than ``tomllib``, which is 3.11+ while this suite
#: supports 3.10 — there the import alone fails collection of the whole file.
_PROJECT_NAME = re.compile(r'^name\s*=\s*["\']([^"\']+)["\']', re.M)
_OPTIONAL_BLOCK = re.compile(
    r"^\[project\.optional-dependencies\]\n(.*?)(?=^\[|\Z)", re.M | re.S
)
_EXTRA_NAME = re.compile(r"^([\w.-]+)\s*=\s*\[", re.M)

#: ``pip install`` … then, anywhere on the same line, ``thing[a,b]``. ``thing``
#: is either a distribution name or a bare dot for "this repository", which is
#: how a workflow spells it, with the extras in brackets after the dot.
#:
#: Each extra must *start* with a letter or a digit, as PEP 508 requires. That
#: is not decoration: without it the pattern reads an elision in prose —
#: ``[dev,...]``, written in ``test_ci_reads_what_it_is_told.py`` to stand for
#: "whatever extras" — as a promise of an extra named ``...``, and reports a
#: ghost in a sentence that promises nothing.
_EXTRA = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_PROMISE = re.compile(
    r"pip install[^\n]*?([A-Za-z0-9][A-Za-z0-9._-]*|\.)"
    rf"\[({_EXTRA}(?:\s*,\s*{_EXTRA})*)\]"
)

#: Directories whose contents are not shipped instructions.
_UNSCANNED = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
        ".private",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "site-packages",
    }
)
_TEXT = frozenset(
    {".md", ".py", ".yml", ".yaml", ".txt", ".toml", ".cfg", ".rst", ".sh"}
)


def _bricks() -> list[str]:
    """The brick names, from the file the fetch script reads."""
    text = (REPO_ROOT / "SKILLS.txt").read_text(encoding="utf-8")
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _checkout(brick: str) -> Path | None:
    repo = REPO_ROOT.parent / brick
    return repo if repo.is_dir() else None


def _manifest_of(repo: Path) -> tuple[str | None, set[str]]:
    """``(distribution name, declared extras)`` for a checkout."""
    path = repo / "pyproject.toml"
    if not path.is_file():
        return None, set()
    text = path.read_text(encoding="utf-8", errors="replace")
    name = _PROJECT_NAME.search(text)
    block = _OPTIONAL_BLOCK.search(text)
    extras = set(_EXTRA_NAME.findall(block.group(1))) if block else set()
    return (name.group(1) if name else None), extras


def _manifests() -> dict[str, set[str]]:
    """Every suite distribution this machine can see, to its declared extras."""
    out: dict[str, set[str]] = {}
    for repo in [
        REPO_ROOT,
        *(p for p in (_checkout(b) for b in _bricks()) if p is not None),
    ]:
        name, extras = _manifest_of(repo)
        if name is not None:
            out[name] = extras
    return out


def _sources(repo: Path) -> list[Path]:
    return sorted(
        path
        for path in repo.rglob("*")
        if path.is_file()
        and path.suffix in _TEXT
        and not _UNSCANNED & set(path.relative_to(repo).parts)
    )


def _promises(repo: Path) -> list[tuple[str, int, str, str]]:
    """``(file, line, distribution, extra)`` for every install line in a repo."""
    own_name, _ = _manifest_of(repo)
    out: list[tuple[str, int, str, str]] = []
    for path in _sources(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _PROMISE.finditer(text):
            dist, extras = match.group(1), match.group(2)
            if dist == ".":
                if own_name is None:
                    continue
                dist = own_name
            line = text.count("\n", 0, match.start()) + 1
            for extra in extras.split(","):
                extra = extra.strip()
                if extra:
                    out.append((str(path.relative_to(repo)), line, dist, extra))
    return out


def _ghosts(repo: Path, manifests: dict[str, set[str]]) -> list[str]:
    """Promises in ``repo`` naming an extra of a *suite* distribution that has none."""
    bad = []
    for rel, line, dist, extra in _promises(repo):
        if dist not in manifests:
            continue  # a third-party distribution, or a brick not checked out
        if extra not in manifests[dist]:
            bad.append(
                f"{rel}:{line} promises {dist}[{extra}]; {dist} declares "
                f"{sorted(manifests[dist]) or 'no extras at all'}"
            )
    return bad


def test_this_repository_promises_no_extra_that_does_not_exist() -> None:
    """The hub's own documents, SKILL.md files included."""
    ghosts = _ghosts(REPO_ROOT, _manifests())
    assert not ghosts, (
        "a pip install line names an extra nobody declares:\n" + "\n".join(ghosts)
    )


@pytest.mark.parametrize("brick", _bricks(), ids=lambda value: value)
def test_a_brick_promises_no_extra_that_does_not_exist(brick: str) -> None:
    """Each brick's own documents, read from here against every manifest."""
    repo = _checkout(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}")
    ghosts = _ghosts(repo, _manifests())
    assert not ghosts, (
        f"{brick}: a pip install line names an extra nobody declares:\n"
        + "\n".join(ghosts)
    )


def test_the_scan_reads_real_install_lines() -> None:
    """
    A file that found nothing to check reads exactly like a file that passed.

    The regexes above are the whole check: one bad character in ``_PROMISE``
    and every case goes green while reading nothing. So this asks the smaller
    question the cases cannot — that there are install lines here at all, and
    that the manifests they are judged against were actually parsed.
    """
    manifests = _manifests()
    assert len(manifests) >= 2, (
        f"only {len(manifests)} suite manifest(s) parsed ({sorted(manifests)}): "
        f"the cases above would compare every promise against nothing and pass. "
        f"Either no sibling is checked out, or _PROJECT_NAME stopped matching."
    )
    assert any(extras for extras in manifests.values()), (
        f"not one manifest declares an extra, across {sorted(manifests)}: "
        f"_OPTIONAL_BLOCK or _EXTRA_NAME stopped matching, and every promise "
        f"would then look like a ghost — or none would."
    )
    promises = _promises(REPO_ROOT)
    assert promises, (
        "no pip install line with an extra found anywhere in this repository, "
        "which has install blocks in its README and in every SKILL.md: "
        "_PROMISE stopped matching how they are written."
    )
