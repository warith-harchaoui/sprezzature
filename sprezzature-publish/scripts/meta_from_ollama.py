#!/usr/bin/env python3
"""
meta_from_ollama
================

Draft HTML ``<meta>`` tags from a page's *goal and content*, using a local
Ollama model. The tool reads either a free-text goal description, an existing
HTML file, or a live URL — alone or in combination — and returns a single
JSON object with suggested values for the canonical web meta surfaces.

The script does NOT write to your HTML. It prints the suggestions to stdout;
the author reviews and pastes (or pipes into a build step).

Output schema
-------------
Every successful run emits a JSON object with these keys (string unless
otherwise noted):

* ``title`` — page title, ≤ 60 chars, topic first, brand last separated by " — ".
* ``description`` — meta description, 120–155 chars, one factual sentence.
* ``og_title`` — Open Graph title, usually the topic part of ``title``.
* ``og_description`` — Open Graph description, mirrors ``description``.
* ``og_image_alt`` — short alt for the hero image. ``""`` if no hero known.
* ``twitter_title``, ``twitter_description`` — mirror the og fields.
* ``schema_type`` — Schema.org ``@type`` for JSON-LD (``WebSite``, ``Article``, …).
* ``keywords_hint`` — array of 3–8 short keywords for the author's reference.
  *Not* meant to be emitted as ``<meta name="keywords">`` (a deprecated tag).
* ``canonical`` — included only when ``--canonical`` was passed.

Usage
-----
::

    # From a goal description only
    python meta_from_ollama.py --goal "Marketing landing for product X" \\
                               --site-name "Acme"

    # From a local HTML file
    python meta_from_ollama.py path/to/page.html --site-name "Acme"

    # From a live URL, in French, pinned to a canonical URL
    python meta_from_ollama.py https://example.com/about \\
                               --lang fr --canonical https://example.com/about

    # Bypass the on-disk cache for this single run
    python meta_from_ollama.py --goal "FAQ page" --no-cache

Standards
---------
The keys mirror the union of W3C HTML / WHATWG HTML Living Standard,
Open Graph (`ogp.me`_), Twitter Cards, Schema.org and Google Search
Central guidance. See ``sprezzature/references/meta-tags.md``.

.. _ogp.me: https://ogp.me/

Notes
-----
* Requires Python 3.10+, ``requests``. No Pillow dependency.
* Default model and endpoint are inherited from :mod:`alt_from_ollama`
  (``OLLAMA_URL``, ``OLLAMA_MODEL`` — the one model is qwen3-vl:8b).
* On-disk cache lives under ``~/.cache/sprezzature-skill/meta/`` by default.
  Override with ``SPREZZATURE_CACHE_DIR``; disable with ``SPREZZATURE_NO_CACHE=1`` or
  ``--no-cache``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path as _PathHelper

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
import urllib.request
from pathlib import Path
from typing import Optional

import click
import requests
from sprezzature_local.llm import chat as _llm_chat

# Shared Ollama helpers live in _ollama.py inside this skill folder so
# the script does not need a cross-skill import after the 0.2.0 split.
sys.path.insert(0, str(Path(__file__).parent))
from _ollama import (  # noqa: E402
    OLLAMA_URL,
    LANG_INSTRUCTIONS,
    detect_lang,
    pick_default_model,
)
from _lang import detect_text_language, extract_body_text  # noqa: E402


# ── Module-level configuration ────────────────────────────────────────────────

#: Hard limit on the size of HTML text content forwarded to the model. Pages
#: longer than this are truncated; the meta-tag task does not benefit from
#: feeding the entire DOM.
PAGE_TEXT_LIMIT: int = 6000

#: Directory where successful JSON outputs are cached. Override with the
#: ``SPREZZATURE_CACHE_DIR`` env var.
CACHE_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "meta"

#: Cache toggle, mirroring the same flag in :mod:`alt_from_ollama`.
NO_CACHE: bool = bool((os.environ.get("SPREZZATURE_NO_CACHE") or os.environ.get("FRONT_NO_CACHE")))

#: Schema-of-output fragment appended to every prompt. Kept verbatim to give
#: the model an explicit contract — ``format=json`` on the Ollama call also
#: enforces this at parse time, but the human-readable spec helps the model.
JSON_SCHEMA_HINT: str = """
Return a single JSON object, no prose around it, with exactly these keys:

  title              ≤ 60 chars, page-topic first, brand last separated by " — ".
  description        120–155 chars, one sentence, no marketing buzzwords.
  og_title           ≤ 60 chars. Usually identical to title (without brand).
  og_description     ≤ 155 chars. Usually identical to description.
  og_image_alt       Short description of the hero image content. ≤ 125 chars.
                     Empty string if no hero image is known.
  twitter_title      Same content as og_title.
  twitter_description Same content as og_description.
  schema_type        One of: WebSite, Article, NewsArticle, BlogPosting,
                     Product, Person, Recipe, Event, FAQPage,
                     LocalBusiness, Organization.
  keywords_hint      Array of 3–8 short keywords for the author's reference.
                     These are NOT meant to be emitted as <meta name="keywords">.

Rules:
  - No "Welcome to", no "Discover", no "Boost", no emojis.
  - Do not invent facts (numbers, names, claims).
  - If a value is unknown, return an empty string for it.
  - Output strict JSON — double-quoted keys and strings, no trailing comma.
"""


# ── Cache helpers ───────────────────────────────────────────────────────────

def _cache_key(goal: str, page_text: str, site_name: str, lang: str, model: str) -> str:
    """
    Compute a 32-character cache key from the inputs that affect the output.

    Parameters
    ----------
    goal : str
        Free-text goal description supplied via ``--goal``.
    page_text : str
        Text extracted from the source (HTML file or URL), or ``""``.
    site_name : str
        Brand / site name supplied via ``--site-name``.
    lang : str
        Two-letter language code.
    model : str
        Ollama model tag, e.g. ``qwen3-vl:8b``.

    Returns
    -------
    str
        32 hex characters suitable as a filename stem.
    """
    h = hashlib.sha256()
    # NUL separators avoid ambiguity when one input contains a delimiter.
    h.update(f"{goal}\x00{page_text}\x00{site_name}\x00{lang}\x00{model}".encode("utf-8"))
    return h.hexdigest()[:32]


def _cache_get(key: str) -> Optional[dict]:
    """
    Return the cached JSON object for ``key``, or ``None`` on a miss.

    A corrupt cache file is treated as a miss; the model call runs and
    rewrites the entry.
    """
    if NO_CACHE:
        return None
    path = CACHE_DIR / f"{key}.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _cache_set(key: str, value: dict) -> None:
    """
    Store ``value`` in the cache under ``key``. Failures are swallowed.

    Cache writes are opportunistic — a read-only filesystem or a quota
    exhaustion must not break the primary action.
    """
    if NO_CACHE:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        # Intentional silent fail.
        pass


# ── HTML fetching + cheap text extraction ───────────────────────────────────

def fetch_url(url: str) -> str:
    """
    Fetch an HTTP(S) URL and return the body as a string.

    Parameters
    ----------
    url : str
        Absolute ``http(s)://`` URL.

    Returns
    -------
    str
        Decoded response body. Bytes that fail to decode as UTF-8 are
        replaced with ``"?"`` (``errors="ignore"`` in ``decode``).
    """
    with urllib.request.urlopen(url, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_text(html: str, limit: int = PAGE_TEXT_LIMIT) -> str:
    """
    Return the readable body text of an HTML page, truncated to ``limit``.

    Delegates to the shared :func:`_lang.extract_body_text` (the one canonical
    HTML→text extractor across the suite — drops ``<script>`` / ``<style>``,
    strips tags, collapses whitespace) and applies the meta-specific length cap.

    Parameters
    ----------
    html : str
        Raw HTML.
    limit : int, optional
        Truncate the extracted text at this many characters. Default
        :data:`PAGE_TEXT_LIMIT`.

    Returns
    -------
    str
        Whitespace-collapsed body text, truncated to ``limit``.
    """
    return extract_body_text(html, "html")[:limit]


# ── Prompt + JSON extraction ────────────────────────────────────────────────

# ── Prompt construction ─────────────────────────────────────────────────────
#
# The prompt body and JSON schema live in
# scripts/prompts/meta_tags_json.yaml. This function only assembles the
# dynamic prefix (language line + optional brand / goal / page blocks)
# before delegating to the loader.

# Deferred import — see plain_language.py for the same pattern.
try:
    from _prompts import render as render_prompt  # type: ignore
    HAVE_PROMPTS = True
except ImportError:
    HAVE_PROMPTS = False


def build_prompt(goal: str, page_text: str, site_name: str, lang: str) -> str:
    """
    Compose the prompt sent to the model.

    Parameters
    ----------
    goal : str
        Page goal as supplied by the caller.
    page_text : str
        Extracted page text (may be empty).
    site_name : str
        Brand / site name (may be empty).
    lang : str
        Target language code.

    Returns
    -------
    str
        Full prompt ready to send to Ollama's ``/api/generate``.
    """
    lang_line: str = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["en"])
    brand_block: str = f"\nBrand / site name: {site_name}\n" if site_name else ""
    goal_block: str = f"\nPage goal: {goal}\n" if goal else ""
    page_block: str = (
        f"\nPage content (extracted text):\n{page_text}\n" if page_text else ""
    )

    if not HAVE_PROMPTS:
        # Fallback when _prompts is not importable. Keeps a usable —
        # though minimal — prompt so the script does not hard-crash.
        return (
            f"{lang_line}\n{JSON_SCHEMA_HINT}"
            f"{brand_block}{goal_block}{page_block}\nWrite the JSON now."
        )

    return render_prompt(
        "meta_tags_json",
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        lang_line=lang_line,
        brand_block=brand_block,
        goal_block=goal_block,
        page_block=page_block,
    )


def extract_json(text: str) -> dict:
    """
    Locate the first JSON object in a (possibly noisy) model reply.

    Some models still wrap their JSON in stray prose despite ``format=json``.
    The recovery is conservative — slice from the first ``{`` to the last
    ``}`` and try to parse what is between.

    Parameters
    ----------
    text : str
        Raw model output.

    Returns
    -------
    dict
        Parsed JSON object.

    Raises
    ------
    ValueError
        When no balanced braces are found.
    json.JSONDecodeError
        When the bracketed content is not valid JSON.
    """
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Model did not return JSON. Raw response:\n{text}")
    return json.loads(text[start:end + 1])


# ── CLI entry point ─────────────────────────────────────────────────────────


@sprezzature_command(
    "sprezzature-publish-meta",
    help=(
        "Draft per-page meta tags (title, description, Open Graph, Twitter "
        "Card, Schema.org @type) via a local Ollama model. Returns a strict "
        "JSON object on stdout."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-publish-meta page.html --site-name 'Acme'\n"
        "  sprezzature-publish-meta --goal 'Landing page for an ML lab' --lang en\n"
    ),
)
@click.argument("source", required=False, default=None)
@click.option(
    "--goal",
    default="",
    help="Free-text page goal.",
)
@click.option(
    "--site-name",
    "site_name",
    default="",
    help="Brand or site name.",
)
@click.option(
    "--canonical",
    default="",
    help="Canonical absolute URL. Echoed straight into the JSON output.",
)
@click.option(
    "--lang",
    default=None,
    help="BCP-47 base tag (en, fr, es, …).",
)
@click.option(
    "--no-cache",
    "no_cache",
    is_flag=True,
    default=False,
    help="Bypass the on-disk cache for this run.",
)
def _cli(
    source: Optional[str],
    goal: str,
    site_name: str,
    canonical: str,
    lang: Optional[str],
    no_cache: bool,
) -> int:
    """Click command body for ``meta_from_ollama``; returns an int exit code.

    Returns
    -------
    int
        Process exit code: ``0`` on success, ``1`` on a JSON parse failure,
        ``2`` on Ollama connectivity failure.
    """
    # The cache flag is module-level; flipping it inside the command keeps
    # the control flow in this function instead of leaking into Click.
    if no_cache:
        global NO_CACHE
        NO_CACHE = True

    # Either a source or a goal must be present; otherwise the model has
    # nothing to work from. ``UsageError`` mirrors the prior argparse
    # ``parser.error`` path so ``main()`` still raises ``SystemExit(2)``.
    if not source and not goal:
        raise click.UsageError("Provide a source (HTML path or URL) or --goal.")

    # Pull the page text first so the cache key incorporates the actual content.
    page_text: str = ""
    if source:
        if re.match(r"^https?://", source, re.I):
            page_text = extract_text(fetch_url(source))
        else:
            page_text = extract_text(
                Path(source).read_text(encoding="utf-8", errors="ignore")
            )

    # Language: explicit --lang wins. Otherwise ALWAYS detect from the
    # extracted page text via langdetect — no configured default; the
    # env/locale signal is only the no-text floor.
    if lang:
        resolved_lang: str = lang.lower()[:2]
    elif page_text:
        resolved_lang = detect_text_language(page_text, fallback=detect_lang())
    else:
        resolved_lang = detect_lang()
    # The model is fixed (qwen3-vl:8b, the one authorized LLM); not a CLI knob.
    resolved_model: str = pick_default_model()

    # Cache check — fast path returns immediately when the inputs match a
    # previous run.
    cache_k = _cache_key(goal, page_text, site_name, resolved_lang, resolved_model)
    cached = _cache_get(cache_k)
    if cached is not None:
        # The canonical URL is *not* part of the cache key (it does not affect
        # the model's output), so it is layered on at print time.
        if canonical:
            cached["canonical"] = canonical
        json.dump(cached, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    prompt = build_prompt(goal, page_text, site_name, resolved_lang)

    try:
        raw: str = str(_llm_chat(prompt, model=resolved_model))
    except requests.exceptions.ConnectionError:
        click.echo(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            f"Run `python sprezzature-accessibility/scripts/install_alt_ai.py` or `ollama serve`.",
            err=True,
        )
        return 2
    try:
        parsed = extract_json(raw)
    except Exception as e:
        # The model failed to produce parseable JSON. Surface the raw output
        # so the user can debug the prompt instead of getting a cryptic trace.
        click.echo(str(e), err=True)
        return 1

    _cache_set(cache_k, parsed)
    if canonical:
        parsed["canonical"] = canonical
    json.dump(parsed, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Delegates to the Click command; see :func:`_cli`."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
