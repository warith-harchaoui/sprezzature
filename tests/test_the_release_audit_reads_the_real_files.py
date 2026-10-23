"""
``audit_releases.py`` reports the release state, and this keeps it readable.

The script is a report, not a gate, and that is deliberate: the only invariant
strong enough to test -- "the current version is tagged" -- is false for the
twenty minutes of every release between the version bump and the tag, so a
test asserting it would fire on the one workflow it exists to protect.

What *can* be tested is that the report is still reading the files it claims
to read. A parser that quietly stops matching reports a clean suite, which is
the failure mode a report has instead of a false green.

No network here. ``--pypi`` is exercised by running it, not by a test that
would turn an outage into a red build.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "audit_releases.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from skills_manifest import SHIPPED_SKILLS  # noqa: E402


@pytest.fixture(scope="module")
def report() -> str:
    done = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _row(report: str, name: str) -> list[str] | None:
    for line in report.splitlines():
        if line.startswith(name + " "):
            return line.split()
    return None


def test_the_report_names_this_repository_and_reads_its_version(report: str) -> None:
    """The version column is the one ``pyproject.toml`` holds, not a default."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^\s*version\s*=\s*"([\d.]+)"', pyproject, re.M)
    assert version, "this repository's pyproject.toml has no version"
    row = _row(report, "sprezzature")
    assert row is not None, f"audit_releases printed no row for this repository:\n{report}"
    assert row[1] == version.group(1), (
        f"the report reads version {row[1]}, pyproject.toml says "
        f"{version.group(1)} — the version parser stopped matching"
    )


def test_the_report_reads_the_changelog_too(report: str) -> None:
    """Both house styles of changelog heading are understood.

    ``## [1.2.1] — 2026-10-21`` in eight repositories, ``## v1.5.0 (2026-10-21):``
    in ``sprezzature-audio``. A pattern that knows only the first reports a dash
    for the second, which reads as "no changelog" and is not.
    """
    row = _row(report, "sprezzature")
    assert row is not None
    assert row[2] != "—", (
        "the report cannot find a version heading in this repository's "
        "CHANGELOG.md, which has one"
    )


def test_the_report_covers_every_brick_this_machine_holds(report: str) -> None:
    """A report that silently shrank to one repository is not a report."""
    here = [
        brick for brick in SHIPPED_SKILLS
        if (REPO_ROOT.parent / brick / "pyproject.toml").is_file()
    ]
    if not here:
        pytest.skip("no sibling checkout; run scripts/fetch_siblings.sh")
    missing = [brick for brick in here if _row(report, brick) is None]
    assert not missing, f"audit_releases skipped {missing}, which are checked out here"
