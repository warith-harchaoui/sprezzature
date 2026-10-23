"""
The shop window is audited by the tools it sells.

``test_the_site_holds_together.py`` says, in its own docstring, that
accessibility rules live in ``sprezzature-accessibility``'s linter and
contrast in ``sprezzature-colors``, and that it owns only the plumbing those
two assume. That sentence was true and nothing followed from it: neither
linter had ever been pointed at ``web/``. The delegation was real, the hand-off
was not.

Run by hand on 2026-10-23, the a11y linter found nothing and the Laws of UX
auditor found six, all six on the one page every other guard exempts --
``vision.html``, the merge notice, whose two links had no focus ring and whose
call to action had no 44-pixel hit area. A page that every check steps around
is where quality goes to drop.

The linters are imported from the sibling checkouts rather than from an
install, because that is what CI has: ``scripts/fetch_siblings.sh`` fetches
``/sprezzature_*/`` and ``/scripts/`` for each brick. A machine with neither
skips, and the companion at the bottom refuses to let the whole file go quiet
that way.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)


def _brick(name: str) -> Path | None:
    """A sibling checkout holding an importable package, or ``None``."""
    repo = REPO_ROOT.parent / name
    package = repo / name.replace("-", "_")
    return repo if (package / "__init__.py").is_file() else None


def _import_from(brick: str, module: str):
    """Import a brick's package from its checkout, not from site-packages.

    An editable install of a brick can be months behind its repository -- five
    of them were on 2026-10-23, and one of those gaps hid the console script
    the brick's own SKILL.md tells an agent to call. Reading the checkout means
    this test audits the code in the tree it is run against.
    """
    repo = _brick(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}; run scripts/fetch_siblings.sh")
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    return __import__(module, fromlist=["*"])


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_passes_the_accessibility_linter(page: Path) -> None:
    """Twenty static rules, run over the site that advertises them."""
    lint = _import_from("sprezzature-accessibility", "sprezzature_accessibility")
    findings = lint.lint_file(page)
    assert not findings, (
        f"{page.relative_to(WEB)}: "
        + "; ".join(f"L{f.line} [{f.rule}] {f.message}" for f in findings)
    )


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_passes_the_laws_of_ux_auditor(page: Path) -> None:
    """The decidable fraction of the canonical Laws of UX, same idea."""
    laws = _import_from("sprezzature-ux-laws", "sprezzature_ux_laws")
    findings = laws.audit_file(page)
    assert not findings, (
        f"{page.relative_to(WEB)}: "
        + "; ".join(f"L{f.line} [{f.law}] {f.message}" for f in findings)
    )


def test_the_linters_are_not_blind() -> None:
    """Both tools fire on markup that is wrong, so a clean site means something.

    Without this the file is two hundred assertions that an empty list is
    empty, and an import that silently returned a stub would read as a site
    with nothing wrong with it.
    """
    lint = _import_from("sprezzature-accessibility", "sprezzature_accessibility")
    laws = _import_from("sprezzature-ux-laws", "sprezzature_ux_laws")
    broken = (
        "<!doctype html><html><head><title>x</title></head><body>"
        '<img src="a.png">'
        '<div onclick="go()">click me</div>'
        "<h1>A</h1><h3>B</h3>"
        "</body></html>"
    )
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "broken.html"
        page.write_text(broken, encoding="utf-8")
        a11y = lint.lint_file(page)
        ux = laws.audit_file(page)
    rules = {f.rule for f in a11y}
    assert {"img-missing-alt", "html-missing-lang"} <= rules, sorted(rules)
    assert ux, "the Laws of UX auditor found nothing in markup written to break it"


def test_there_are_pages_to_check() -> None:
    """A glob that stops matching would make everything above vacuous."""
    assert len(_PAGES) >= 30, [p.name for p in _PAGES]
