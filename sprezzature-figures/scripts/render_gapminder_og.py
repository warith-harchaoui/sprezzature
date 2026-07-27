#!/usr/bin/env python3
"""
render_gapminder_og — social-preview PNGs for the Hans Rosling tribute pages.

The animated tribute lives in an SVG, which social networks can't use as a link
preview, so we rasterise one spread-out frame (year 2019) of each language's SVG
to a PNG at the chart's own aspect ratio. Run after ``make_gapminder.py``.

Needs a headless Chrome (Playwright, ``channel="chrome"``) because the frame is
chosen by seeking the SMIL animation — something static renderers can't do.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SVG_DIR = HERE.parent / "assets" / "svg-examples"
OUT_DIR = HERE.parent.parent / "web" / "img" / "figures"
FRAME_SECONDS = 69.0   # 1950 + 69 = 2019, a nicely spread-out cloud (dur is 75 s)
JOBS = [("gapminder-animated.svg", "gapminder-animated.png"),
        ("gapminder-animated.fr.svg", "gapminder-animated.fr.png")]


def main() -> None:
    """Rasterise the 2019 frame of each SVG to a preview PNG."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for svg, png in JOBS:
            page = browser.new_page(viewport={"width": 1020, "height": 520}, device_scale_factor=2)
            page.goto((SVG_DIR / svg).as_uri())
            page.wait_for_timeout(300)
            page.evaluate("(t) => { const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime(t); }",
                          FRAME_SECONDS)
            page.wait_for_timeout(150)
            page.screenshot(path=str(OUT_DIR / png))
            print(f"wrote {OUT_DIR / png}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
