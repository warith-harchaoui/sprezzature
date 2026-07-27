#!/usr/bin/env python3
"""
validate_skill
==============

Shared, YAML-strict validator for a single Anthropic Claude / OpenCode
skill folder. Replaces the previous regex-only frontmatter check that
let ``mapping values are not allowed here`` errors slip through CI.

The validator answers one question: **would the Claude / OpenCode
runtime accept this skill as-is?**

The contract checked is intentionally narrow — it mirrors what real
parsers (PyYAML, ruamel) and the Anthropic skill spec require:

1. ``<skill>/SKILL.md`` exists and is non-empty.
2. The file starts with a ``---\\n...\\n---`` frontmatter block.
3. The frontmatter is parsable by ``yaml.safe_load``.
4. The parsed result is a mapping (``dict``).
5. ``name`` is present, a non-empty string, and matches the folder name.
6. ``description`` is present, a non-empty string, 50-1024 chars (the
   Anthropic spec caps at 1024).
7. The Markdown body after the frontmatter is not empty.
8. No surface-level placeholders (``TODO``, ``TBD``, ``FIXME``,
   ``XXX``) remain in ``SKILL.md`` itself. References and scripts
   are allowed to track follow-ups in TODO comments.

Higher-level / content-quality checks (forbidden framework imports,
trademarked terms, LLM-marketing phrases, INDEX.md path resolution)
stay in ``sprezzature-ui/scripts/validate.py`` because they're specific to
the sprezzature-ui skill. This module is the cross-skill foundation.

Usage
-----
::

    # Validate one skill folder
    python3 scripts/validate_skill.py sprezzature-ui/

    # Validate every skill in the repo (exit non-zero on any failure)
    python3 scripts/validate_skill.py sprezzature-ui/ sprezzature-cli-gui/ \\
        sprezzature-publish/ sprezzature-accessibility/

    # Programmatic use (returns a list of error strings; empty on PASS)
    from scripts.validate_skill import validate_skill
    errors: list[str] = validate_skill(Path("sprezzature-ui"))

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


# ── Module-level configuration ──────────────────────────────────────────────

#: Anthropic skill spec caps description at 1024 chars. Lower bound is a
#: project convention — anything shorter is almost certainly missing
#: trigger phrases.
DESCRIPTION_MIN: int = 50
DESCRIPTION_MAX: int = 1024

#: Frontmatter delimiter regex. Matches the canonical
#: ``---\n<yaml>\n---\n`` shape; everything after the closing ``---``
#: is treated as the Markdown body.
FRONTMATTER_RE: re.Pattern[str] = re.compile(
    r"^---\n(?P<yaml>.*?)\n---\n(?P<body>.*)\Z",
    re.DOTALL,
)

#: Placeholder tokens we refuse to ship in SKILL.md proper. Documented
#: TODOs in references/scripts are fine — this list scopes to the
#: skill's *entry* file only.
PLACEHOLDER_TOKENS: tuple[str, ...] = ("TODO", "TBD", "FIXME", "XXX")


# ── Single-skill validator ─────────────────────────────────────────────────

def validate_skill(skill_dir: Path) -> list[str]:
    """
    Validate one skill folder.

    Parameters
    ----------
    skill_dir : Path
        Path to the skill folder (e.g. ``Path("sprezzature-ui")``). Must
        exist and be a directory.

    Returns
    -------
    list of str
        Human-readable error messages — empty when the skill passes.
        The caller decides how to surface them (print, raise, …).

    Examples
    --------
    >>> errors = validate_skill(Path("sprezzature-ui"))
    >>> errors
    []
    """
    errors: list[str] = []
    skill_dir = skill_dir.resolve()

    # ── Check 1: directory must exist ──────────────────────────────────
    if not skill_dir.is_dir():
        return [f"{skill_dir}: skill folder does not exist or is not a directory"]

    skill_name: str = skill_dir.name
    skill_md: Path = skill_dir / "SKILL.md"

    # ── Check 2: SKILL.md must exist and be non-empty ──────────────────
    if not skill_md.is_file():
        return [f"{skill_name}: SKILL.md missing at {skill_md}"]
    raw: str = skill_md.read_text(encoding="utf-8")
    if not raw.strip():
        return [f"{skill_name}: SKILL.md is empty"]

    # ── Check 3: frontmatter delimiters ────────────────────────────────
    m = FRONTMATTER_RE.match(raw)
    if m is None:
        return [
            f"{skill_name}: SKILL.md must start with a '---\\n<yaml>\\n---\\n' "
            f"frontmatter block (found: {raw[:60]!r}…)"
        ]
    yaml_text: str = m.group("yaml")
    body: str = m.group("body")

    # ── Check 4: frontmatter parses as YAML ────────────────────────────
    parsed: Any
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        # The Anthropic / OpenCode runtimes call a real parser too; if
        # this fails, the skill is silently rejected at load time.
        return [f"{skill_name}: SKILL.md frontmatter is not valid YAML — {e}"]

    # ── Check 5: parsed YAML must be a mapping ─────────────────────────
    if not isinstance(parsed, dict):
        return [
            f"{skill_name}: SKILL.md frontmatter must parse to a mapping "
            f"(got {type(parsed).__name__})"
        ]

    # ── Check 6: name field ────────────────────────────────────────────
    name = parsed.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{skill_name}: frontmatter 'name' missing or empty")
    elif name != skill_name:
        errors.append(
            f"{skill_name}: frontmatter name={name!r} does not match "
            f"folder name {skill_name!r}"
        )

    # ── Check 7: description field ─────────────────────────────────────
    description = parsed.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_name}: frontmatter 'description' missing or empty")
    else:
        # Normalise whitespace the way the Anthropic spec implicitly
        # does (block scalars collapse newlines to single spaces).
        normalised: str = " ".join(description.split())
        length: int = len(normalised)
        if length < DESCRIPTION_MIN:
            errors.append(
                f"{skill_name}: description too short "
                f"({length} chars; need ≥ {DESCRIPTION_MIN})"
            )
        elif length > DESCRIPTION_MAX:
            errors.append(
                f"{skill_name}: description exceeds {DESCRIPTION_MAX} chars "
                f"({length})"
            )

    # ── Check 8: body after frontmatter must be non-empty ──────────────
    if not body.strip():
        errors.append(f"{skill_name}: SKILL.md Markdown body is empty")

    # ── Check 9: no surface-level placeholders in SKILL.md ─────────────
    placeholder_hits: list[str] = []
    for token in PLACEHOLDER_TOKENS:
        # Word-boundary regex so we don't flag "todo" inside "todos" or
        # other legitimate substrings.
        for i, line in enumerate(raw.splitlines(), 1):
            if re.search(rf"\b{token}\b", line):
                placeholder_hits.append(f"L{i}: {line.strip()}")
                break  # one hit per token is enough — keep output short
    if placeholder_hits:
        errors.append(
            f"{skill_name}: SKILL.md contains placeholder token(s) — "
            + "; ".join(placeholder_hits)
        )

    # ── Check 10: no README.md anywhere inside the skill folder ────────
    # The Anthropic skill spec explicitly forbids ``README.md`` *inside*
    # the skill folder: "Don't include README.md inside your skill
    # folder. All documentation goes in SKILL.md or references/." That
    # rule covers nested paths too (e.g. ``assets/examples/.../README.md``),
    # so we walk the whole tree, not just the top level. The repo-level
    # README.md sitting *next to* the skill folder is fine and
    # encouraged — it's the entry point for human visitors on GitHub.
    nested_readmes: list[Path] = sorted(skill_dir.rglob("README.md"))
    if nested_readmes:
        errors.append(
            f"{skill_name}: README.md found inside the skill folder "
            f"(spec forbids it): "
            + ", ".join(str(p.relative_to(skill_dir)) for p in nested_readmes)
        )

    return errors


# ── Multi-skill CLI ────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """
    Parse the command-line arguments.

    Returns
    -------
    argparse.Namespace
        With ``.skills`` (list of ``Path``) and ``.quiet`` (bool).
    """
    parser = argparse.ArgumentParser(
        prog="validate_skill",
        description="Strict YAML-based validator for Anthropic-spec skill folders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "skills",
        nargs="+",
        type=Path,
        help="One or more skill folders to validate (e.g. sprezzature-ui sprezzature-accessibility).",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress the per-skill PASS line; only print failures.",
    )
    return parser.parse_args()


def main() -> int:
    """
    CLI entrypoint.

    Returns
    -------
    int
        ``0`` when every skill passes; ``1`` when one or more fail.
    """
    args = parse_args()
    failures: int = 0
    for skill_dir in args.skills:
        errors = validate_skill(skill_dir)
        if errors:
            failures += 1
            for err in errors:
                print(f"FAIL {err}", file=sys.stderr)
        elif not args.quiet:
            print(f"PASS {skill_dir.resolve().name}: SKILL.md is well-formed")
    if failures:
        print(
            f"\n{failures} skill(s) failed validation.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
