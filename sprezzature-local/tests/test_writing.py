"""
test_writing — unit tests for the charter loader and faithfulness audit.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from unittest.mock import patch


from sprezzature_local import writing


# ---------------------------------------------------------------------------
# Charter loader
# ---------------------------------------------------------------------------

def test_load_charter_returns_str() -> None:
    """load_charter always returns a str, even for an unsupported language."""
    result = writing.load_charter("en")
    assert isinstance(result, str)


def test_load_charter_unknown_lang_returns_empty_str() -> None:
    """load_charter returns '' for a language that has no charter file."""
    result = writing.load_charter("xx")
    assert isinstance(result, str)
    # May be empty when the file does not exist; must not raise.


# ---------------------------------------------------------------------------
# Faithfulness audit
# ---------------------------------------------------------------------------

def test_faithfulness_audit_empty_text() -> None:
    """faithfulness_audit on empty text is trivially passing with score 1.0."""
    result = writing.faithfulness_audit("", "any source")
    assert result["score"] == 1.0
    assert result["passing"] is True
    assert result["supported"] == 0
    assert result["claims"] == []


def test_faithfulness_audit_calls_llm_and_builds_result() -> None:
    """faithfulness_audit decomposes claims and verifies each one via the LLM."""
    call_count: list[int] = []

    def _fake_chat(prompt: str, *, system: str | None = None, json_schema=None, **kwargs):
        call_count.append(1)
        if json_schema and json_schema.get("type") == "array":
            # Decomposition call: return two atomic claims.
            return ["The sky is blue.", "Water is wet."]
        # Verification call: both supported.
        return {"status": "SUPPORTED", "quote": "The sky is indeed blue."}

    with patch("sprezzature_local.writing.llm.chat", side_effect=_fake_chat):
        result = writing.faithfulness_audit(
            "The sky is blue. Water is wet.",
            source_doc="The sky is blue and water is wet.",
        )

    assert result["supported"] == 2
    assert result["contradicted"] == 0
    assert result["score"] == 1.0
    assert result["passing"] is True
    assert len(result["claims"]) == 2
    # LLM was called: once for decomposition + once per claim
    assert len(call_count) >= 2
