"""
sprezzature_local — offline runtime for the sprezzature skill suite.

Gives all nine sprezzature skills a local, agent-free runtime driven by a
local model served by Ollama, vLLM, or any OpenAI-compatible server.  No
cloud API call is made at inference time.

Public API
----------
From ``llm``:
    ``chat``    — send a prompt (text or vision) to the configured backend.
    ``embed``   — return a float embedding vector (Ollama only).

From ``ralph``:
    ``ralph_loop``   — generic produce-inspect-fix-repeat driver.
    ``eyeball_loop`` — autonomous visual quality loop (PNG + vision model).
    ``prose_loop``   — paragraph-pair seam loop (text model + charter).

From ``writing``:
    ``load_charter``       — return the writing charter for a language code.
    ``faithfulness_audit`` — RAGAS-style per-claim faithfulness check.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from .llm import chat, embed
from .ralph import eyeball_loop, prose_loop, ralph_loop
from .writing import faithfulness_audit, load_charter

__all__ = [
    "chat",
    "embed",
    "ralph_loop",
    "eyeball_loop",
    "prose_loop",
    "load_charter",
    "faithfulness_audit",
]

__version__ = "0.1.0"
__author__ = "Warith Harchaoui"
__email__ = "warith.harchaoui@gmail.com"
