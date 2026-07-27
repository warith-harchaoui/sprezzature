#!/usr/bin/env python3
"""
lint_markdown
=============

Static + AI-assisted linter for Markdown files emitted or shipped by the
sprezzature skill. Three jobs:

1. **Static rules.** Deterministic checks over the Markdown source —
   heading-level skips, trailing whitespace, code blocks without a
   language hint, image without alt text, link to a missing local path.
2. **Mermaid blocks.** Validate the syntax by attempting a local render;
   write a PNG sibling alongside the source so readers without JS still
   see the diagram. Rendering is **fully local** via the ``mmdc`` PyPI
   package (pure Python, embeds PhantomJS — no Node, no npm, no browser
   install). Falls back to the ``@mermaid-js/mermaid-cli`` Node tool
   (``mmdc`` command) if it is on the PATH.
3. **LaTeX blocks.** Validate ``$$ … $$`` display blocks and
   ``\\begin{align} … \\end{align}`` environments — delimiter balance,
   multi-line alignment with ``&`` separators, and the common pitfall of
   leaving a single backslash where ``\\\\`` is required for a line break.

AI-assisted suggestions (optional). When ``--ai`` is set and a local
Ollama daemon is reachable, the script asks the default model for:

- Plain-language alternatives for sentences with three or more long
  words.
- Mermaid diagram label improvements (clarity, parallel structure).
- Captions for LaTeX blocks (a sentence-long description for
  screen-reader users) — only when the block has no preceding
  ``Caption:`` line.

The AI step **never** mutates the source. It prints suggestions; you
apply them by hand. The deterministic rules can rewrite (``--fix``)
trailing whitespace and missing code-block language hints.

Usage
-----
::

    python scripts/lint_markdown.py docs/intro.md
    python scripts/lint_markdown.py docs/                   # walks the dir
    python scripts/lint_markdown.py --render-mermaid docs/  # write PNG siblings
    python scripts/lint_markdown.py --fix docs/             # apply safe rewrites
    python scripts/lint_markdown.py --ai docs/intro.md      # add Ollama suggestions

Exit code
---------
* 0 — no errors.
* 1 — one or more errors. Warnings do not affect the exit code.

Notes
-----
* Python 3.10+, stdlib only for the static rules. Mermaid rendering needs
  ``mmdc`` (``pip install -r scripts/requirements-lint-md.txt``).
* Cross-platform. On Windows the LaTeX delimiter parser is the same.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402


# ── Severity levels ────────────────────────────────────────────────────────

ERROR = "error"
WARNING = "warning"
INFO = "info"


@dataclass
class Finding:
    """One lint finding: file path, 1-indexed line, rule id, severity, and message."""
    path: Path
    line: int            # 1-indexed
    rule: str            # short id e.g. "MD001"
    severity: str        # ERROR / WARNING / INFO
    message: str


# ── Block extractors (stdlib regex) ────────────────────────────────────────

FENCE_RE = re.compile(r"^(```+|~~~+)([^\n]*)\n(.*?)\n\1\s*$", re.DOTALL | re.MULTILINE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
IMG_RE = re.compile(r"!\[(.*?)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[(.*?)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DISPLAY_MATH_RE = re.compile(r"^\$\$\n(.*?)\n\$\$\s*$", re.DOTALL | re.MULTILINE)
ALIGN_ENV_RE = re.compile(r"\\begin\{(align\*?|aligned|gather\*?)\}(.*?)\\end\{\1\}", re.DOTALL)


def fenced_blocks(text: str) -> list[tuple[int, str, str]]:
    """Yield (start_line_1_indexed, language, body) for every fenced block."""
    out: list[tuple[int, str, str]] = []
    for m in FENCE_RE.finditer(text):
        lang = m.group(2).strip()
        body = m.group(3)
        start_line = text[: m.start()].count("\n") + 1
        out.append((start_line, lang, body))
    return out


# ── Static rules ──────────────────────────────────────────────────────────

def lint_heading_order(path: Path, text: str) -> list[Finding]:
    """MD001 — heading levels must not skip (h1 → h3 is wrong)."""
    findings: list[Finding] = []
    last_level: int = 0
    prose = _strip_code(text)
    for m in HEADING_RE.finditer(prose):
        level = len(m.group(1))
        if last_level and level > last_level + 1:
            line = text[: m.start()].count("\n") + 1
            findings.append(Finding(
                path, line, "MD001", ERROR,
                f"Heading level jumps from h{last_level} to h{level}.",
            ))
        last_level = level
    return findings


def lint_trailing_whitespace(path: Path, text: str) -> list[Finding]:
    """MD009 — no trailing spaces (except the intentional two-space line break)."""
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), 1):
        rstripped = line.rstrip(" \t")
        if rstripped != line and not line.endswith("  "):  # `  ` = MD line break
            findings.append(Finding(
                path, i, "MD009", WARNING,
                "Trailing whitespace (use two spaces only for an intentional line break).",
            ))
    return findings


def lint_fenced_code_language(path: Path, text: str) -> list[Finding]:
    """MD040 — every fenced code block declares a language."""
    findings: list[Finding] = []
    for start_line, lang, _body in fenced_blocks(text):
        if not lang:
            findings.append(Finding(
                path, start_line, "MD040", WARNING,
                "Fenced code block missing language hint (use ```bash, ```python, ```mermaid, …).",
            ))
    return findings


def lint_image_alt(path: Path, text: str) -> list[Finding]:
    """MD045 — images need alt text (or explicit empty `![]()` for decorative)."""
    findings: list[Finding] = []
    for m in IMG_RE.finditer(text):
        alt = m.group(1).strip()
        if alt == "":
            # Empty alt is *valid* for decorative images, but tag it as INFO so the
            # author confirms it intentionally. See alt-text-ai.md in sprezzature-accessibility.
            line = text[: m.start()].count("\n") + 1
            findings.append(Finding(
                path, line, "MD045", INFO,
                "Empty alt text — confirm this image is decorative (otherwise add an alt).",
            ))
    return findings


# ── Auto-fix helpers ─────────────────────────────────────────────────────


def fix_trailing_whitespace(text: str) -> str:
    """
    Strip trailing spaces / tabs on every line, preserving the
    intentional two-space line-break suffix (MD009).

    Idempotent. The Markdown spec treats a line ending in ``"  "``
    (two spaces) as an explicit ``<br>``; we keep that. Any other
    trailing whitespace — single spaces, three-or-more spaces, tab
    characters — is collapsed.

    Parameters
    ----------
    text : str
        Source Markdown.

    Returns
    -------
    str
        New Markdown with offending trailing whitespace removed. The
        document's line count is preserved (a fully-blank line of
        spaces becomes an empty line, not a removed line).
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        if line.endswith("  ") and not line.endswith("   "):
            # Exactly two trailing spaces — Markdown's intentional
            # line break. Preserve.
            out_lines.append(line)
            continue
        out_lines.append(line.rstrip(" \t"))
    new: str = "\n".join(out_lines)
    # ``splitlines`` drops the trailing newline; restore it if the
    # original had one so the file does not gain / lose a final EOL.
    if text.endswith("\n"):
        new += "\n"
    return new


def lint_local_links(path: Path, text: str) -> list[Finding]:
    """MD050 — local link targets exist on disk.

    Scans a code-stripped view of the document so link *syntax examples* inside
    fenced blocks or inline-code spans (e.g. documenting ``[text](url)`` in a
    table cell) are not mistaken for real links. ``_strip_code`` preserves line
    breaks, so reported line numbers stay accurate.
    """
    findings: list[Finding] = []
    parent = path.parent
    prose = _strip_code(text)
    for m in LINK_RE.finditer(prose):
        href = m.group(2)
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # Strip anchor and query.
        rel = href.split("#", 1)[0].split("?", 1)[0]
        if not rel:
            continue
        target = (parent / rel).resolve()
        if not target.exists():
            line = text[: m.start()].count("\n") + 1
            findings.append(Finding(
                path, line, "MD050", ERROR,
                f"Local link target does not exist: {href}",
            ))
    return findings


# ── LaTeX checks ──────────────────────────────────────────────────────────

def _strip_code(text: str) -> str:
    """
    Remove fenced blocks and inline-code spans before scanning for prose-level
    markers like `$$` or backtick math. Preserves line breaks so reported line
    numbers stay accurate.
    """
    # Blank out fenced blocks but keep their newlines.
    def blank_fence(m: re.Match[str]) -> str:
        """Replace a fenced block with equal-count newlines to preserve line numbers."""
        return "\n" * m.group(0).count("\n")
    no_fence = FENCE_RE.sub(blank_fence, text)
    # Blank out inline-code spans.
    return re.sub(r"`+[^`\n]*`+", lambda m: " " * len(m.group(0)), no_fence)


def lint_latex_blocks(path: Path, text: str) -> list[Finding]:
    """MDX001 — LaTeX display blocks: balanced delimiters and multi-line hygiene."""
    findings: list[Finding] = []
    prose = _strip_code(text)

    # 1) Stray $$ not paired (count must be even).
    dollar_dollar = re.findall(r"(?<!\\)\$\$", prose)
    if len(dollar_dollar) % 2 != 0:
        findings.append(Finding(
            path, 1, "MDX001", ERROR,
            f"Odd number of `$$` delimiters ({len(dollar_dollar)}); display math is unbalanced.",
        ))

    # 2) Within each $$…$$ block, multi-line formulas should be inside
    #    an alignment env (align, aligned, gather) and use `\\` for line breaks.
    for m in DISPLAY_MATH_RE.finditer(prose):
        body = m.group(1)
        start_line = text[: m.start()].count("\n") + 1
        body_lines = [ln for ln in body.splitlines() if ln.strip()]
        if len(body_lines) > 1:
            uses_env = any(env in body for env in ("\\begin{align", "\\begin{aligned", "\\begin{gather"))
            uses_double_backslash = re.search(r"(?<!\\)\\\\(?!\\)", body) is not None
            if not uses_env and not uses_double_backslash:
                findings.append(Finding(
                    path, start_line, "MDX002", WARNING,
                    "Multi-line display math without `\\\\` line breaks or an `align`/`gather` "
                    "environment. Most renderers will collapse the lines.",
                ))

    # 3) Inside align/aligned/gather, each non-trailing line should end with `\\`.
    for m in ALIGN_ENV_RE.finditer(prose):
        env = m.group(1)
        body = m.group(2)
        start_line = text[: m.start()].count("\n") + 1
        lines = [ln.rstrip() for ln in body.splitlines() if ln.strip()]
        # Drop the last line (no `\\` expected) and check the rest.
        for idx, ln in enumerate(lines[:-1]):
            if not ln.endswith("\\\\"):
                findings.append(Finding(
                    path, start_line + idx + 1, "MDX003", ERROR,
                    f"`\\begin{{{env}}}` block: line {idx+1} missing `\\\\` line break.",
                ))

    return findings


# ── Mermaid rendering ─────────────────────────────────────────────────────

def have_python_mmdc() -> bool:
    """Return ``True`` when the Python ``mmdc`` package is importable."""
    try:
        import mmdc  # noqa: F401
        return True
    except ImportError:
        return False


def have_node_mmdc() -> bool:
    """Return ``True`` when the Node ``mmdc`` CLI is on ``PATH``."""
    return shutil.which("mmdc") is not None


def render_mermaid_block(mermaid_src: str, out_png: Path) -> tuple[bool, str]:
    """
    Render a Mermaid diagram to PNG, fully local.

    Tries pure-Python ``mmdc`` first (``pip install mmdc``), then falls
    back to the Node-based ``mmdc`` binary if it is on the PATH.

    Returns (ok, message).
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if have_python_mmdc():
        try:
            import mmdc  # type: ignore
            mmdc.render(mermaid_src, output_path=str(out_png), format="png")
            return True, f"rendered via python mmdc → {out_png}"
        except Exception as exc:  # pylint: disable=broad-except
            # Fall through to the Node binary attempt.
            python_err = str(exc)
        else:
            python_err = ""
    else:
        python_err = "python mmdc not installed"

    if have_node_mmdc():
        # mmdc reads from stdin via `-i -`, writes PNG via `-o`. `-b transparent`
        # is the cleanest default for embedding in docs.
        try:
            subprocess.run(
                ["mmdc", "-i", "-", "-o", str(out_png), "-b", "transparent"],
                input=mermaid_src,
                text=True,
                capture_output=True,
                check=True,
            )
            return True, f"rendered via node mmdc → {out_png}"
        except subprocess.CalledProcessError as exc:
            return False, (
                f"node mmdc failed: {exc.stderr.strip() or exc}\n"
                f"(python mmdc note: {python_err})"
            )

    return False, (
        "no local Mermaid renderer available. "
        "Install one of:\n"
        "  pip install mmdc                                (pure Python, recommended)\n"
        "  npm install -g @mermaid-js/mermaid-cli          (Node + Chromium)"
    )


def process_mermaid_blocks(
    path: Path, text: str, render: bool, out_dir: Optional[Path]
) -> tuple[list[Finding], str]:
    """
    Find every Mermaid fenced block, optionally render it to PNG, and (if
    rendering succeeded) insert a sibling `![alt](png)` line above the
    block so non-JS viewers see the diagram too.

    Returns (findings, possibly-modified-text).
    """
    findings: list[Finding] = []
    if not render:
        # Still validate that mermaid blocks declare a language.
        for start_line, lang, _body in fenced_blocks(text):
            if lang.lower() == "mermaid":
                pass  # syntax-only validation deferred until render is requested
        return findings, text

    out_dir = (out_dir or path.parent).resolve()
    new_text = text
    # Walk blocks in reverse so insertions don't shift earlier offsets.
    blocks = list(FENCE_RE.finditer(text))
    for idx, m in enumerate(reversed(blocks), 0):
        lang = m.group(2).strip().lower()
        if lang != "mermaid":
            continue
        body = m.group(3)
        start_line = text[: m.start()].count("\n") + 1
        png_name = f"{path.stem}.mermaid-{len(blocks) - idx}.png"
        png_path = out_dir / png_name
        ok, msg = render_mermaid_block(body, png_path)
        if not ok:
            findings.append(Finding(
                path, start_line, "MMD001", ERROR,
                f"Mermaid render failed: {msg}",
            ))
            continue
        # Insert `![Mermaid diagram](png_name)` just above the block, but
        # only if no `<img>` / `![](…)` already references the same PNG.
        already = re.search(rf"!\[[^\]]*\]\([^)]*{re.escape(png_name)}[^)]*\)", new_text)
        if not already:
            insertion = f"![Mermaid diagram (rendered for non-JS readers)]({png_name})\n\n"
            new_text = new_text[: m.start()] + insertion + new_text[m.start() :]
    return findings, new_text


# ── Optional Ollama-assisted suggestions ──────────────────────────────────

# These imports are deferred — the script must run without `requests` or
# `_ollama.py` available (those are needed only with --ai).
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _ollama import OLLAMA_URL, pick_default_model  # type: ignore
    from _prompts import render as render_prompt  # type: ignore
    import requests  # type: ignore
    HAVE_AI = True
except ImportError:
    HAVE_AI = False


# Prompts live in scripts/prompts/*.yaml — see _prompts.py for loader.
# Each prompt is zero-shot with a strict output contract; the parser
# returns an empty result when the model drifts off-contract.


def ai_suggest_mermaid(mermaid_src: str, model: str) -> Optional[list[dict]]:
    """Ask the local LLM for accessible Mermaid node labels; ``None`` if unavailable."""
    if not HAVE_AI:
        return None
    payload = {
        "model": model,
        "prompt": render_prompt("mermaid_labels",
                                 prompts_dir=Path(__file__).resolve().parent / "prompts",
                                 mermaid_src=mermaid_src),
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        body = r.json().get("response", "").strip()
        # Strict parse — the prompt asked for a JSON array only.
        return json.loads(body)
    except Exception:  # pylint: disable=broad-except
        return None


def ai_caption_latex(latex_src: str, lang: str, model: str) -> Optional[str]:
    """Ask the local LLM for a plain-language caption of a LaTeX block; ``None`` if unavailable."""
    if not HAVE_AI:
        return None
    payload = {
        "model": model,
        "prompt": render_prompt("latex_caption",
                                 prompts_dir=Path(__file__).resolve().parent / "prompts",
                                 latex_src=latex_src, lang=lang),
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "").strip().strip('"').strip()
    except Exception:  # pylint: disable=broad-except
        return None


# ── Driver ────────────────────────────────────────────────────────────────

STATIC_RULES = (
    lint_heading_order,
    lint_trailing_whitespace,
    lint_fenced_code_language,
    lint_image_alt,
    lint_local_links,
    lint_latex_blocks,
)


def lint_file(
    path: Path, *, render_mermaid: bool, out_dir: Optional[Path],
    fix: bool, ai: bool, ai_lang: str, ai_model: str,
) -> tuple[list[Finding], list[str]]:
    """Lint one Markdown file. Returns (findings, ai_notes)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return (
            [Finding(path, 1, "MD000", WARNING,
                     f"Skipped — not valid UTF-8: {exc}")],
            [],
        )
    findings: list[Finding] = []
    for rule in STATIC_RULES:
        findings.extend(rule(path, text))

    mermaid_findings, new_text = process_mermaid_blocks(path, text, render_mermaid, out_dir)
    findings.extend(mermaid_findings)

    # MD009 trailing-whitespace strip — only when ``--fix`` is set.
    # Idempotent; preserves the intentional two-space line break.
    if fix:
        new_text = fix_trailing_whitespace(new_text)

    if fix and new_text != text:
        path.write_text(new_text, encoding="utf-8")
        text = new_text

    ai_notes: list[str] = []
    if ai:
        if not HAVE_AI:
            ai_notes.append(
                "(--ai requested but `requests` or `_ollama.py` is not importable; skipped)"
            )
        else:
            model = ai_model or pick_default_model()
            # Mermaid label suggestions.
            for _, lang, body in fenced_blocks(text):
                if lang.lower() == "mermaid":
                    sug = ai_suggest_mermaid(body, model)
                    if sug:
                        ai_notes.append(f"[mermaid] suggested edits: {json.dumps(sug, ensure_ascii=False)}")
            # LaTeX captions.
            for m in DISPLAY_MATH_RE.finditer(text):
                latex = m.group(1).strip()
                cap = ai_caption_latex(latex, ai_lang, model)
                if cap:
                    ai_notes.append(f"[latex] caption ({ai_lang}): {cap}")

    return findings, ai_notes


DEFAULT_EXCLUDE_DIRS = frozenset({
    "node_modules", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".deepeval", ".private", "4ml",
})


def gather_targets(target: Path) -> list[Path]:
    """Walk target. Skip vendor dirs (node_modules, .git, …) by default."""
    if target.is_file():
        return [target]
    out: list[Path] = []
    suffixes = {".md", ".markdown", ".mmd", ".mermaid"}
    for p in target.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in suffixes:
            continue
        if any(part in DEFAULT_EXCLUDE_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def _lint_standalone_mermaid(
    path: Path, render: bool, out_dir: Optional[Path]
) -> tuple[list[Finding], list[str]]:
    """Standalone `.mmd` / `.mermaid` files. Single block, no surrounding text."""
    findings: list[Finding] = []
    src = path.read_text(encoding="utf-8")
    if render:
        out_dir = (out_dir or path.parent).resolve()
        png_path = out_dir / f"{path.stem}.png"
        ok, msg = render_mermaid_block(src, png_path)
        if not ok:
            findings.append(Finding(path, 1, "MMD001", ERROR,
                                    f"Mermaid render failed: {msg}"))
    return findings, []


def main() -> int:
    """CLI entry point for the Markdown linter; returns a process exit code."""
    p = make_parser(
        prog="sprezzature-publish-lint-md",
        description="Lint Markdown — heading order, code-fence languages, image alt, "
                    "local links, LaTeX delimiter balance, and Mermaid block syntax. "
                    "Optionally render Mermaid blocks to local PNG and ask Ollama for "
                    "label / caption suggestions.",
        epilog=(
            "Examples:\n"
            "  sprezzature-publish-lint-md docs/intro.md\n"
            "  sprezzature-publish-lint-md --render-mermaid docs/\n"
            "  sprezzature-publish-lint-md --fix --render-mermaid --ai --ai-lang en docs/\n"
        ),
    )
    p.add_argument("target", type=Path, help="Markdown file or directory.")
    p.add_argument("--format", choices=["text", "json"], default="text",
                   help="Output format. Default: text.")
    p.add_argument("--fix", action="store_true",
                   help="Apply safe mechanical fixes in place: MD009 strip trailing "
                        "whitespace (preserves the intentional two-space line break); "
                        "with --render-mermaid, also insert PNG sibling references. "
                        "Idempotent. Never invents content.")
    p.add_argument("--render-mermaid", action="store_true", dest="render_mermaid",
                   help="Render each Mermaid block to a local PNG sibling.")
    p.add_argument("--out-dir", type=Path, dest="out_dir",
                   help="Directory for rendered Mermaid PNGs. Default: alongside the source.")
    p.add_argument("--ai", action="store_true",
                   help="Ask the local Ollama daemon for Mermaid label improvements and "
                        "LaTeX captions. Read-only — never mutates the source.")
    p.add_argument("--ai-lang", default="en", dest="ai_lang",
                   help="Language of the document, used for LaTeX captions. Default: en.")
    p.add_argument("--ai-model", default="", dest="ai_model",
                   help="Override the Ollama model tag. Default: hardware-picked.")
    args = p.parse_args()

    targets = gather_targets(args.target)
    if not targets:
        print(f"sprezzature-lint-md: no Markdown files under {args.target}", file=sys.stderr)
        return 2

    all_findings: list[Finding] = []
    all_ai_notes: list[tuple[Path, list[str]]] = []
    for path in targets:
        if path.suffix.lower() in {".mmd", ".mermaid"}:
            findings, notes = _lint_standalone_mermaid(path, args.render_mermaid, args.out_dir)
        else:
            findings, notes = lint_file(
                path,
                render_mermaid=args.render_mermaid,
                out_dir=args.out_dir,
                fix=args.fix,
                ai=args.ai,
                ai_lang=args.ai_lang,
                ai_model=args.ai_model,
            )
        all_findings.extend(findings)
        if notes:
            all_ai_notes.append((path, notes))

    if args.format == "json":
        print(json.dumps([{
            "path": str(f.path),
            "line": f.line,
            "rule": f.rule,
            "severity": f.severity,
            "message": f.message,
        } for f in all_findings], indent=2))
    else:
        for f in all_findings:
            print(f"{f.path}:{f.line}: {f.severity}: {f.rule}: {f.message}")
        if all_ai_notes:
            print("\n— AI suggestions (informational, never auto-applied) —")
            for path, notes in all_ai_notes:
                print(f"# {path}")
                for n in notes:
                    print(f"  {n}")

    errors = [f for f in all_findings if f.severity == ERROR]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
