"""
test_single_llm — enforce the one-authorized-model rule.

House rule (absolute): the ONLY model the sprezzature skills use is ``qwen3-vl:8b``
(Qwen3-VL 8B, Q4_K_M) via Ollama. No other model tag, no MLX, anywhere in the
skill scripts — forever. This test makes that machine-checkable, the same way
the repo gates skill-spec conformance and Claude-trailer-free commits.

``qwen3-vl:8b`` is a vision-language model (VLM) that handles both text
generation (captions, alt text, narration, translation) and image understanding
(Ralph Eyeball Loop visual critique). It is the single model for all tasks —
see docs/LLM_CHOICE.md for the rationale and sources.

Scope: every ``sprezzature-*/scripts/*.py``. Not a VLM / LLM (allowed, unchecked):
whisper.cpp (captions), NeMo Sortformer/TitaNet (diarization), SHAP/DoWhy
(figures) — those are ASR / diarization / stats models, not the Ollama VLM.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Every shipped skill's Python scripts.
SCRIPTS = sorted(
    p for p in REPO_ROOT.glob("sprezzature-*/scripts/*.py")
    if "__pycache__" not in p.parts
)

#: Model families that are NOT the one authorized VLM. Any literal mention in a
#: skill script is a violation. ``qwen3-vl:8b`` is deliberately absent — it is
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


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_no_forbidden_model_tag(script: Path) -> None:
    """A skill script must not name any model tag other than qwen3-vl:8b."""
    text = script.read_text(encoding="utf-8")
    hits = sorted(set(FORBIDDEN_MODEL.findall(text)))
    assert not hits, (
        f"{script.relative_to(REPO_ROOT)} names non-authorized model tag(s) {hits}. "
        "The one authorized VLM is qwen3-vl:8b via Ollama (see docs/LLM_CHOICE.md)."
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_no_mlx_tag(script: Path) -> None:
    """A skill script must not name an MLX model tag (``…-mlx``)."""
    text = script.read_text(encoding="utf-8")
    hits = sorted(set(MLX_TAG.findall(text)))
    assert not hits, (
        f"{script.relative_to(REPO_ROOT)} names an MLX tag {hits}. No MLX — qwen3-vl:8b only."
    )


def test_authorized_vlm_is_the_declared_default() -> None:
    """The Ollama-backed scripts that declare a default model use qwen3-vl:8b."""
    # These are the scripts with a hard-coded default model constant.
    declarers = [
        REPO_ROOT / "sprezzature-vision" / "scripts" / "alt_from_ollama.py",
        REPO_ROOT / "sprezzature-vision" / "scripts" / "install_alt_ai.py",
        REPO_ROOT / "sprezzature-publish" / "scripts" / "_ollama.py",
        REPO_ROOT / "sprezzature-audio" / "scripts" / "name_from_transcript.py",
        REPO_ROOT / "sprezzature-audio" / "scripts" / "translate_captions.py",
        REPO_ROOT / "sprezzature-publish" / "scripts" / "narrate_post.py",
        REPO_ROOT / "sprezzature-figures" / "scripts" / "ralph_eyeball_loop.py",
    ]
    for script in declarers:
        assert '"qwen3-vl:8b"' in script.read_text(encoding="utf-8"), (
            f"{script.relative_to(REPO_ROOT)} must declare qwen3-vl:8b as its default model."
        )


#: The Ollama VLM scripts. The model is fixed at qwen3-vl:8b for all of them —
#: none may expose a user-facing switch to pick a different model. (whisper.cpp
#: ``--model`` in sprezzature-audio/captions is an ASR model, not the VLM, so it is
#: intentionally NOT in this list.)
LLM_SCRIPTS = [
    REPO_ROOT / "sprezzature-vision" / "scripts" / "alt_from_ollama.py",
    REPO_ROOT / "sprezzature-vision" / "scripts" / "install_alt_ai.py",
    REPO_ROOT / "sprezzature-audio" / "scripts" / "name_from_transcript.py",
    REPO_ROOT / "sprezzature-audio" / "scripts" / "translate_captions.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "plain_language.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "meta_from_ollama.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "narrate_post.py",
]

#: An option-definition literal that would expose the LLM model on the command
#: line — click ``@click.option("--model"...)`` or argparse
#: ``add_argument("--model"...)`` / ``"--ai-hints-model"``. Prose mentions and
#: internal ``model=`` kwargs are fine; a *defined CLI flag* is the violation.
_MODEL_FLAG = re.compile(r'"--(?:model|ai-hints-model)"')


@pytest.mark.parametrize("script", LLM_SCRIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_vlm_model_is_not_user_selectable(script: Path) -> None:
    """No VLM script may expose a ``--model`` (or ``--ai-hints-model``) CLI flag.

    The one authorized VLM is qwen3-vl:8b, fixed — not a knob. ``OLLAMA_MODEL``
    survives only as a bare test seam (env var, never a documented user option).
    """
    text = script.read_text(encoding="utf-8")
    assert not _MODEL_FLAG.search(text), (
        f"{script.relative_to(REPO_ROOT)} defines a user-facing model flag. "
        "The VLM is fixed at qwen3-vl:8b — remove the --model / --ai-hints-model option."
    )


@pytest.mark.parametrize(
    "skill_md",
    sorted(REPO_ROOT.glob("sprezzature-*/SKILL.md")),
    ids=lambda p: p.parent.name,
)
def test_skill_description_advertises_no_model_override(skill_md: Path) -> None:
    """A skill's ``description:`` frontmatter must not advertise a model override.

    The user-facing contract is one model, qwen3-vl:8b. A description that
    dangles ``OLLAMA_MODEL`` / ``--model`` as an override contradicts the lock
    and is the exact drift this gate prevents (see the v0.25.0 assessment).
    """
    text = skill_md.read_text(encoding="utf-8")
    # Isolate the YAML ``description:`` block (up to the next top-level key).
    m = re.search(r"(?ms)^description:\s*>-?\n(.*?)^\w[\w-]*:", text)
    description = m.group(1) if m else ""
    for needle in ("OLLAMA_MODEL", "--model"):
        assert needle not in description, (
            f"{skill_md.relative_to(REPO_ROOT)} description advertises {needle!r}. "
            "The model is fixed at qwen3-vl:8b — do not surface an override in the description."
        )
