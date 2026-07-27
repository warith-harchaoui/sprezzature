#!/usr/bin/env python3
"""
captions_from_whisper
=====================

Generate captions / transcripts for an audio or video file through
``vocal-helper`` — the project author's whisper.cpp over-layer (which wraps
the ``pywhispercpp`` binding, owns the model defaults, the word-timestamp
wiring, the hallucination guard, and the vocabulary-biasing prompt lever).

The companion installer (``install_captions.py``) pre-downloads the GGML
weights into the shared cache; ``vocal-helper`` (and its transitive
``pywhispercpp``) is declared in ``requirements-captions.txt``.

The script accepts any common container (mp4, mov, mp3, wav, m4a, …),
extracts a 16 kHz mono WAV stream (which whisper.cpp expects), decodes it
to a float32 buffer via ``audio-helper``, drives it through
``vocal-helper``'s ``WhisperStage`` as a single whole-file segment (no VAD,
no diarization — that lives in the ``diarize`` tier), then formats the
segments as WebVTT (default), SRT, or plain text.

Cache shape mirrors :mod:`alt_from_ollama`: SHA-256 of (extracted-audio
bytes + model + lang + format), short hex name, stored under
``~/.cache/sprezzature-skill/captions/``.

Usage
-----
::

    # Captions for a video → input.vtt next to the file
    python captions_from_whisper.py video.mp4

    # Plain transcript for an audio-only file
    python captions_from_whisper.py podcast.mp3 --format text

    # Specific language + SRT
    python captions_from_whisper.py interview.wav --lang fr --format srt

    # Override the model (smaller / faster)
    python captions_from_whisper.py call.m4a --model small

Notes
-----
* Python 3.10+. ``vocal-helper`` (pulling ``pywhispercpp``) is declared in
  ``requirements-captions.txt``; :mod:`install_captions` pre-downloads the
  GGML weights.
* Audio extraction and decoding use ``video-helper`` / ``audio-helper``
  from the project author's GitHub (hard dependencies of this tier),
  ``ffmpeg`` as a last-resort extraction fallback.

.. _audio-helper: https://github.com/warith-harchaoui/audio-helper
.. _video-helper: https://github.com/warith-harchaoui/video-helper

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path as _PathHelper

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click

if TYPE_CHECKING:
    import numpy

# Vocabulary + language helpers — shared with the other Ollama-backed scripts.
sys.path.insert(0, str(Path(__file__).parent))
from _vocab import resolve_vocab_terms  # noqa: E402
from _lang import detect_text_language  # noqa: E402


# ── Module-level configuration ────────────────────────────────────────────────

#: Cache directory shared with the rest of the skill's helpers.
CACHE_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "captions"

#: Where install_captions.py pre-downloads GGML weights. The model loader
#: reads from this directory, falling back to ``pywhispercpp``'s own download.
WHISPER_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "whisper"

#: Cache toggle, mirroring the other helpers.
NO_CACHE: bool = bool((os.environ.get("SPREZZATURE_NO_CACHE") or os.environ.get("FRONT_NO_CACHE")))

#: Default model alias if the user does not pass ``--model``.
DEFAULT_MODEL: str = "large-v3-turbo"

#: Extensions recognized as video containers (have an audio track to extract).
VIDEO_EXTS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"})


# ── Audio extraction (helper libs first, ffmpeg fallback) ───────────────────

def extract_audio(src: Path, dst: Path) -> None:
    """
    Re-encode the audio track of ``src`` to a 16 kHz mono WAV at ``dst``.

    The helper libraries `audio-helper`_ / `video-helper`_ are tried first;
    if either is unavailable, the function falls back to a ``ffmpeg``
    subprocess.

    Parameters
    ----------
    src : Path
        Source audio or video file.
    dst : Path
        Output WAV path. The parent directory is created if missing.

    Raises
    ------
    SystemExit
        On any extraction failure (no helper, no ``ffmpeg``).

    .. _audio-helper: https://github.com/warith-harchaoui/audio-helper
    .. _video-helper: https://github.com/warith-harchaoui/video-helper
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Optimistic import — the helpers are not required.
    try:
        from video_helper import extract_audio_track  # type: ignore
        if src.suffix.lower() in VIDEO_EXTS:
            extract_audio_track(str(src), str(dst), sample_rate=16000, channels=1)
            return
    except ImportError:
        pass
    try:
        from audio_helper import sound_converter  # type: ignore
        sound_converter(str(src), str(dst), freq=16000, channels=1)
        return
    except ImportError:
        pass

    # ffmpeg fallback. Quiet, single-pass, overwrite if present.
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "Neither `audio-helper` / `video-helper` nor `ffmpeg` is available.\n"
            "Install one of:\n"
            "    pip install audio-helper   (PyPI)\n"
            "    pip install video-helper   (PyPI)\n"
            "    brew install ffmpeg   (macOS / Homebrew — https://brew.sh)\n"
            "    apt install ffmpeg    (Debian / Ubuntu)\n"
            "    winget install Gyan.FFmpeg   (Windows)\n"
        )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src),
         "-ac", "1", "-ar", "16000", str(dst)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # Guard against a wedged ffmpeg on a corrupt/streaming input. Audio
        # extraction is fast; 30 min is generous even for a feature-length file.
        timeout=1800,
    )


# ── Prompt composition ─────────────────────────────────────────────────────

#: Hard cap on the initial-prompt length. Whisper's encoder context limits
#: the prompt to ~224 tokens; ~150 words is a safe ceiling in any language.
MAX_PROMPT_WORDS: int = 150

#: Per-language opening sentence for the composed prompt. The natural prose
#: pattern beats a bare comma-separated list — whisper.cpp was trained on
#: continuous text.
PROMPT_OPENERS: dict[str, str] = {
    "en": "The following terms may appear in the audio:",
    "fr": "Les termes suivants peuvent apparaître dans l'audio :",
    "es": "Los siguientes términos pueden aparecer en el audio:",
    "de": "Folgende Begriffe können im Audio vorkommen:",
    "it": "I seguenti termini possono apparire nell'audio:",
    "pt": "Os seguintes termos podem aparecer no áudio:",
    "nl": "De volgende termen kunnen in de audio voorkomen:",
    "ar": "قد تظهر المصطلحات التالية في الصوت:",
    "ja": "以下の用語が音声に現れる可能性があります：",
    "zh": "以下术语可能出现在音频中：",
}


def compose_prompt(vocab: list[str], lang: str) -> str:
    """
    Compose a natural-prose ``initial_prompt`` from a vocabulary list.

    The output is a single sentence in ``lang`` listing the terms,
    truncated so the whole prompt stays under :data:`MAX_PROMPT_WORDS`
    words. Whisper's prompt encoder caps around 224 tokens — staying
    under ~150 words leaves headroom across every supported language.

    Parameters
    ----------
    vocab : list of str
        Terms to mention.
    lang : str
        Two-letter language code; selects the opener phrasing.

    Returns
    -------
    str
        Composed prompt, or an empty string when ``vocab`` is empty.
    """
    if not vocab:
        return ""
    opener: str = PROMPT_OPENERS.get(lang, PROMPT_OPENERS["en"])
    # Truncate the term list so the full sentence stays under the cap.
    # ``opener`` is short — well under 10 words; the rest of the budget
    # belongs to the terms themselves.
    budget: int = MAX_PROMPT_WORDS - len(opener.split())
    kept: list[str] = []
    running: int = 0
    for term in vocab:
        word_count: int = len(term.split())
        if running + word_count > budget:
            break
        kept.append(term)
        running += word_count
    if not kept:
        # Single very-long term; truncate it word-wise so we still produce
        # *something* useful.
        kept = [" ".join(vocab[0].split()[:budget])]
    return f"{opener} {', '.join(kept)}."


def resolve_vocab(
    source: Path,
    *,
    prompt: str,
    vocab_file: Optional[Path],
    vocab_from: Optional[Path],
    auto_project: bool,
    lang: str,
) -> str:
    """
    Resolve the final ``initial_prompt`` from the available inputs.

    Thin adapter on top of :func:`_vocab.resolve_vocab_terms` — adds the
    explicit-prompt shortcut and runs the captions-specific
    :func:`compose_prompt` over the extracted terms.

    Parameters
    ----------
    source : Path
        Audio / video file.
    prompt : str
        Value of ``--prompt`` (empty when unused).
    vocab_file : Path or None
        Value of ``--vocab``.
    vocab_from : Path or None
        Value of ``--vocab-from`` (file or directory).
    auto_project : bool
        When ``True``, find the project root and use the whole tree.
    lang : str
        Two-letter language code, used by :func:`compose_prompt`.

    Returns
    -------
    str
        Final initial-prompt text. May be empty.
    """
    if prompt:
        return prompt
    terms: list[str] = resolve_vocab_terms(
        source,
        vocab_file=vocab_file,
        vocab_from=vocab_from,
        auto_project=auto_project,
    )
    return compose_prompt(terms, lang)


# ── Cache helpers ───────────────────────────────────────────────────────────

def _cache_key(audio: bytes, model_name: str, lang: str, fmt: str, prompt: str) -> str:
    """
    Compute a 32-character cache key from the inputs that affect the output.

    Parameters
    ----------
    audio : bytes
        Bytes of the extracted 16 kHz mono WAV.
    model_name : str
        Model alias used for this run (e.g. ``large-v3-turbo``).
    lang : str
        Two-letter language code, or empty for autodetect.
    fmt : str
        Output format (``vtt`` / ``srt`` / ``text``).
    prompt : str
        Composed ``initial_prompt`` (vocabulary biasing). Empty when no
        prompt was supplied.

    Returns
    -------
    str
        32 hex characters.
    """
    h = hashlib.sha256()
    h.update(audio)
    h.update(b"\x00")
    h.update(f"{model_name}\x00{lang}\x00{fmt}\x00{prompt}".encode("utf-8"))
    return h.hexdigest()[:32]


def _cache_get(key: str) -> Optional[str]:
    """Return cached output for ``key``, or ``None`` on a miss."""
    if NO_CACHE:
        return None
    for ext in ("vtt", "srt", "txt"):
        path = CACHE_DIR / f"{key}.{ext}"
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def _cache_set(key: str, text: str, fmt: str) -> None:
    """Store ``text`` in the cache. Failures are swallowed."""
    if NO_CACHE:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ext = "txt" if fmt == "text" else fmt
        (CACHE_DIR / f"{key}.{ext}").write_text(text, encoding="utf-8")
    except OSError:
        pass


# ── Time formatting ─────────────────────────────────────────────────────────

def _format_timestamp(centiseconds: int, *, srt: bool = False) -> str:
    """
    Format a timestamp expressed in 10-ms units as ``HH:MM:SS.mmm`` (VTT)
    or ``HH:MM:SS,mmm`` (SRT).

    Parameters
    ----------
    centiseconds : int
        Time value in 10-ms units, as returned by pywhispercpp.
    srt : bool, optional
        Format with a comma decimal separator for SRT.

    Returns
    -------
    str
        Formatted timestamp string.
    """
    total_ms: int = max(0, int(centiseconds)) * 10
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, ms = divmod(rem, 1_000)
    sep: str = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{ms:03d}"


# ── Segment → output format ─────────────────────────────────────────────────

def segments_to_vtt(segments: list) -> str:
    """
    Render pywhispercpp segments as a WebVTT document.

    Parameters
    ----------
    segments : list
        Sequence of ``pywhispercpp.model.Segment`` instances, each with
        ``t0``, ``t1`` (10-ms units), and ``text`` attributes.

    Returns
    -------
    str
        WebVTT document, ready to write to ``<file>.vtt``.
    """
    lines: list[str] = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp(seg.t0)
        end = _format_timestamp(seg.t1)
        text = seg.text.strip()
        if not text:
            continue
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def segments_to_srt(segments: list) -> str:
    """
    Render pywhispercpp segments as a SubRip (SRT) document.

    Parameters
    ----------
    segments : list
        Sequence of ``pywhispercpp.model.Segment`` instances.

    Returns
    -------
    str
        SRT document.
    """
    lines: list[str] = []
    idx: int = 1
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        start = _format_timestamp(seg.t0, srt=True)
        end = _format_timestamp(seg.t1, srt=True)
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
        idx += 1
    return "\n".join(lines)


def segments_to_text(segments: list) -> str:
    """
    Render pywhispercpp segments as a plain transcript with paragraph
    breaks on long pauses.

    Long pauses are defined as ``> 1.5 s`` between consecutive segments;
    they introduce a blank line so the transcript reads as paragraphs
    rather than as one wall of text.

    Parameters
    ----------
    segments : list
        Sequence of ``pywhispercpp.model.Segment`` instances.

    Returns
    -------
    str
        Plain text transcript.
    """
    out: list[str] = []
    prev_t1: Optional[int] = None
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        # Pause threshold in 10-ms units → 1.5 s == 150.
        if prev_t1 is not None and seg.t0 - prev_t1 > 150:
            out.append("")
        out.append(text)
        prev_t1 = seg.t1
    # End the file with a single trailing newline.
    return "\n".join(out) + "\n"


# ── Model loading + transcription ───────────────────────────────────────────

def _resolve_model_arg(model: str) -> str:
    """
    Resolve the ``--model`` argument to whatever ``pywhispercpp.Model``
    accepts.

    Resolution order:

    1. ``SPREZZATURE_WHISPER_MODEL`` env var → absolute path (explicit override).
    2. Pre-downloaded ``WHISPER_DIR / ggml-<alias>.bin`` → absolute path.
    3. The bare alias → pywhispercpp downloads on demand.

    Parameters
    ----------
    model : str
        Model alias supplied by the caller.

    Returns
    -------
    str
        Either an absolute filesystem path or the bare alias.
    """
    if override := (os.environ.get("SPREZZATURE_WHISPER_MODEL") or os.environ.get("FRONT_WHISPER_MODEL")):
        return override
    cached: Path = WHISPER_DIR / f"ggml-{model}.bin"
    if cached.is_file():
        return str(cached)
    return model


def _pcm_from_wav(wav_path: Path) -> tuple["numpy.ndarray", int]:  # noqa: F821
    """
    Load ``wav_path`` as a mono float32 buffer at 16 kHz for whisper.cpp.

    Uses ``audio-helper``'s :func:`audio_helper.load_audio` (a hard
    dependency of the captions tier) so the resampling / mono-mixdown
    path is shared with the rest of the author's audio stack rather than
    re-implemented here.

    Parameters
    ----------
    wav_path : pathlib.Path
        A WAV file (already 16 kHz mono, but re-resolved defensively).

    Returns
    -------
    tuple[numpy.ndarray, int]
        ``(pcm, sample_rate)`` — ``pcm`` is 1-D ``float32`` in [-1, 1].
    """
    import numpy as np
    from audio_helper import load_audio  # type: ignore

    pcm, sample_rate = load_audio(
        str(wav_path), target_sample_rate=16000, to_mono=True, to_numpy=True
    )
    return np.asarray(pcm, dtype=np.float32), int(sample_rate)


def _run_whisper_stage(
    pcm: "numpy.ndarray",  # noqa: F821
    sample_rate: int,
    *,
    model_arg: str,
    lang: str,
    initial_prompt: str,
) -> list:
    """
    Transcribe a whole-file PCM buffer through ``vocal-helper``'s
    :class:`vocal_helper.asr.WhisperStage` and adapt the result back to
    the centisecond ``Segment``-shaped objects the renderers expect.

    ``vocal-helper`` is the author's whisper.cpp over-layer: it owns the
    model defaults (``large-v3-turbo-q5_0``), the ``token_timestamps``
    wiring, the ``min_segment_ms`` hallucination guard, and the
    ``initial_prompt`` vocabulary-biasing lever. The captions tier drives
    it as a single whole-file segment — no VAD, no diarization (that
    lives in the separate ``diarize`` tier) — so this stays the light,
    offline caption path while delegating the actual STT to the helper.

    The stage's public contract is the ``run(inbox, outbox)`` coroutine
    consuming :class:`~vocal_helper.types.DiarizedSegment` and emitting
    :class:`~vocal_helper.types.Utterance`; we feed one segment plus the
    ``None`` sentinel and drain the utterances.

    Parameters
    ----------
    pcm : numpy.ndarray
        Mono ``float32`` samples in [-1, 1].
    sample_rate : int
        Sample rate of ``pcm`` (16 kHz for whisper.cpp).
    model_arg : str
        Absolute GGML path (from :func:`_resolve_model_arg`) or a bare
        alias for ``vocal-helper`` / pywhispercpp to download on demand.
    lang : str
        Two-letter language code, or empty for autodetect.
    initial_prompt : str
        Vocabulary-biasing prompt.

    Returns
    -------
    list
        ``SimpleNamespace`` items with ``t0`` / ``t1`` (10-ms units) and
        ``text`` — the shape :func:`segments_to_vtt` and friends consume.
    """
    import asyncio
    from types import SimpleNamespace

    from vocal_helper.asr import WhisperStage  # type: ignore
    from vocal_helper.types import DiarizedSegment  # type: ignore

    sr: int = int(sample_rate) or 16000
    segment: DiarizedSegment = {
        "t0": 0.0,
        "t1": float(len(pcm)) / float(sr),
        "sample_rate": sr,
        "speaker": "S0",
        "pcm": pcm,
    }
    stage = WhisperStage(
        model=model_arg,
        language=(lang or "auto"),
        initial_prompt=initial_prompt,
    )

    async def _drive() -> list:
        """Drive one segment through the async caption stage and return its cues."""
        inbox: asyncio.Queue = asyncio.Queue()
        outbox: asyncio.Queue = asyncio.Queue()
        await inbox.put(segment)
        await inbox.put(None)
        await stage.run(inbox, outbox)
        utterances: list = []
        while True:
            item = await outbox.get()
            if item is None:
                break
            utterances.append(item)
        return utterances

    utterances = asyncio.run(_drive())

    # ``Utterance.words`` is a list of ``(t0_sec, t1_sec, text)`` triplets —
    # whisper's segment-level cues when driven on a whole file. Convert the
    # seconds back to the centisecond units the renderers were written for.
    segments: list = []
    for utt in utterances:
        for start_s, end_s, word_text in utt.get("words", []):
            segments.append(
                SimpleNamespace(
                    t0=int(round(float(start_s) * 100)),
                    t1=int(round(float(end_s) * 100)),
                    text=word_text,
                )
            )
    return segments


def transcribe(
    src: Path,
    *,
    model: str = DEFAULT_MODEL,
    lang: str = "",
    fmt: str = "vtt",
    initial_prompt: str = "",
) -> str:
    """
    Transcribe ``src`` and return the output as a string.

    Parameters
    ----------
    src : Path
        Audio or video file path.
    model : str, optional
        Model alias from :mod:`install_captions`. Default ``large-v3-turbo``.
    lang : str, optional
        Two-letter language code. Empty (default) lets the model
        autodetect.
    fmt : str, optional
        Output format: ``vtt`` (default), ``srt``, or ``text``.
    initial_prompt : str, optional
        Vocabulary-biasing prompt passed to whisper.cpp. Use
        :func:`compose_prompt` or :func:`resolve_vocab` to build it
        from a glossary or project tree.

    Returns
    -------
    str
        File contents in the requested format.
    """
    # The heavy work is deferred behind the ``_pcm_from_wav`` /
    # ``_run_whisper_stage`` seams so this module stays importable for the
    # renderer tests without ``vocal-helper`` / ``audio-helper`` present,
    # and so callers can stub the STT step directly.
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "input.wav"
        extract_audio(src, wav_path)
        audio_bytes: bytes = wav_path.read_bytes()

        key = _cache_key(audio_bytes, model, lang, fmt, initial_prompt)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        # Resolve a local GGML path when we have one; otherwise pass the
        # alias straight through and let vocal-helper / pywhispercpp manage
        # the download.
        model_arg: str = _resolve_model_arg(model)

        # Decode to a 16 kHz mono float32 buffer (audio-helper), then run it
        # through vocal-helper's WhisperStage as a single whole-file segment.
        pcm, sample_rate = _pcm_from_wav(wav_path)
        segments = _run_whisper_stage(
            pcm,
            sample_rate,
            model_arg=model_arg,
            lang=lang,
            initial_prompt=initial_prompt,
        )

        if fmt == "vtt":
            text = segments_to_vtt(segments)
        elif fmt == "srt":
            text = segments_to_srt(segments)
        else:
            text = segments_to_text(segments)

        _cache_set(key, text, fmt)
        return text


# ── CLI entry point ───────────────────────────────────────────────────────


@sprezzature_command(
    "sprezzature-audio-captions",
    help=(
        "Generate WebVTT / SRT / plain-text captions or a transcript from "
        "an audio or video file via local vocal-helper (whisper.cpp). "
        "Project-vocab biasing "
        "via --prompt / --vocab / --vocab-from / --auto-project."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-captions talk.mp4\n"
        "  sprezzature-audio-captions podcast.mp3 --format text --lang en\n"
        "  sprezzature-audio-captions interview.wav --lang fr --format srt\n"
    ),
)
@click.argument("source", type=click.Path(path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["vtt", "srt", "text"]),
    default="vtt",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--lang",
    default="",
    help="Two-letter language code. Empty lets whisper.cpp autodetect.",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Model alias.",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path. Default: sibling of the source with the format extension.",
)
@click.option(
    "--no-cache",
    "no_cache",
    is_flag=True,
    default=False,
    help="Bypass the on-disk cache for this run.",
)
# Vocabulary biasing. ``--prompt`` wins outright; the other three are
# equivalent extraction sources whose extracted terms are composed into
# the script's initial_prompt template.
@click.option(
    "--prompt",
    default="",
    help="Verbatim text passed to whisper.cpp as initial_prompt.",
)
@click.option(
    "--vocab",
    type=click.Path(path_type=Path),
    default=None,
    help="Glossary file; one term per line; '#' starts a comment.",
)
@click.option(
    "--vocab-from",
    "vocab_from",
    type=click.Path(path_type=Path),
    default=None,
    help="File or directory whose text is mined for proper nouns and identifiers.",
)
@click.option(
    "--auto-project",
    "auto_project",
    is_flag=True,
    default=False,
    help=(
        "Walk upward from the source to find the project root, then "
        "collect vocabulary from the whole tree."
    ),
)
def _cli(
    source: Path,
    fmt: str,
    lang: str,
    model: str,
    out: Optional[Path],
    no_cache: bool,
    prompt: str,
    vocab: Optional[Path],
    vocab_from: Optional[Path],
    auto_project: bool,
) -> int:
    """Click command body for ``captions_from_whisper``; returns an int code.

    Writes the transcript to a sibling file by default (or to ``--out``
    when supplied), prints the destination path to stdout, and exits ``1``
    when the source is missing. Behaviour is identical to the prior
    argparse-driven ``main``.
    """
    if no_cache:
        global NO_CACHE
        NO_CACHE = True

    if not source.is_file():
        click.echo(f"No such file: {source}", err=True)
        return 1

    # Language for the opener: explicit --lang wins. Otherwise ALWAYS detect
    # by sniffing the vocabulary sources via langdetect — no configured
    # default; "en" is only the no-signal floor.
    vocab_lang: str = lang
    if not vocab_lang:
        sniff: str = ""
        if vocab_from is not None and vocab_from.is_file():
            sniff = vocab_from.read_text(encoding="utf-8", errors="ignore")[:4000]
        elif vocab is not None and vocab.is_file():
            sniff = vocab.read_text(encoding="utf-8", errors="ignore")[:4000]
        if sniff:
            vocab_lang = detect_text_language(sniff, fallback="en")
        else:
            vocab_lang = "en"

    initial_prompt: str = resolve_vocab(
        source,
        prompt=prompt,
        vocab_file=vocab,
        vocab_from=vocab_from,
        auto_project=auto_project,
        lang=vocab_lang,
    )

    text = transcribe(
        source,
        model=model,
        lang=lang,
        fmt=fmt,
        initial_prompt=initial_prompt,
    )

    # Resolve a sibling output path.
    ext: str = "txt" if fmt == "text" else fmt
    out_path: Path = out or source.with_suffix(f".{ext}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"→ Wrote {out_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Writes the output to a sibling file by default."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
