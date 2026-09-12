"""
Tests for the skill sync tool.

What matters is that it refuses to write by default and never destroys the
copy it replaces — an agent's installed skills are not something to
overwrite as a side effect.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sync():
    spec = importlib.util.spec_from_file_location(
        "_sync_skills", ROOT / "scripts" / "sync_local_skills.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_it_finds_the_repo_skills() -> None:
    """Every sprezzature-* folder with a SKILL.md, and nothing else."""
    module = _sync()
    found = {p.name for p in module.repo_skills(ROOT)}
    assert "sprezzature-figures" in found
    assert all(n.startswith("sprezzature-") for n in found)
    assert len(found) >= 8


def test_identical_folders_read_as_up_to_date(tmp_path: Path) -> None:
    """No diff, no noise."""
    module = _sync()
    src, dst = tmp_path / "a", tmp_path / "b"
    for d in (src, dst):
        d.mkdir()
        (d / "SKILL.md").write_text("same\n", encoding="utf-8")
    assert module.compare(src, dst) == ("up to date", 0)


def test_drift_is_counted_in_skill_md_lines(tmp_path: Path) -> None:
    """
    Only SKILL.md is compared line by line.

    It is the file an agent reads and the one whose staleness misleads; a
    byte-diff over 77 MB of vendored assets tells nobody anything.
    """
    module = _sync()
    src, dst = tmp_path / "a", tmp_path / "b"
    for d in (src, dst):
        d.mkdir()
    (src / "SKILL.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (dst / "SKILL.md").write_text("one\nCHANGED\nthree\n", encoding="utf-8")
    verdict, lines = module.compare(src, dst)
    assert verdict == "stale"
    assert lines >= 2


def test_a_missing_install_is_reported_not_crashed(tmp_path: Path) -> None:
    """A skill nobody installed is a fact, not an error."""
    module = _sync()
    src = tmp_path / "a"
    src.mkdir()
    (src / "SKILL.md").write_text("x\n", encoding="utf-8")
    assert module.compare(src, tmp_path / "nowhere")[0] == "not installed"


def test_refresh_keeps_the_copy_it_replaces(tmp_path: Path) -> None:
    """
    The previous version is moved aside, never deleted.

    Overwriting what an agent reads is worth doing carefully: if the new
    copy is wrong, the old one has to still exist.
    """
    module = _sync()
    src = tmp_path / "repo" / "sprezzature-x"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("new\n", encoding="utf-8")
    installed = tmp_path / "home" / "skills" / "sprezzature-x"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text("old\n", encoding="utf-8")

    kept = module.refresh(src, installed)
    assert (installed / "SKILL.md").read_text() == "new\n"
    assert kept.is_dir() and (kept / "SKILL.md").read_text() == "old\n"


def test_the_backup_is_not_itself_loaded_as_a_skill(tmp_path: Path) -> None:
    """
    The old copy must land outside the skills directory.

    The first version of this named the backup <skill>.superseded and left
    it in place. The runtime loaded every backup as a skill of its own, so
    an agent saw the refreshed description *and* the stale one it was meant
    to replace — worse than the drift the tool exists to fix.
    """
    module = _sync()
    src = tmp_path / "repo" / "sprezzature-x"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("new\n", encoding="utf-8")
    skills = tmp_path / "home" / "skills"
    installed = skills / "sprezzature-x"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text("old\n", encoding="utf-8")

    kept = module.refresh(src, installed)
    assert kept.parent != skills, f"the backup stayed in {skills}"
    assert skills not in kept.parents, f"{kept} is under the skills directory"
    # and the skills directory holds exactly the one skill
    assert [p.name for p in skills.iterdir()] == ["sprezzature-x"]


def test_audit_is_the_default() -> None:
    """
    Installing under $HOME changes what every future agent session reads.

    That is not something to do as a side effect of running a script, so
    --apply has to be asked for.
    """
    module = _sync()
    parser_defaults = module.main.__doc__
    assert parser_defaults  # the entry point is documented
    source = (ROOT / "scripts" / "sync_local_skills.py").read_text(encoding="utf-8")
    assert '"--apply", action="store_true"' in source
    assert "Default: audit only" in source
