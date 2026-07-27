"""
test_dogfood_audits — run every shipped template through its compatible auditor.

The claim "each skill makes artifacts and audits them" only holds if our own
shipped artifacts pass our own auditors. This test dogfoods them:

* every shipped HTML template (sprezzature-ui components / snippets / starter page and
  the cli-gui demo page) must lint clean under ``sprezzature-accessibility`` — zero
  findings;
* every shipped figure spec (``sprezzature-figures/assets/vega-examples/*.json``) must
  raise **no error-severity** findings from the figure auditor (warnings are
  advisory nudges, not gate failures).

All checks are static and fast, so this runs in full in CI (the "light" tier is
the same as local — there is nothing heavy to defer). Intentionally-broken
linter fixtures under ``tests/fixtures/`` are excluded on purpose.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "sprezzature-accessibility" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "sprezzature-figures" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "sprezzature-ux-laws" / "scripts"))
import audit_figure as af  # noqa: E402
import audit_laws_of_ux as ux  # noqa: E402
from lint_a11y import lint_file  # noqa: E402


# ── Shipped HTML templates → sprezzature-accessibility (0 findings) ───────────────

def _shipped_html() -> list[Path]:
    """Every shipped HTML template we author — excludes the deliberately-broken
    linter fixtures under tests/fixtures/."""
    roots = [
        REPO_ROOT / "sprezzature-ui" / "assets",
        REPO_ROOT / "sprezzature-cli-gui" / "assets" / "examples",
    ]
    out: list[Path] = []
    for root in roots:
        out.extend(sorted(root.rglob("*.html")))
    return out


HTML_TEMPLATES = _shipped_html()


def test_html_templates_discovered() -> None:
    """Guard: the discovery actually found templates (a moved dir shouldn't
    silently make this test vacuous)."""
    assert len(HTML_TEMPLATES) >= 10


@pytest.mark.parametrize("path", HTML_TEMPLATES, ids=lambda p: p.name)
def test_shipped_html_template_lints_clean(path: Path) -> None:
    """Every shipped HTML template passes the static a11y lint with 0 findings."""
    findings = lint_file(path, set())
    assert findings == [], (
        f"{path.relative_to(REPO_ROOT)} has {len(findings)} a11y finding(s): "
        + "; ".join(f"{f.rule}" for f in findings)
    )


# ── Shipped figure specs → sprezzature-figures auditor (0 errors) ─────────────────

FIGURE_SPECS = sorted((REPO_ROOT / "sprezzature-figures" / "assets" / "vega-examples").glob("*.json"))


def test_figure_specs_discovered() -> None:
    """Guard: the vega-examples directory is non-empty."""
    assert len(FIGURE_SPECS) >= 20


@pytest.mark.parametrize("path", FIGURE_SPECS, ids=lambda p: p.name)
def test_shipped_figure_spec_has_no_audit_errors(path: Path) -> None:
    """Every shipped figure spec raises no error-severity audit findings."""
    spec = json.loads(path.read_text(encoding="utf-8"))
    errors = [f for f in af.rules_for_vega(spec, str(path)) if f["severity"] == "error"]
    assert errors == [], (
        f"{path.name} has audit error(s): " + "; ".join(f["rule"] for f in errors)
    )


# ── Shipped HTML templates → sprezzature-ux-laws (no error-severity findings) ──────

@pytest.mark.parametrize("path", HTML_TEMPLATES, ids=lambda p: p.name)
def test_shipped_html_template_has_no_ux_law_errors(path: Path) -> None:
    """Every shipped HTML template passes the Laws-of-UX audit with no
    error-severity findings (hard violations). Warnings are advisory nudges and
    are not gated here."""
    findings = ux.audit_file(path, set(ux.LAW_REGISTRY))
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], (
        f"{path.relative_to(REPO_ROOT)} has UX-law error(s): "
        + "; ".join(f"{f.law}@{f.line}" for f in errors)
    )


def test_labelled_control_span_is_not_a_fake_button() -> None:
    """A styled <span> inside a <label> that holds a real <input> (the accessible
    segmented-control pattern) must NOT be flagged as a fake button by jakob."""
    from audit_laws_of_ux import Walker, check_jakob  # noqa: E402
    html = (
        '<label><input type="radio" name="fmt" value="png" class="peer sr-only">'
        '<span class="cursor-pointer">PNG</span></label>'
    )
    walker = Walker()
    walker.feed(html)
    findings = check_jakob(walker, "seg.html")
    assert [f for f in findings if f.law == "jakob"] == []
