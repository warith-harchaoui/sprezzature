#!/usr/bin/env python3
"""
md_to_html
==========

Single-file Markdown → HTML converter that integrates the sprezzature skill's
output rules: vanilla JS + Tailwind (Play CDN for the prototype path) +
the three-Roboto typography rule (Roboto / Roboto Serif / Roboto Mono)
+ dark-mode peer.

Three behaviours that distinguish this from a plain Markdown → HTML pipe:

1. **Mermaid blocks render to local PNG.** Same backend as
   ``lint_markdown.py`` (pure-Python ``mmdc`` → Node ``mmdc`` fallback).
   The HTML embeds the PNG (``<img>``) so the diagram works with JS
   disabled; the original Mermaid source is kept in a ``<details>`` so
   the page stays maintainable.

2. **LaTeX renders via KaTeX**, loaded from the CDN by default. KaTeX
   handles single-line display math, multi-line ``align`` /
   ``aligned`` / ``gather`` environments, and inline ``$ … $``. For an
   offline build, pass ``--katex-base path/to/local/katex/`` to point
   at a self-hosted bundle.

3. **Front-skill HTML shell.** Sticky header, three-state theme switch
   (Auto / Light / Dark) persisted in ``localStorage``, semantic
   surface tokens, focus rings, ``prefers-reduced-motion`` guards. The
   shell is the same one used by ``4ml-new/public/index.html``.

Usage
-----
::

    python scripts/md_to_html.py README.md --out site/
    python scripts/md_to_html.py docs/ --out site/ --title "Project docs"
    python scripts/md_to_html.py README.md --out site/ --katex-base /static/katex/

Exit code
---------
* 0 — every input file converted successfully.
* 1 — one or more conversions failed.

Notes
-----
* Python 3.10+. Requires the ``markdown`` PyPI package (small, MIT).
* Mermaid rendering needs ``mmdc`` (see ``requirements-lint-md.txt``).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402

# Reuse the Mermaid renderer + fenced-block extractor from the linter so
# both tools agree on what a Mermaid block looks like and how it is
# rendered.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_markdown import FENCE_RE, render_mermaid_block  # noqa: E402
from _lang import detect_text_language  # noqa: E402


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}" data-color-scheme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">

  <!-- PROTOTYPE: Tailwind Play CDN. For production, swap to Tailwind CLI / Vite. -->
  <script src="https://cdn.tailwindcss.com?plugins=typography,forms"></script>
  <script>
    tailwind.config = {{
      darkMode: ['class', '[data-color-scheme="dark"]'],
      theme: {{ extend: {{
        fontFamily: {{
          sans:  ['Roboto', '-apple-system', 'BlinkMacSystemFont',
                  '"Segoe UI"', 'system-ui', 'sans-serif'],
          serif: ['Roboto Serif', 'Georgia', 'Cambria', 'serif'],
          mono:  ['Roboto Mono', 'ui-monospace', 'SFMono-Regular',
                  'Menlo', 'Consolas', 'monospace'],
        }},
        colors: {{
          'brand-blue': '#0A84FF',
        }},
      }} }},
    }};
  </script>

  <!-- KaTeX (LaTeX rendering). Loads from {katex_base}. -->
  <link rel="stylesheet" href="{katex_base}katex.min.css">
  <script defer src="{katex_base}katex.min.js"></script>
  <script defer src="{katex_base}contrib/auto-render.min.js"
          onload="renderMathInElement(document.body, {{
            delimiters: [
              {{left: '$$', right: '$$', display: true}},
              {{left: '$',  right: '$',  display: false}},
              {{left: '\\\\(', right: '\\\\)', display: false}},
              {{left: '\\\\[', right: '\\\\]', display: true}},
            ],
            throwOnError: false,
          }});"></script>

  <style>
    :root {{
      --surface-primary: #ffffff; --surface-secondary: #f5f5f7;
      --label-primary: #1d1d1f; --label-secondary: #515154;
      --separator: #d2d2d7;
    }}
    [data-color-scheme="dark"] {{
      --surface-primary: #1c1c1e; --surface-secondary: #2c2c2e;
      --label-primary: #f5f5f7; --label-secondary: #a1a1a6;
      --separator: #38383a;
    }}
    html, body {{ background: var(--surface-primary); color: var(--label-primary); }}
    .label-2 {{ color: var(--label-secondary); }}
    .border-sep {{ border-color: var(--separator); }}
    .surface-2 {{ background: var(--surface-secondary); }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
      }}
    }}
  </style>
</head>
<body class="font-sans antialiased text-[16px] leading-relaxed">

  <header class="sticky top-0 z-30 border-b border-sep" style="background:var(--surface-primary)">
    <div class="mx-auto flex w-full max-w-3xl items-center gap-3 px-4 py-3">
      <a href="#top" class="font-semibold">{site_name}</a>
      <button id="theme-toggle" type="button"
              class="ml-auto inline-flex h-11 min-w-11 items-center justify-center rounded-full surface-2 px-3 text-[14px] font-medium
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue focus-visible:ring-offset-2"
              aria-label="Toggle color scheme">
        <span id="theme-toggle-label">Auto</span>
      </button>
    </div>
  </header>

  <main id="top" class="mx-auto w-full max-w-3xl px-4 py-10 prose prose-lg dark:prose-invert">
{body}
  </main>

  <script type="module">
    const KEY='front-md-color-scheme', MODES=['auto','light','dark'];
    const root=document.documentElement, btn=document.getElementById('theme-toggle'),
          lbl=document.getElementById('theme-toggle-label');
    const mql=window.matchMedia('(prefers-color-scheme: dark)');
    function apply(m){{
      root.setAttribute('data-color-scheme', m==='auto' ? (mql.matches?'dark':'light') : m);
      lbl.textContent = m[0].toUpperCase()+m.slice(1);
    }}
    function cur(){{ const s=localStorage.getItem(KEY); return MODES.includes(s)?s:'auto'; }}
    apply(cur());
    btn.addEventListener('click', () => {{
      const n = MODES[(MODES.indexOf(cur())+1) % MODES.length];
      localStorage.setItem(KEY, n); apply(n);
    }});
    mql.addEventListener('change', () => {{ if (cur()==='auto') apply('auto'); }});
  </script>

</body>
</html>
"""


@dataclass
class Conversion:
    """Result of converting one Markdown file: source, destination, success flag, message."""
    src: Path
    dst: Path
    ok: bool
    message: str


#: Mermaid diagram kinds → a human noun, so the fallback alt says what the
#: reader is looking at instead of the meaningless "Mermaid diagram".
_MERMAID_KINDS: dict[str, str] = {
    "flowchart": "flowchart", "graph": "flowchart", "sequencediagram": "sequence diagram",
    "classdiagram": "class diagram", "statediagram": "state diagram",
    "erdiagram": "entity-relationship diagram", "gantt": "Gantt chart",
    "pie": "pie chart", "journey": "user-journey map", "gitgraph": "Git graph",
    "mindmap": "mind map", "timeline": "timeline", "quadrantchart": "quadrant chart",
}


def _mermaid_alt(body: str) -> str:
    """
    Derive meaningful alt text for a rendered Mermaid block.

    Prefers the author's own accessibility text — Mermaid's ``accDescr``
    (a full description) then ``accTitle`` (a short label). When neither is
    present, falls back to naming the *kind* of diagram (e.g. "flowchart
    diagram") rather than the meaningless "Mermaid diagram", and notes that the
    source is available below.

    Parameters
    ----------
    body : str
        The raw Mermaid source inside the fenced block.

    Returns
    -------
    str
        Alt text for the ``<img>``.
    """
    # accDescr can be a one-liner (``accDescr: ...``) or a block
    # (``accDescr { ... }``); accept the one-line forms of both directives.
    m = re.search(r"^\s*accDescr\s*:\s*(.+?)\s*$", body, re.MULTILINE)
    if m:
        return m.group(1)
    m = re.search(r"^\s*accDescr\s*\{\s*(.+?)\s*\}", body, re.DOTALL)
    if m:
        return " ".join(m.group(1).split())
    m = re.search(r"^\s*accTitle\s*:\s*(.+?)\s*$", body, re.MULTILINE)
    if m:
        return m.group(1)
    # No author-supplied text: name the diagram kind from its first keyword.
    for line in body.splitlines():
        token = line.strip().split()[0].lower() if line.strip() else ""
        # Strip an ``%%{init}%%`` directive line so the real kind is found.
        if token.startswith("%%"):
            continue
        kind = _MERMAID_KINDS.get(token)
        if kind:
            return f"{kind} (diagram source below)"
        if token:
            break
    return "diagram (source below)"


def _replace_mermaid_blocks(text: str, src_path: Path, out_dir: Path) -> tuple[str, int, int]:
    """
    Replace every ```mermaid block with:
      <figure><img src="…png" alt="Mermaid diagram"><details><summary>Source</summary><pre>…</pre></details></figure>

    Renders each block to a PNG under out_dir/<stem>.mermaid-N.png.
    Returns (new_text, rendered_count, failed_count).
    """
    rendered = failed = 0
    blocks = list(FENCE_RE.finditer(text))
    # Walk in reverse so earlier matches keep their offsets.
    for idx, m in enumerate(reversed(blocks)):
        lang = m.group(2).strip().lower()
        if lang != "mermaid":
            continue
        body = m.group(3)
        n = len(blocks) - idx
        alt = _mermaid_alt(body)
        png = out_dir / f"{src_path.stem}.mermaid-{n}.png"
        ok, msg = render_mermaid_block(body, png)
        if not ok:
            failed += 1
            print(f"md_to_html: mermaid render failed in {src_path.name}: {msg}", file=sys.stderr)
            continue
        rendered += 1
        replacement = (
            f'<figure class="my-6">'
            f'<img src="{png.name}" alt="{html.escape(alt)}" loading="lazy">'
            f'<details class="mt-2 text-sm label-2"><summary>Source</summary>'
            f'<pre><code class="language-mermaid">{html.escape(body)}</code></pre>'
            f'</details></figure>'
        )
        text = text[: m.start()] + replacement + text[m.end():]
    return text, rendered, failed


def convert_one(src: Path, out_dir: Path, *, title: str, site_name: str,
                lang: str, description: str, katex_base: str) -> Conversion:
    """Convert a single Markdown file to a styled standalone HTML page."""
    try:
        import markdown  # type: ignore
    except ImportError:
        return Conversion(
            src, out_dir / f"{src.stem}.html", False,
            "missing dependency: `pip install markdown` (see requirements-md-to-html.txt)",
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = src.read_text(encoding="utf-8")
    # Language: detect from the document rather than assuming English, matching
    # the rest of the project (sprezzature-vision / sprezzature-audio detect, never default
    # silently). ``--lang auto`` (the default) triggers detection per file.
    if lang in ("", "auto"):
        lang = detect_text_language(raw)
    with_mermaid, rendered, failed = _replace_mermaid_blocks(raw, src, out_dir)

    md = markdown.Markdown(
        extensions=["extra", "toc", "tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    body_html = md.convert(with_mermaid)
    # Derive a title from the first H1 if the user didn't pass one.
    if title == "":
        m = re.search(r"^#\s+(.+?)\s*$", raw, re.MULTILINE)
        title = (m.group(1).strip() if m else src.stem)
    if description == "":
        # First non-empty paragraph after the title.
        body_lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.startswith("#")]
        description = (body_lines[0] if body_lines else "")[:160]

    page = PAGE_TEMPLATE.format(
        lang=html.escape(lang),
        title=html.escape(title),
        description=html.escape(description),
        site_name=html.escape(site_name or title),
        katex_base=katex_base,
        body=body_html,
    )
    dst = out_dir / f"{src.stem}.html"
    dst.write_text(page, encoding="utf-8")
    msg = f"ok ({rendered} mermaid rendered, {failed} failed)"
    return Conversion(src, dst, failed == 0, msg)


def gather_inputs(target: Path) -> list[Path]:
    """Return the Markdown files to convert (the file, or all ``*.md`` under a dir)."""
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.md")) + sorted(target.rglob("*.markdown"))


def main() -> int:
    """CLI entry point for the Markdown-to-HTML converter; returns a process exit code."""
    p = make_parser(
        prog="sprezzature-publish-md-to-html",
        description="Markdown → HTML converter integrated with the sprezzature skill — "
                    "local Mermaid PNG rendering, KaTeX for LaTeX, Tailwind shell.",
        epilog="Examples:\n"
               "  sprezzature-publish-md-to-html README.md --out site/\n"
               "  sprezzature-publish-md-to-html docs/ --out site/ --title 'Docs' --lang en\n",
    )
    p.add_argument("target", type=Path, help="Markdown file or directory.")
    p.add_argument("--out", type=Path, required=True, help="Output directory.")
    p.add_argument("--title", default="", help="Page title. Default: first H1 of each source.")
    p.add_argument("--site-name", default="", dest="site_name",
                   help="Sticky-header brand name. Default: page title.")
    p.add_argument("--lang", default="auto",
                   help="HTML lang attribute (BCP-47). Default: auto = detect per file.")
    p.add_argument("--description", default="",
                   help="Meta description. Default: first prose paragraph (truncated).")
    p.add_argument(
        "--katex-base", default="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/",
        dest="katex_base",
        help="Base URL for KaTeX assets. Pass a local path for an offline build. "
             "Default: jsdelivr CDN.",
    )
    args = p.parse_args()

    inputs = gather_inputs(args.target)
    if not inputs:
        print(f"front-md-to-html: no Markdown files under {args.target}", file=sys.stderr)
        return 2

    # Mirror the input tree into the output so two sources with the same
    # basename in different directories do NOT overwrite each other
    # (e.g. api/index.md and guide/index.md → api/index.html, guide/index.html).
    # The root is the directory the user pointed at (or a single file's parent).
    root = args.target if args.target.is_dir() else args.target.parent

    failures = 0
    for src in inputs:
        rel_dir = src.resolve().relative_to(root.resolve()).parent
        out_subdir = args.out / rel_dir
        result = convert_one(
            src, out_subdir,
            title=args.title, site_name=args.site_name,
            lang=args.lang, description=args.description,
            katex_base=args.katex_base.rstrip("/") + "/",
        )
        print(f"{result.src} → {result.dst}: {result.message}")
        if not result.ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
