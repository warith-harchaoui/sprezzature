"""
test_prompts — regression tests for the YAML-backed prompts.

Each Ollama-backed script delegates its prompt construction to a YAML
file under <skill>/scripts/prompts/. These tests assert that:

1. The YAML loader (`_prompts.load_prompt`) can read each file using
   the stdlib fallback (PyYAML is optional).
2. The resulting prompt strings contain the field substitutions the
   script promised to the model.

No Ollama call is made — these tests are pure string assembly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLISH_SCRIPTS = REPO_ROOT / "sprezzature-publish" / "scripts"
A11Y_SCRIPTS = REPO_ROOT / "sprezzature-accessibility" / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _add_publish_scripts_to_path() -> None:
    sys.path.insert(0, str(PUBLISH_SCRIPTS))
    sys.path.insert(0, str(A11Y_SCRIPTS))


# ── YAML files load cleanly ─────────────────────────────────────────────────

@pytest.mark.parametrize(
    "skill, name, must_contain",
    [
        # sprezzature-publish prompts
        ("sprezzature-publish", "mermaid_labels",          "Reply with a JSON array"),
        ("sprezzature-publish", "latex_caption",           "Plain UTF-8 text"),
        ("sprezzature-publish", "plain_language_rewrite",  "Reply with the rewritten text only"),
        ("sprezzature-publish", "meta_tags_json",          "Return a single JSON object"),
        # sprezzature-vision alt-text prompts (short + long)
        ("sprezzature-vision",  "alt_short_default",       "Reply with the alt text only"),
        ("sprezzature-vision",  "alt_short_informative",   "informative image"),
        ("sprezzature-vision",  "alt_short_functional",    "action or destination"),
        ("sprezzature-vision",  "alt_short_text",          "verbatim"),
        ("sprezzature-vision",  "alt_short_complex",       "complex image"),
        ("sprezzature-vision",  "alt_short_group",         "group of images"),
        ("sprezzature-vision",  "alt_long_complex",        "Markdown"),
        ("sprezzature-vision",  "alt_long_group",          "group of related images"),
        ("sprezzature-vision",  "alt_long_default",        "long-form description"),
    ],
)
def test_prompt_yaml_loads(skill: str, name: str, must_contain: str) -> None:
    """Every prompt YAML the project ships parses and exposes its contract."""
    from _prompts import load_prompt  # type: ignore
    prompts_dir = REPO_ROOT / skill / "scripts" / "prompts"
    data = load_prompt(name, prompts_dir=prompts_dir)
    assert "template" in data
    haystack = data.get("output_contract", "") + data["template"] + data.get("task", "")
    assert must_contain in haystack


# ── plain_language.build_prompt ─────────────────────────────────────────────

def test_plain_language_build_prompt_substitutes_runtime_fields() -> None:
    from plain_language import build_prompt  # type: ignore
    out = build_prompt(
        text="Marketing seamlessly boosts revenue.",
        grade=8,
        lang="en",
        preserve=["Sprezzature"],
    )
    assert "grade-8" in out
    assert "Marketing seamlessly boosts revenue." in out
    assert "Keep these tokens verbatim" in out
    assert "Sprezzature" in out
    # The banned-word list lives in the YAML and must reach the prompt.
    assert "world-class" in out


def test_plain_language_build_prompt_without_preserve_omits_clause() -> None:
    from plain_language import build_prompt  # type: ignore
    out = build_prompt(text="Hello.", grade=8, lang="en", preserve=[])
    assert "Keep these tokens verbatim" not in out


# ── meta_from_ollama.build_prompt ───────────────────────────────────────────

def test_meta_build_prompt_includes_brand_goal_blocks_when_supplied() -> None:
    from meta_from_ollama import build_prompt  # type: ignore
    out = build_prompt(
        goal="Landing page for a small ML lab",
        page_text="",
        site_name="4ml",
        lang="en",
    )
    assert "Brand / site name: 4ml" in out
    assert "Page goal: Landing page for a small ML lab" in out
    assert "Return a single JSON object" in out
    assert "Write the JSON now." in out


def test_meta_build_prompt_omits_blocks_when_empty() -> None:
    from meta_from_ollama import build_prompt  # type: ignore
    out = build_prompt(goal="", page_text="", site_name="", lang="en")
    assert "Brand / site name" not in out
    assert "Page goal" not in out
    assert "Return a single JSON object" in out
    assert "Write the JSON now." in out


# ── alt_from_ollama.prompt_for + long_prompt_for ───────────────────────────

@pytest.mark.parametrize(
    "kind, must_contain",
    [
        ("informative", "informative image"),
        ("functional",  "link or button"),
        ("text",        "verbatim"),
        ("complex",     "complex image"),
        ("group",       "group of images"),
        ("decorative",  "Write alt text for this image"),  # falls through to default
    ],
)
def test_alt_short_prompt_per_kind(kind: str, must_contain: str) -> None:
    from alt_from_ollama import prompt_for  # type: ignore
    out = prompt_for(kind=kind, lang="en", context="A dashboard tile")
    assert "Write the alt text in English." in out
    assert must_contain in out


def test_alt_short_text_kind_skips_base_rules() -> None:
    """The `text` purpose extracts verbatim text; generic rules don't apply."""
    from alt_from_ollama import prompt_for  # type: ignore
    out = prompt_for(kind="text", lang="en", context="")
    # The "do not start with image of" rule belongs to the generic kinds.
    assert "Do not start with 'image of'" not in out
    assert "verbatim" in out


@pytest.mark.parametrize(
    "kind, must_contain",
    [
        ("complex", "chart type / diagram type"),
        ("group",   "group of related images"),
        ("other",   "long-form description"),  # falls through to default
    ],
)
def test_alt_long_prompt_per_kind(kind: str, must_contain: str) -> None:
    from alt_from_ollama import long_prompt_for  # type: ignore
    out = long_prompt_for(kind=kind, lang="en", context="")
    assert must_contain in out


def test_alt_prompt_substitutes_context_when_supplied() -> None:
    from alt_from_ollama import prompt_for  # type: ignore
    out = prompt_for(kind="informative", lang="en", context="Hero image of the homepage")
    assert "Page context: Hero image of the homepage." in out


def test_alt_prompt_omits_context_block_when_empty() -> None:
    from alt_from_ollama import prompt_for  # type: ignore
    out = prompt_for(kind="informative", lang="en", context="")
    assert "Page context:" not in out
