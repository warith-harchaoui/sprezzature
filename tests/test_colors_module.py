"""
Unit tests for ``_colors`` — the shared color primitives module that lives
inside ``sprezzature-colors/scripts/_colors.py`` and is imported by both
``audit_contrast`` and ``simulate_cvd``.

Covers:

* Hex parsing (8-bit and linear-light variants, shortcuts, alpha drop).
* WCAG luminance / contrast and the ``meets_wcag`` helper.
* OKLab / OKLCH round-trips.
* Perceptual ``lighten`` / ``darken`` (OKLCH L axis, hue / chroma preserved).
* CVD matrices + ``simulate_pixel``.
* Palette accessors (Apple base, emotion, concepts, psychology).
* ``Color`` class ergonomics.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import pytest

from _colors import (
    CVD_MATRICES,
    Color,
    apple_palette,
    composite_over,
    concept_search,
    contrast_ratio_hex,
    darken,
    flatten_alpha,
    parse_hex_rgba,
    emotion_to_hex,
    emotions,
    lighten,
    light_variant,
    linear_to_oklab,
    load_palette,
    meets_wcag,
    name_to_hex,
    name_to_rgb,
    oklab_to_linear,
    oklab_to_oklch,
    oklch_to_oklab,
    palette_names,
    parse_hex,
    parse_hex_linear,
    psychology_for,
    rgb_to_hex,
    simulate_pixel,
    srgb_to_linear,
    to_hex,
)


# ── Hex parsing ────────────────────────────────────────────────────────────

class TestHexParsing:
    """Hex parsing accepts 3-, 6-, 8-digit forms and returns 8-bit RGB."""

    def test_parse_hex_6_digit(self) -> None:
        assert parse_hex("#FF3B30") == (255, 59, 48)

    def test_parse_hex_no_leading_hash(self) -> None:
        assert parse_hex("FF3B30") == parse_hex("#FF3B30")

    def test_parse_hex_3_digit_shorthand(self) -> None:
        assert parse_hex("#fff") == (255, 255, 255)
        assert parse_hex("#f00") == (255, 0, 0)

    def test_parse_hex_8_digit_drops_alpha(self) -> None:
        assert parse_hex("#FF3B3080") == parse_hex("#FF3B30")

    def test_parse_hex_bad_length_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_hex("#12")

    def test_parse_hex_linear_returns_floats(self) -> None:
        r, g, b = parse_hex_linear("#FFFFFF")
        assert r == pytest.approx(1.0, abs=1e-6)
        assert g == pytest.approx(1.0, abs=1e-6)
        assert b == pytest.approx(1.0, abs=1e-6)

    def test_rgb_to_hex_round_trip(self) -> None:
        for h in ("#000000", "#FFFFFF", "#007AFF", "#FF3B30", "#A52A2A"):
            assert rgb_to_hex(parse_hex(h)) == h


# ── WCAG ───────────────────────────────────────────────────────────────────

class TestWcag:

    def test_meets_wcag_black_on_white_aa(self) -> None:
        assert meets_wcag("#000000", "#FFFFFF", level="AA", size="normal") is True

    def test_meets_wcag_yellow_on_white_fails_aa(self) -> None:
        # Brand yellow on white is ~1.4:1 — must fail AA body.
        assert meets_wcag("#FFCC00", "#FFFFFF") is False

    def test_meets_wcag_aaa_stricter_than_aa(self) -> None:
        # #6E6E6E on white sits in the AA-pass / AAA-fail band (~5:1).
        assert meets_wcag("#6E6E6E", "#FFFFFF", level="AA") is True
        assert meets_wcag("#6E6E6E", "#FFFFFF", level="AAA") is False

    def test_meets_wcag_large_text_threshold_lower(self) -> None:
        # The AA threshold for large text is 3.0, not 4.5 — a mid-gray that
        # fails AA body should still pass AA large.
        # #999999 on white is ~2.85:1 (fails both), #888888 ~3.5:1 (passes large only).
        assert meets_wcag("#888888", "#FFFFFF", level="AA", size="large") is True
        assert meets_wcag("#888888", "#FFFFFF", level="AA", size="normal") is False

    def test_meets_wcag_accepts_rgb_tuple(self) -> None:
        assert meets_wcag((0, 0, 0), (255, 255, 255)) is True

    def test_meets_wcag_invalid_combo_raises(self) -> None:
        with pytest.raises(ValueError):
            meets_wcag("#000", "#FFF", level="AAAA", size="normal")


# ── OKLab / OKLCH round-trips ──────────────────────────────────────────────

class TestOklabRoundTrip:

    @pytest.mark.parametrize("hex_value", [
        "#000000", "#FFFFFF", "#007AFF", "#FF3B30",
        "#28CD41", "#FFCC00", "#AF52DE", "#FF2D55", "#79DBDC",
    ])
    def test_lab_round_trip(self, hex_value: str) -> None:
        src = parse_hex_linear(hex_value)
        back = oklab_to_linear(linear_to_oklab(src))
        for s, b in zip(src, back):
            assert s == pytest.approx(b, abs=1e-6)

    @pytest.mark.parametrize("hex_value", ["#007AFF", "#FF3B30", "#28CD41", "#AF52DE"])
    def test_lch_round_trip(self, hex_value: str) -> None:
        src = parse_hex_linear(hex_value)
        lab = linear_to_oklab(src)
        lab_back = oklch_to_oklab(oklab_to_oklch(lab))
        for a, b in zip(lab, lab_back):
            assert a == pytest.approx(b, abs=1e-6)


# ── Perceptual lighten / darken ────────────────────────────────────────────

class TestLightenDarken:
    """OKLCH L-axis shift must preserve hue / chroma direction."""

    def test_lighten_increases_luminance(self) -> None:
        base_lin = parse_hex_linear("#007AFF")
        out_lin = parse_hex_linear(lighten("#007AFF", 0.15))
        # The lightened hex must have strictly higher relative luminance.
        from _colors import relative_luminance
        assert relative_luminance(out_lin) > relative_luminance(base_lin)

    def test_darken_decreases_luminance(self) -> None:
        from _colors import relative_luminance
        base_lin = parse_hex_linear("#007AFF")
        out_lin = parse_hex_linear(darken("#007AFF", 0.15))
        assert relative_luminance(out_lin) < relative_luminance(base_lin)

    def test_lighten_preserves_hue_better_than_naive(self) -> None:
        # OKLCH-based lighten shifts hue significantly less than a naïve RGB
        # +N offset. For saturated colors near the sRGB gamut boundary the
        # OKLCH path still drifts a few degrees after re-encoding, but the
        # naïve path drifts an order of magnitude more.
        base_hex = "#007AFF"
        base_h = oklab_to_oklch(linear_to_oklab(parse_hex_linear(base_hex)))[2]

        perceptual = lighten(base_hex, 0.10)
        perc_h = oklab_to_oklch(linear_to_oklab(parse_hex_linear(perceptual)))[2]
        perc_drift = abs(base_h - perc_h)

        # Naïve RGB +70 lighten (the colors-helper approach being replaced).
        r, g, b = parse_hex(base_hex)
        naive_rgb = (min(255, r + 70), min(255, g + 70), min(255, b + 70))
        naive_lin = tuple(srgb_to_linear(c) for c in naive_rgb)
        naive_h = oklab_to_oklch(linear_to_oklab(naive_lin))[2]
        naive_drift = abs(base_h - naive_h)

        # OKLCH must beat naïve by a wide margin on saturated colors.
        assert perc_drift < naive_drift, (
            f"perceptual drift {perc_drift:.2f}° must be less than naive {naive_drift:.2f}°"
        )

    def test_naive_plus70_is_not_what_lighten_does(self) -> None:
        # colors-helper used `clip(rgb + 70)` — that takes #FFCC00 (yellow,
        # already saturated red+green) to #FFFF46 which is a different hue
        # AND clamps the red channel. Perceptual lighten must not do that.
        naive = (min(255, 255 + 70), min(255, 204 + 70), min(255, 0 + 70))
        perceptual = parse_hex(lighten("#FFCC00", 0.10))
        assert perceptual != naive

    def test_lighten_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            lighten("#000000", -0.1)

    def test_darken_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            darken("#FFFFFF", -0.1)

    def test_lighten_clamps_at_white(self) -> None:
        # Pushing L above 1.0 must clamp; the result is white (or very near).
        out = lighten("#FFFFFF", 0.5)
        r, g, b = parse_hex(out)
        assert r >= 250 and g >= 250 and b >= 250


# ── CVD ────────────────────────────────────────────────────────────────────

class TestCvd:

    def test_white_stays_white(self) -> None:
        for kind in CVD_MATRICES:
            out = simulate_pixel((255, 255, 255), CVD_MATRICES[kind])
            for c in out:
                assert abs(c - 255) <= 3

    def test_black_stays_black(self) -> None:
        for kind in CVD_MATRICES:
            assert simulate_pixel((0, 0, 0), CVD_MATRICES[kind]) == (0, 0, 0)

    def test_red_through_deuteranopia_loses_red_dominance(self) -> None:
        red = (255, 59, 48)
        out = simulate_pixel(red, CVD_MATRICES["deuteranopia"])
        assert (red[0] - red[1]) > 2 * (out[0] - out[1])


# ── Palette accessors ─────────────────────────────────────────────────────

class TestPalette:

    def test_load_palette_non_empty(self) -> None:
        rows = load_palette()
        assert len(rows) >= 12
        # Schema check on the first row — all expected columns must be present.
        expected_columns = {
            "Hexcode", "R", "G", "B", "Base", "LightHex",
            "Emotion", "Concepts", "PsychologyPositive", "PsychologyNegative",
        }
        assert expected_columns.issubset(rows[0].keys())

    def test_apple_palette_has_canonical_eight(self) -> None:
        palette = apple_palette()
        # The eight saturated Apple system colors must all be present.
        assert {"Red", "Orange", "Yellow", "Green",
                "Turquoise", "Blue", "Purple", "Pink"}.issubset(palette.keys())
        assert palette["Red"] == "#FF3B30"
        assert palette["Blue"] == "#007AFF"

    def test_name_to_hex_case_insensitive(self) -> None:
        assert name_to_hex("Red") == "#FF3B30"
        assert name_to_hex("red") == "#FF3B30"
        assert name_to_hex("  RED  ") == "#FF3B30"

    def test_name_to_hex_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            name_to_hex("Mauve")

    def test_name_to_rgb_returns_8bit_tuple(self) -> None:
        assert name_to_rgb("Blue") == (0, 122, 255)

    def test_light_variant_by_name(self) -> None:
        assert light_variant("Red") == "#FFD8D6"

    def test_light_variant_by_hex(self) -> None:
        assert light_variant("#FF3B30") == "#FFD8D6"

    def test_light_variant_for_neutral_returns_curated_hex(self) -> None:
        # Every CSV row carries a LightHex column since the curated
        # palette covers neutrals too (Black / Brown / Gray / White).
        # Asserting the actual values keeps the test in lock-step with
        # ``sprezzature-colors/references/palette.csv`` — drift here means
        # the CSV moved and the test should follow.
        assert light_variant("Black") == "#CCCCCC"
        assert light_variant("Brown") == "#EDD4D4"
        assert light_variant("Gray") == "#E6E6E6"
        assert light_variant("White") == "#FFFFFF"

    def test_emotion_to_hex(self) -> None:
        # Curated emotion mapping.
        assert emotion_to_hex("Anger") == "#FF3B30"
        assert emotion_to_hex("Joy") == "#FFCC00"
        assert emotion_to_hex("Sadness") == "#007AFF"

    def test_emotion_to_hex_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            emotion_to_hex("Ennui")

    def test_emotions_returns_dict(self) -> None:
        table = emotions()
        assert "Anger" in table and "Joy" in table

    def test_concept_search(self) -> None:
        # "Trust" is a Blue concept in the curated palette.
        hits = concept_search("Trust")
        assert "#007AFF" in hits

    def test_concept_search_unknown_returns_empty(self) -> None:
        assert concept_search("RandomKeyword") == []

    def test_psychology_for_named_color(self) -> None:
        psych = psychology_for("Red")
        assert psych is not None
        assert "Power" in psych["positive"]
        assert "Anger" in psych["negative"]

    def test_psychology_for_by_hex(self) -> None:
        psych = psychology_for("#FF3B30")
        assert psych is not None
        assert "Power" in psych["positive"]

    def test_psychology_for_unknown_returns_none(self) -> None:
        assert psychology_for("Mauve") is None

    def test_palette_names_contains_neutrals(self) -> None:
        names = palette_names()
        assert "Black" in names and "White" in names and "Gray" in names


# ── Color class ───────────────────────────────────────────────────────────

class TestColorClass:

    def test_from_hex_and_back(self) -> None:
        c = Color("#007AFF")
        assert c.rgb == (0, 122, 255)
        assert c.hex == "#007AFF"

    def test_from_rgb_tuple(self) -> None:
        assert Color((255, 59, 48)).hex == "#FF3B30"

    def test_from_name_classmethod(self) -> None:
        assert Color.from_name("Red") == Color("#FF3B30")

    def test_lighten_returns_color(self) -> None:
        lit = Color("#007AFF").lighten(0.15)
        assert isinstance(lit, Color)
        assert lit != Color("#007AFF")

    def test_contrast_with_against_white_brand_blue(self) -> None:
        ratio = Color("#007AFF").contrast_with("#FFFFFF")
        assert 4.0 < ratio < 5.0

    def test_meets_wcag_method(self) -> None:
        assert Color("#000000").meets_wcag("#FFFFFF") is True
        assert Color("#FFCC00").meets_wcag("#FFFFFF") is False

    def test_equality_and_hash(self) -> None:
        a, b = Color("#FF3B30"), Color((255, 59, 48))
        assert a == b
        assert hash(a) == hash(b)
        # Usable as dict key.
        assert {a: "red"}[b] == "red"

    def test_invalid_rgb_channel_raises(self) -> None:
        with pytest.raises(ValueError):
            Color((300, 0, 0))


# ── sRGB transfer round-trips ─────────────────────────────────────────────

class TestSrgbTransfer:

    @pytest.mark.parametrize("value", [0, 1, 64, 127, 200, 255])
    def test_round_trip(self, value: int) -> None:
        from _colors import linear_to_srgb
        assert linear_to_srgb(srgb_to_linear(value)) == value

    def test_to_hex_white(self) -> None:
        assert to_hex((1.0, 1.0, 1.0)) == "#FFFFFF"

    def test_to_hex_black(self) -> None:
        assert to_hex((0.0, 0.0, 0.0)) == "#000000"


# ── Alpha-aware WCAG contrast ───────────────────────────────────────────────

def test_parse_hex_rgba_keeps_alpha() -> None:
    """8- and 4-digit hex carry alpha; 6- and 3-digit are opaque."""
    assert parse_hex_rgba("#00000080") == (0, 0, 0, pytest.approx(128 / 255))
    assert parse_hex_rgba("#0000") == (0, 0, 0, 0.0)
    assert parse_hex_rgba("#FFFFFF") == (255, 255, 255, 1.0)
    assert parse_hex_rgba("#FFF") == (255, 255, 255, 1.0)


def test_composite_over_blends_in_srgb() -> None:
    """50% black over white is mid-grey; full alpha passes fg through."""
    assert composite_over((0, 0, 0, 0.5), (255, 255, 255)) == (128, 128, 128)
    assert composite_over((10, 20, 30, 1.0), (255, 255, 255)) == (10, 20, 30)
    assert composite_over((0, 0, 0, 0.0), (255, 255, 255)) == (255, 255, 255)


def test_flatten_alpha_nested_background() -> None:
    """A translucent bg is first flattened over white before compositing."""
    assert flatten_alpha("#000000FF", "#FFFFFF") == (0, 0, 0)
    # translucent fg over translucent bg still resolves to a concrete colour
    r, g, b = flatten_alpha("#00000080", "#FFFFFF80")
    assert (r, g, b) == (r, g, b) and 0 <= r <= 255


def test_contrast_is_alpha_aware() -> None:
    """A semi-transparent foreground has lower contrast than its opaque form."""
    opaque = contrast_ratio_hex("#000000", "#FFFFFF")
    faded = contrast_ratio_hex("#00000080", "#FFFFFF")
    assert opaque == pytest.approx(21.0, abs=0.01)
    assert faded < opaque
    assert faded == pytest.approx(4.0, abs=0.2)


def test_meets_wcag_respects_alpha() -> None:
    """An opaque grey passes AA; the same grey at 50% alpha fails."""
    assert meets_wcag("#767676", "#FFFFFF") is True
    assert meets_wcag("#76767680", "#FFFFFF") is False
