"""
test_md_to_html — regression tests for the Markdown → HTML converter.

Covers three defects fixed together:

1. Same-basename sources in different directories must not overwrite each
   other — the output mirrors the input tree.
2. The document language is detected, not silently assumed to be English.
3. A Mermaid block gets meaningful alt text (author ``accTitle`` / ``accDescr``,
   else the diagram kind), never the meaningless "Mermaid diagram".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "sprezzature-publish" / "scripts" / "md_to_html.py"

sys.path.insert(0, str(REPO_ROOT / "sprezzature-publish" / "scripts"))
from md_to_html import _mermaid_alt  # noqa: E402


def _run(target: Path, out: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the converter on ``target`` writing into ``out``."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(target), "--out", str(out)],
        capture_output=True, text=True, check=True,
    )


def test_directory_structure_is_preserved(tmp_path: Path) -> None:
    """Two ``index.md`` files in different dirs produce distinct outputs."""
    src = tmp_path / "src"
    (src / "api").mkdir(parents=True)
    (src / "guide").mkdir(parents=True)
    (src / "api" / "index.md").write_text("# API\n\nThe API page.\n", encoding="utf-8")
    (src / "guide" / "index.md").write_text("# Guide\n\nThe guide page.\n", encoding="utf-8")
    out = tmp_path / "out"

    _run(src, out)

    # Both survive — the flat-``stem`` bug would have left only one index.html.
    assert (out / "api" / "index.html").is_file()
    assert (out / "guide" / "index.html").is_file()
    assert "API" in (out / "api" / "index.html").read_text(encoding="utf-8")
    assert "Guide" in (out / "guide" / "index.html").read_text(encoding="utf-8")


def test_language_is_detected_not_assumed(tmp_path: Path) -> None:
    """A French document is tagged ``lang="fr"``, not the old default ``en``."""
    src = tmp_path / "doc.md"
    src.write_text(
        "# Bonjour\n\nCeci est un document en langue française pour vérifier "
        "la détection automatique de la langue du contenu.\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    _run(src, out)
    html = (out / "doc.html").read_text(encoding="utf-8")
    assert 'lang="fr"' in html


def test_mermaid_alt_prefers_author_text_then_kind() -> None:
    """accDescr > accTitle > diagram-kind fallback; never 'Mermaid diagram'."""
    assert _mermaid_alt("graph TD\n  accDescr: The full build pipeline\n  A-->B") == \
        "The full build pipeline"
    assert _mermaid_alt("flowchart LR\n  accTitle: Request lifecycle\n  A-->B") == \
        "Request lifecycle"
    assert _mermaid_alt("sequenceDiagram\n  A->>B: hi") == "sequence diagram (diagram source below)"
    # An %%{init}%% directive line must not be mistaken for the diagram kind.
    assert _mermaid_alt("%%{init: {}}%%\nflowchart LR\n A-->B").startswith("flowchart")
    assert "Mermaid diagram" not in _mermaid_alt("flowchart LR\n A-->B")
