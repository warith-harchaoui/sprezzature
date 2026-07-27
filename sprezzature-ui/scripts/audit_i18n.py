#!/usr/bin/env python3
"""
audit_i18n
==========

Static audit half of the sprezzature-ui unified-i18n rule: translatable strings
— GUI labels and LLM prompts — belong in one per-project catalog,
``locales/i18n.yaml``, never embedded in JavaScript or inlined in Python.

This script flags the two violations of that rule, deterministically and
without a browser, a model, or the network:

- I18N001 — a translation dictionary embedded in JS / HTML: an object
  literal that maps locale codes (``en``, ``fr``, …) to strings, or a variable
  named ``i18n`` / ``translations`` / ``messages`` / ``locales`` / ``strings``
  assigned an object literal. Those belong in ``locales/i18n.yaml``.
- I18N002 — an LLM prompt inlined in Python: a module- or class-level
  constant whose name contains ``PROMPT`` / ``TEMPLATE`` / ``SYSTEM`` /
  ``INSTRUCTION`` assigned a string literal, instead of being loaded from
  ``locales/i18n.yaml`` (or a ``prompts/*.yaml`` catalog).

It is the counterpart to :mod:`i18n_make` (the make half). Output is a JSON
array of findings (``--json``) or human-readable lines, plus an exit code
(0 clean, 1 on any finding) — suitable for ``pre-commit`` and CI.

Usage
-----
::

    # Audit a project tree (or explicit files) for i18n-in-code violations
    python audit_i18n.py app.js index.html engine.py
    python audit_i18n.py --json src/            # machine-readable, recurse dirs

    # 0 = clean, 1 = at least one finding
    python audit_i18n.py src/ && echo "i18n clean"

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402

#: File extensions treated as GUI code (checked for I18N001).
JS_EXTS: tuple[str, ...] = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".html", ".htm")

#: File extensions treated as Python (checked for I18N002).
PY_EXTS: tuple[str, ...] = (".py",)

#: Variable names that, when assigned an object literal in JS, are a
#: translation catalog living in code rather than in locales/i18n.yaml.
_JS_I18N_NAMES = r"(?:i18n|translations?|messages|locales|strings|dictionary|langs?|LOCALES|I18N|TRANSLATIONS|MESSAGES)"

#: `const i18n = {`, `let translations = {`, `window.MESSAGES = {`, … — a
#: named translation table declared in JS.
_JS_NAMED_TABLE = re.compile(
    r"(?:const|let|var|window\.\w*\.?|\bexport\s+const)\s*" + _JS_I18N_NAMES + r"\s*=\s*\{",
    re.IGNORECASE,
)

#: An object literal whose keys are locale codes mapping to string/object
#: values — e.g. ``{ en: "Save", fr: "Enregistrer" }`` — regardless of the
#: variable name. We require at least TWO distinct locale keys so a lone
#: ``{ en: ... }`` config object is not mistaken for a catalog.
_LOCALE_KEY = re.compile(
    r"""["']?\b(en|fr|es|de|it|pt|nl|ja|zh|ko|ru|ar|hi)\b["']?\s*:\s*["'{]""",
    re.IGNORECASE,
)

#: Python constant names that signal an LLM prompt (I18N002) when assigned a
#: string literal directly rather than loaded from a catalog. Deliberately
#: narrow to ``PROMPT`` / ``INSTRUCTION``: a bare ``*_TEMPLATE`` matches HTML /
#: string templates (e.g. ``PAGE_TEMPLATE``) that are NOT prompts, so it is
#: excluded to keep the rule precise (prompts are ~always named ``*PROMPT*``).
_PY_PROMPT_NAME = re.compile(r"(PROMPT|INSTRUCTION)", re.IGNORECASE)


def _finding(rule: str, severity: str, path: str, line: int, message: str, snippet: str) -> Dict[str, Any]:
    """Build one finding dict in the shared auditor shape.

    Parameters
    ----------
    rule : str
        Stable rule id (``I18N001`` / ``I18N002``).
    severity : str
        ``"error"`` — every i18n-in-code hit blocks by default.
    path : str
        File the finding is in.
    line : int
        1-based line number.
    message : str
        Human-readable explanation + the fix ("move to locales/i18n.yaml").
    snippet : str
        The offending source line, stripped.

    Returns
    -------
    dict
        A single finding, JSON-serialisable.
    """
    return {"rule": rule, "severity": severity, "path": path, "line": line,
            "message": message, "snippet": snippet}


def audit_js(path: Path) -> List[Dict[str, Any]]:
    """Flag GUI translation dictionaries embedded in a JS / HTML file (I18N001).

    Two detectors, deduplicated per line: a translation table declared under a
    telltale name (``const i18n = {``), and any object literal that maps two or
    more locale codes to values (``{ en: …, fr: … }``).

    Parameters
    ----------
    path : pathlib.Path
        A ``.js`` / ``.ts`` / ``.html`` (etc.) file.

    Returns
    -------
    list of dict
        Findings; empty when the file keeps its strings out of code.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> p = pathlib.Path(tempfile.mkstemp(suffix=".js")[1])
    >>> _ = p.write_text('const i18n = { en: "Save", fr: "Enregistrer" };')
    >>> [f["rule"] for f in audit_js(p)]
    ['I18N001']
    """
    findings: List[Dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    flagged_lines: set[int] = set()
    for i, line in enumerate(text.splitlines(), start=1):
        # Detector 1: a named translation table (const i18n = { … ).
        if _JS_NAMED_TABLE.search(line):
            flagged_lines.add(i)
            continue
        # Detector 2: an inline object literal keyed by >= 2 locale codes.
        # Count DISTINCT locale keys on the line so `{ en: x }` alone (a
        # plausible non-catalog config) does not trip the rule.
        distinct = {m.group(1).lower() for m in _LOCALE_KEY.finditer(line)}
        if len(distinct) >= 2:
            flagged_lines.add(i)
    lines = text.splitlines()
    for i in sorted(flagged_lines):
        findings.append(_finding(
            "I18N001", "error", str(path), i,
            "GUI translations embedded in JS/HTML — move them to locales/i18n.yaml "
            "and load via the compiled locales/i18n.json (see i18n_make.py).",
            lines[i - 1].strip()[:160],
        ))
    return findings


def audit_py(path: Path) -> List[Dict[str, Any]]:
    """Flag LLM prompts inlined in a Python file (I18N002).

    Walks the AST for module- or class-level assignments whose target name
    looks like a prompt (``*PROMPT*`` / ``*INSTRUCTION*``, case-insensitive)
    and whose value is a string literal. Loading a prompt
    from a catalog (``load_prompt(...)`` / ``render_prompt(...)``) is a call,
    not a constant string, so compliant code is never flagged.

    Parameters
    ----------
    path : pathlib.Path
        A ``.py`` file.

    Returns
    -------
    list of dict
        Findings; empty when prompts are loaded from a catalog.
    """
    findings: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        # Not valid Python (a template, a fragment) — nothing to audit.
        return findings

    def check(name: str, value: ast.expr, lineno: int) -> None:
        # Only string-literal values count; a ``load_prompt(...)`` call is fine.
        """Flag a string-literal GUI/prompt value that should live in ``locales/i18n.yaml``."""
        is_str = isinstance(value, ast.Constant) and isinstance(value.value, str)
        # A joined f-string (ast.JoinedStr) built inline is also an inlined prompt.
        is_fstr = isinstance(value, ast.JoinedStr)
        if (is_str or is_fstr) and _PY_PROMPT_NAME.search(name):
            findings.append(_finding(
                "I18N002", "error", str(path), lineno,
                f"LLM prompt '{name}' inlined in Python — move it to "
                "locales/i18n.yaml (prompts:) or a prompts/*.yaml catalog and load it.",
                name,
            ))

    # Only module top-level + class-body assignments (constants), not locals.
    bodies: List[ast.stmt] = list(tree.body)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bodies.extend(node.body)
    for node in bodies:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    check(tgt.id, node.value, node.lineno)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            check(node.target.id, node.value, node.lineno)
    return findings


def audit_path(path: Path) -> List[Dict[str, Any]]:
    """Audit a single file by extension, dispatching to the JS or Python check.

    Parameters
    ----------
    path : pathlib.Path
        File to audit.

    Returns
    -------
    list of dict
        Findings for the file (empty if the extension is not audited).
    """
    suffix = path.suffix.lower()
    if suffix in JS_EXTS:
        return audit_js(path)
    if suffix in PY_EXTS:
        return audit_py(path)
    return []


def gather(paths: List[str]) -> List[Path]:
    """Expand the CLI path arguments into a sorted list of auditable files.

    Directories are walked recursively; the two audited extension groups
    (JS-family, Python) are kept, everything else is dropped. Common vendor /
    build dirs are skipped so a bundled third-party translation file does not
    produce noise.

    Parameters
    ----------
    paths : list of str
        Files and/or directories from the command line.

    Returns
    -------
    list of pathlib.Path
        Deduplicated, sorted files to audit.
    """
    skip = {"node_modules", ".git", "__pycache__", "dist", "build", "vendor", ".venv"}
    out: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in JS_EXTS + PY_EXTS \
                        and not (set(f.parts) & skip):
                    out.add(f)
        elif p.is_file():
            out.add(p)
    return sorted(out)


def main() -> int:
    """CLI entry point. Returns 0 when clean, 1 on any finding.

    Returns
    -------
    int
        Process exit code (0 clean, 1 findings).
    """
    p = make_parser(
        prog="sprezzature-ui-i18n-audit",
        description="Flag GUI translations embedded in JS/HTML and LLM prompts "
                    "inlined in Python — both belong in locales/i18n.yaml.",
        epilog=__doc__,
    )
    p.add_argument("paths", nargs="+", help="Files and/or directories to audit.")
    p.add_argument("--json", action="store_true", help="Emit findings as a JSON array.")
    args = p.parse_args()

    findings: List[Dict[str, Any]] = []
    for f in gather(args.paths):
        findings.extend(audit_path(f))

    if args.json:
        json.dump(findings, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for fd in findings:
            # `path:line: RULE message` — one grep-friendly line per finding.
            print(f"{fd['path']}:{fd['line']}: {fd['rule']} {fd['message']}")
        print()
        print(f"{len(findings)} finding(s)." if findings else "0 findings.")

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
