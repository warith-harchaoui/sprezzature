"""
Tests for ``palette_to_tailwind`` — the make-side emitter that turns
``sprezzature-colors/references/palette.csv`` into a Tailwind v3+
``theme.extend.colors`` block (or a complete ``tailwind.config.js``).

Covers:

* Default ``--emit theme`` output: emits exactly the 8 saturated brand
  hues; does NOT emit Brown / Black / Gray / White unless
  ``--include-neutrals`` is passed.
* ``--with-dark`` derives a dark variant per token via OKLCH.
* ``--emit config`` produces a parseable, valid ``module.exports``
  literal containing the brand block plus the canonical
  label / surface / separator tokens.
* CSV → emitted-config round-trip: every saturated Base name from the
  CSV appears in the emitted block with its CSV-canonical hex.
* ``--out PATH`` writes the rendered string to disk and exits 0.

The script is stdlib-only so the tests do not need a fixture
directory beyond ``tmp_path``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ``conftest.py`` adds ``sprezzature-colors/scripts`` to ``sys.path`` so
# these imports resolve cleanly.
from _colors import apple_palette, load_palette
from palette_to_tailwind import (
    SATURATED_BASES,
    render_brand_block,
    render_full_config,
)


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = (
    REPO_ROOT / "sprezzature-colors" / "scripts" / "palette_to_tailwind.py"
)


# ── In-process rendering ──────────────────────────────────────────────────


def test_default_emits_only_saturated() -> None:
    """The default (no ``--include-neutrals``) yields exactly 8 brand entries."""
    rows = load_palette()
    block: str = render_brand_block(rows)
    # Each emitted entry sits on its own line; count the lines that
    # carry a colon-followed-by-DEFAULT pattern, which is unique to
    # brand entries (not the comment lines).
    entries: list[str] = [
        ln for ln in block.splitlines() if "DEFAULT:" in ln
    ]
    assert len(entries) == len(SATURATED_BASES) == 8


def test_neutrals_only_appear_when_opted_in() -> None:
    """``include_neutrals=True`` adds Brown / Black / Gray / White rows."""
    rows = load_palette()
    saturated: str = render_brand_block(rows, include_neutrals=False)
    with_neutrals: str = render_brand_block(rows, include_neutrals=True)
    for neutral in ("brown", "black", "gray", "white"):
        assert neutral not in saturated, (
            f"'{neutral}' leaked into the default (saturated-only) block"
        )
        assert neutral in with_neutrals, (
            f"'{neutral}' missing from --include-neutrals output"
        )


def test_with_dark_adds_one_field_per_entry() -> None:
    """``with_dark`` injects exactly one ``dark: '#XXXXXX'`` per brand row."""
    rows = load_palette()
    block: str = render_brand_block(rows, with_dark=True)
    dark_count: int = sum(1 for ln in block.splitlines() if "dark:" in ln)
    assert dark_count == 8


def test_csv_hexes_are_preserved_verbatim() -> None:
    """Every CSV hex for the 8 saturated bases must appear in the output."""
    rows = load_palette()
    expected: dict[str, str] = apple_palette()  # {Name: #HEX}
    block: str = render_brand_block(rows)
    for name, hex_code in expected.items():
        assert hex_code.upper() in block.upper(), (
            f"saturated hex {hex_code} for {name} missing from output"
        )


def test_full_config_contains_brand_and_non_brand_tokens() -> None:
    """``--emit config`` carries the canonical label / surface / separator block."""
    rows = load_palette()
    config: str = render_full_config(rows)
    # Module shape — must be valid Tailwind config skeleton.
    assert config.startswith("/** @type {import('tailwindcss').Config}")
    assert "module.exports" in config
    # The block must carry the canonical non-brand tokens.
    for token in ("label:", "surface:", "separator:"):
        assert token in config, f"{token} missing from --emit config"
    # ...and at least the sprezzature-ui-required brand keys.
    for brand_key in ("blue", "red", "green"):
        assert f"{brand_key}" in config


def test_emitted_block_indent_matches_reference() -> None:
    """Brand block uses 8-space indent (matches stack-tailwind.md depth)."""
    rows = load_palette()
    block: str = render_brand_block(rows, indent=8)
    # The literal ``        brand: {`` line — eight leading spaces.
    assert "\n        brand: {\n" in "\n" + block + "\n"


# ── CLI surface ────────────────────────────────────────────────────────────


def test_version_flag() -> None:
    """``--version`` exits 0 and names the script."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "sprezzature-colors-palette-to-tailwind" in proc.stdout


def test_help_flag_advertises_emit_choices() -> None:
    """``--help`` exits 0 and documents both emit modes."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    collapsed: str = " ".join(proc.stdout.split())
    assert "theme" in collapsed
    assert "config" in collapsed
    assert "--with-dark" in collapsed
    assert "--include-neutrals" in collapsed


def test_stdout_emits_block_by_default() -> None:
    """No flags → emit theme block to stdout, exit 0."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "brand: {" in proc.stdout
    assert "#007AFF" in proc.stdout  # blue base


def test_out_flag_writes_file(tmp_path: Path) -> None:
    """``--out PATH`` writes to disk and prints a confirmation to stderr."""
    target: Path = tmp_path / "tailwind.config.js"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--emit", "config", "--out", str(target)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert target.exists()
    body: str = target.read_text(encoding="utf-8")
    assert "module.exports" in body
    assert "brand:" in body
    assert "wrote" in proc.stderr  # informational line


def test_out_flag_failure_is_reported(tmp_path: Path) -> None:
    """A bad ``--out`` path exits 1 and prints to stderr (no traceback)."""
    bogus: Path = tmp_path / "nonexistent-subdir" / "tailwind.config.js"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(bogus)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "write failed" in proc.stderr


@pytest.mark.parametrize("base", sorted(SATURATED_BASES))
def test_each_saturated_base_emits_a_token(base: str) -> None:
    """Smoke: every name in :data:`SATURATED_BASES` lands in the output."""
    rows = load_palette()
    block: str = render_brand_block(rows)
    assert base.lower() in block, f"{base.lower()} missing from emitted block"
