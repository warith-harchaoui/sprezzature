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

The engines are loaded from each brick's ``scripts/`` directory by file
path, not imported as packages. That is not a style choice: a sibling fetched
by ``scripts/fetch_siblings.sh`` is a *checkout*, and ``import
sprezzature_accessibility`` fails there with ``No module named
sprezzature_accessibility_scripts`` — the package name maps to ``scripts/``
through ``[tool.setuptools.package-dir]``, which only exists once something is
installed. Written against the editable installs on a developer's machine,
this file would have raised a collection error on every CI run. A machine with
no sibling checkout skips, and the companion at the bottom refuses to let the
whole file go quiet that way.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)


def _engine_path(brick: str, module: str) -> Path | None:
    """The brick's engine module in its checkout, or ``None`` if absent."""
    candidate = REPO_ROOT.parent / brick / "scripts" / f"{module}.py"
    return candidate if candidate.is_file() else None


#: Loaded engines, by brick. Module-scoped because each one inserts its own
#: ``scripts/`` directory on ``sys.path`` at import and then imports its
#: private helpers (``_argparse``, ``_lang``) by bare name. Those helpers are
#: deliberate duplicates kept byte-identical across the bricks -- which is what
#: ``tests/test_helper_sync.py`` is for -- so whichever copy lands in
#: ``sys.modules`` first serves the rest, and loading twice would only pay the
#: cost again.
_LOADED: dict[str, object] = {}


def _engine(brick: str, module: str):
    """Load a brick's engine from its checkout, by file path.

    Not ``import sprezzature_accessibility``: a sibling fetched by
    ``fetch_siblings.sh`` is a checkout, and that package's ``__init__``
    re-exports from ``sprezzature_accessibility_scripts``, a name that only
    resolves once the distribution is installed. The engine itself is a plain
    module in ``scripts/``, which is one of the paths the fetch brings.

    Reading the checkout rather than an install also means this audits the
    code in the tree it is run against. Five editable installs on this machine
    were months behind their repositories on 2026-10-23, and one of those gaps
    hid the console script the brick's own SKILL.md tells an agent to call.
    """
    if brick in _LOADED:
        return _LOADED[brick]
    path = _engine_path(brick, module)
    if path is None:
        pytest.skip(f"no checkout for {brick}; run scripts/fetch_siblings.sh")
    name = f"_engine_{module}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    engine = importlib.util.module_from_spec(spec)
    # Registered before execution, not after: both engines define
    # dataclasses, and `@dataclass` resolves its own module through
    # `sys.modules[cls.__module__]`. With the entry missing that lookup
    # returns None and the decorator dies on `None.__dict__`, several frames
    # away from anything that mentions importing.
    sys.modules[name] = engine
    spec.loader.exec_module(engine)
    _LOADED[brick] = engine
    return engine


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_passes_the_accessibility_linter(page: Path) -> None:
    """Twenty static rules, run over the site that advertises them."""
    lint = _engine("sprezzature-accessibility", "lint_a11y")
    findings = lint.lint_file(page)
    assert not findings, (
        f"{page.relative_to(WEB)}: "
        + "; ".join(f"L{f.line} [{f.rule}] {f.message}" for f in findings)
    )


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_passes_the_laws_of_ux_auditor(page: Path) -> None:
    """The decidable fraction of the canonical Laws of UX, same idea."""
    laws = _engine("sprezzature-ux-laws", "audit_laws_of_ux")
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
    lint = _engine("sprezzature-accessibility", "lint_a11y")
    laws = _engine("sprezzature-ux-laws", "audit_laws_of_ux")
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


def test_this_run_had_both_engines_to_run() -> None:
    """A file that skipped every case reads exactly like a file that passed."""
    missing = [
        brick
        for brick, module in (
            ("sprezzature-accessibility", "lint_a11y"),
            ("sprezzature-ux-laws", "audit_laws_of_ux"),
        )
        if _engine_path(brick, module) is None
    ]
    if missing:
        pytest.skip(
            f"no checkout for {missing}; CI runs scripts/fetch_siblings.sh first"
        )
    assert _LOADED, "both checkouts are here and neither engine was loaded"
