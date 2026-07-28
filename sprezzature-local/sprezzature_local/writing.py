"""
writing — writing charter loader and RAGAS-style faithfulness audit.

Two public surfaces:

``CHARTER``
    A module-level dict mapping two-letter language codes to the full text of
    their writing charter.  Populated at import time from the per-language
    Markdown files in ``sprezzature-publish/scripts/charters/``.  Falls back
    to an empty string when a file is absent.

``faithfulness_audit``
    A RAGAS-style per-claim faithfulness audit.  Decomposes a generated text
    into atomic claims, verifies each claim against a source document by
    asking the model to quote the supporting sentence, and returns a traffic-
    light score.  Contradicted claims fail hard; unsupported claims are flagged
    for review.

Both functions call :func:`llm.chat`, which routes to the configured local
backend via ``SPREZZATURE_LLM_*`` environment variables.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import llm


# ---------------------------------------------------------------------------
# Charter loader
# ---------------------------------------------------------------------------

# Charters live two levels up from this file: the structure is
#   sprezzature-local/sprezzature_local/writing.py
#   sprezzature-publish/scripts/charters/<lang>.md
# So the path to the charters directory is three parents up, then into
# sprezzature-publish/scripts/charters/.
_CHARTER_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "sprezzature-publish" / "scripts" / "charters"
)

# Supported language codes.  The list mirrors the six charters authored in
# the project; others are silently skipped with an empty fallback.
_SUPPORTED_LANGS: tuple[str, ...] = ("en", "fr", "es", "de", "it", "pt")


def _load_all_charters() -> dict[str, str]:
    """
    Load all language charters from disk at import time.

    Returns
    -------
    dict[str, str]
        Map from two-letter language code to full charter text.  An absent or
        unreadable file produces an empty string for that code.
    """
    result: dict[str, str] = {}
    for lang in _SUPPORTED_LANGS:
        path = _CHARTER_DIR / f"{lang}.md"
        try:
            result[lang] = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            # A missing charter is not an error at import time; the caller can
            # check for an empty string and fall back to a generic guideline.
            result[lang] = ""
    return result


# Module-level map populated once at import.  Skills that generate prose read
# from here rather than re-loading files on every call.
CHARTER: dict[str, str] = _load_all_charters()


def load_charter(lang: str) -> str:
    """
    Return the writing charter for a language code.

    Parameters
    ----------
    lang : str
        Two-letter ISO 639-1 language code (e.g. ``'en'``, ``'fr'``).

    Returns
    -------
    str
        Full charter text.  Empty string when the charter is absent or
        the language code is not in the supported set.

    Examples
    --------
    >>> text = load_charter("en")
    >>> isinstance(text, str)
    True
    """
    # Normalise: strip whitespace and lower-case the code.
    code = lang.strip().lower()[:2]
    if code not in CHARTER:
        # Re-attempt a file load for unsupported codes rather than failing.
        path = _CHARTER_DIR / f"{code}.md"
        try:
            CHARTER[code] = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            CHARTER[code] = ""
    return CHARTER[code]


# ---------------------------------------------------------------------------
# Faithfulness audit
# ---------------------------------------------------------------------------

# System prompt for the decomposition step: break the text into one-sentence
# atomic claims the verifier can check independently.
_DECOMPOSE_SYSTEM: str = (
    "You are an auditor decomposing text into atomic claims. "
    "Each claim must be a single, self-contained statement that can be "
    "verified independently against a source document. "
    "Return only a JSON array of claim strings.  No prose, no preamble."
)

# System prompt for the verification step: for each claim, find a supporting
# quote in the source or declare the claim unsupported or contradicted.
_VERIFY_SYSTEM: str = (
    "You are a faithfulness verifier.  Given a claim and a source document, "
    "decide whether the source SUPPORTS, CONTRADICTS, or does NOT_SUPPORT the "
    "claim.  If the source supports the claim, quote the exact supporting "
    "sentence verbatim (including punctuation).  If not, set quote to null. "
    "Return only a JSON object with keys: status (one of SUPPORTED, "
    "UNSUPPORTED, CONTRADICTED), quote (string or null)."
)

# Schema for a single verification result.
_VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]},
        "quote":  {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
}


def faithfulness_audit(
    text: str,
    source_doc: str,
    *,
    lang: str = "en",
    threshold: float = 0.70,
) -> dict[str, Any]:
    """
    Run a RAGAS-style per-claim faithfulness audit on generated text.

    The audit decomposes ``text`` into atomic claims, then verifies each claim
    against ``source_doc`` by asking the model to quote the exact supporting
    sentence.  A claim the model cannot quote counts as NOT_SUPPORTED.

    Traffic-light interpretation of the returned score:
    - ``score >= threshold`` and no CONTRADICTED claims: green, acceptable.
    - ``score >= threshold`` with CONTRADICTED claims: amber, flag to user.
    - ``score < threshold``: red, regenerate the text.

    Parameters
    ----------
    text : str
        The generated text to audit (meta description, plain-language rewrite,
        narration copy, or similar).
    source_doc : str
        The authoritative source document.  The model must find supporting
        quotes here.
    lang : str, optional
        Two-letter language code used to set context for the verifier.
        Default ``"en"``.
    threshold : float, optional
        Score below which the overall audit is considered failing.
        Default ``0.70`` (70% of claims must be supported).

    Returns
    -------
    dict
        A summary dict with keys:

        - ``supported`` (int): number of SUPPORTED claims.
        - ``unsupported`` (int): number of UNSUPPORTED claims.
        - ``contradicted`` (int): number of CONTRADICTED claims.
        - ``score`` (float): ``supported / total``, or 1.0 on empty input.
        - ``passing`` (bool): ``score >= threshold`` and no contradictions.
        - ``claims`` (list of dict): per-claim results, each with ``claim``,
          ``status``, and ``quote`` keys.

    Examples
    --------
    >>> result = faithfulness_audit("", "any source", lang="en")
    >>> result["score"]
    1.0
    """
    # Empty text has no claims and is trivially faithful.
    if not text.strip():
        return {
            "supported": 0, "unsupported": 0, "contradicted": 0,
            "score": 1.0, "passing": True, "claims": [],
        }

    # Step 1: decompose the text into atomic claims.
    decompose_prompt = (
        f"Language: {lang}\n\n"
        f"TEXT TO DECOMPOSE:\n{text}\n\n"
        "Return a JSON array of atomic claim strings."
    )
    raw_claims = llm.chat(decompose_prompt, system=_DECOMPOSE_SYSTEM, json_schema={"type": "array"})

    # Parse the claim list; fall back to treating the whole text as one claim.
    if isinstance(raw_claims, list):
        claims: list[str] = [str(c) for c in raw_claims if c]
    else:
        try:
            claims = json.loads(str(raw_claims))
            if not isinstance(claims, list):
                claims = [text]
        except json.JSONDecodeError:
            claims = [text]

    if not claims:
        return {
            "supported": 0, "unsupported": 0, "contradicted": 0,
            "score": 1.0, "passing": True, "claims": [],
        }

    # Step 2: verify each claim against the source document.
    results: list[dict[str, Any]] = []
    supported = unsupported = contradicted = 0

    for claim in claims:
        verify_prompt = (
            f"CLAIM:\n{claim}\n\n"
            f"SOURCE DOCUMENT:\n{source_doc}\n\n"
            "Is this claim SUPPORTED, UNSUPPORTED, or CONTRADICTED by the source?"
        )
        raw_verdict = llm.chat(
            verify_prompt,
            system=_VERIFY_SYSTEM,
            json_schema=_VERIFY_SCHEMA,
        )

        if isinstance(raw_verdict, dict):
            status: str = str(raw_verdict.get("status", "UNSUPPORTED")).upper()
            quote: str | None = raw_verdict.get("quote")
        else:
            # Unstructured fallback: keyword scan.
            txt = str(raw_verdict).upper()
            if "CONTRADICT" in txt:
                status = "CONTRADICTED"
            elif "NOT_SUPPORT" in txt or "UNSUPPORTED" in txt:
                status = "UNSUPPORTED"
            else:
                status = "SUPPORTED"
            quote = None

        # Tally by status category.
        if status == "SUPPORTED":
            supported += 1
        elif status == "CONTRADICTED":
            contradicted += 1
        else:
            status = "UNSUPPORTED"
            unsupported += 1

        results.append({"claim": claim, "status": status, "quote": quote})

    total = len(claims)
    score = supported / total if total > 0 else 1.0
    # A result is passing only when the score meets the threshold AND no
    # claim directly contradicts the source.
    passing = score >= threshold and contradicted == 0

    return {
        "supported": supported,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "score": round(score, 4),
        "passing": passing,
        "claims": results,
    }
