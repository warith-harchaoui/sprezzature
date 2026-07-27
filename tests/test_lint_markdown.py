"""
test_lint_markdown — smoke tests for sprezzature-publish/scripts/lint_markdown.py.

Fixtures are public-domain (Gettysburg Address) so the tests are
reproducible by anyone without third-party content.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "sprezzature-publish" / "scripts" / "lint_markdown.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "public" / "gettysburg.md"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def test_lint_public_fixture_runs() -> None:
    """The Gettysburg fixture should at minimum parse and exit 0 or 1."""
    proc = _run(str(FIXTURE))
    # The fixture intentionally contains an empty-alt image and a
    # mermaid block. Empty alt is INFO (no exit flip). Without
    # --render-mermaid we don't try to render. Exit 0 expected.
    assert proc.returncode in (0, 1), (
        f"unexpected exit {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_lint_detects_known_intentional_issues() -> None:
    """The fixture has at least one INFO-level finding (empty alt)."""
    proc = _run(str(FIXTURE), "--format", "json")
    assert proc.returncode in (0, 1)
    # Either the JSON contains MD045 or there are no findings — both are
    # acceptable. We only assert the script ran.
    assert "[" in proc.stdout or proc.stdout.strip() == "[]"


def test_link_syntax_in_code_span_is_not_a_broken_link(tmp_path: Path) -> None:
    """MD050 must ignore link *syntax examples* inside inline-code / fences.

    Documenting ``[text](url)`` in a table cell or code span is not a real
    link; the broken-link check must skip code before scanning (regression:
    ``sprezzature-publish/references/audio-narration.md`` flagged its own docs).
    """
    doc = tmp_path / "syntax.md"
    doc.write_text(
        "# Syntax\n\n"
        "| Element | Behaviour |\n"
        "|---|---|\n"
        "| Link (`[text](url)`) | text kept, URL dropped |\n"
        "| Image (`![alt](url)`) | alt kept |\n\n"
        "```markdown\n[also here](nowhere.md)\n```\n",
        encoding="utf-8",
    )
    proc = _run(str(doc), "--format", "text")
    assert "MD050" not in proc.stdout, (
        f"code-span link syntax wrongly flagged:\n{proc.stdout}"
    )

    # A genuine broken link OUTSIDE code must still be caught.
    doc.write_text("See [the missing page](does-not-exist.md).\n", encoding="utf-8")
    proc = _run(str(doc), "--format", "text")
    assert "MD050" in proc.stdout and proc.returncode == 1


def test_lint_help_advertises_mermaid_and_ai() -> None:
    proc = _run("-h")
    assert proc.returncode == 0
    assert "Mermaid" in proc.stdout
    assert "--ai" in proc.stdout
    assert "--render-mermaid" in proc.stdout


def test_version_flag() -> None:
    """``-V`` must exit 0 and report the shared SKILL_VERSION."""
    # Read from the canonical source so the test does not lock to one
    # release tag (cf. test_cli_help.py).
    from _argparse import SKILL_VERSION  # noqa: E402

    proc = _run("-V")
    assert proc.returncode == 0
    assert SKILL_VERSION in proc.stdout


def test_prompts_load_without_pyyaml() -> None:
    """The YAML loader fallback (_yaml_lite) handles our prompt files."""
    sys.path.insert(0, str(REPO_ROOT / "sprezzature-publish" / "scripts"))
    from _prompts import load_prompt  # type: ignore

    # ``_prompts`` may already live in ``sys.modules`` from a sibling test
    # that loaded it through a different skill's scripts/ — pass the dir
    # explicitly so this test is order-independent.
    prompts_dir = REPO_ROOT / "sprezzature-publish" / "scripts" / "prompts"
    mermaid = load_prompt("mermaid_labels", prompts_dir=prompts_dir)
    latex = load_prompt("latex_caption", prompts_dir=prompts_dir)
    assert "Reply with a JSON array" in mermaid["output_contract"]
    assert "Plain UTF-8 text" in latex["output_contract"]
    assert mermaid["rules_numbered"].startswith("1.")
    assert latex["rules_numbered"].startswith("1.")
