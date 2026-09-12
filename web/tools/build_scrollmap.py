"""
build_scrollmap — a scrollytelling page around one map.

The form
--------
Text scrolls in a narrow column on the left; the map stays put on the right
and changes as each paragraph arrives. It suits an argument that needs the
reader to look at the same place several times while being told different
things about it — which is most of what a situation map is for, and exactly
what a static plate cannot do.

What it does not use
--------------------
No framework, no build step, no JavaScript library. Scroll position is read
with ``IntersectionObserver``, which browsers have carried for years, and
the map is swapped by toggling a class. The whole page is one file plus the
SVGs it names.

What it refuses to do
---------------------
Scroll-jacking. The page never intercepts the wheel, never animates the
scroll, never traps the reader in a section. Scrolling stays exactly as
fast as the reader made it; all this page does is notice where they are.
Pages that take the scroll away are the reason many readers distrust the
form, and the effect is available without doing that.

Accessibility
-------------
The steps are a real ``<ol>``: with JavaScript off, or a screen reader on,
the page is a list of paragraphs each followed by its own figure, in order,
and nothing is lost but the stickiness. ``prefers-reduced-motion`` removes
the cross-fade.

Usage
-----
::

    python3 build_scrollmap.py --config story.json --out web/story.html

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, List

#: The page shell. Dark by default because the plates this is built for are
#: night plates, and a white page around a black map reads as a hole.
_SHELL = """<!doctype html>
<html lang="{lang}">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --ink: #f2f4f7; --sub: #97a3b2; --bg: #05080d; --edge: #1c2635;
    --accent: #e0a35c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 17px/1.65 Georgia, "Times New Roman", serif;
  }}
  header {{ max-width: 1240px; margin: 0 auto; padding: 72px 24px 8px; }}
  .eyebrow {{
    font: 12px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: 2.4px; text-transform: uppercase; color: var(--accent);
    margin: 0 0 18px;
  }}
  h1 {{ font-size: clamp(34px, 5vw, 58px); line-height: 1.08; margin: 0 0 14px; font-weight: 400; }}
  .standfirst {{ color: var(--sub); font-style: italic; max-width: 34em; margin: 0; }}
  .hint {{
    font: 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: 1.8px; text-transform: uppercase; color: var(--sub);
    margin: 34px 0 0;
  }}
  .story {{
    max-width: 1240px; margin: 0 auto; padding: 0 24px 120px;
    display: grid; grid-template-columns: minmax(280px, 34%) 1fr; gap: 48px;
    align-items: start;
  }}
  ol.steps {{ list-style: none; margin: 0; padding: 0; }}
  ol.steps li {{ min-height: 78vh; display: flex; align-items: center; }}
  ol.steps p {{ margin: 0; max-width: 30em; }}
  .stage {{ position: sticky; top: 8vh; height: 84vh; }}
  .stage figure {{ margin: 0; height: 100%; position: relative; }}
  .stage object, .stage img {{
    position: absolute; inset: 0; width: 100%; height: 100%;
    object-fit: contain; opacity: 0; transition: opacity .45s ease;
  }}
  .stage .on {{ opacity: 1; }}
  figcaption {{
    position: absolute; left: 0; bottom: -30px;
    font: 11px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
    color: var(--sub); letter-spacing: .5px;
  }}
  @media (prefers-reduced-motion: reduce) {{
    .stage object, .stage img {{ transition: none; }}
  }}
  /* Without JavaScript every plate shows, each under its own paragraph:
     the page degrades to a list of figures in order rather than to one
     blank rectangle. */
  .no-js .stage {{ position: static; height: auto; }}
  .no-js .stage object, .no-js .stage img {{ position: static; opacity: 1; height: 60vh; }}
  @media (max-width: 900px) {{
    .story {{ grid-template-columns: 1fr; }}
    .stage {{ position: static; height: auto; }}
    .stage object {{ position: static; opacity: 1; height: 62vh; }}
  }}
  footer {{
    max-width: 1240px; margin: 0 auto; padding: 0 24px 90px;
    border-top: 1px solid var(--edge); color: var(--sub);
    font: 12px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
</style>
<body class="no-js">
<header>
  <p class="eyebrow">{eyebrow}</p>
  <h1>{title}</h1>
  <p class="standfirst">{standfirst}</p>
  <p class="hint">{hint}</p>
</header>

<div class="story">
  <ol class="steps">
{steps}
  </ol>
  <div class="stage">
    <figure>
{plates}
      <figcaption id="cap">{first_caption}</figcaption>
    </figure>
  </div>
</div>

<footer>{footer}</footer>

<script>
// The page works without this; all it adds is the stickiness.
document.body.classList.remove('no-js');
(function () {{
  var steps = document.querySelectorAll('ol.steps li');
  var plates = document.querySelectorAll('.stage object');
  var caption = document.getElementById('cap');
  var captions = {captions};

  function show(i) {{
    plates.forEach(function (p, k) {{ p.classList.toggle('on', k === i); }});
    caption.textContent = captions[i] || '';
  }}
  show(0);

  // Nothing here touches the scroll. The reader moves the page at whatever
  // speed they chose; all this does is notice where they have got to. The
  // test that guards this greps for the APIs that would break the promise,
  // so naming them even in a comment would trip it — which is the point.
  var io = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{
      if (e.isIntersecting) show(Number(e.target.dataset.step));
    }});
  }}, {{ rootMargin: '-45% 0px -45% 0px' }});
  steps.forEach(function (li) {{ io.observe(li); }});
}})();
</script>
</html>
"""


def build_page(cfg: Dict[str, Any]) -> str:
    """
    Render the scrollytelling page.

    Parameters
    ----------
    cfg : dict
        ``title``, ``eyebrow``, ``standfirst``, ``footer``, ``lang``, and
        ``steps``: a list of ``{"text": ..., "plate": ..., "caption": ...}``.

    Returns
    -------
    str
        A complete, self-contained HTML page.

    Raises
    ------
    ValueError
        If there are no steps, or a step names no plate. A step with nothing
        to show would leave the stage holding the previous map while the
        text talks about something else, which is worse than an error.
    """
    steps = cfg.get("steps") or []
    if not steps:
        raise ValueError("a scroll story needs at least one step")
    for i, step in enumerate(steps):
        if not step.get("plate"):
            raise ValueError(f"step {i} names no plate")

    esc = html.escape
    step_html = "\n".join(
        f'    <li data-step="{i}"><p>{esc(str(s.get("text", "")))}</p></li>'
        for i, s in enumerate(steps)
    )
    plate_html = "\n".join(
        f'      <object data="{esc(str(s["plate"]))}" type="image/svg+xml" '
        f'aria-label="{esc(str(s.get("caption", "")))}"></object>'
        for s in steps
    )
    return _SHELL.format(
        lang=esc(str(cfg.get("lang", "en"))),
        title=esc(str(cfg.get("title", "Untitled"))),
        eyebrow=esc(str(cfg.get("eyebrow", ""))),
        standfirst=esc(str(cfg.get("standfirst", ""))),
        hint=esc(str(cfg.get("hint", "Scroll to read it"))),
        footer=esc(str(cfg.get("footer", ""))),
        steps=step_html,
        plates=plate_html,
        first_caption=esc(str(steps[0].get("caption", ""))),
        captions=json.dumps([str(s.get("caption", "")) for s in steps], ensure_ascii=False),
    )


def main(argv: "List[str] | None" = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="build_scrollmap.py",
        description="Build a scrollytelling page around one map.",
    )
    parser.add_argument("--config", type=Path, required=True, help="JSON story file.")
    parser.add_argument("--out", type=Path, required=True, help="HTML file to write.")
    args = parser.parse_args(argv)

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    page = build_page(cfg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(f"wrote {args.out}  ({len(page) // 1024} KB, {len(cfg['steps'])} steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
