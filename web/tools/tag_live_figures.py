#!/usr/bin/env python3
"""Mark which gallery figures should render as a live, interactive <object>.

Part of the standard figure-integration process. A gallery card embeds its SVG
with <img>, which is a flat picture — CSS :hover/:focus isolation, native
<title> tooltips and animation never fire. `js/live-figures.js` upgrades a card
to a live <object> when it scrolls into view, but only for cards tagged
`data-live` here; the fullscreen lightbox (`js/lightbox.js`) does the same for
any SVG on demand.

This tool scans every gallery SVG for the markers that mean "there is something
to interact with or animate" and (re)writes the `data-live` attribute on the
matching <img> cards in figures.html and fr/figures.html. Idempotent.

Run it after adding or regenerating figures:  python tools/tag_live_figures.py
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
FIGURES = WEB / "img" / "figures"
PAGES = [WEB / "figures.html", WEB / "fr" / "figures.html"]

# An SVG is worth making live if it carries hover/focus styling, an animation,
# or the in-figure fullscreen control.
INTERACTIVE = re.compile(
    r":hover|:focus|<animate|@keyframes|animation:|marching|fullscreen|"
    r"data-fs|prefers-reduced-motion"
)


def interactive_names() -> set[str]:
    names = set()
    for svg in FIGURES.glob("*.svg"):
        try:
            if INTERACTIVE.search(svg.read_text(encoding="utf-8", errors="ignore")):
                names.add(svg.stem)
        except OSError:
            pass
    return names


def retag(page: Path, names: set[str]) -> int:
    html = page.read_text(encoding="utf-8")
    html = re.sub(r'\s+data-live="[^"]*"', "", html)  # clear old tags

    def tag(m: re.Match) -> str:
        whole, src = m.group(0), m.group(1)
        stem = src.rsplit("/", 1)[-1][:-4]
        return whole[:-1] + f' data-live="{src}">' if stem in names else whole

    html = re.sub(r'<img src="([^"]+\.svg)"[^>]*>', tag, html)
    page.write_text(html, encoding="utf-8")
    return html.count("data-live=")


def main() -> int:
    names = interactive_names()
    for page in PAGES:
        if page.exists():
            print(f"{page.name}: {retag(page, names)} live figures")
    print(f"{len(names)} interactive SVGs detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
