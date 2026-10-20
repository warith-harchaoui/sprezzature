"""
test_single_llm — enforce the one-authorized-model rule, where the code is.

House rule (absolute): the ONLY model the sprezzature skills use is ``qwen3-vl:8b``
(Qwen3-VL 8B, Q4_K_M) via Ollama. No other model tag, no MLX, anywhere in the
skill code — forever. This test makes that machine-checkable, the same way the
repo gates skill-spec conformance and Claude-trailer-free commits.

``qwen3-vl:8b`` is a vision-language model (VLM) that handles both text
generation (captions, alt text, narration, translation) and image understanding
(Ralph Eyeball Loop visual critique). It is the single model for all tasks —
see docs/LLM_CHOICE.md for the rationale and sources.

Why this file had stopped checking anything
-------------------------------------------
It globbed ``sprezzature-*/scripts/*.py`` **in this repository**. Every brick
took its code to its own package during the split, so that glob matches nothing
and the three parametrised tests collected zero cases each — "got empty
parameter set", which pytest reports as a skip and a reader takes for a pass. A
rule described as holding "forever" was enforced over an empty set for weeks.

The code is in the sibling checkouts, which is where this now looks: 418 files
across the nine bricks, their ``scripts/``, their package and their ``src/``.
``scripts/fetch_siblings.sh`` is what puts them there, in CI and in a clone that
has only this repository.

Scope: Python that ships. Not a VLM / LLM (allowed, unchecked): whisper.cpp
(captions), NeMo Sortformer / TitaNet (diarization), SHAP / DoWhy (figures) —
those are ASR / diarization / stats models, not the Ollama VLM.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent

#: Model families that are NOT the one authorized VLM. Any literal mention in
#: shipped code is a violation. ``qwen3-vl:8b`` is deliberately absent — it is
#: the only allowed tag. The negative lookahead ``(?!3-vl)`` allows ``qwen3-vl``
#: while banning every other Qwen variant (qwen2.5, qwen2.5vl, qwen3:8b,
#: qwen2.5-coder, …). Covers every model previously pulled or considered.
FORBIDDEN_MODEL = re.compile(
    r"\b(?:gemma4\w*|gemma3\w*|gemma2\w*|gemma\b|llava\w*|moondream\w*|"
    r"qwen(?!3-vl)[\d.]\w*|llama[\d.]*-?vision\w*|llama3[\d.:]*\w*|"
    r"mistral\w*|pixtral\w*|phi[\d]\w*|deepseek\w*|internvl\w*|minicpm\w*|nomic-embed\w*)\b",
    re.IGNORECASE,
)

#: A concrete ``model:tag-mlx`` literal (an MLX build). "No MLX" prose is fine;
#: an actual ``…-mlx`` tag is not.
MLX_TAG = re.compile(r"[\w.]+:[\w.]*-mlx\b", re.IGNORECASE)

#: The VLM path: everything that reaches a model does so through this helper,
#: which resolves tag and backend from ``SPREZZATURE_LLM_*``. Derived rather
#: than listed, because a hand-kept list of "the Ollama scripts" is what went
#: empty here — one entry at a time, each removal correct, the set silently
#: reaching zero.
VLM_ROUTE = re.compile(r"best_engine_ai_helper")

#: An option-definition literal that would expose the LLM model on the command
#: line — Click ``@click.option("--model"...)`` or argparse
#: ``add_argument("--model"...)`` / ``"--ai-hints-model"``. Prose mentions and
#: internal ``model=`` kwargs are fine; a *defined CLI flag* is the violation.
MODEL_FLAG = re.compile(r'"--(?:model|ai-hints-model)"')


def _sources(brick: str) -> list[Path]:
    """Python that `brick` ships: its scripts, its package, its ``src/``."""
    root = SIBLINGS / brick
    if not (root / "pyproject.toml").is_file():
        return []
    found = (
        set(root.glob("scripts/**/*.py"))
        | set(root.glob("sprezzature_*/**/*.py"))
        | set(root.glob("src/**/*.py"))
    )
    return sorted(
        p for p in found if "__pycache__" not in p.parts and "tests" not in p.parts
    )


def _all_sources() -> list[Path]:
    """Every brick's shipped Python, across the sibling checkouts."""
    return [p for brick in SHIPPED_SKILLS for p in _sources(brick)]


def test_there_is_code_to_scan() -> None:
    """A rule enforced over an empty set is the failure mode this file had.

    Skipped, loudly, when no brick is checked out beside this repository: that
    is a bare clone, and the pre-push hook says how many it can see. What this
    refuses is the other case — siblings present and the glob finding nothing,
    which is what happens when a package layout changes on one side only.
    """
    checkouts = [
        brick for brick in SHIPPED_SKILLS if (SIBLINGS / brick / "pyproject.toml").is_file()
    ]
    if not checkouts:
        pytest.skip(
            "no brick is checked out beside this repository; "
            "run scripts/fetch_siblings.sh to enforce the model rule"
        )
    empty = [brick for brick in checkouts if not _sources(brick)]
    assert not empty, (
        f"{empty} are checked out and ship no Python this test can find. Either "
        f"the package layout moved or the globs above stopped matching; both "
        f"make the model rule unenforced for those bricks."
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_no_forbidden_model_tag(brick: str) -> None:
    """Shipped code must not name any model tag other than qwen3-vl:8b."""
    sources = _sources(brick)
    if not sources:
        pytest.skip(f"{brick} is not checked out beside this repository")
    offences = [
        f"{p.relative_to(SIBLINGS)}: {sorted(set(hits))}"
        for p in sources
        if (hits := FORBIDDEN_MODEL.findall(p.read_text(encoding="utf-8", errors="replace")))
    ]
    assert not offences, (
        f"{brick} names non-authorized model tag(s). The one authorized VLM is "
        f"qwen3-vl:8b via Ollama (see docs/LLM_CHOICE.md):\n  "
        + "\n  ".join(offences)
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_no_mlx_tag(brick: str) -> None:
    """Shipped code must not name an MLX model tag (``…-mlx``)."""
    sources = _sources(brick)
    if not sources:
        pytest.skip(f"{brick} is not checked out beside this repository")
    offences = [
        f"{p.relative_to(SIBLINGS)}: {sorted(set(hits))}"
        for p in sources
        if (hits := MLX_TAG.findall(p.read_text(encoding="utf-8", errors="replace")))
    ]
    assert not offences, (
        f"{brick} names an MLX tag. No MLX — qwen3-vl:8b only:\n  "
        + "\n  ".join(offences)
    )


def test_the_vlm_model_is_not_user_selectable() -> None:
    """No file on the VLM path may expose a ``--model`` CLI flag.

    The one authorized VLM is fixed — not a knob. ``SPREZZATURE_LLM_*`` survives
    as a backend seam read by the helper, never as a documented user option.
    """
    sources = _all_sources()
    if not sources:
        pytest.skip("no brick is checked out beside this repository")
    on_the_path = [
        p for p in sources
        if VLM_ROUTE.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert on_the_path, (
        "nothing routes through best_engine_ai_helper any more. Either the LLM "
        "path was renamed — in which case VLM_ROUTE above is now blind — or the "
        "suite stopped calling a model at all."
    )
    offences = [
        str(p.relative_to(SIBLINGS))
        for p in on_the_path
        if MODEL_FLAG.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not offences, (
        f"{offences} define a user-facing model flag. The VLM is fixed at "
        f"qwen3-vl:8b — remove the --model / --ai-hints-model option."
    )


# ``test_authorized_vlm_is_the_declared_default`` stood here, over a list of the
# scripts that hard-coded a default model constant. Nothing declares one now:
# the tag and the backend are resolved inside best_engine_ai_helper from
# ``SPREZZATURE_LLM_*``, which is why `test_the_vlm_model_is_not_user_selectable`
# above asks its question of the files that reach the helper rather than of the
# files that used to name a model. Deleted rather than kept over an empty list —
# that is the shape this whole file was in.
