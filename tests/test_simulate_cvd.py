"""
Unit tests for simulate_cvd.py.

The script is pure-math (no model), so we test the sRGB transfer
functions, the per-pixel transform, and a smoke check that the matrix
output for a known red-on-white pair collapses correctly under
deuteranopia.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import pytest

from simulate_cvd import (
    CVD_MATRICES,
    linear_to_srgb,
    parse_types,
    simulate_pixel,
    srgb_to_linear,
)


class TestSrgbTransfer:
    """The sRGB transfer function and its inverse must round-trip."""

    @pytest.mark.parametrize("value", [0, 1, 64, 127, 200, 255])
    def test_round_trip(self, value: int) -> None:
        assert linear_to_srgb(srgb_to_linear(value)) == value

    def test_clamp_low(self) -> None:
        assert linear_to_srgb(-0.5) == 0

    def test_clamp_high(self) -> None:
        assert linear_to_srgb(1.5) == 255

    def test_zero_maps_to_zero(self) -> None:
        assert srgb_to_linear(0) == 0.0
        assert linear_to_srgb(0.0) == 0


class TestSimulatePixel:
    """The matrices must transform pixels in expected directions."""

    def test_red_through_deuteranopia_loses_red_dominance(self) -> None:
        """
        Bright pure red, viewed through deuteranopia, must lose its
        red dominance (the M cone is missing, but the perceptual
        result is a desaturated yellow/brown — not still bright red).
        """
        red = (255, 59, 48)  # brand red
        out = simulate_pixel(red, CVD_MATRICES["deuteranopia"])
        # The simulated red channel must drop significantly OR the green
        # channel must rise sharply so the pair is no longer "saturated red".
        # Either way, R - G must shrink by half.
        assert (red[0] - red[1]) > 2 * (out[0] - out[1])

    def test_white_stays_white_within_tolerance(self) -> None:
        for kind in CVD_MATRICES:
            out = simulate_pixel((255, 255, 255), CVD_MATRICES[kind])
            for c in out:
                # All matrices in the Machado et al. set preserve neutrals
                # to within rounding precision.
                assert abs(c - 255) <= 3

    def test_black_stays_black(self) -> None:
        for kind in CVD_MATRICES:
            out = simulate_pixel((0, 0, 0), CVD_MATRICES[kind])
            assert out == (0, 0, 0)


class TestParseTypes:
    """CLI alias parsing accepts shorthands and full names."""

    def test_shorthand(self) -> None:
        assert parse_types("prot,deut") == ["protanopia", "deuteranopia"]

    def test_full_names(self) -> None:
        assert parse_types("protanopia,tritanopia") == ["protanopia", "tritanopia"]

    def test_empty_returns_all(self) -> None:
        # An empty argument falls back to "all three".
        assert parse_types("") == ["protanopia", "deuteranopia", "tritanopia"]

    def test_unknown_raises(self) -> None:
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            parse_types("blueblindness")
