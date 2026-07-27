#!/usr/bin/env python3
"""
translate_captions
==================

Translate an existing caption file (``.vtt`` / ``.srt``) into a second
language and emit a **two-track** ``<video>`` / ``<audio>`` snippet — the
native transcription plus a translated subtitle track.

The design mirrors the alt-text language logic in :mod:`alt_from_ollama`:
the *native* captions stay in the audio's own language (what
:mod:`captions_from_whisper` produced), and the *translation* is written in
the language of the **surrounding text** — the prose around the media on
the page — detected the same way, then translated by the one authorized
LLM (``qwen3-vl:8b`` via Ollama). W3C-correct track kinds are used:

* ``kind="captions"``  — same-language transcription (may carry sound cues);
* ``kind="subtitles"`` — dialogue translation into another language.

The translation runs on the *already-produced* ``.vtt``/``.srt``, so this
step is decoupled from the caption backend (``vocal-helper``): it never
touches audio. Cues are translated in **batched windows** (several cues per
Ollama call) so the small model sees cross-cue context and sentences that
straddle a cue boundary translate coherently; each translated segment is
re-attached to its original cue's timestamps 1:1, so timing is preserved.

Like alt-text, the translated track is a **draft** — verify before shipping.

Usage
-----
::

    # Target language detected from the page that embeds the media
    python translate_captions.py interview.vtt --in article.html

    # Explicit target language, free-form context text
    python translate_captions.py talk.vtt --lang fr --context "Une conférence sur…"

    # Print the two-track HTML snippet for a named media file
    python translate_captions.py interview.vtt --lang es --media interview.mp4

Notes
-----
* Python 3.10+. Needs a reachable local Ollama daemon
  (``http://localhost:11434``) serving ``qwen3-vl:8b`` — the one authorized
  model, not user-selectable. ``langdetect`` (declared in
  ``requirements-captions.txt``) sharpens language detection but the script
  degrades gracefully without it.
* No audio dependency — parses / re-emits captions only.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
from _lang import detect_text_language, extract_body_text, language_name  # noqa: E402
from caption_diarize import parse_caption_cues  # noqa: E402

import click  # noqa: E402


# ── Module-level configuration ────────────────────────────────────────────────

#: Default local Ollama endpoint (same as :mod:`alt_from_ollama` /
#: :mod:`name_from_transcript`).
DEFAULT_OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")

#: The one authorized model: qwen3-vl:8b (via Ollama). No other tag, no MLX.
#: Not a CLI knob; ``OLLAMA_MODEL`` survives only as a test seam.
DEFAULT_OLLAMA_MODEL: str = "qwen3-vl:8b"

#: How many cues to send per Ollama call. Big enough to give the model
#: cross-cue context (so a sentence split across cues translates as one),
#: small enough to keep the strict-JSON reply reliable on an 8B model.
DEFAULT_BATCH_SIZE: int = 8

class TranslationError(RuntimeError):
    """Raised when the model reply cannot be aligned back to the cues.

    Carrying this as its own type lets the batch driver distinguish a
    recoverable count-mismatch (retry per-cue) from a hard failure that
    must abort loudly rather than risk misaligned subtitles.
    """


# ── Language resolution ───────────────────────────────────────────────────────

def detect_source_language(cues: List[Dict[str, object]], fallback: str = "en") -> str:
    """
    Detect the caption's own (audio) language from its cue text.

    Parameters
    ----------
    cues : list of dict
        Parsed cues, each with a ``"text"`` key.
    fallback : str, optional
        Two-letter code returned when detection has no signal, by
        default ``"en"``.

    Returns
    -------
    str
        Lower-case two-letter language code.
    """
    # Concatenate a generous slice of cue text — langdetect wants ≥20
    # non-whitespace characters to commit, and a few cues rarely suffice.
    joined: str = " ".join(str(c.get("text", "")) for c in cues)
    return detect_text_language(joined, fallback=fallback)


def resolve_target_language(
    explicit: Optional[str],
    context_text: str,
    fallback: str = "en",
) -> str:
    """
    Resolve the translation's target language.

    Resolution order: an explicit ``--lang`` wins; otherwise the language
    of the surrounding text (``--context`` / ``--in`` document body) is
    detected; failing any signal, ``fallback``.

    Parameters
    ----------
    explicit : str or None
        Value of ``--lang``, or ``None`` when the user did not pass one.
    context_text : str
        Surrounding-text signal (context hint and/or embedding-document
        body) from which to detect the language.
    fallback : str, optional
        Code used when nothing else resolves, by default ``"en"``.

    Returns
    -------
    str
        Lower-case two-letter target language code.
    """
    if explicit:
        return explicit.strip().lower()[:2]
    if context_text.strip():
        return detect_text_language(context_text, fallback=fallback)
    return fallback


# ── VTT emission ──────────────────────────────────────────────────────────────

def _format_timestamp(seconds: float) -> str:
    """
    Format a time in seconds as a WebVTT ``HH:MM:SS.mmm`` timestamp.

    Parameters
    ----------
    seconds : float
        Cue time in seconds (as parsed by
        :func:`caption_diarize.parse_caption_cues`).

    Returns
    -------
    str
        WebVTT timestamp string.
    """
    total_ms: int = max(0, round(float(seconds) * 1000.0))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def render_vtt(cues: List[Dict[str, object]]) -> str:
    """
    Render translated cues as a plain WebVTT document.

    The subtitle track is dialogue-only (no ``<v Name>`` voice tags): W3C
    reserves those for the same-language ``captions`` track, and
    :func:`caption_diarize.parse_caption_cues` has already stripped them.

    Parameters
    ----------
    cues : list of dict
        Cues with ``"start"`` / ``"end"`` (seconds) and translated
        ``"text"``.

    Returns
    -------
    str
        A WebVTT document, ready to write to ``<stem>.<lang>.vtt``.
    """
    lines: List[str] = ["WEBVTT", ""]
    for cue in cues:
        text: str = str(cue.get("text", "")).strip()
        if not text:
            continue
        start: str = _format_timestamp(float(cue["start"]))  # type: ignore[arg-type]
        end: str = _format_timestamp(float(cue["end"]))  # type: ignore[arg-type]
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ── Translation core (pure — Ollama injected as a seam) ────────────────────────

def translate_cues(
    cues: List[Dict[str, object]],
    *,
    translate_batch: Callable[[List[str]], List[str]],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[Dict[str, object]]:
    """
    Translate cue text in batched windows, preserving timestamps 1:1.

    Each window of ``batch_size`` cues is handed to ``translate_batch`` in
    one call so the model sees cross-cue context. When a window comes back
    with the wrong number of segments (the small model merged or split
    lines), the window is retried **one cue at a time** — which cannot
    misalign. If even a single-cue call fails to return exactly one
    segment, the function raises rather than emit misaligned subtitles.

    Parameters
    ----------
    cues : list of dict
        Parsed cues (``"start"`` / ``"end"`` / ``"text"``).
    translate_batch : callable
        ``list[str] -> list[str]`` translating a window of cue texts,
        preserving order and count. Injected so tests need no daemon.
    batch_size : int, optional
        Cues per window, by default :data:`DEFAULT_BATCH_SIZE`.

    Returns
    -------
    list of dict
        New cue dicts with the same timestamps and translated ``"text"``.

    Raises
    ------
    TranslationError
        When a per-cue retry still cannot yield a 1:1 alignment.
    """
    texts: List[str] = [str(c.get("text", "")) for c in cues]
    out_texts: List[str] = []

    for i in range(0, len(texts), batch_size):
        window: List[str] = texts[i : i + batch_size]

        # Fast path: translate the whole window in one call for context.
        try:
            translated: List[str] = translate_batch(window)
            if len(translated) != len(window):
                # Count mismatch — the model merged/split lines. Fall
                # through to the per-cue path, which cannot misalign.
                raise TranslationError("window count mismatch")
        except TranslationError:
            translated = []
            for one_text in window:
                single: List[str] = translate_batch([one_text])
                if len(single) != 1:
                    # A single cue must map to exactly one segment. If not,
                    # abort loudly — never silently drop or shift cues.
                    raise TranslationError(
                        "single-cue translation did not return exactly one "
                        "segment; aborting to avoid misaligned subtitles"
                    )
                translated.append(single[0])

        out_texts.extend(translated)

    # Re-attach translations to their original timestamps in order.
    return [{**cue, "text": new_text} for cue, new_text in zip(cues, out_texts)]


# ── Ollama plumbing (the one authorized LLM: qwen3-vl:8b) ────────────────────────

def _reachable(url: str) -> bool:
    """
    Return ``True`` when the Ollama daemon answers ``/api/tags``.

    Parameters
    ----------
    url : str
        Ollama base URL.

    Returns
    -------
    bool
        Whether the daemon responded within the probe timeout.
    """
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=1.5) as fh:
            return fh.status == 200
    except Exception:  # noqa: BLE001 — any failure means "not reachable".
        return False


def _resolve_ollama_model(base: str) -> str:
    """
    Return the model tag to send: the ``OLLAMA_MODEL`` test seam, else ``base``.

    Parameters
    ----------
    base : str
        The canonical model (``qwen3-vl:8b``).

    Returns
    -------
    str
        Model tag. ``OLLAMA_MODEL`` exists only so tests can point at a
        stub; it is never surfaced as a user-facing option.
    """
    return os.environ.get("OLLAMA_MODEL", "").strip() or base


def make_ollama_translator(
    *,
    url: str,
    model: str,
    source_lang: str,
    target_lang: str,
) -> Callable[[List[str]], List[str]]:
    """
    Build a ``list[str] -> list[str]`` translator backed by local Ollama.

    The returned callable sends a window of cue texts as a numbered JSON
    object and expects the same keys back, each value translated. Order
    and count are reconstructed from the keys, so the reply is robust to
    key reordering.

    Parameters
    ----------
    url : str
        Ollama endpoint.
    model : str
        Model tag (``qwen3-vl:8b``).
    source_lang : str
        Two-letter source language code (a hint for the model).
    target_lang : str
        Two-letter target language code.

    Returns
    -------
    callable
        The batch translator injected into :func:`translate_cues`.
    """
    target_name: str = language_name(target_lang, default=target_lang)
    source_name: str = language_name(source_lang, default=source_lang)

    system: str = (
        f"You are a professional subtitle translator. Translate each "
        f"numbered caption line from {source_name} into {target_name}. "
        f"Keep the meaning and register; keep each line concise enough to "
        f"read on screen. Return STRICT JSON only — no prose, no markdown: "
        f"an object whose keys are exactly the input keys and whose values "
        f"are the translations. Do not merge, split, add, or drop keys."
    )

    def translate(window: List[str]) -> List[str]:
        """Translate one window of cue texts via Ollama, preserving order."""
        # Number the lines 1..K so we can map the reply back positionally.
        payload: Dict[str, str] = {str(n + 1): text for n, text in enumerate(window)}
        body: Dict[str, object] = {
            "model": model,
            "system": system,
            "prompt": json.dumps(payload, ensure_ascii=False),
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 8192},
        }
        req = urllib.request.Request(
            url.rstrip("/") + "/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as fh:
                reply = json.loads(fh.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise TranslationError(f"Ollama call failed: {exc}") from exc

        raw: str = str(reply.get("response", "")).strip()
        try:
            mapping = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranslationError(f"model did not return JSON: {raw[:80]!r}") from exc
        if not isinstance(mapping, dict):
            raise TranslationError("model reply was not a JSON object")

        # Rebuild the list positionally; a missing key means a length
        # mismatch, which the caller turns into a per-cue retry.
        out: List[str] = []
        for n in range(1, len(window) + 1):
            value = mapping.get(str(n))
            if not isinstance(value, str):
                raise TranslationError(f"missing / non-string translation for line {n}")
            out.append(value.strip())
        return out

    return translate


# ── Two-track snippet ──────────────────────────────────────────────────────────

def two_track_snippet(
    *,
    media: str,
    native_vtt: str,
    translated_vtt: str,
    audio_lang: str,
    target_lang: str,
) -> str:
    """
    Build the two-``<track>`` HTML snippet (native captions + translation).

    Parameters
    ----------
    media : str
        Media file name/URL for the ``<source>``.
    native_vtt : str
        File name of the native-language ``captions`` track.
    translated_vtt : str
        File name of the translated ``subtitles`` track.
    audio_lang : str
        Two-letter code of the audio (native captions) language.
    target_lang : str
        Two-letter code of the translation language.

    Returns
    -------
    str
        A ready-to-paste ``<video>`` element with both tracks.
    """
    native_label: str = language_name(audio_lang, default=audio_lang)
    target_label: str = language_name(target_lang, default=target_lang)
    return (
        "<video controls>\n"
        f'  <source src="{media}" />\n'
        f'  <track kind="captions" srclang="{audio_lang}" '
        f'label="{native_label}" src="{native_vtt}" default />\n'
        f'  <track kind="subtitles" srclang="{target_lang}" '
        f'label="{target_label}" src="{translated_vtt}" />\n'
        "</video>"
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

@sprezzature_command(
    "sprezzature-audio-translate",
    help=(
        "Translate an existing .vtt/.srt into the surrounding-text language "
        "via the local Ollama model and emit a two-track <video> snippet "
        "(native captions + translated subtitles). Runs on captions only — "
        "no audio, decoupled from the caption backend."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-translate interview.vtt --in article.html\n"
        "  sprezzature-audio-translate talk.vtt --lang fr --media talk.mp4\n"
    ),
)
@click.argument("captions", type=click.Path(path_type=Path))
@click.option("--lang", "-l", "target_lang", default=None,
              help="Target language code (e.g. fr, es). Default: detect from "
                   "the surrounding text (--in / --context).")
@click.option("--in", "in_doc", type=click.Path(path_type=Path), default=None,
              help="Document embedding the media; its body text is the "
                   "surrounding-text signal for language detection.")
@click.option("--context", "-c", default="",
              help="Free-form surrounding text used to detect the target "
                   "language when --lang is omitted.")
@click.option("--media", default=None,
              help="Media file name for the emitted <source>. "
                   "Default: derived from the captions file name.")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output translated .vtt. Default: sibling "
                   "'<stem>.<lang>.vtt'.")
@click.option("--url", "ollama_url", default=DEFAULT_OLLAMA_URL, show_default=True,
              help="Ollama endpoint URL.")
@click.option("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, show_default=True,
              help="Cues translated per model call.")
def _cli(
    captions: Path,
    target_lang: Optional[str],
    in_doc: Optional[Path],
    context: str,
    media: Optional[str],
    out: Optional[Path],
    ollama_url: str,
    batch_size: int,
) -> int:
    """Click command body; returns an int exit code."""
    if not captions.is_file():
        click.echo(f"No such file: {captions}", err=True)
        return 1

    cues = parse_caption_cues(captions.read_text(encoding="utf-8"))
    if not cues:
        click.echo(f"No caption cues found in {captions}", err=True)
        return 1

    # Assemble the surrounding-text signal for language detection: the
    # explicit --context plus the embedding document's body text.
    context_text: str = context
    if in_doc is not None:
        if not in_doc.is_file():
            click.echo(f"No such file: {in_doc}", err=True)
            return 1
        doc_body: str = extract_body_text(in_doc.read_text(encoding="utf-8"))
        context_text = (context + "\n" + doc_body).strip() if context else doc_body

    source_lang: str = detect_source_language(cues)
    resolved_target: str = resolve_target_language(target_lang, context_text)

    # Nothing to translate when the surrounding text is already the audio's
    # language — emit a note and stop (the native captions stand alone).
    if resolved_target == source_lang:
        click.echo(
            f"Source and target language match ({source_lang}); "
            "no translation track needed.",
            err=True,
        )
        return 0

    # Translation requires the model — fail loud if the daemon is absent,
    # unlike the optional LLM refinement in name_from_transcript.
    if not _reachable(ollama_url):
        click.echo(
            f"Ollama not reachable at {ollama_url}. Start it and pull the "
            "model:\n    ollama serve\n    ollama pull qwen3-vl:8b",
            err=True,
        )
        return 1

    resolved_model: str = _resolve_ollama_model(DEFAULT_OLLAMA_MODEL)
    click.echo(
        f"→ Translating {len(cues)} cues {source_lang}→{resolved_target} "
        f"via Ollama ({resolved_model} @ {ollama_url})…",
        err=True,
    )
    translator = make_ollama_translator(
        url=ollama_url,
        model=resolved_model,
        source_lang=source_lang,
        target_lang=resolved_target,
    )
    try:
        translated_cues = translate_cues(cues, translate_batch=translator, batch_size=batch_size)
    except TranslationError as exc:
        click.echo(f"Translation failed: {exc}", err=True)
        return 1

    out_path: Path = out or Path(str(captions.with_suffix("")) + f".{resolved_target}.vtt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_vtt(translated_cues) + "\n", encoding="utf-8")
    click.echo(f"→ Wrote {out_path}")

    # Print the two-track snippet so the user can paste both tracks at once.
    media_name: str = media or (captions.stem + ".mp4")
    click.echo("\n" + two_track_snippet(
        media=media_name,
        native_vtt=captions.name,
        translated_vtt=out_path.name,
        audio_lang=source_lang,
        target_lang=resolved_target,
    ))
    click.echo(
        "\n(Draft translation — verify before shipping.)", err=True,
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Writes ``<stem>.<lang>.vtt`` next to the input."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
