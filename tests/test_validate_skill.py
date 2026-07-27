"""
test_validate_skill — coverage for the YAML-strict skill validator
shared at ``scripts/validate_skill.py``.

The validator is the cross-skill foundation: every SKILL.md must pass
it before a release is tagged. The tests cover both the happy path
(all four shipped skills validate green) and the negative paths a
careless edit would otherwise let slip into a release:

* invalid YAML in the frontmatter (the original failure mode that
  motivated the rewrite — unquoted ``:`` characters silently broke
  ``yaml.safe_load`` even though the regex check still passed),
* missing or empty ``name`` / ``description``,
* ``name`` that doesn't match the folder,
* missing or malformed frontmatter delimiters,
* empty Markdown body,
* the CLI's exit code is non-zero on any failure and zero when every
  skill passes.

Each negative case builds a throw-away skill folder under ``tmp_path``
so the suite stays deterministic and never depends on git state or
network.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from validate_skill import (
    DESCRIPTION_MAX,
    DESCRIPTION_MIN,
    validate_skill,
)


# ── Helpers ────────────────────────────────────────────────────────────────

#: A description long enough to clear the minimum-length check. Reused
#: across the negative-case builders so each fake skill only flips one
#: rule at a time.
GOOD_DESCRIPTION: str = (
    "A throw-away skill folder used by the test suite. Its only purpose "
    "is to exercise one validator rule at a time, so the description is "
    "deliberately bland and long enough to pass the length check."
)


def _make_skill(
    root: Path,
    name: str,
    *,
    frontmatter: str | None = "DEFAULT",
    body: str = "# heading\n\nNon-empty body.\n",
) -> Path:
    """
    Build a synthetic skill folder under ``root`` and return its path.

    Parameters
    ----------
    root : Path
        Parent directory (typically ``tmp_path``).
    name : str
        Skill folder name (also expected as the YAML ``name`` field
        unless the caller overrides ``frontmatter``).
    frontmatter : str or None, optional
        YAML body (without the ``---`` delimiters). Pass ``None`` to
        omit the frontmatter block entirely. The sentinel ``"DEFAULT"``
        means *"emit a sane frontmatter that matches the folder name"*.
    body : str, optional
        Markdown body after the frontmatter.

    Returns
    -------
    Path
        The skill folder path.
    """
    skill_dir: Path = root / name
    skill_dir.mkdir(parents=True)
    if frontmatter == "DEFAULT":
        frontmatter = f'name: {name}\ndescription: >-\n  {GOOD_DESCRIPTION}\n'
    if frontmatter is None:
        content: str = body
    else:
        content = f"---\n{frontmatter}---\n{body}"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


# ── Happy path — shipped skills ────────────────────────────────────────────

@pytest.mark.parametrize(
    "skill_name",
    list(__import__("skills_manifest").SHIPPED_SKILLS),
)
def test_shipped_skill_passes(repo_root: Path, skill_name: str) -> None:
    """Every skill on ``main`` must validate green."""
    errors = validate_skill(repo_root / skill_name)
    assert errors == [], f"{skill_name} unexpectedly failed: {errors}"


# ── Negative paths — fake skills under tmp_path ────────────────────────────

class TestNegativeCases:
    """One rule violated per test, in a throw-away skill folder."""

    def test_missing_skill_md(self, tmp_path: Path) -> None:
        # Empty folder — no SKILL.md at all.
        skill = tmp_path / "ghost"
        skill.mkdir()
        errors = validate_skill(skill)
        assert errors and "SKILL.md missing" in errors[0]

    def test_invalid_yaml_frontmatter(self, tmp_path: Path) -> None:
        # The original real-world bug: unquoted ``:`` inside the
        # description value tricks the YAML parser into starting a
        # nested mapping. The validator must catch it.
        broken: str = (
            'name: badyaml\n'
            'description: Hello world: this colon breaks parsing\n'
        )
        skill = _make_skill(tmp_path, "badyaml", frontmatter=broken)
        errors = validate_skill(skill)
        assert errors and "not valid YAML" in errors[0]

    def test_missing_name_field(self, tmp_path: Path) -> None:
        fm: str = f'description: >-\n  {GOOD_DESCRIPTION}\n'
        skill = _make_skill(tmp_path, "noname", frontmatter=fm)
        errors = validate_skill(skill)
        assert any("'name' missing or empty" in e for e in errors)

    def test_missing_description_field(self, tmp_path: Path) -> None:
        fm: str = "name: nodesc\n"
        skill = _make_skill(tmp_path, "nodesc", frontmatter=fm)
        errors = validate_skill(skill)
        assert any("'description' missing or empty" in e for e in errors)

    def test_name_mismatches_folder(self, tmp_path: Path) -> None:
        # Folder is "folder-a" but frontmatter says "folder-b".
        fm: str = f'name: folder-b\ndescription: >-\n  {GOOD_DESCRIPTION}\n'
        skill = _make_skill(tmp_path, "folder-a", frontmatter=fm)
        errors = validate_skill(skill)
        assert any("does not match folder name" in e for e in errors)

    def test_no_frontmatter_at_all(self, tmp_path: Path) -> None:
        # SKILL.md exists but starts with a heading, not ``---``.
        skill = _make_skill(
            tmp_path, "raw",
            frontmatter=None,
            body="# raw\n\nNo frontmatter here.\n",
        )
        errors = validate_skill(skill)
        assert errors and "frontmatter block" in errors[0]

    def test_empty_body(self, tmp_path: Path) -> None:
        fm: str = f'name: bodyless\ndescription: >-\n  {GOOD_DESCRIPTION}\n'
        skill = _make_skill(tmp_path, "bodyless", frontmatter=fm, body="\n  \n")
        errors = validate_skill(skill)
        assert any("Markdown body is empty" in e for e in errors)

    def test_description_too_short(self, tmp_path: Path) -> None:
        # Below the spec's lower bound.
        short: str = "x" * (DESCRIPTION_MIN - 1)
        fm: str = f'name: short\ndescription: >-\n  {short}\n'
        skill = _make_skill(tmp_path, "short", frontmatter=fm)
        errors = validate_skill(skill)
        assert any("description too short" in e for e in errors)

    def test_description_too_long(self, tmp_path: Path) -> None:
        # Above the Anthropic 1024-char cap.
        long: str = "x" * (DESCRIPTION_MAX + 1)
        fm: str = f'name: toolong\ndescription: >-\n  {long}\n'
        skill = _make_skill(tmp_path, "toolong", frontmatter=fm)
        errors = validate_skill(skill)
        assert any("exceeds" in e for e in errors)

    def test_placeholder_token_in_skill_md(self, tmp_path: Path) -> None:
        fm: str = f'name: todo\ndescription: >-\n  {GOOD_DESCRIPTION}\n'
        body: str = "# todo\n\nThis section has a TODO marker.\n"
        skill = _make_skill(tmp_path, "todo", frontmatter=fm, body=body)
        errors = validate_skill(skill)
        assert any("placeholder token" in e for e in errors)

    def test_readme_at_skill_root_is_rejected(self, tmp_path: Path) -> None:
        # The Anthropic spec forbids README.md anywhere inside a skill
        # folder. The top-level case is the obvious one.
        skill = _make_skill(tmp_path, "readme-top")
        (skill / "README.md").write_text("# stray README\n", encoding="utf-8")
        errors = validate_skill(skill)
        assert any("README.md found inside" in e for e in errors)

    def test_readme_nested_is_rejected(self, tmp_path: Path) -> None:
        # The non-obvious case: a README hiding under
        # ``assets/examples/.../`` is just as bad. The validator must
        # walk the whole tree, not just the top level.
        skill = _make_skill(tmp_path, "readme-nested")
        nested: Path = skill / "assets" / "examples" / "demo"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# stray nested\n", encoding="utf-8")
        errors = validate_skill(skill)
        assert any("README.md found inside" in e for e in errors)
        # The error message should name the nested path so the
        # maintainer doesn't have to grep for it.
        assert any("assets/examples/demo/README.md" in e for e in errors)


# ── CLI contract — exit codes ──────────────────────────────────────────────

class TestCLIContract:
    """``python scripts/validate_skill.py …`` exit code matches result."""

    def test_exit_zero_on_all_pass(self, repo_root: Path) -> None:
        from skills_manifest import SHIPPED_SKILLS

        proc = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "validate_skill.py"),
                *[str(repo_root / s) for s in SHIPPED_SKILLS],
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            f"expected 0, got {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    def test_exit_nonzero_on_broken_yaml(
        self, repo_root: Path, tmp_path: Path
    ) -> None:
        # Build a broken skill in tmp_path and feed it to the CLI.
        broken: str = (
            'name: broken\n'
            'description: bad: yaml: here\n'
        )
        skill = _make_skill(tmp_path, "broken", frontmatter=broken)
        proc = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "validate_skill.py"),
                str(skill),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert "not valid YAML" in proc.stderr


# ── validate_all orchestrator ──────────────────────────────────────────────

def test_validate_all_passes_on_shipped_repo(repo_root: Path) -> None:
    """The top-level orchestrator exits 0 on the shipped repo."""
    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "validate_all.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"validate_all.py exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "PASS — all 9 skill(s)" in proc.stdout
