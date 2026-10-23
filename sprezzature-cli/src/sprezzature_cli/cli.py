"""
cli — the `sprezzature` Click driver.

Maps `sprezzature <skill> <action> [args ...]` to the right tool for the
matching skill. Shells out via subprocess; never imports the target
script, so a stdlib-only tool stays zero-dep when invoked this way.

One layout, after the split
---------------------------
This used to describe two: the skills that still carried their scripts
inside the monorepo, and the ones extracted into standalone pip packages.
There is one left. Every brick is its own package now, so every
sub-command goes through :func:`_run_tool`, which tries, in order: the
package's registered console script on ``$PATH``; ``<skill>/scripts/<script>``
inside a discovered skill folder, the pre-split layout, kept because a
hand-built folder is a fair thing to point the driver at; then
``python -m <module>`` against the package's script module, which works
even where no console script is registered. When none resolve, the error
names all three attempts and the ``pip install`` that would fix it.

Three routes stopped at the second and third of those — two colour tools and
the caption installer — because when they were written their bricks shipped no
command for them. All three are registered now, so all three are named here.

Nine sub-commands bypassed that and shelled straight to an in-repo file
until 2026-10-20 — one per brick that had not yet moved when they were
written. They had all moved. Every one of those commands exited 2 on any
clean checkout, and the test that should have caught it was held up by an
untracked ``__pycache__``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
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
    """Return the absolute path to the skill folder, or None if missing.

    What makes a folder a skill is its ``SKILL.md`` — the contract an agent
    reads. It used to be a ``scripts/`` directory, from when every skill
    carried runnable code beside that contract. None do: the scripts left for
    their own pip packages, and the only thing still answering ``is_dir()``
    in those folders was a ``__pycache__`` nobody commits. So this resolved to
    None for every shipped skill, on any clean checkout, and
    ``sprezzature ui validate`` and eight sibling sub-commands exited 2 with
    "skill not found".

    ``scripts/`` still counts, with or without a contract file beside it: that
    is the layout :func:`_run_tool` falls back to, and a folder built by hand
    for a one-off tool is a fair thing to point the driver at.
    """
    for base in _candidate_bases():
        candidate = base / skill_name
        if (candidate / "SKILL.md").is_file() or (candidate / SCRIPTS_SUBDIR).is_dir():
            return candidate
    return None


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

    # `script=""` means the brick never had an in-repo script to fall back to:
    # the four extracted bricks forwarded wholesale at the bottom of this file
    # have a console script and a module and nothing else. Joining "" onto the
    # scripts/ path would test the directory itself, which exists.
    skill_root = _find_skill(skill) if script else None
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
        + (f"{skill}/scripts/{script} on $SPREZZATURE_SKILLS_PATH, " if script else "")
        + f"and `python -m {module}`" + (" (not importable)." if module else ".") + "\n"
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
    """sprezzature-ui — UI generation, and the i18n tools that come with it.

    ``sprezzature ui validate`` stood here, for the pre-ship content gate.
    That gate never left the monorepo — it reads a *skill folder* in this
    repository, not anything in a user's project — so a published driver
    offering it was offering a command that cannot work from an install. It
    lives beside the other repository-level validators, as
    ``python scripts/validate_all.py`` in a checkout.

    What `sprezzature-ui` does install are the two i18n tools below.
    """


@ui.command(name="i18n-audit", context_settings=CONTEXT_SETTINGS, add_help_option=False,
            help="Audit a project for strings hard-coded in JS instead of the locale files.")
@click.pass_context
def ui_i18n_audit(ctx: click.Context) -> None:
    """Audit JS translation dicts and inline prompts for untranslated copy."""
    sys.exit(_run_tool(
        "sprezzature-ui", "audit_i18n.py", tuple(ctx.args),
        console_script="sprezzature-ui-i18n-audit",
        module="sprezzature_ui_scripts.audit_i18n",
    ))


@ui.command(name="i18n-make", context_settings=CONTEXT_SETTINGS, add_help_option=False,
            help="Scaffold or recompile locales/i18n.yaml and its JS loader.")
@click.pass_context
def ui_i18n_make(ctx: click.Context) -> None:
    """Scaffold or recompile ``locales/i18n.yaml`` and the JS loader beside it."""
    sys.exit(_run_tool(
        "sprezzature-ui", "i18n_make.py", tuple(ctx.args),
        console_script="sprezzature-ui-i18n-make",
        module="sprezzature_ui_scripts.i18n_make",
    ))


# ── accessibility ───────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Accessibility skill (sprezzature-accessibility).")
def accessibility() -> None:
    """sprezzature-accessibility — pre-commit a11y gates and content tooling."""


@accessibility.command(name="lint", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                       help="Static a11y lint over HTML files (20 rules).")
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
        console_script="sprezzature-audio-install",
        module="sprezzature_audio_scripts.install_captions",
    ))


# ── vision ──────────────────────────────────────────────────────────────────

@cli.group(context_settings=GROUP_CONTEXT_SETTINGS, help="Vision skill (sprezzature-accessibility): W3C-compliant alt text via a local vision model.")
def vision() -> None:
    """sprezzature-accessibility — W3C-compliant alt text via a local Ollama vision model."""


@vision.command(name="alt", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="W3C-compliant alt text via a local Ollama vision model (qwen3-vl:8b).")
@click.pass_context
def vision_alt(ctx: click.Context) -> None:
    """Draft W3C-compliant alt text via the local Ollama vision model."""
    # ``make-alt``, not ``sprezzature-accessibility-alt``: the brick ships both
    # front doors on one table, and the argparse one needs no extra. Its Click
    # twin imports Click at load, so on a bare ``pip install`` it is a command
    # on $PATH that cannot start — and both steps below would then be spent on
    # a tool the user does have, in a spelling that cannot run it.
    sys.exit(_run_tool(
        "sprezzature-accessibility", "alt_from_ollama.py", tuple(ctx.args),
        console_script="make-alt",
        module="sprezzature_accessibility.alt_cli",
    ))


@vision.command(name="install", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="Install Ollama and pull the vision model used by `sprezzature vision alt`.")
@click.pass_context
def vision_install(ctx: click.Context) -> None:
    """Install Ollama and pull the vision model used by ``sprezzature vision alt``."""
    sys.exit(_run_tool(
        "sprezzature-accessibility", "install_alt_ai.py", tuple(ctx.args),
        console_script="sprezzature-accessibility-install-alt",
        module="sprezzature_accessibility_scripts.install_alt_ai",
    ))


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
        console_script="sprezzature-colors-contrast",
        module="sprezzature_colors_scripts.audit_contrast",
    ))


@colors.command(name="cvd", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                help="Color-vision-deficiency (protanopia / deuteranopia / tritanopia) rendering.")
@click.pass_context
def colors_cvd(ctx: click.Context) -> None:
    """Render a screenshot under protanopia / deuteranopia / tritanopia."""
    sys.exit(_run_tool(
        "sprezzature-colors", "simulate_cvd.py", tuple(ctx.args),
        console_script="sprezzature-colors-cvd",
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
    sys.exit(_run_tool(
        "sprezzature-publish", "favicons.py", tuple(ctx.args),
        console_script="sprezzature-publish-icons",
        module="sprezzature_publish_scripts.favicons",
    ))


@publish.command(name="meta", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Draft per-page meta tags (title, description, OG, Twitter, JSON-LD).")
@click.pass_context
def publish_meta(ctx: click.Context) -> None:
    """Draft per-page meta tags (title, description, OG, Twitter, JSON-LD)."""
    sys.exit(_run_tool(
        "sprezzature-publish", "meta_from_ollama.py", tuple(ctx.args),
        console_script="sprezzature-publish-meta",
        module="sprezzature_publish_scripts.meta_from_ollama",
    ))


@publish.command(name="indexes", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Emit robots.txt + sitemap.xml + llms.txt + Atom/RSS + humans.txt.")
@click.pass_context
def publish_indexes(ctx: click.Context) -> None:
    """Emit robots.txt + sitemap.xml + llms.txt + Atom/RSS + humans.txt."""
    sys.exit(_run_tool(
        "sprezzature-publish", "site_indexes.py", tuple(ctx.args),
        console_script="sprezzature-publish-indexes",
        module="sprezzature_publish_scripts.site_indexes",
    ))


@publish.command(name="plain", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Rewrite UI copy in plain language at a target grade.")
@click.pass_context
def publish_plain(ctx: click.Context) -> None:
    """Rewrite UI copy in plain language at a target reading grade."""
    sys.exit(_run_tool(
        "sprezzature-publish", "plain_language.py", tuple(ctx.args),
        console_script="sprezzature-publish-plain",
        module="sprezzature_publish_scripts.plain_language",
    ))


@publish.command(name="lint-md", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Lint Markdown — headings, alt text, links, LaTeX delimiters, Mermaid (rendered locally).")
@click.pass_context
def publish_lint_md(ctx: click.Context) -> None:
    """Lint Markdown — headings, alt text, links, LaTeX, Mermaid."""
    sys.exit(_run_tool(
        "sprezzature-publish", "lint_markdown.py", tuple(ctx.args),
        console_script="sprezzature-publish-lint",
        module="sprezzature_publish_scripts.lint_markdown",
    ))


@publish.command(name="md-to-html", context_settings=CONTEXT_SETTINGS, add_help_option=False,
                 help="Convert Markdown → HTML with local Mermaid PNG embed, KaTeX LaTeX, three-Roboto + Tailwind shell.")
@click.pass_context
def publish_md_to_html(ctx: click.Context) -> None:
    """Convert Markdown to HTML (Mermaid PNG, KaTeX, Tailwind shell)."""
    sys.exit(_run_tool(
        "sprezzature-publish", "md_to_html.py", tuple(ctx.args),
        console_script="sprezzature-publish-html",
        module="sprezzature_publish_scripts.md_to_html",
    ))


# ── The four bricks whose own command is already the whole surface ──────────
#
# `figures`, `maps`, `cli-gui` and `ux-laws` were reachable through this driver
# by no name at all. Nine bricks ship, five had a group here, and the package
# description called itself "one entry point for the sprezzature skills" — a
# sentence that was true of a bit more than half of them.
#
# They are forwarded wholesale rather than mirrored, and that is the difference
# from the groups above. `sprezzature-figures`, `sprezzature-maps`,
# `sprezzature-cli-gui` and `sprezzature-ux-laws` are each already a complete
# sub-command tree of their own; re-declaring their commands here would put a
# second copy of a surface in a place that cannot see when the first one
# changes, which is the thing SURFACES.md exists to forbid. A pass-through has
# one name to keep true — the console script — and the hub's
# tests/test_the_driver_routes_to_what_exists.py checks it, from the
# repository that sees every brick. `_run_tool` is called directly rather
# than through a helper for the same reason: that guard reads literal
# arguments out of the syntax tree, and a wrapper would hide them from it.
#
# `--help` therefore shows the brick's own help, not a Click stub: that is what
# `add_help_option=False` plus `allow_extra_args` buys.


@cli.command(name="figures", context_settings=CONTEXT_SETTINGS, add_help_option=False,
             help="Figures skill (sprezzature-figures): 167 SVG chart kinds, audits, diagrams.")
@click.pass_context
def figures(ctx: click.Context) -> None:
    """sprezzature-figures — every argument goes to its own command."""
    sys.exit(_run_tool(
        "sprezzature-figures", "", tuple(ctx.args),
        console_script="sprezzature-figures",
        module="sprezzature_figures.cli",
    ))


@cli.command(name="maps", context_settings=CONTEXT_SETTINGS, add_help_option=False,
             help="Maps skill (sprezzature-maps): choropleths, situation plates, GPS traces.")
@click.pass_context
def maps(ctx: click.Context) -> None:
    """sprezzature-maps — every argument goes to its own command."""
    sys.exit(_run_tool(
        "sprezzature-maps", "", tuple(ctx.args),
        console_script="sprezzature-maps",
        module="sprezzature_maps.cli_click",
    ))


@cli.command(name="cli-gui", context_settings=CONTEXT_SETTINGS, add_help_option=False,
             help="CLI-GUI skill (sprezzature-cli-gui): wrap a command-line tool in a web UI.")
@click.pass_context
def cli_gui(ctx: click.Context) -> None:
    """sprezzature-cli-gui — every argument goes to its own command."""
    sys.exit(_run_tool(
        "sprezzature-cli-gui", "", tuple(ctx.args),
        console_script="sprezzature-cli-gui",
        module="sprezzature_cli_gui.cli",
    ))


@cli.command(name="ux-laws", context_settings=CONTEXT_SETTINGS, add_help_option=False,
             help="Laws of UX skill (sprezzature-ux-laws): the decidable fraction, from raw HTML.")
@click.pass_context
def ux_laws(ctx: click.Context) -> None:
    """sprezzature-ux-laws — every argument goes to its own command."""
    sys.exit(_run_tool(
        "sprezzature-ux-laws", "", tuple(ctx.args),
        console_script="sprezzature-ux-laws",
        module="sprezzature_ux_laws.cli_click",
    ))
