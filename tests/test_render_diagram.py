"""
test_render_diagram — the sprezzature-figures Ralph Eyeball Loop renderer.

`render_diagram.py` turns a declarative graphical source (Vega-Lite JSON,
TikZ, Mermaid) into an image so the agent can *look* at it and refine the
source. The rasterisation itself needs external toolchains (vl-convert,
tectonic, mmdc) that CI does not carry, so those paths are exercised only
for their fail-loud behaviour. Everything deterministic — kind detection,
background resolution, palette theming of the source, and ``--dry-run`` —
is unit-tested here without any toolchain.

Author
------
Project maintainers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "sprezzature-figures" / "scripts"))

import render_diagram as rd  # noqa: E402


# ------------------------------------------------------------------
# Kind detection
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "name, body, expected",
    [
        ("fig.vl.json", '{"$schema": "x", "mark": "bar"}', "vega"),
        ("fig.json", '{"mark": "bar", "encoding": {}}', "vega"),
        ("diagram.tex", "\\documentclass{standalone}", "tikz"),
        ("d.tikz", "\\begin{tikzpicture}\\end{tikzpicture}", "tikz"),
        ("flow.mmd", "graph TD; A-->B", "mermaid"),
        ("flow.mermaid", "sequenceDiagram\n A->>B: hi", "mermaid"),
    ],
)
def test_detect_kind_by_extension(name: str, body: str, expected: str) -> None:
    """Extension wins first; each maps to the right kind."""
    assert rd.detect_kind(name, body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        ("\\begin{tikzpicture}\\draw (0,0);\\end{tikzpicture}", "tikz"),
        ("flowchart LR\n a --> b", "mermaid"),
        ('{"$schema": "https://vega/v5", "mark": "point", "encoding": {}}', "vega"),
    ],
)
def test_detect_kind_by_content(body: str, expected: str) -> None:
    """An ambiguous extension falls back to a content sniff."""
    assert rd.detect_kind("mystery.txt", body) == expected


def test_detect_kind_unknown_fails_loud() -> None:
    """A source that matches nothing raises rather than guessing."""
    with pytest.raises(SystemExit):
        rd.detect_kind("mystery.txt", "just some prose, no markers")


# ------------------------------------------------------------------
# Background resolution
# ------------------------------------------------------------------
def test_background_transparent_is_none() -> None:
    """Transparent resolves to None (the renderer sets it explicitly later)."""
    assert rd.resolve_background("transparent", dark=False) is None


def test_background_white_and_dark() -> None:
    """Named backgrounds resolve to the expected house hexes."""
    assert rd.resolve_background("white", dark=False) == "#FFFFFF"
    assert rd.resolve_background("dark", dark=False) == rd._DARK_BG


def test_background_auto_follows_dark_flag() -> None:
    """auto tracks --dark for the canvas color."""
    assert rd.resolve_background("auto", dark=False) == rd._LIGHT_BG
    assert rd.resolve_background("auto", dark=True) == rd._DARK_BG


def test_background_explicit_hex_passthrough() -> None:
    """An explicit #RRGGBB is returned verbatim."""
    assert rd.resolve_background("#123456", dark=False) == "#123456"


def test_background_rejects_garbage() -> None:
    """An unrecognised background fails loud."""
    with pytest.raises(SystemExit):
        rd.resolve_background("chartreuse", dark=False)


# ------------------------------------------------------------------
# TikZ palette theming
# ------------------------------------------------------------------
def test_tikz_preamble_defines_palette_colors() -> None:
    """The preamble defines front-prefixed colors from the palette."""
    preamble = rd.tikz_color_preamble(dark=False)
    assert "\\definecolor{sprezzatureBlue}{HTML}{007AFF}" in preamble
    assert "\\definecolor{sprezzatureFg}" in preamble
    assert "\\definecolor{sprezzatureBg}" in preamble


def test_wrap_tikz_fragment_becomes_document() -> None:
    """A bare tikzpicture fragment is wrapped into a standalone document."""
    body = "\\begin{tikzpicture}\\draw (0,0) -- (1,1);\\end{tikzpicture}"
    doc = rd.wrap_tikz_document(body, dark=False, theme=True)
    assert doc.startswith("\\documentclass[border=6pt]{standalone}")
    assert "\\usepackage{tikz}" in doc
    assert body in doc
    assert "\\definecolor{sprezzatureBlue}" in doc  # theme injected


def test_wrap_tikz_wraps_loose_commands() -> None:
    """Loose TikZ commands get their own tikzpicture environment."""
    doc = rd.wrap_tikz_document("\\draw (0,0) circle (1);", dark=False, theme=False)
    assert "\\begin{tikzpicture}" in doc
    assert "\\definecolor" not in doc  # theme suppressed


def test_wrap_tikz_respects_full_document() -> None:
    """A source that already declares a documentclass is left untouched."""
    full = "\\documentclass{article}\n\\begin{document}hi\\end{document}"
    assert rd.wrap_tikz_document(full, dark=False, theme=True) == full


# ------------------------------------------------------------------
# Mermaid palette theming
# ------------------------------------------------------------------
def test_mermaid_init_directive_is_valid_json_theme() -> None:
    """The init directive carries a parseable base-theme block."""
    line = rd.mermaid_init_directive(dark=False, background="#FFFFFF")
    assert line.startswith("%%{init: ") and line.rstrip().endswith("}%%")
    payload = json.loads(line.strip()[len("%%{init: "):-len("}%%")])
    assert payload["theme"] == "base"
    assert payload["themeVariables"]["fontFamily"].startswith("Roboto")
    assert payload["themeVariables"]["background"] == "#FFFFFF"


def test_mermaid_theme_injected_when_absent() -> None:
    """A diagram without its own init gets the palette directive prepended."""
    out = rd.inject_mermaid_theme("graph TD; A-->B", dark=False, background=None, theme=True)
    assert out.startswith("%%{init:")
    assert "graph TD; A-->B" in out


def test_mermaid_theme_not_double_injected() -> None:
    """An existing init directive is respected, not duplicated."""
    src = "%%{init: {\"theme\":\"dark\"}}%%\ngraph TD; A-->B"
    assert rd.inject_mermaid_theme(src, dark=False, background=None, theme=True) == src


def test_mermaid_theme_suppressed_with_no_theme() -> None:
    """--no-theme leaves the source verbatim."""
    src = "graph TD; A-->B"
    assert rd.inject_mermaid_theme(src, dark=False, background=None, theme=False) == src


# ------------------------------------------------------------------
# themed_source dispatch + Vega passthrough
# ------------------------------------------------------------------
def test_vega_source_passes_through_untouched() -> None:
    """Vega colors live in the spec's own config; the source is not rewritten."""
    spec = '{"mark": "bar"}'
    assert rd.themed_source("vega", spec, dark=False, background="#FFFFFF", theme=True) == spec


# ------------------------------------------------------------------
# CLI: --dry-run and argument guards (no toolchain needed)
# ------------------------------------------------------------------
def test_dry_run_prints_themed_tikz(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--dry-run emits the palette-themed source and skips rendering."""
    src = tmp_path / "d.tex"
    src.write_text("\\begin{tikzpicture}\\draw (0,0) -- (1,1);\\end{tikzpicture}", encoding="utf-8")
    rc = rd.main([str(src), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "\\documentclass[border=6pt]{standalone}" in out
    assert "\\definecolor{sprezzatureBlue}" in out


def test_render_requires_out(tmp_path: Path) -> None:
    """Without --out (and not --dry-run) the CLI exits non-zero."""
    src = tmp_path / "d.mmd"
    src.write_text("graph TD; A-->B", encoding="utf-8")
    assert rd.main([str(src)]) == 2


def test_missing_source_file_exits() -> None:
    """A non-existent source path exits non-zero, not a traceback."""
    assert rd.main(["/no/such/file.vl.json", "--out", "x.png"]) == 2
