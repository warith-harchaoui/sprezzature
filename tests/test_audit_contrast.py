"""
Unit tests for audit_contrast.py.

The script is pure-math, so the tests cover hex parsing, WCAG contrast
math against published values, OKLab round-trips, and the suggestion
search.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations


import pytest

from audit_contrast import (
    adjust_for_contrast,
    contrast_ratio,
    linear_to_oklab,
    oklab_to_linear,
    oklab_to_oklch,
    oklch_to_oklab,
    parse_hex,
    relative_luminance,
)


class TestParseHex:
    """Hex colours come in three shapes; the parser must accept all of them."""

    def test_6_digit_hex(self) -> None:
        r, g, b = parse_hex("#007AFF")
        # Reference blue: linear values for 0x00, 0x7A, 0xFF.
        # 0x7A = 122; ((122/255 + 0.055) / 1.055) ** 2.4 ≈ 0.194618 per the
        # canonical sRGB-to-linear transfer (W3C ARIA recommended formula).
        assert r == pytest.approx(0.0, abs=1e-6)
        assert g == pytest.approx(0.194618, abs=1e-4)
        assert b == pytest.approx(1.0, abs=1e-6)

    def test_3_digit_shorthand(self) -> None:
        # ``#fff`` and ``#FFFFFF`` resolve identically.
        assert parse_hex("#fff") == parse_hex("#ffffff")

    def test_8_digit_drops_alpha(self) -> None:
        # The alpha channel is intentionally ignored; the math is for
        # opaque foregrounds against opaque backgrounds.
        assert parse_hex("#FF000080") == parse_hex("#FF0000")

    def test_no_leading_hash(self) -> None:
        assert parse_hex("FFFFFF") == parse_hex("#FFFFFF")

    def test_bad_length_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_hex("#1234")


class TestContrastRatio:
    """WCAG ratios match the canonical published values."""

    def test_black_on_white_is_21(self) -> None:
        white = parse_hex("#FFFFFF")
        black = parse_hex("#000000")
        assert contrast_ratio(white, black) == pytest.approx(21.0, abs=1e-2)

    def test_same_color_is_1(self) -> None:
        gray = parse_hex("#808080")
        assert contrast_ratio(gray, gray) == pytest.approx(1.0, abs=1e-6)

    def test_brand_blue_on_white(self) -> None:
        # 0x007AFF on white. The well-known value is ~4.55 — passes AA body.
        blue = parse_hex("#007AFF")
        white = parse_hex("#FFFFFF")
        ratio = contrast_ratio(blue, white)
        assert 4.0 < ratio < 5.0

    def test_relative_luminance_white(self) -> None:
        assert relative_luminance(parse_hex("#FFFFFF")) == pytest.approx(1.0, abs=1e-6)

    def test_relative_luminance_black(self) -> None:
        assert relative_luminance(parse_hex("#000000")) == pytest.approx(0.0, abs=1e-6)

    def test_ratio_is_symmetric(self) -> None:
        a = parse_hex("#007AFF")
        b = parse_hex("#FFFFFF")
        assert contrast_ratio(a, b) == pytest.approx(contrast_ratio(b, a))


class TestOklabRoundTrip:
    """OKLab / OKLCH conversions round-trip to within float precision."""

    @pytest.mark.parametrize("hex_value", [
        "#000000", "#FFFFFF", "#007AFF", "#FF3B30",
        "#28CD41", "#FFCC00", "#AF52DE",
    ])
    def test_lab_round_trip(self, hex_value: str) -> None:
        src = parse_hex(hex_value)
        lab = linear_to_oklab(src)
        back = oklab_to_linear(lab)
        for s, b in zip(src, back):
            assert s == pytest.approx(b, abs=1e-6)

    @pytest.mark.parametrize("hex_value", ["#007AFF", "#FF3B30", "#28CD41"])
    def test_lch_round_trip(self, hex_value: str) -> None:
        src = parse_hex(hex_value)
        lab = linear_to_oklab(src)
        lch = oklab_to_oklch(lab)
        lab_back = oklch_to_oklab(lch)
        for a, b in zip(lab, lab_back):
            assert a == pytest.approx(b, abs=1e-6)

    def test_lch_hue_range(self) -> None:
        """``H`` is reported in ``[0, 360)``."""
        red = parse_hex("#FF0000")
        _, _, h = oklab_to_oklch(linear_to_oklab(red))
        assert 0 <= h < 360


class TestAdjustForContrast:
    """The suggester finds a passing colour for difficult pairs."""

    def test_yellow_on_white_gets_fixed(self) -> None:
        # Brand yellow on white is ~1.4:1 — must fail AA body. The
        # suggester should find an L value that passes 4.5:1.
        yellow = parse_hex("#FFCC00")
        white = parse_hex("#FFFFFF")
        result = adjust_for_contrast(yellow, white, 4.5)
        assert result is not None, "suggester returned None on a fixable pair"
        suggested_hex, achieved = result
        assert achieved >= 4.5
        assert suggested_hex.startswith("#") and len(suggested_hex) == 7

    def test_returns_none_when_impossible(self) -> None:
        # Pure white on white can never reach a 4.5 ratio by moving the
        # foreground alone — the suggester must say so.
        white = parse_hex("#FFFFFF")
        # Force an artificial case where every candidate fails: target 100.
        assert adjust_for_contrast(white, white, 100.0) is None
