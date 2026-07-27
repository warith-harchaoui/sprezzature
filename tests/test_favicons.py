"""
test_favicons — coverage for ``sprezzature-publish/scripts/favicons.py``.

Covers the colour parser, the square resize, the alpha-flatten, the
maskable variant, and an end-to-end run that emits every expected
artefact (PNG variants, ICO, apple-touch, manifest, head snippet).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

import favicons as fv  # noqa: E402


def _make_source(path: Path, *, size: int = 256, color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> Path:
    """Write a square solid-colour PNG and return its path."""
    Image.new("RGBA", (size, size), color).save(path, format="PNG")
    return path


# ── parse_hex ───────────────────────────────────────────────────────────────

class TestParseHex:
    def test_six_digit(self):
        assert fv.parse_hex("#FF8000") == (255, 128, 0)

    def test_three_digit_expanded(self):
        # ``#f00`` is shorthand for ``#ff0000``.
        assert fv.parse_hex("#f00") == (255, 0, 0)

    def test_without_leading_hash(self):
        assert fv.parse_hex("00ff00") == (0, 255, 0)

    def test_bad_length_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            fv.parse_hex("#1234")

    def test_non_hex_raises(self):
        with pytest.raises(ValueError):
            # Underlying ``int(..., 16)`` raises ValueError, which is a
            # superclass of ArgumentTypeError's parent — either way it
            # must not silently return a wrong colour.
            fv.parse_hex("#zzzzzz")


# ── resize_square ───────────────────────────────────────────────────────────

class TestResizeSquare:
    def test_output_size_matches(self):
        src = Image.new("RGBA", (100, 50), (0, 0, 255, 255))
        out = fv.resize_square(src, 64)
        assert out.size == (64, 64)

    def test_aspect_preserved_with_centering(self):
        # Non-square source: the long edge is scaled to ``size`` and the
        # short edge fits within. The padded corners stay transparent.
        src = Image.new("RGBA", (100, 50), (0, 0, 0, 255))
        out = fv.resize_square(src, 64)
        # Top-left corner is outside the scaled artwork → fully transparent.
        assert out.getpixel((0, 0))[3] == 0
        # Centre is inside the artwork → opaque.
        assert out.getpixel((32, 32))[3] == 255


# ── flatten_on ──────────────────────────────────────────────────────────────

class TestFlattenOn:
    def test_returns_rgb(self):
        src = Image.new("RGBA", (8, 8), (255, 0, 0, 128))
        flat = fv.flatten_on((0, 255, 0), src)
        assert flat.mode == "RGB"

    def test_transparent_pixels_get_background(self):
        src = Image.new("RGBA", (4, 4), (0, 0, 0, 0))  # fully transparent
        flat = fv.flatten_on((10, 20, 30), src)
        # Background colour shows through everywhere.
        assert flat.getpixel((1, 1)) == (10, 20, 30)


# ── make_maskable ───────────────────────────────────────────────────────────

class TestMakeMaskable:
    def test_canvas_is_maskable_size(self):
        src = Image.new("RGBA", (256, 256), (0, 100, 200, 255))
        out = fv.make_maskable(src, (0, 0, 0))
        assert out.size == (fv.MASKABLE_SIZE, fv.MASKABLE_SIZE)
        assert out.mode == "RGB"

    def test_outer_ring_is_background(self):
        # The artwork lives in the central 80% of the canvas. A pixel
        # well inside the outer 10% bleed must show the background.
        src = Image.new("RGBA", (256, 256), (0, 100, 200, 255))
        out = fv.make_maskable(src, (200, 200, 200))
        # 1% in from the edge — definitely inside the bleed.
        assert out.getpixel((4, 4)) == (200, 200, 200)


# ── End-to-end main() ───────────────────────────────────────────────────────

class TestMain:
    def test_emits_full_set(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        source = _make_source(tmp_path / "logo.png", size=256, color=(0, 122, 255, 255))
        out_dir = tmp_path / "public"

        # Drive argparse via sys.argv.
        argv = [
            "favicons",
            str(source),
            "--out", str(out_dir),
            "--name", "Test App",
            "--bg", "#FFFFFF",
            "--theme-dark", "#000000",
        ]
        monkeypatch.setattr(sys, "argv", argv)
        rc = fv.main()
        assert rc == 0

        # Every advertised artefact lands on disk.
        expected = [
            "favicon-16.png", "favicon-32.png", "favicon-48.png",
            "icon-192.png", "icon-512.png",
            "apple-touch-icon.png",
            "icon-maskable-512.png",
            "favicon.ico",
            "site.webmanifest",
            "head.html",
        ]
        for name in expected:
            assert (out_dir / name).is_file(), f"missing {name}"

        # PNG sizes are correct.
        for size, name in [(16, "favicon-16.png"), (32, "favicon-32.png"),
                           (192, "icon-192.png"), (512, "icon-512.png")]:
            assert Image.open(out_dir / name).size == (size, size)

        # apple-touch-icon is 180×180 and opaque.
        touch = Image.open(out_dir / "apple-touch-icon.png")
        assert touch.size == (fv.APPLE_TOUCH_SIZE, fv.APPLE_TOUCH_SIZE)
        assert touch.mode == "RGB"

        # Manifest parses and contains the maskable variant.
        manifest = json.loads((out_dir / "site.webmanifest").read_text(encoding="utf-8"))
        assert manifest["name"] == "Test App"
        assert any(icon.get("purpose") == "maskable" for icon in manifest["icons"])
        # The two theme-color meta tags appear in the head snippet.
        head = (out_dir / "head.html").read_text(encoding="utf-8")
        assert 'prefers-color-scheme: light' in head
        assert 'prefers-color-scheme: dark' in head
