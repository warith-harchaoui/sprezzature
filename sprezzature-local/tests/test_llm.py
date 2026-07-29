"""
test_llm — unit tests for the pluggable LLM backend.

All tests mock ``requests.post`` so no live server is required.
Each test sets the relevant env vars via ``monkeypatch``, calls the
public API, and asserts on the URL, payload, or return value.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sprezzature_local import llm as _llm


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mock_resp(body: dict) -> MagicMock:
    """Return a requests.Response mock that returns *body* from .json()."""
    m = MagicMock()
    m.json.return_value = body
    m.raise_for_status.return_value = None
    m.status_code = 200
    return m


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip all SPREZZATURE_LLM_* env vars before each test."""
    for key in (
        "SPREZZATURE_LLM_BACKEND",
        "SPREZZATURE_LLM_TEXT",
        "SPREZZATURE_LLM_VISION",
        "SPREZZATURE_LLM_BASE_URL",
        "SPREZZATURE_LLM_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_chat_ollama_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat() with the ollama backend posts to /api/generate and returns response."""
    monkeypatch.setenv("SPREZZATURE_LLM_BACKEND", "ollama")
    monkeypatch.setenv("SPREZZATURE_LLM_TEXT", "test-model")

    with patch("requests.post", return_value=_mock_resp({"response": "hello"})) as mock_post:
        result = _llm.chat("say hi")

    assert result == "hello"
    url: str = mock_post.call_args[0][0]
    assert url.endswith("/api/generate")


def test_chat_openai_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat() with the openai backend posts to /v1/chat/completions and returns content."""
    monkeypatch.setenv("SPREZZATURE_LLM_BACKEND", "openai")
    monkeypatch.setenv("SPREZZATURE_LLM_TEXT", "gpt-test")

    reply = {"choices": [{"message": {"content": "world"}}]}
    with patch("requests.post", return_value=_mock_resp(reply)) as mock_post:
        result = _llm.chat("hi")

    assert result == "world"
    url: str = mock_post.call_args[0][0]
    assert url.endswith("/v1/chat/completions")


def test_chat_uses_vision_model_when_images_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat() selects SPREZZATURE_LLM_VISION when images are supplied."""
    monkeypatch.setenv("SPREZZATURE_LLM_BACKEND", "ollama")
    monkeypatch.setenv("SPREZZATURE_LLM_TEXT", "text-model")
    monkeypatch.setenv("SPREZZATURE_LLM_VISION", "vision-model")

    with patch("requests.post", return_value=_mock_resp({"response": "seen"})) as mock_post:
        result = _llm.chat("describe", images=[b"\x89PNG"])

    assert result == "seen"
    payload: dict = mock_post.call_args[1]["json"]
    assert payload["model"] == "vision-model"
    # Image is included as a base64 string in the payload
    assert payload.get("images")


def test_chat_uses_text_model_for_text_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat() selects SPREZZATURE_LLM_TEXT when no images are supplied."""
    monkeypatch.setenv("SPREZZATURE_LLM_BACKEND", "ollama")
    monkeypatch.setenv("SPREZZATURE_LLM_TEXT", "text-only-model")

    with patch("requests.post", return_value=_mock_resp({"response": "text"})) as mock_post:
        _llm.chat("hello")

    payload: dict = mock_post.call_args[1]["json"]
    assert payload["model"] == "text-only-model"
    assert "images" not in payload


def test_embed_calls_embeddings_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed() posts to /api/embeddings and returns the embedding vector."""
    monkeypatch.setenv("SPREZZATURE_LLM_BACKEND", "ollama")
    monkeypatch.setenv("SPREZZATURE_LLM_TEXT", "embed-model")

    with patch("requests.post", return_value=_mock_resp({"embedding": [0.1, 0.2, 0.3]})) as mock_post:
        result = _llm.embed("hello")

    assert result == [0.1, 0.2, 0.3]
    url: str = mock_post.call_args[0][0]
    assert url.endswith("/api/embeddings")
