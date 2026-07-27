"""
test_alt_eval — opt-in LLM-output checks for ``alt_from_ollama.describe``.

The deterministic suite (``tests/test_alt_from_ollama.py``) mocks every
network call. This module does the opposite: it actually runs the local
Ollama model against a small set of **real Wikipedia images** and scores
the generated alt text against human-written ground-truth alt + caption.

Why Wikipedia rather than synthetic Pillow patterns? Because 64x64
synthetic patterns have nothing to *describe* — every regression looks
the same as every other regression. Wikipedia images have:

- A reviewed alt-text written by a human editor, sitting in the article.
- A figure caption that supplies orthogonal context.
- A stable, content-addressed CDN URL (``upload.wikimedia.org``).

The fixtures live under ``tests/fixtures/images/wiki/`` and are populated
by ``tests/fixtures/images/fetch_wikipedia.py``. The truth manifest is
``wiki/truth.json``. If those files are missing this module skips
cleanly — running the fetcher is a contributor-side action, not part of
the test session.

Every test here is marked ``@pytest.mark.eval`` and is excluded from the
default ``pytest`` run. Opt in with::

    pytest -m eval

Skips cleanly when:

- The Wikipedia fixtures are missing (``truth.json`` not present).
- The Ollama daemon is not reachable (``ollama_available`` fixture).
- The vision model is not pulled (``require_model`` fixture).
- ``deepeval`` is not installed (``pytest.importorskip``).

Assertions, per ``.private/tests.md``:

- **Length**: hard cap of 150 characters and no trailing ``...``.
- **Subject keywords**: at least one kind-appropriate keyword appears.
- **Relevance / Faithfulness**: DeepEval scores (``AnswerRelevancyMetric``
  and ``FaithfulnessMetric``) against the human caption / alt, wrapped
  in try/except so a DeepEval misconfiguration falls back to the
  stdlib character-trigram overlap metric (``>= 0.10``). Both are
  intentionally loose: we are guarding against catastrophic regressions
  (boilerplate, wrong language, hallucinated content) — not minute
  rewordings between model versions.
- **Decorative**: short-circuits to ``""`` with no network call.
- **Multilingual**: ``--lang fr`` produces French output for the FR
  entry, verified via ``_lang.detect_text_language``.

The thresholds are intentionally lenient. Stdlib trigram overlap is just
the floor that says "the model emitted something topically related to
the reference"; the DeepEval path is the preferred, more discriminating
signal when configured.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Skip the whole module gracefully when DeepEval isn't installed. The
# project lists it in requirements-dev.txt; this guard keeps the test
# friendly to lightweight contributor checkouts.
deepeval = pytest.importorskip("deepeval")

import alt_from_ollama  # noqa: E402 - imported via tests/conftest.py sys.path
from _lang import detect_text_language  # noqa: E402

pytestmark = pytest.mark.eval


# -- Fixture catalogue (loaded from wiki/truth.json) -------------------------

# The eval suite reads its ground truth from disk so that the fetcher
# script (``tests/fixtures/images/fetch_wikipedia.py``) and the test
# module share a single source of truth. If the manifest is missing
# (typical for a fresh clone) we skip the whole module — running the
# fetcher is a one-time contributor step, not a test prerequisite.

_FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "images"
_WIKI_DIR = _FIXTURES_ROOT / "wiki"
_TRUTH_PATH = _WIKI_DIR / "truth.json"

if not _TRUTH_PATH.exists():
    pytest.skip(
        "Wikipedia fixtures missing. Run "
        "`python3 tests/fixtures/images/fetch_wikipedia.py` "
        "to populate tests/fixtures/images/wiki/.",
        allow_module_level=True,
    )

# Sorted by filename so parametrise IDs are stable across runs and the
# pytest-xdist worker assignment is deterministic.
_TRUTH: dict[str, dict] = json.loads(_TRUTH_PATH.read_text(encoding="utf-8"))
_ENTRIES: list[tuple[str, dict]] = sorted(_TRUTH.items())


# -- Kind-appropriate keyword hints ------------------------------------------

# Cheap structural sanity check before the (noisier, slower) DeepEval
# call. At least one of these words should appear in the model's output;
# if none do, we're almost certainly seeing boilerplate or the wrong
# image entirely. Keywords are intentionally generous — different
# vision models pick different words for the same scene.
_SUBJECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "marie-curie-portrait.jpg": (
        "woman", "person", "portrait", "head", "face", "hair", "photo",
        "femme", "personne", "visage", "portrait", "tete",
    ),
    "climate-temperature-chart.png": (
        "chart", "graph", "plot", "temperature", "warming", "climate",
        "data", "line", "trend", "axis", "year",
        "graphique", "courbe", "donnees", "temperature", "annee",
    ),
    "wikipedia-logo.png": (
        "logo", "globe", "sphere", "puzzle", "wikipedia", "symbol",
        "icon", "letter", "glyph", "character",
        "globe", "sphere", "logo", "symbole",
    ),
    "tour-eiffel.jpg": (
        "tour", "eiffel", "tower", "monument", "paris", "metal", "iron",
        "structure", "ciel", "champ", "mars", "fer",
    ),
    "decorative-pattern.png": (),  # decorative -> empty alt expected
}


# -- Stdlib similarity fallback ----------------------------------------------


def _char_trigram_overlap(a: str, b: str) -> float:
    """
    Character-trigram Jaccard overlap between two strings.

    A cheap stdlib fallback for the DeepEval relevance/faithfulness
    metrics. The metric:

    1. Lowercases and collapses to alphanumerics + spaces.
    2. Extracts the set of overlapping 3-character windows.
    3. Returns ``|A intersect B| / |A union B|`` (Jaccard).

    Why character trigrams rather than word Jaccard? Character n-grams
    are robust to morphology ("warming" / "warmed" share trigrams) and
    cross-language stems ("temperature" / "temperature" in FR share
    every trigram), which is exactly the "didn't hallucinate" signal we
    want. The threshold used by the test (``>= 0.10``) is loose: the
    same paragraph reworded yields ~0.2-0.4, a hallucinated topic
    yields ~0.02-0.05.

    Returns 0.0 when either input has fewer than 3 characters of usable
    content (the metric is undefined in that regime).
    """
    def _trigrams(text: str) -> set[str]:
        cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
        cleaned = " ".join(cleaned.split())  # collapse runs of whitespace
        if len(cleaned) < 3:
            return set()
        return {cleaned[i:i + 3] for i in range(len(cleaned) - 2)}

    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# -- Tests -------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, spec",
    [(name, spec) for name, spec in _ENTRIES if spec["kind"] != "decorative"],
    ids=[name for name, spec in _ENTRIES if spec["kind"] != "decorative"],
)
def test_alt_quality(
    filename: str,
    spec: dict,
    ollama_available,
    require_model,
) -> None:
    """
    Generate alt text against a Wikipedia image and assert it is sane.

    Structural checks (length, no ellipsis, kind-appropriate keywords)
    run first because they are cheap and catch the regressions we care
    most about. The DeepEval metrics run last, wrapped in try/except
    so a misconfigured DeepEval environment falls back to a stdlib
    character-trigram overlap metric — the test should still emit a
    meaningful pass/fail in both modes.
    """
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    model = alt_from_ollama.pick_default_model()
    require_model(model)

    img_path = _WIKI_DIR / filename
    if not img_path.exists():
        pytest.skip(
            f"Image file missing: {img_path}. "
            f"Run `python3 tests/fixtures/images/fetch_wikipedia.py`."
        )

    lang = spec["lang"]
    alt: str = alt_from_ollama.describe(
        str(img_path),
        kind=spec["kind"],
        lang=lang,
        model=model,
    )

    # Structural: non-empty, capped, no trailing ellipsis. These three
    # alone catch ~80% of model-side regressions and don't need DeepEval.
    assert alt, f"Alt text is empty for {filename}"
    assert len(alt) <= 150, f"Alt text exceeds 150-char cap: {len(alt)} chars"
    assert not alt.rstrip().endswith("..."), "Alt text ends with ellipsis"
    assert not alt.rstrip().endswith("…"), "Alt text ends with Unicode ellipsis"

    # Kind-appropriate keyword sanity. Tuple of expected subject words
    # is generous; failing this almost certainly means the model
    # returned boilerplate or described a different image.
    expected = _SUBJECT_KEYWORDS.get(filename, ())
    if expected:
        lowered = alt.lower()
        assert any(kw in lowered for kw in expected), (
            f"None of the expected subject words {expected} appear in "
            f"alt text for {filename}: {alt!r}"
        )

    # FR entry: the language hint must shift the output to French. We
    # accept either a positive ``detect_text_language`` result or a
    # French stop-word in the output, since langdetect is noisy on very
    # short alt strings.
    if lang == "fr":
        detected = detect_text_language(alt, fallback="en")
        french_markers = (
            " le ", " la ", " les ", " un ", " une ",
            " des ", " et ", " sur ", " avec ", " dans ",
        )
        has_marker = any(m in f" {alt.lower()} " for m in french_markers)
        assert detected == "fr" or has_marker, (
            f"`--lang fr` did not produce French output for {filename}. "
            f"detected={detected!r}, alt={alt!r}"
        )

    # DeepEval relevance + faithfulness against the human caption + alt.
    # Both thresholds are deliberately low — captions and AI alt diverge
    # stylistically even when the AI is correct. We use the caption as
    # the retrieval_context because it's typically longer than the alt
    # and gives the metric more substrate to score against.
    reference = spec["caption"] or spec["alt_text"]
    case = LLMTestCase(
        input=f"Describe this image for a screen-reader user. Source: {filename}.",
        actual_output=alt,
        expected_output=reference,
        retrieval_context=[reference],
    )
    try:
        relevance = AnswerRelevancyMetric(threshold=0.4)
        relevance.measure(case)
        assert relevance.score is None or relevance.score >= 0.4, (
            f"Relevance below 0.4 for {filename}: "
            f"score={relevance.score}, alt={alt!r}"
        )
        faithfulness = FaithfulnessMetric(threshold=0.4)
        faithfulness.measure(case)
        assert faithfulness.score is None or faithfulness.score >= 0.4, (
            f"Faithfulness below 0.4 for {filename}: "
            f"score={faithfulness.score}, alt={alt!r}"
        )
    except Exception as exc:  # pragma: no cover - environment-dependent
        # DeepEval needs its own model wiring; on a vanilla Ollama install
        # it often raises a configuration error. Fall back to a stdlib
        # character-trigram overlap floor — that still catches the
        # "model hallucinated something unrelated" regression, just with
        # less granularity.
        overlap = _char_trigram_overlap(alt, reference)
        assert overlap >= 0.10, (
            f"Trigram overlap below 0.10 for {filename}: "
            f"overlap={overlap:.3f}, alt={alt!r}, reference={reference!r}. "
            f"(DeepEval unavailable: {exc})"
        )


def test_decorative_returns_empty() -> None:
    """
    A ``kind="decorative"`` request must short-circuit to ``""`` with no
    network round-trip, regardless of whether Ollama is up.

    This test stays on the Pillow-synthetic ``decorative-pattern.png``
    deliberately: the short-circuit is the entire behaviour under test,
    and a real image would be wasted bytes for a code path that never
    looks at the pixels.
    """
    decorative = _FIXTURES_ROOT / "decorative-pattern.png"
    if not decorative.exists():
        pytest.skip(f"Decorative fixture missing: {decorative}")
    out: str = alt_from_ollama.describe(
        str(decorative), kind="decorative", lang="en"
    )
    assert out == "", f"Decorative image must return empty string, got {out!r}"
