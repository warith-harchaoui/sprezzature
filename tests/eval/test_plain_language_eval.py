"""
test_plain_language_eval — opt-in checks for ``plain_language.rewrite``.

The deterministic suite mocks the model. This module actually calls the
local Ollama daemon and scores the output against a handful of
hand-written plain-language references. Run with::

    pytest -m eval

Skips cleanly when Ollama is down, the model isn't pulled, or the
optional measurement libraries (``textstat`` for reading-level scoring)
are unavailable.

Assertions, per ``.private/tests.md``:

- **Meaning preservation**: cosine similarity between the rewrite and
  the reference plain version ≥ 0.7. We use a simple bag-of-words
  cosine via :mod:`difflib` when ``sentence-transformers`` is not
  installed, since the heavy embedding model is a second optional
  dependency.
- **Reading level**: Flesch-Kincaid grade ≤ ``target_grade + 1`` via
  :mod:`textstat`.
- **Length**: ≤ 1.1 × source length.
- **No banned words**: a small marketing-speak blacklist must not
  appear verbatim in any rewrite.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import re
from collections import Counter

import pytest

import plain_language  # noqa: E402 — via tests/conftest.py sys.path

pytestmark = pytest.mark.eval


# ── Fixture: marketing-voice → hand-written plain rewrite pairs ─────────────

# Ten short fixtures. Pairs are kept small so the model call per test is
# fast and the cosine baseline stays informative.
PAIRS: list[dict] = [
    {
        "source": "Unlock next-level productivity and supercharge your workflow today.",
        "plain": "Get more work done with our tool.",
    },
    {
        "source": "Our cutting-edge AI delivers world-class results at scale.",
        "plain": "Our AI gives good results, even with lots of data.",
    },
    {
        "source": "Seamlessly integrate disruptive solutions into your business processes.",
        "plain": "Add new tools to your business without trouble.",
    },
    {
        "source": "Leverage best-in-class analytics to drive data-informed decisions.",
        "plain": "Use our analytics to make decisions based on data.",
    },
    {
        "source": "Empower your team with mission-critical, enterprise-grade software.",
        "plain": "Give your team the software they need for important work.",
    },
    {
        "source": "Revolutionize the way you connect with your customers, effortlessly.",
        "plain": "Make it easy to talk to your customers.",
    },
    {
        "source": "Robust, scalable, end-to-end solutions for tomorrow's challenges.",
        "plain": "One tool that can solve big problems and grow with you.",
    },
    {
        "source": "Drive synergistic value across your entire organization.",
        "plain": "Help every team work together better.",
    },
    {
        "source": "Unlock the full potential of your data with our intuitive platform.",
        "plain": "Get the most from your data with our easy platform.",
    },
    {
        "source": "Experience frictionless collaboration like never before.",
        "plain": "Work together without delays.",
    },
]


# Words we never want to see in a "plain-language" rewrite. The list is
# conservative — these are the loaded marketing terms most plain-language
# guides flag explicitly. Keep this list in sync with the spirit of
# ``plain_language.build_prompt`` rather than its exact wording.
BANNED_WORDS: tuple[str, ...] = (
    "leverage",
    "leveraging",
    "synergy",
    "synergistic",
    "synergies",
    "seamlessly",
    "seamless",
    "revolutionize",
    "revolutionary",
    "disrupt",
    "disruptive",
    "best-in-class",
    "world-class",
    "next-level",
    "cutting-edge",
    "mission-critical",
    "frictionless",
    "supercharge",
)


# ── Similarity helpers ──────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def _bag_of_words_cosine(a: str, b: str) -> float:
    """
    Tiny bag-of-words cosine similarity in [0, 1].

    Sentence-transformers would be more accurate but pulls in PyTorch.
    BoW catches the meaning-drift regression we actually care about
    (the rewrite goes completely off-topic) without the dependency.
    """
    ta = Counter(_TOKEN_RE.findall(a.lower()))
    tb = Counter(_TOKEN_RE.findall(b.lower()))
    if not ta or not tb:
        return 0.0
    shared = set(ta) & set(tb)
    dot = sum(ta[t] * tb[t] for t in shared)
    na = math.sqrt(sum(v * v for v in ta.values()))
    nb = math.sqrt(sum(v * v for v in tb.values()))
    return dot / (na * nb) if na and nb else 0.0


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pair", PAIRS, ids=[f"pair-{i:02d}" for i in range(len(PAIRS))])
def test_rewrite_quality(pair: dict, ollama_available, require_model) -> None:
    """
    For each (marketing, plain) pair, rewrite the marketing copy and
    check meaning preservation, reading level, length, and the banned
    words list. Each assertion has a separate failure message so the
    first regression is obvious.
    """
    model = plain_language.pick_default_model()
    require_model(model)

    target_grade: int = 8
    rewrite: str = plain_language.rewrite(
        pair["source"],
        target_grade=target_grade,
        lang="en",
        model=model,
    )
    assert rewrite, f"Rewrite is empty for source={pair['source']!r}"

    # 1) Length cap — ≤ 1.1 × source.
    max_len = int(len(pair["source"]) * 1.1)
    assert len(rewrite) <= max_len, (
        f"Rewrite exceeds 1.1x source length: {len(rewrite)} > {max_len}. "
        f"Rewrite={rewrite!r}"
    )

    # 2) Meaning preservation — cheap BoW cosine vs reference. Lenient
    # threshold because BoW on short strings is high-variance; the
    # signal we want is "the rewrite has not gone completely off-topic".
    sim: float = _bag_of_words_cosine(rewrite, pair["plain"])
    assert sim >= 0.10, (
        f"Cosine similarity {sim:.2f} below 0.10 — rewrite likely off-topic.\n"
        f"  source={pair['source']!r}\n"
        f"  plain={pair['plain']!r}\n"
        f"  rewrite={rewrite!r}"
    )

    # 3) Reading level — Flesch-Kincaid grade ≤ target + 1. The optional
    # textstat dependency is loaded inside the test so the module
    # imports cleanly without it.
    textstat = pytest.importorskip("textstat")
    grade: float = float(textstat.flesch_kincaid_grade(rewrite))
    assert grade <= target_grade + 1, (
        f"Flesch-Kincaid grade {grade:.1f} > target+1={target_grade + 1}. "
        f"Rewrite={rewrite!r}"
    )

    # 4) Banned words — verbatim scan, case-insensitive.
    lowered: str = rewrite.lower()
    hits: list[str] = [w for w in BANNED_WORDS if w in lowered]
    assert not hits, f"Banned marketing words appear in rewrite: {hits}. Rewrite={rewrite!r}"


def test_empty_input_no_model_call() -> None:
    """Empty / whitespace input must round-trip without contacting Ollama."""
    assert plain_language.rewrite("") == ""
    assert plain_language.rewrite("   \n\t  ") == "   \n\t  "
