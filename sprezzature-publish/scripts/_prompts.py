"""
_prompts — load prompts from YAML files alongside each script.

Each YAML file declares ``role``, ``task``, ``rules``, ``output_contract``
and a ``template`` Python format-string. ``load_prompt(name)`` returns
the assembled template with the meta-fields pre-substituted; the caller
supplies the runtime fields (e.g. ``mermaid_src``).

YAML is parsed with ``yaml.safe_load`` if PyYAML is installed; otherwise
a minimal stdlib parser handles the subset we use (scalars, multiline
``|`` blocks, ``-`` lists). The fallback keeps the prompts script
zero-dep for users who skip the ``--ai`` path.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# Default lookup directory — used when callers do not pass an explicit
# ``prompts_dir`` argument. Resolves to the prompts/ folder next to this
# file. When the same helper is imported by scripts in different skills,
# callers should pass ``prompts_dir=Path(__file__).parent / "prompts"``
# explicitly so each script finds its own YAML files.
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_yaml(text: str) -> dict[str, Any]:
    """Use PyYAML if available; otherwise fall back to a tiny parser."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return _yaml_lite(text)


def _yaml_lite(text: str) -> dict[str, Any]:
    """
    Parse the subset of YAML we use: top-level scalar/list/multiline-block
    entries. No anchors, no flow style, no nested maps. Good enough for the
    prompt files; falls over on anything else.
    """
    data: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2)
        if rest == "|":
            # Multiline block — collect indented lines.
            block_lines: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                block_lines.append(lines[i][2:] if lines[i].startswith("  ") else lines[i])
                i += 1
            data[key] = "\n".join(block_lines).rstrip() + "\n"
        elif rest == "":
            # Possibly a list; peek at the next line.
            items: list[str] = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(lines[i].lstrip()[2:])
                i += 1
            data[key] = items if items else ""
        else:
            data[key] = rest
            i += 1
    return data


def load_prompt(name: str, prompts_dir: Path | None = None) -> dict[str, Any]:
    """
    Load a prompt YAML by name (without extension) and return the dict.

    The returned dict contains the original keys plus ``rules_numbered``
    (rules pre-formatted as ``1. …\\n2. …``) for direct use in the
    ``template`` string. ``prompts_dir`` overrides the default lookup
    directory — pass it when this helper is imported by scripts that
    live outside this skill so each script finds its own YAML files.
    """
    base_dir = prompts_dir if prompts_dir is not None else PROMPTS_DIR
    path = base_dir / f"{name}.yaml"
    data = _load_yaml(path.read_text(encoding="utf-8"))
    rules = data.get("rules", [])
    if isinstance(rules, list):
        data["rules_numbered"] = "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))
    else:
        data["rules_numbered"] = ""
    return data


def render(name: str, prompts_dir: Path | None = None, **runtime: Any) -> str:
    """Load ``name``, substitute the runtime fields, return the prompt string."""
    data = load_prompt(name, prompts_dir=prompts_dir)
    template = data["template"]
    # Pre-substitute the meta-fields first.
    meta = {k: v for k, v in data.items() if k != "template"}
    base = template.format(**meta, **runtime)
    return base
