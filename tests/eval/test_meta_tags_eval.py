"""
test_meta_tags_eval — opt-in checks for ``meta_from_ollama``.

Runs the CLI against five hand-picked HTML fixtures (landing, article,
product, profile, faq) and asserts on the structure of the JSON output.
Run with::

    pytest -m eval

Skips cleanly when Ollama or the chosen model is unavailable.

Assertions, per ``.private/tests.md``:

- The output is parseable JSON with every required key present.
- ``title`` ≤ 60 characters.
- ``description`` between 100 and 155 characters.
- ``og_title`` is approximately ``title`` minus the brand suffix.
- ``schema_type`` matches the page kind.
- ``keywords_hint`` length 3–8.

The expected ``schema_type`` per kind is a small mapping:

==========  =================================
kind        acceptable schema_type values
==========  =================================
landing     WebSite, WebPage
article     Article, BlogPosting, NewsArticle
product     Product, ItemPage
profile     Person, ProfilePage
faq         FAQPage
==========  =================================

The list is permissive on purpose — different Schema.org types are
defensible for the same page kind, and we are protecting against the
model returning a wildly wrong type, not relitigating SEO guidance.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import meta_from_ollama  # noqa: E402 — via tests/conftest.py sys.path

pytestmark = pytest.mark.eval


# Schema.org @type values we accept per fixture kind. Any one match is fine.
SCHEMA_TYPES_BY_KIND: dict[str, set[str]] = {
    "landing": {"WebSite", "WebPage", "Organization"},
    "article": {"Article", "BlogPosting", "NewsArticle", "TechArticle"},
    "product": {"Product", "ItemPage"},
    "profile": {"Person", "ProfilePage", "AboutPage"},
    "faq": {"FAQPage"},
}


def _run_meta_cli(eval_repo_root: Path, html_path: Path, *, lang: str = "en") -> dict:
    """
    Invoke ``meta_from_ollama`` as a subprocess and return the parsed JSON.

    Subprocess (rather than calling ``main()`` in-process) keeps each
    test isolated from the module's mutable globals (``NO_CACHE``).
    """
    script = eval_repo_root / "sprezzature-publish" / "scripts" / "meta_from_ollama.py"
    proc = subprocess.run(
        [sys.executable, str(script), str(html_path), "--lang", lang, "--no-cache"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"meta_from_ollama exited {proc.returncode}\nstderr:\n{proc.stderr}\n"
            f"stdout:\n{proc.stdout}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"meta_from_ollama stdout is not JSON: {e}\nraw:\n{proc.stdout}")


@pytest.mark.parametrize("kind", ["landing", "article", "product", "profile", "faq"])
def test_meta_tag_shape(
    kind: str,
    html_fixture,
    eval_repo_root,
    ollama_available,
    require_model,
) -> None:
    """End-to-end: run the CLI, parse stdout, assert on every constraint."""
    model = meta_from_ollama.pick_default_model()
    require_model(model)

    html = html_fixture(kind)
    data: dict = _run_meta_cli(eval_repo_root, html)

    # Required keys — anything missing here is a hard fail before the
    # finer-grained checks. Names mirror what ``build_prompt`` asks for.
    required = ("title", "description", "schema_type")
    missing = [k for k in required if k not in data]
    assert not missing, f"Missing required keys {missing} in: {data}"

    # title ≤ 60 chars
    title: str = (data.get("title") or "").strip()
    assert title, "title is empty"
    assert len(title) <= 60, f"title exceeds 60 chars ({len(title)}): {title!r}"

    # description 100..155 chars — Google's SERP truncation window.
    desc: str = (data.get("description") or "").strip()
    assert 100 <= len(desc) <= 155, (
        f"description length {len(desc)} outside 100..155: {desc!r}"
    )

    # schema_type matches the page kind. Compare case-insensitively
    # against the accepted set for this kind.
    schema_type: str = (data.get("schema_type") or "").strip()
    accepted = SCHEMA_TYPES_BY_KIND[kind]
    accepted_lower = {s.lower() for s in accepted}
    assert schema_type.lower() in accepted_lower, (
        f"schema_type {schema_type!r} not in expected {sorted(accepted)} for kind={kind}"
    )

    # og_title — when present, should approximate the title (case-insensitive
    # substring either way handles the "title minus brand" pattern).
    og_title: str = (data.get("og_title") or "").strip()
    if og_title:
        a, b = og_title.lower(), title.lower()
        assert a in b or b in a or any(
            tok in b for tok in a.split() if len(tok) > 4
        ), f"og_title {og_title!r} bears no resemblance to title {title!r}"

    # keywords_hint length 3..8 — when present.
    keywords = data.get("keywords_hint")
    if keywords is not None:
        # Some models return a comma-separated string instead of a list;
        # normalise both shapes.
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        assert isinstance(keywords, list), f"keywords_hint must be a list, got {type(keywords)}"
        assert 3 <= len(keywords) <= 8, (
            f"keywords_hint length {len(keywords)} outside 3..8: {keywords}"
        )
