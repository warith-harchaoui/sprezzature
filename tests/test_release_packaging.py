"""
test_release_packaging — end-to-end smoke test for ``scripts/release.sh``.

What this checks
----------------
Running ``scripts/release.sh`` against a throw-away version into a
temporary directory must produce:

* one tarball per shipped skill, plus a bundle tarball,
* a ``SHA256SUMS`` file whose entries verify against the artifacts,
* tarballs that extract cleanly to a folder named after the skill,
* a valid ``SKILL.md`` inside each extracted skill (re-checked with
  the strict YAML validator),
* no junk in the archives — ``.git``, ``__pycache__``,
  ``.pytest_cache``, ``.DS_Store``, etc. must not be packaged.

The test is hermetic: the script runs into ``tmp_path``, the existing
``dist/`` directory in the repo is untouched, and no network access is
required. ``tar`` and a ``sha256sum`` / ``shasum`` binary are the only
host dependencies (both are baseline on Linux / macOS).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from validate_skill import validate_skill


# ── Constants ──────────────────────────────────────────────────────────────

#: Version label used for the test build. Must not start with ``v`` —
#: release.sh rejects ``v``-prefixed inputs.
TEST_VERSION: str = "0.0.0-test"

#: The shipped skills, in the same order release.sh packages them.
#: Sourced from ``SKILLS.txt`` via ``scripts/skills_manifest.py`` so
#: this list cannot drift from the release script / the validator.
from skills_manifest import SHIPPED_SKILLS as SKILLS  # noqa: E402

#: Patterns whose presence inside a packaged tarball is a regression.
#: Catches both the macOS Finder turds and the Python tooling caches.
BANNED_PATTERNS: tuple[str, ...] = (
    ".DS_Store",
    "__MACOSX",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git/",
)


# ── Shared fixture: actually invoke release.sh ─────────────────────────────

#: Repo root resolved from this file's location so the fixture below
#: can be module-scoped without requesting the function-scoped
#: ``repo_root`` fixture (pytest scope mismatch).
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built_release(tmp_path_factory) -> Path:
    """
    Run ``scripts/release.sh`` once per test module and return the dist dir.

    Reusing the same build across tests keeps the suite fast (tar
    + sha256 over the four skill trees takes a few seconds).
    """
    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH — release.sh cannot run")
    out_dir: Path = tmp_path_factory.mktemp("release")
    proc = subprocess.run(
        ["bash", str(_REPO_ROOT / "scripts" / "release.sh"),
         TEST_VERSION, str(out_dir)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"release.sh exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return out_dir


# ── Tarball + checksum invariants ──────────────────────────────────────────

def test_release_produces_expected_artifacts(built_release: Path) -> None:
    """Five tarballs + SHA256SUMS, no extras."""
    artifacts = sorted(p.name for p in built_release.iterdir())
    expected = sorted(
        [f"{s}-{TEST_VERSION}.tar.gz" for s in SKILLS]
        + [f"sprezzature-skills-{TEST_VERSION}.tar.gz", "SHA256SUMS"]
    )
    assert artifacts == expected, (
        f"unexpected dist contents: got {artifacts}, want {expected}"
    )


def test_sha256sums_match_artifacts(built_release: Path) -> None:
    """Recompute every SHA256 from disk and confirm SHA256SUMS is honest."""
    declared: dict[str, str] = {}
    for line in (built_release / "SHA256SUMS").read_text().splitlines():
        if not line.strip():
            continue
        sha, name = line.split(maxsplit=1)
        declared[name.strip()] = sha
    for name, expected_sha in declared.items():
        path = built_release / name
        assert path.is_file(), f"SHA256SUMS lists missing file: {name}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected_sha, (
            f"checksum mismatch for {name}: "
            f"declared {expected_sha}, actual {actual}"
        )


# ── Per-skill tarball integrity ────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", SKILLS)
def test_skill_tarball_contains_valid_skill(
    built_release: Path, tmp_path: Path, skill_name: str,
) -> None:
    """Extract the per-skill tarball and re-run the YAML validator on it."""
    tarball: Path = built_release / f"{skill_name}-{TEST_VERSION}.tar.gz"
    extract_dir: Path = tmp_path / f"extract-{skill_name}"
    extract_dir.mkdir()
    with tarfile.open(tarball, "r:gz") as tf:
        # Use the safe filter where available (Python ≥ 3.12 deprecates the
        # default); fall back silently on older runtimes.
        try:
            tf.extractall(extract_dir, filter="data")
        except TypeError:
            tf.extractall(extract_dir)

    extracted: Path = extract_dir / skill_name
    assert extracted.is_dir(), (
        f"{skill_name} tarball did not contain a top-level "
        f"{skill_name}/ folder"
    )
    errors = validate_skill(extracted)
    assert errors == [], (
        f"extracted {skill_name} failed validator: {errors}"
    )


@pytest.mark.parametrize("skill_name", SKILLS)
def test_skill_tarball_has_no_banned_files(
    built_release: Path, skill_name: str,
) -> None:
    """No `.git`, `__pycache__`, or `.DS_Store` should ride along."""
    tarball: Path = built_release / f"{skill_name}-{TEST_VERSION}.tar.gz"
    with tarfile.open(tarball, "r:gz") as tf:
        for member in tf.getnames():
            for banned in BANNED_PATTERNS:
                assert banned not in member, (
                    f"{skill_name} tarball includes banned path "
                    f"matching {banned!r}: {member}"
                )


@pytest.mark.parametrize("skill_name", SKILLS)
def test_skill_tarball_includes_referenced_scripts(
    built_release: Path, tmp_path: Path, skill_name: str,
) -> None:
    """
    If the skill's SKILL.md references a script path, it must be in the
    tarball. Catches stale doc → missing-file regressions like the
    ``cli-gui-workflow.md`` slip-up that v0.3.2 fixed.
    """
    tarball: Path = built_release / f"{skill_name}-{TEST_VERSION}.tar.gz"
    extract_dir: Path = tmp_path / f"refs-{skill_name}"
    extract_dir.mkdir()
    with tarfile.open(tarball, "r:gz") as tf:
        try:
            tf.extractall(extract_dir, filter="data")
        except TypeError:
            tf.extractall(extract_dir)
    skill_root: Path = extract_dir / skill_name
    skill_md = (skill_root / "SKILL.md").read_text()
    # Look for any local path-shaped backtick reference. The pattern
    # deliberately stays narrow: only `scripts/...` / `references/...`
    # / `assets/...` paths that look like real on-disk files (have an
    # extension or look like a known directory).
    import re
    candidates: set[str] = set(re.findall(
        r"`((?:scripts|references|assets)/[A-Za-z0-9._\-/]+)`",
        skill_md,
    ))
    missing: list[str] = []
    for rel in candidates:
        # Strip Markdown trailing punctuation if any leaked into the match.
        rel = rel.rstrip(".,;:)")
        # Some references include trailing ``.md`` or ``.py`` — keep them
        # as written. Bare directory references (no extension) are OK if
        # the directory exists.
        target: Path = skill_root / rel
        if "." in target.name:
            ok = target.is_file()
        else:
            ok = target.exists()
        if not ok:
            missing.append(rel)
    assert not missing, (
        f"{skill_name} SKILL.md references missing paths: {missing}"
    )


# ── Bundle tarball ─────────────────────────────────────────────────────────

def test_bundle_tarball_contains_every_skill(
    built_release: Path, tmp_path: Path,
) -> None:
    """The bundle is a single tarball that contains all four skills."""
    bundle: Path = built_release / f"sprezzature-skills-{TEST_VERSION}.tar.gz"
    extract_dir: Path = tmp_path / "bundle"
    extract_dir.mkdir()
    with tarfile.open(bundle, "r:gz") as tf:
        try:
            tf.extractall(extract_dir, filter="data")
        except TypeError:
            tf.extractall(extract_dir)
    for name in SKILLS:
        skill_root = extract_dir / name
        assert skill_root.is_dir(), f"bundle missing {name}/"
        errors = validate_skill(skill_root)
        assert errors == [], f"bundled {name} failed validator: {errors}"


# ── Reasonable file size ───────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", SKILLS)
def test_skill_tarball_size_sanity(
    built_release: Path, skill_name: str,
) -> None:
    """Catch accidental inclusion of model weights / video / etc."""
    tarball: Path = built_release / f"{skill_name}-{TEST_VERSION}.tar.gz"
    size_mb: float = tarball.stat().st_size / 1_000_000
    # 10 MB is generous — the biggest shipped skill (sprezzature-ui with
    # the three-Roboto WOFF2 bundle: Roboto + Roboto Serif + Roboto Mono,
    # variable + italic-variable each, latin subset) is well under 1 MB
    # compressed. Anything over 10 MB is almost certainly a fixture /
    # cache that slipped in.
    assert size_mb < 10, (
        f"{tarball.name} is {size_mb:.1f} MB — almost certainly a "
        "fixture / cache / model file that slipped in"
    )
