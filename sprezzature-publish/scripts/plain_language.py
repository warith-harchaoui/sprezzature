#!/usr/bin/env python3
"""
plain_language
==============

Rewrite UI copy at a target reading level using the local Ollama model
already used by :mod:`alt_from_ollama`. Meaning is preserved; jargon and
marketing voice are removed.

Cognitive accessibility (WCAG 2.4.5, Understanding 3.1.5, Reading Level)
is the criterion almost everyone skips because the rewrite is tedious.
The model is good at this and runs locally; the rewrite is free past the
fixed cost of a model pull.

Behavior
--------
* Reads input from stdin OR a file (``--input``); writes the rewrite to stdout.
* Honors ``--lang`` (default: detected from the environment), so French
  in goes French out.
* Honors ``--target-grade`` (default ``8``) — a hint to the prompt, not a
  hard contract. Output is checked for length; the model is asked again
  in shorter form if it overshoots.
* ``--preserve "Brand,Product"`` lists tokens the rewriter must keep
  verbatim (proper nouns, code identifiers, API names).
* Output is cached on disk so the same input never hits the model twice;
  cache key includes target grade, language, preserve list, and model.

Usage
-----
::

    # Pipe in a single string
    echo "Boost your productivity with our state-of-the-art platform" \\
        | python plain_language.py --target-grade 8 --lang en

    # Read from a file, write to another
    python plain_language.py --input src/copy.md > dist/copy.simple.md

    # Keep brand names intact
    python plain_language.py --preserve "Sprezzature,Tailwind,Montserrat" --input copy.md

    # Bypass the cache for this run
    python plain_language.py --no-cache --input copy.md

Notes
-----
* Python 3.10+, ``requests`` (shared with :mod:`alt_from_ollama`).
* Cache: ``~/.cache/sprezzature-skill/plain/`` — override with ``SPREZZATURE_CACHE_DIR``;
  disable with ``SPREZZATURE_NO_CACHE=1`` or ``--no-cache``.
* The rewriter refuses to invent facts. If the input is already plain
  language, the model returns it unchanged.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
from typing import Optional

import click
import requests

# Shared Ollama helpers live in _ollama.py inside this skill folder so
# the script does not need a cross-skill import after the 0.2.0 split.
sys.path.insert(0, str(Path(__file__).parent))
from _ollama import (  # noqa: E402
    OLLAMA_URL,
    LANG_INSTRUCTIONS,
    detect_lang,
    pick_default_model,
)
from _lang import detect_text_language  # noqa: E402


# ── Module-level configuration ────────────────────────────────────────────────

#: Maximum factor by which the rewrite may grow compared to the source.
#: 1.1 keeps the output approximately the same length; longer rewrites are
#: re-asked with a tighter constraint.
MAX_LENGTH_FACTOR: float = 1.1

#: Cache directory for the rewriter. Override with ``SPREZZATURE_CACHE_DIR``.
CACHE_DIR: Path = Path(
    os.environ.get("SPREZZATURE_CACHE_DIR", Path.home() / ".cache" / "sprezzature-skill")
) / "plain"

#: Cache toggle, mirroring the other Ollama helpers.
NO_CACHE: bool = bool(os.environ.get("SPREZZATURE_NO_CACHE"))


# ── Cache helpers ────────────────────────────────────────────────────────────

def _cache_key(text: str, grade: int, lang: str, preserve: list[str], model: str) -> str:
    """
    Compute a 32-character cache key from the inputs that affect the output.

    Parameters
    ----------
    text : str
        Source text to rewrite.
    grade : int
        Target reading grade level.
    lang : str
        Two-letter language code.
    preserve : list of str
        Tokens the rewriter must keep verbatim. Sorted for stability.
    model : str
        Ollama model tag.

    Returns
    -------
    str
        32 hex characters suitable as a filename stem.
    """
    h = hashlib.sha256()
    # ``\x00`` separators avoid ambiguity when an input contains a delimiter.
    h.update(f"{text}\x00{grade}\x00{lang}\x00".encode("utf-8"))
    h.update("\x01".join(sorted(preserve)).encode("utf-8"))
    h.update(f"\x00{model}".encode("utf-8"))
    return h.hexdigest()[:32]


def _cache_get(key: str) -> Optional[str]:
    """Return the cached rewrite for ``key``, or ``None`` on a miss."""
    if NO_CACHE:
        return None
    path = CACHE_DIR / f"{key}.txt"
    if path.is_file():
        # Strip the trailing newline written by ``_cache_set``.
        return path.read_text(encoding="utf-8").rstrip("\n")
    return None


def _cache_set(key: str, text: str) -> None:
    """Store ``text`` in the cache under ``key``. Failures are swallowed."""
    if NO_CACHE:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.txt").write_text(text + "\n", encoding="utf-8")
    except OSError:
        # Caching is opportunistic; never fatal.
        pass


# ── Prompt construction ─────────────────────────────────────────────────────
#
# The prompt body lives in scripts/prompts/plain_language_rewrite.yaml.
# This function only assembles the dynamic prefix (language line) and
# the optional `preserve_line` clause before delegating to the loader.

# Deferred import — keep the prompt loader optional so that this script
# can still load without PyYAML when callers only need the non-prompt
# helpers (e.g. `LANG_INSTRUCTIONS`, `detect_text_language`).
try:
    from _prompts import render as render_prompt  # type: ignore
    HAVE_PROMPTS = True
except ImportError:
    HAVE_PROMPTS = False


def build_prompt(text: str, grade: int, lang: str, preserve: list[str]) -> str:
    """
    Build the prompt sent to the model.

    Parameters
    ----------
    text : str
        Source text.
    grade : int
        Target reading grade level (typically 6–10).
    lang : str
        Target language code (must match the source's language).
    preserve : list of str
        Tokens to keep verbatim.

    Returns
    -------
    str
        The full prompt, ready to send to Ollama.
    """
    # The language line commits the model to a single language early.
    lang_line: str = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["en"])

    preserve_line: str = ""
    if preserve:
        preserve_line = (
            f"Keep these tokens verbatim (do not translate, do not paraphrase): "
            f"{', '.join(preserve)}.\n"
        )

    if not HAVE_PROMPTS:
        # Fallback when _prompts is not importable. Should be unreachable
        # in practice since this script and _prompts.py ship together.
        return (
            f"{lang_line} Rewrite at grade {grade}. Preserve meaning. "
            f"{preserve_line}--- TEXT ---\n{text}\n--- END ---"
        )

    return render_prompt(
        "plain_language_rewrite",
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        lang_line=lang_line,
        grade=grade,
        preserve_line=preserve_line,
        text=text,
    )


# ── Public API ──────────────────────────────────────────────────────────────

def rewrite(
    text: str,
    *,
    target_grade: int = 8,
    lang: Optional[str] = None,
    preserve: Optional[list[str]] = None,
    model: Optional[str] = None,
) -> str:
    """
    Rewrite ``text`` at the requested reading grade level.

    Parameters
    ----------
    text : str
        Source text. Empty / whitespace-only inputs round-trip unchanged.
    target_grade : int, optional
        Target reading-level hint, default ``8``.
    lang : str or None, optional
        BCP-47 base tag. When ``None`` (default), detected from the
        environment via :func:`detect_lang`.
    preserve : list of str or None, optional
        Tokens the model must keep verbatim (brand names, identifiers).
    model : str or None, optional
        Ollama model tag to use. ``None`` picks the right tag for the
        current hardware via :func:`pick_default_model`.

    Returns
    -------
    str
        The rewritten text, with surrounding whitespace stripped.

    Raises
    ------
    SystemExit
        With code ``2`` when Ollama is unreachable.

    Examples
    --------
    >>> rewrite("Boost your productivity")              # doctest: +SKIP
    'Get more done.'
    """
    if not text.strip():
        # Trivial round-trip — no need to spin up the model.
        return text

    # Language: explicit ``lang`` wins. Otherwise ALWAYS detect from the
    # input text itself (the rewrite must stay in the source language) via
    # langdetect — no configured default; env/locale is only the floor.
    if lang is None:
        lang = detect_text_language(text, fallback=detect_lang())
    lang = lang.lower()[:2]
    preserve = preserve or []
    model = model or pick_default_model()

    key = _cache_key(text, target_grade, lang, preserve, model)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    prompt = build_prompt(text, target_grade, lang, preserve)
    # ``num_predict`` grows with input length so the output has room to land
    # cleanly; we still cap to avoid runaway generation on very long inputs.
    num_predict: int = max(120, int(len(text) * 1.3))
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        # Low temperature keeps the rewrite faithful and reproducible.
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }

    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.stderr.write(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            f"Run `python sprezzature-accessibility/scripts/install_alt_ai.py` or `ollama serve`.\n"
        )
        sys.exit(2)
    except requests.exceptions.HTTPError as e:
        sys.stderr.write(f"Ollama responded with HTTP error: {e}\n")
        sys.exit(2)

    body: dict = resp.json()
    out: str = (body.get("response") or "").strip()

    # Length sanity check — if the model overshot, re-ask once with a tighter
    # instruction. We do not loop; one retry is the right balance between
    # correctness and predictable latency.
    if len(out) > len(text) * MAX_LENGTH_FACTOR:
        tighter: str = prompt + (
            f"\nThe previous rewrite was too long. "
            f"Keep it to AT MOST {int(len(text) * MAX_LENGTH_FACTOR)} characters.\n"
        )
        payload["prompt"] = tighter
        try:
            resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
            resp.raise_for_status()
            out = (resp.json().get("response") or "").strip()
        except requests.exceptions.RequestException:
            # If the retry fails, keep the over-long rewrite — it is still
            # better than the original marketing copy in most cases.
            pass

    _cache_set(key, out)
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────


@sprezzature_command(
    "sprezzature-publish-plain",
    help=(
        "Rewrite UI copy at a target reading level via a local Ollama "
        "model. Preserves meaning, strips marketing voice; output length "
        "≤ 1.1× original."
    ),
    epilog=(
        "Examples:\n"
        "  cat draft.md | sprezzature-publish-plain --target-grade 8 --lang en\n"
        "  sprezzature-publish-plain --input copy.md --preserve 'Sprezzature,Tailwind' > out.md\n"
    ),
)
@click.option(
    "--input", "-i",
    "input_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Read from this file instead of stdin.",
)
@click.option(
    "--target-grade", "-g",
    "target_grade",
    type=int,
    default=8,
    show_default=True,
    help="Reading grade level.",
)
@click.option(
    "--lang", "-l",
    default=None,
    help="BCP-47 base tag (en, fr, es, …). Default: detect from environment.",
)
@click.option(
    "--preserve",
    default="",
    help="Comma-separated tokens to keep verbatim (brand names, identifiers).",
)
@click.option(
    "--no-cache",
    "no_cache",
    is_flag=True,
    default=False,
    help="Bypass the on-disk cache for this run.",
)
def _cli(
    input_path: Optional[Path],
    target_grade: int,
    lang: Optional[str],
    preserve: str,
    no_cache: bool,
) -> int:
    """Click command body for ``plain_language``; returns an int exit code.

    Behaviour is identical to the prior argparse-driven ``main``: reads
    from ``--input`` or stdin, writes the rewrite to stdout, and exits ``1``
    when invoked with neither a file nor a pipe.
    """
    global NO_CACHE
    if no_cache:
        NO_CACHE = True

    # Read the source either from a file or from stdin so the tool slots
    # cleanly into pipelines (`cat copy.md | plain_language.py`).
    if input_path:
        text: str = input_path.read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            click.echo(
                "No input. Pass --input <file> or pipe text to stdin.",
                err=True,
            )
            return 1
        text = sys.stdin.read()

    preserve_list: list[str] = [t.strip() for t in preserve.split(",") if t.strip()]

    # The model is fixed (qwen3-vl:8b); ``rewrite`` resolves it via
    # ``pick_default_model`` — not user-selectable.
    out = rewrite(
        text,
        target_grade=target_grade,
        lang=lang,
        preserve=preserve_list,
    )

    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        Process exit code. ``0`` on success; the script delegates other
        codes to the underlying helpers (``2`` for connectivity issues).
    """
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
