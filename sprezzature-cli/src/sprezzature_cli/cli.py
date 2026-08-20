"""
cli — the `sprezzature` Click driver.

Maps `sprezzature <skill> <action> [args ...]` to the right tool for the
matching skill. Shells out via subprocess; never imports the target
script. This keeps the stdlib-only scripts (validate, lint, contrast,
cvd, site-indexes) zero-dep when invoked directly.

Two skill layouts to support
-----------------------------
Some skills still carry their scripts inside this monorepo
(``sprezzature-ui``, ``sprezzature-vision``, ``sprezzature-publish``): for
those, shelling out to ``<skill>/scripts/<script>.py`` is enough. Others
(``sprezzature-accessibility``, ``sprezzature-audio``, ``sprezzature-colors``,
and more over time) have had their scripts extracted to standalone pip
packages; the in-repo ``scripts/`` folder for those now only holds the
SKILL.md's own agentic contract, no runnable code. ``_run_tool`` tries,
in order: the standalone package's registered console script on
``$PATH``, the in-repo ``scripts/<script>`` (if it still exists), then
``python -m <module>`` against the standalone package's script module
(importable once the package is pip-installed even without a
console-script entry, e.g. ``sprezzature-colors``). A clean, actionable
error replaces the previous "script not found" dead end when none apply.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Optional

import click

from sprezzature_cli import __version__


# Per-skill script directory layout. Each value is the relative path inside
# a skill folder where the script lives.
SCRIPTS_SUBDIR = "scripts"

# Search order for finding a skill folder by name. Each element is a base
# directory that contains `sprezzature-<name>/` folders.
def _candidate_bases() -> list[Path]:
    """Return the ordered base dirs searched for ``sprezzature-<name>`` skill folders."""
    bases: list[Path] = []
    env = (os.environ.get("SPREZZATURE_SKILLS_PATH") or os.environ.get("FRONT_SKILLS_PATH") or "")
    for chunk in env.split(":"):
        chunk = chunk.strip()
        if chunk:
            bases.append(Path(chunk).expanduser())
    bases.append(Path.cwd())
    bases.append(Path.home() / ".claude" / "skills")
    bases.append(Path.home() / ".opencode" / "skills")
    return bases


def _find_skill(skill_name: str) -> Optional[Path]:
    """Return the absolute path to the skill folder, or None if missing."""
    for base in _candidate_bases():
        candidate = base / skill_name
        if (candidate / SCRIPTS_SUBDIR).is_dir():
            return candidate
        # Fallback: assume `base` *is* the repo root and `skill_name` lives
        # directly inside it (the in-repo layout).
        candidate = base / skill_name
        if (candidate / "SKILL.md").is_file() and (candidate / SCRIPTS_SUBDIR).is_dir():
            return candidate
    return None


def _run_script(skill: str, script: str, extra: tuple[str, ...]) -> int:
    """Execute `python <skill>/scripts/<script>` with the extra args.

    Only correct for skills whose scripts still live in this monorepo
    (``sprezzature-ui``, ``sprezzature-vision``, ``sprezzature-publish``).
    For an extracted skill, use :func:`_run_tool` instead.
    """
    skill_root = _find_skill(skill)
    if skill_root is None:
        bases = "\n  ".join(str(b) for b in _candidate_bases())
        click.echo(
            f"sprezzature: skill {skill!r} not found.\n"
            f"Searched (in order):\n  {bases}\n"
            f"Set $SPREZZATURE_SKILLS_PATH or install the skill folder under one of these.",
            err=True,
        )
        return 2
    target = skill_root / SCRIPTS_SUBDIR / script
    if not target.is_file():
        click.echo(f"sprezzature: {script} not found inside {skill_root}.", err=True)
        return 2
    completed = subprocess.run([sys.executable, str(target), *extra])
    return completed.returncode


def _module_available(module: str) -> bool:
    """Return True when ``module`` can be imported without importing it."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        # ValueError: a parent package that itself fails to import cleanly
        # (find_spec still walks it). Treat either as "not usable".
        return False


def _run_tool(
    skill: str,
    script: str,
    extra: tuple[str, ...],
    *,
    console_script: Optional[str] = None,
    module: Optional[str] = None,
) -> int:
    """Run a skill's tool via the first invocation that resolves.

    Tries, in order:

    1. ``console_script`` on ``$PATH``: the standalone pip package's
       registered command (e.g. ``sprezzature-accessibility-lint``).
    2. ``<skill>/scripts/<script>`` inside the discovered skill folder:
       the pre-extraction, in-repo layout, still current for the skills
       that have not moved out.
    3. ``python -m <module>``: the standalone package's script module.
       Works even for packages with no console-script entry (e.g.
       ``sprezzature-colors``), as long as the package is pip-installed.

    Returns the wrapped process's exit code, or 2 with an actionable
    message on stderr when none of the three resolve.
    """
    if console_script is not None:
        found = shutil.which(console_script)
        if found is not None:
            completed = subprocess.run([found, *extra])
            return completed.returncode

    skill_root = _find_skill(skill)
    if skill_root is not None:
        target = skill_root / SCRIPTS_SUBDIR / script
        if target.is_file():
            completed = subprocess.run([sys.executable, str(target), *extra])
            return completed.returncode

    if module is not None and _module_available(module):
        completed = subprocess.run([sys.executable, "-m", module, *extra])
        return completed.returncode

    hint = f"pip install {skill}"
    click.echo(
        f"sprezzature: no working install found for {skill} → {script}.\n"
        f"Tried: {console_script or '(no console script)'} on $PATH, "
        f"{skill}/scripts/{script} on $SPREZZATURE_SKILLS_PATH, "
        f"and `python -m {module}`" + (" (not importable)." if module else ".") + "\n"
        f"Install the standalone package: {hint}",
        err=True,
    )
    return 2


# ── Root group ──────────────────────────────────────────────────────────────

CONTEXT_SETTINGS = {
    # Forward unknown options to the wrapped script. We deliberately
    # omit `help_option_names` here — with `add_help_option=False` on
    # leaf commands, `--help` (and `-h`) flow through to the wrapped
    # script so the user sees the script's real options, not Click's
    # one-line stub.
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}

# Groups keep their own help handling so `sprezzature --help`, `sprezzature accessibility --help`,
# etc. show the driver's subcommand listing.
GROUP_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=GROUP_CONTEXT_SETTINGS)
@click.version_option(__version__, "-V", "--version", prog_name="sprezzature")
def cli() -> None:
    """
    sprezzature — unified driver for the sprezzature-* skills.

    Each sub-command shells out to the matching script in the matching
    skill folder. Skills are discovered via $SPREZZATURE_SKILLS_PATH, the current
    working directory, ~/.claude/skills/ or ~/.opencode/skills/.
    """


# ── ui ──────────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="UI generation skill (sprezzature-ui).")
def ui() -> None:
    """sprezzature-ui — UI generation and pre-ship validation."""


@ui.command(name="validate", context_settings=CONTEXT_SETTINGS, add_help_option=False,
            help="Run the sprezzature-ui pre-ship quality gate.")
@click.pass_context
def ui_validate(ctx: click.Context) -> None:
    """Run the sprezzature-ui pre-ship quality gate (delegates to ``validate.py``)."""
    sys.exit(_run_script("sprezzature-ui", "validate.py", tuple(ctx.args)))


# ── accessibility ───────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Accessibility skill (sprezzature-accessibility).")
def accessibility() -> None:
    """sprezzature-accessibility — pre-commit a11y gates and content tooling."""


@accessibility.command(name="lint", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                       help="Static a11y lint over HTML files (14 rules).")
@click.pass_context
def accessibility_lint(ctx: click.Context) -> None:
    """Run the static a11y lint over HTML files (delegates to ``lint_a11y.py``)."""
    sys.exit(_run_tool(
        "sprezzature-accessibility", "lint_a11y.py", tuple(ctx.args),
        console_script="sprezzature-accessibility-lint",
        module="sprezzature_accessibility_scripts.lint_a11y",
    ))


# ── audio ───────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Audio skill (sprezzature-audio): WebVTT / SRT captions via local whisper.cpp.")
def audio() -> None:
    """sprezzature-audio — local AI captions and transcripts for video / audio."""


@audio.command(name="captions", context_settings=CONTEXT_SETTINGS, add_help_option=False,
               help="WebVTT / SRT / plain-text captions via local whisper.cpp.")
@click.pass_context
def audio_captions(ctx: click.Context) -> None:
    """Generate WebVTT / SRT / plain-text captions via local whisper.cpp."""
    sys.exit(_run_tool(
        "sprezzature-audio", "captions_from_whisper.py", tuple(ctx.args),
        console_script="sprezzature-audio-captions",
        module="sprezzature_audio_scripts.captions_from_whisper",
    ))


@audio.command(name="install", context_settings=CONTEXT_SETTINGS, add_help_option=False,
               help="Install pywhispercpp and download the model used by `sprezzature audio captions`.")
@click.pass_context
def audio_install(ctx: click.Context) -> None:
    """Install pywhispercpp and download the caption model."""
    sys.exit(_run_tool(
        "sprezzature-audio", "install_captions.py", tuple(ctx.args),
        module="sprezzature_audio_scripts.install_captions",
    ))


# ── vision ──────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Vision skill (sprezzature-vision): W3C-compliant alt text via a local vision model.")
def vision() -> None:
    """sprezzature-vision — W3C-compliant alt text via a local Ollama vision model."""


@vision.command(name="alt", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="W3C-compliant alt text via a local Ollama vision model (qwen3-vl:8b).")
@click.pass_context
def vision_alt(ctx: click.Context) -> None:
    """Draft W3C-compliant alt text via the local Ollama vision model."""
    sys.exit(_run_script("sprezzature-vision", "alt_from_ollama.py", tuple(ctx.args)))


@vision.command(name="install", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="Install Ollama and pull the vision model used by `sprezzature vision alt`.")
@click.pass_context
def vision_install(ctx: click.Context) -> None:
    """Install Ollama and pull the vision model used by ``sprezzature vision alt``."""
    sys.exit(_run_script("sprezzature-vision", "install_alt_ai.py", tuple(ctx.args)))


# ── colors ──────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Color skill (sprezzature-colors): contrast, CVD, palette.")
def colors() -> None:
    """sprezzature-colors — palette curation, WCAG contrast, CVD simulation."""


@colors.command(name="contrast", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="WCAG contrast audit + OKLCH-neighbour fix hint.")
@click.pass_context
def colors_contrast(ctx: click.Context) -> None:
    """Run the WCAG contrast audit with an OKLCH-neighbour fix hint."""
    sys.exit(_run_tool(
        "sprezzature-colors", "audit_contrast.py", tuple(ctx.args),
        module="sprezzature_colors_scripts.audit_contrast",
    ))


@colors.command(name="cvd", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="Color-vision-deficiency (protanopia / deuteranopia / tritanopia) rendering.")
@click.pass_context
def colors_cvd(ctx: click.Context) -> None:
    """Render a screenshot under protanopia / deuteranopia / tritanopia."""
    sys.exit(_run_tool(
        "sprezzature-colors", "simulate_cvd.py", tuple(ctx.args),
        module="sprezzature_colors_scripts.simulate_cvd",
    ))


# ── publish ─────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Publishing skill (sprezzature-publish): MD → site, meta, favicons, indexes, plain language.")
def publish() -> None:
    """sprezzature-publish — site, meta, favicons, indexes, plain language."""


@publish.command(name="favicons", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Generate favicon / PWA icon set + manifest from a logo.")
@click.pass_context
def publish_favicons(ctx: click.Context) -> None:
    """Generate a favicon / PWA icon set + manifest from one logo."""
    sys.exit(_run_script("sprezzature-publish", "favicons.py", tuple(ctx.args)))


@publish.command(name="meta", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Draft per-page meta tags (title, description, OG, Twitter, JSON-LD).")
@click.pass_context
def publish_meta(ctx: click.Context) -> None:
    """Draft per-page meta tags (title, description, OG, Twitter, JSON-LD)."""
    sys.exit(_run_script("sprezzature-publish", "meta_from_ollama.py", tuple(ctx.args)))


@publish.command(name="indexes", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Emit robots.txt + sitemap.xml + llms.txt + Atom/RSS + humans.txt.")
@click.pass_context
def publish_indexes(ctx: click.Context) -> None:
    """Emit robots.txt + sitemap.xml + llms.txt + Atom/RSS + humans.txt."""
    sys.exit(_run_script("sprezzature-publish", "site_indexes.py", tuple(ctx.args)))


@publish.command(name="plain", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Rewrite UI copy in plain language at a target grade.")
@click.pass_context
def publish_plain(ctx: click.Context) -> None:
    """Rewrite UI copy in plain language at a target reading grade."""
    sys.exit(_run_script("sprezzature-publish", "plain_language.py", tuple(ctx.args)))


@publish.command(name="lint-md", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Lint Markdown — headings, alt text, links, LaTeX delimiters, Mermaid (rendered locally).")
@click.pass_context
def publish_lint_md(ctx: click.Context) -> None:
    """Lint Markdown — headings, alt text, links, LaTeX, Mermaid."""
    sys.exit(_run_script("sprezzature-publish", "lint_markdown.py", tuple(ctx.args)))


@publish.command(name="md-to-html", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Convert Markdown → HTML with local Mermaid PNG embed, KaTeX LaTeX, three-Roboto + Tailwind shell.")
@click.pass_context
def publish_md_to_html(ctx: click.Context) -> None:
    """Convert Markdown to HTML (Mermaid PNG, KaTeX, Tailwind shell)."""
    sys.exit(_run_script("sprezzature-publish", "md_to_html.py", tuple(ctx.args)))
