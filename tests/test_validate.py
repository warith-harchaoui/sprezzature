"""
Test the validator script by running it as a subprocess against the
actual skill folder.

The validator imports SKILL.md / references at module-import time, so
re-importing it in-process for multiple tests is awkward. The cleanest
contract is to run it the way users do — as a script — and assert on
the exit code and stdout.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_validate_passes_on_shipped_skill(repo_root: Path) -> None:
    """The skill on ``main`` must validate green at all times."""
    proc = subprocess.run(
        [sys.executable, str(repo_root / "sprezzature-ui" / "scripts" / "validate.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"validate.py exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "PASS — skill is shippable." in proc.stdout
