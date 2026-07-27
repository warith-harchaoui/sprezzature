"""
test_i18n — unit tests for the unified i18n make + audit (sprezzature-ui).

Covers both halves of the ``locales/i18n.yaml`` rule:

* ``audit_i18n`` (audit) — flags GUI translation dicts embedded in JS/HTML
  (I18N001) and LLM prompts inlined in Python (I18N002); passes compliant code.
* ``i18n_make`` (make) — scaffolds ``locales/i18n.yaml``, compiles it to
  ``locales/i18n.json``, and emits the vanilla-JS loader; ``--init`` is
  idempotent (never clobbers an existing catalog).

The skill ``scripts/`` dirs are on ``sys.path`` via ``tests/conftest.py``, so
the modules import directly.

Author
------
Project maintainers.
"""

from __future__ import annotations

import json
from pathlib import Path

import audit_i18n  # noqa: E402  (path set by conftest)
import i18n_make  # noqa: E402


# ── audit: I18N001 (GUI translations embedded in JS) ────────────────────────

def test_audit_flags_named_js_translation_table(tmp_path: Path) -> None:
    """A ``const i18n = { … }`` table in JS is an I18N001 violation."""
    js = tmp_path / "app.js"
    js.write_text('const i18n = {\n  en: { save: "Save" },\n  fr: { save: "Enregistrer" }\n};\n')
    findings = audit_i18n.audit_path(js)
    assert [f["rule"] for f in findings] == ["I18N001"]
    assert "locales/i18n.yaml" in findings[0]["message"]


def test_audit_flags_inline_locale_object(tmp_path: Path) -> None:
    """An inline object with >= 2 locale keys is flagged even without a name."""
    js = tmp_path / "widget.js"
    js.write_text('const label = { en: "Save", fr: "Enregistrer" };\n')
    assert any(f["rule"] == "I18N001" for f in audit_i18n.audit_path(js))


def test_audit_ignores_single_locale_config(tmp_path: Path) -> None:
    """A lone ``{ en: … }`` (one locale) is NOT a catalog — no false positive."""
    js = tmp_path / "cfg.js"
    js.write_text('const opts = { en: "English", timeout: 30 };\n')
    assert audit_i18n.audit_path(js) == []


def test_audit_passes_clean_gui(tmp_path: Path) -> None:
    """Reading strings via ``t(id)`` (not a JS dict) is compliant."""
    js = tmp_path / "clean.js"
    js.write_text('import { t } from "./locales/i18n.js";\nel.textContent = t("action.save");\n')
    assert audit_i18n.audit_path(js) == []


# ── audit: I18N002 (LLM prompts inlined in Python) ──────────────────────────

def test_audit_flags_inline_python_prompt(tmp_path: Path) -> None:
    """A ``*_PROMPT`` string constant is an I18N002 violation."""
    py = tmp_path / "engine.py"
    py.write_text('SYSTEM_PROMPT = """You are a helpful assistant. Reply in French."""\n')
    findings = audit_i18n.audit_path(py)
    assert [f["rule"] for f in findings] == ["I18N002"]
    assert "SYSTEM_PROMPT" in findings[0]["message"]


def test_audit_ignores_html_template_constant(tmp_path: Path) -> None:
    """``PAGE_TEMPLATE`` is an HTML template, not a prompt — not flagged."""
    py = tmp_path / "render.py"
    py.write_text('PAGE_TEMPLATE = "<html><body>{body}</body></html>"\n')
    assert audit_i18n.audit_path(py) == []


def test_audit_passes_loaded_prompt(tmp_path: Path) -> None:
    """A prompt LOADED from a catalog (a call, not a literal) is compliant."""
    py = tmp_path / "ok.py"
    py.write_text('from _prompts import load_prompt\nPROMPT = load_prompt("summarize")\n')
    assert audit_i18n.audit_path(py) == []


# ── audit: dir recursion + exit-code contract ───────────────────────────────

def test_audit_recurses_dir_and_skips_vendor(tmp_path: Path) -> None:
    """gather() recurses dirs and skips node_modules / vendor bundles."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.js").write_text('const i18n = { en: "x", fr: "y" };\n')
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text('const i18n = { en: "x", fr: "y" };\n')
    files = audit_i18n.gather([str(tmp_path)])
    names = {f.name for f in files}
    assert "a.js" in names and "lib.js" not in names  # vendor skipped


# ── make: scaffold / compile / loader ───────────────────────────────────────

def test_make_scaffolds_catalog_json_and_loader(tmp_path: Path) -> None:
    """A full make run writes i18n.yaml + i18n.json + i18n.js under locales/."""
    catalog = tmp_path / "locales" / "i18n.yaml"
    assert i18n_make.scaffold(catalog) is True
    i18n_make.compile_json(catalog)
    i18n_make.emit_loader(catalog)
    assert catalog.exists()
    data = json.loads((tmp_path / "locales" / "i18n.json").read_text())
    assert "gui" in data and "prompts" in data and data["locales"][0] == "en"
    js = (tmp_path / "locales" / "i18n.js").read_text()
    assert "export function t(" in js and "i18n.json" in js


def test_make_init_is_idempotent(tmp_path: Path) -> None:
    """``scaffold`` never clobbers an existing catalog (returns False)."""
    catalog = tmp_path / "locales" / "i18n.yaml"
    assert i18n_make.scaffold(catalog) is True
    catalog.write_text("locales: [en]\ngui:\n  x: {en: custom}\n")  # user edits
    assert i18n_make.scaffold(catalog) is False        # second run: no-op
    assert "custom" in catalog.read_text()             # user content preserved


def test_make_compile_is_deterministic(tmp_path: Path) -> None:
    """Compiling the same catalog twice yields byte-identical JSON (sorted keys)."""
    catalog = tmp_path / "locales" / "i18n.yaml"
    i18n_make.scaffold(catalog)
    a = i18n_make.compile_json(catalog).read_bytes()
    b = i18n_make.compile_json(catalog).read_bytes()
    assert a == b
