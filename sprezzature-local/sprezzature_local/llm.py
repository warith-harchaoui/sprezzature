"""
llm — pluggable local-model backend for the sprezzature offline runtime.

Exposes two public functions — ``chat`` and ``embed`` — that route calls to
the backend selected by the ``SPREZZATURE_LLM_BACKEND`` environment variable.
All skill scripts that previously called Ollama's ``/api/generate`` directly
import from here; the transport details stay in one file.

Supported backends
------------------
``ollama`` (default)
    Native Ollama REST API.  Calls ``POST {BASE_URL}/api/generate``.
    No extra Python dependencies beyond ``requests``.

``openai``
    OpenAI-compatible REST API (vLLM, llama.cpp server mode, LM Studio,
    Text Generation Inference, OpenAI itself).  Calls
    ``POST {BASE_URL}/v1/chat/completions``.  Requires ``requests``.

``langchain``
    Wraps ``ChatOllama`` or ``ChatOpenAI`` from the LangChain ecosystem.
    Requires the ``[langchain]`` extras: ``langchain-core``,
    ``langchain-ollama``, ``langchain-openai``.

Environment variables
---------------------
SPREZZATURE_LLM_BACKEND : str
    ``ollama`` | ``openai`` | ``langchain``.  Default: ``ollama``.
SPREZZATURE_LLM_BASE_URL : str
    Server URL.  Default: ``http://localhost:11434`` (Ollama).
SPREZZATURE_LLM_TEXT : str
    Model tag to use for text-only prompts.
SPREZZATURE_LLM_VISION : str
    Model tag to use when images are present.
SPREZZATURE_LLM_API_KEY : str
    API key forwarded as the ``Authorization: Bearer`` header.  Usually
    empty for local servers.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Configuration helpers — read once at call time so tests can patch env vars
# ---------------------------------------------------------------------------

def _backend() -> str:
    """Return the selected backend name, lower-cased."""
    return os.environ.get("SPREZZATURE_LLM_BACKEND", "ollama").lower().strip()


def _base_url() -> str:
    """Return the server base URL, trailing-slash stripped."""
    return os.environ.get("SPREZZATURE_LLM_BASE_URL", "http://localhost:11434").rstrip("/")


def _api_key() -> str | None:
    """Return the API key, or None when the env var is absent or empty."""
    val = os.environ.get("SPREZZATURE_LLM_API_KEY", "").strip()
    return val or None


def _resolve_model(images: list[bytes] | None, override: str | None) -> str:
    """
    Pick the model tag for a request.

    Selection order:
    1. ``override`` argument — caller-supplied explicit tag.
    2. ``SPREZZATURE_LLM_VISION`` when images are present.
    3. ``SPREZZATURE_LLM_TEXT`` for text-only requests.
    4. Raise ``ValueError`` when no env var is set and no override is given.

    Parameters
    ----------
    images : list of bytes or None
        Image payloads for this call; ``None`` means text-only.
    override : str or None
        Explicit model tag from the ``model=`` argument, or ``None``.

    Returns
    -------
    str
        The resolved model tag.

    Raises
    ------
    ValueError
        When no model can be determined from the inputs or environment.
    """
    if override:
        # Caller supplied an explicit tag — use it unconditionally.
        return override
    # Pick vision model when images are attached; text model otherwise.
    if images:
        tag = os.environ.get("SPREZZATURE_LLM_VISION", "").strip()
    else:
        tag = os.environ.get("SPREZZATURE_LLM_TEXT", "").strip()

    if not tag:
        env_var = "SPREZZATURE_LLM_VISION" if images else "SPREZZATURE_LLM_TEXT"
        raise ValueError(
            f"No model configured. Set {env_var} (or SPREZZATURE_LLM_TEXT / "
            "SPREZZATURE_LLM_VISION) in the environment, or pass model= explicitly."
        )
    return tag


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------

def _chat_ollama(
    prompt: str,
    *,
    system: str | None,
    images: list[bytes] | None,
    json_schema: dict[str, Any] | None,
    model: str,
    temperature: float,
) -> str | dict[str, Any]:
    """
    Send a chat request to the native Ollama API.

    Parameters
    ----------
    prompt : str
        User-side prompt text.
    system : str or None
        Optional system prompt; forwarded as the ``system`` key.
    images : list of bytes or None
        Raw image bytes to encode as base64 in the ``images`` array.
    json_schema : dict or None
        When set, adds ``"format": "json"`` to the payload and parses
        the response as JSON before returning.
    model : str
        Ollama model tag.
    temperature : float
        Sampling temperature forwarded in ``options``.

    Returns
    -------
    str or dict
        The raw response string, or a parsed dict when json_schema is set.
    """
    import requests  # imported here so non-Ollama paths stay requests-free

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    # System prompt is optional — omitting the key avoids Ollama quirks.
    if system is not None:
        payload["system"] = system

    # Images must be base64 strings, not raw bytes.
    if images:
        payload["images"] = [base64.b64encode(img).decode("ascii") for img in images]

    # Structured JSON output — Ollama's format key constrains the decoder.
    if json_schema is not None:
        payload["format"] = "json"

    url = f"{_base_url()}/api/generate"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    resp = requests.post(url, json=payload, headers=headers, timeout=600)
    resp.raise_for_status()
    text: str = resp.json().get("response", "").strip()

    # Parse JSON when a schema was requested — the caller expects a dict.
    if json_schema is not None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Return an empty dict rather than crashing; the caller should
            # check for missing keys rather than assuming the model replied well.
            return {}
    return text


# ---------------------------------------------------------------------------
# OpenAI-compatible backend (vLLM, llama.cpp, LM Studio, OpenAI, etc.)
# ---------------------------------------------------------------------------

def _chat_openai(
    prompt: str,
    *,
    system: str | None,
    images: list[bytes] | None,
    json_schema: dict[str, Any] | None,
    model: str,
    temperature: float,
) -> str | dict[str, Any]:
    """
    Send a chat request to an OpenAI-compatible endpoint.

    Images are forwarded as ``data:image/png;base64,…`` content parts,
    following the vision API convention that vLLM and LM Studio implement.

    Parameters
    ----------
    prompt : str
        User-side prompt text.
    system : str or None
        System prompt prepended as a ``system`` role message.
    images : list of bytes or None
        Raw PNG bytes encoded into the user message content array.
    json_schema : dict or None
        When set, adds ``response_format: {type: json_object}`` and parses
        the returned content as JSON.
    model : str
        Model name as the server expects it.
    temperature : float
        Sampling temperature.

    Returns
    -------
    str or dict
        Content string from the first choice, or a parsed dict.
    """
    import requests

    messages: list[dict[str, Any]] = []
    if system is not None:
        messages.append({"role": "system", "content": system})

    # Build the user content: either a plain string or a content-parts array.
    if images:
        # Vision content part format: text + one image_url part per image.
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if json_schema is not None:
        payload["response_format"] = {"type": "json_object"}

    url = f"{_base_url()}/v1/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    resp = requests.post(url, json=payload, headers=headers, timeout=600)
    resp.raise_for_status()
    content: str = resp.json()["choices"][0]["message"]["content"].strip()

    if json_schema is not None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return content


# ---------------------------------------------------------------------------
# LangChain backend
# ---------------------------------------------------------------------------

def _chat_langchain(
    prompt: str,
    *,
    system: str | None,
    images: list[bytes] | None,
    json_schema: dict[str, Any] | None,
    model: str,
    temperature: float,
) -> str | dict[str, Any]:
    """
    Send a chat request via LangChain wrappers.

    Selects ``ChatOllama`` when the backend URL looks like an Ollama server
    (default port 11434 or explicit ``ollama`` backend) and ``ChatOpenAI``
    otherwise (for vLLM or remote OpenAI).

    Parameters
    ----------
    prompt : str
        User prompt text.
    system : str or None
        System content prepended as a ``SystemMessage``.
    images : list of bytes or None
        Raw image bytes; passed as base64 ``image_url`` content blocks.
    json_schema : dict or None
        When set, instructs the chain to parse JSON and returns a dict.
    model : str
        Model name forwarded to the wrapper constructor.
    temperature : float
        Sampling temperature.

    Returns
    -------
    str or dict
        Model response content, or a parsed dict when json_schema is set.

    Raises
    ------
    ImportError
        When the ``[langchain]`` extras are not installed.
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "The langchain backend requires the [langchain] extras. Install with:\n"
            "  pip install 'sprezzature-local[langchain]'"
        ) from exc

    # Choose the right wrapper based on the base URL.
    base = _base_url()
    if "11434" in base or base.endswith("ollama"):
        from langchain_ollama import ChatOllama  # type: ignore[import]
        llm = ChatOllama(base_url=base, model=model, temperature=temperature)
    else:
        from langchain_openai import ChatOpenAI  # type: ignore[import]
        key = _api_key() or "local"
        llm = ChatOpenAI(base_url=f"{base}/v1", model=model, temperature=temperature, api_key=key)

    msgs: list[Any] = []
    if system:
        msgs.append(SystemMessage(content=system))

    # Images are passed as content blocks in the HumanMessage.
    if images:
        content_blocks: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        msgs.append(HumanMessage(content=content_blocks))
    else:
        msgs.append(HumanMessage(content=prompt))

    result = llm.invoke(msgs)
    content: str = result.content if hasattr(result, "content") else str(result)

    if json_schema is not None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat(
    prompt: str,
    *,
    system: str | None = None,
    images: list[bytes] | None = None,
    json_schema: dict[str, Any] | None = None,
    model: str | None = None,
    temperature: float = 0.2,
) -> str | dict[str, Any]:
    """
    Send a prompt to the configured local model and return the response.

    This is the single transport entry point for all sprezzature skills.
    The backend, URL, and model are selected from environment variables so
    no skill script contains a hardcoded server address or model tag.

    Parameters
    ----------
    prompt : str
        The user-side prompt text.
    system : str or None, optional
        System prompt.  Forwarded as ``system`` (Ollama) or a system-role
        message (OpenAI-compatible).  ``None`` omits the system turn.
    images : list of bytes or None, optional
        Raw image bytes to include in the request.  When present the model
        selected by ``SPREZZATURE_LLM_VISION`` is used unless ``model=``
        overrides it.
    json_schema : dict or None, optional
        When provided the backend is asked to return structured JSON.  The
        response is parsed and returned as a ``dict`` instead of a ``str``.
        A parse failure returns ``{}``.
    model : str or None, optional
        Explicit model tag.  Overrides ``SPREZZATURE_LLM_TEXT`` and
        ``SPREZZATURE_LLM_VISION``.
    temperature : float, optional
        Sampling temperature forwarded to the model.  Default ``0.2``.

    Returns
    -------
    str or dict
        The model response.  A ``str`` under normal use; a parsed ``dict``
        when ``json_schema`` is set.

    Raises
    ------
    ValueError
        When no model tag can be resolved from the arguments or environment.
    requests.exceptions.ConnectionError
        When the backend server is not reachable.
    requests.exceptions.HTTPError
        When the backend returns a non-2xx status.

    Examples
    --------
    >>> import os; os.environ.setdefault("SPREZZATURE_LLM_TEXT", "qwen3-vl:8b")
    >>> # chat("Describe the sky in one sentence.")   # requires a live server
    """
    resolved_model = _resolve_model(images, model)
    backend = _backend()

    if backend == "ollama":
        return _chat_ollama(
            prompt, system=system, images=images,
            json_schema=json_schema, model=resolved_model, temperature=temperature,
        )
    if backend == "openai":
        return _chat_openai(
            prompt, system=system, images=images,
            json_schema=json_schema, model=resolved_model, temperature=temperature,
        )
    if backend == "langchain":
        return _chat_langchain(
            prompt, system=system, images=images,
            json_schema=json_schema, model=resolved_model, temperature=temperature,
        )
    raise ValueError(
        f"Unknown backend {backend!r}. Set SPREZZATURE_LLM_BACKEND to "
        "'ollama', 'openai', or 'langchain'."
    )


def embed(text: str) -> list[float]:
    """
    Return a float embedding vector for a text string.

    Only the Ollama backend supports native embeddings via
    ``POST /api/embeddings``.  The OpenAI-compatible and LangChain backends
    raise ``NotImplementedError``; use a dedicated embedding server instead.

    Parameters
    ----------
    text : str
        Input text to embed.

    Returns
    -------
    list of float
        Embedding vector from the model.

    Raises
    ------
    NotImplementedError
        When the backend is not ``ollama``.
    ValueError
        When no text model is configured in the environment.
    requests.exceptions.ConnectionError
        When Ollama is unreachable.

    Examples
    --------
    >>> import os; os.environ.setdefault("SPREZZATURE_LLM_TEXT", "qwen3-vl:8b")
    >>> # embed("hello world")  # requires a live Ollama server
    """
    backend = _backend()
    if backend != "ollama":
        raise NotImplementedError(
            f"embed() is only supported with the 'ollama' backend (got {backend!r}). "
            "Use a dedicated embedding server for other backends."
        )

    import requests

    model = _resolve_model(None, None)
    payload = {"model": model, "prompt": text}
    url = f"{_base_url()}/api/embeddings"

    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json().get("embedding", [])
