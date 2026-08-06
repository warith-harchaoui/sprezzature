#!/usr/bin/env python3
"""
narrate_post
============

Generate an audio narration of a Markdown post (blog article, doc page,
essay) using a local OSS text-to-speech engine. Output is **optional
editorial enhancement** — pre-recorded audio of long-form text is
*not* a WCAG 2.x requirement (screen readers already cover that case).
The use cases are: multitasking audience, podcast positioning, and
cognitive-accessibility "alternative format" (WAI-COGA direction).

Pipeline
--------
1. ``_narrate.extract_segments`` parses the Markdown into a list of
   structured segments (heading, paragraph, list item, blockquote).
   Each segment carries baseline narration hints derived from the
   Markdown structure (pause lengths, emotion from leading emoji,
   pace from frontmatter ``narration.tone``).
2. ``_narrate.load_pronunciation`` / ``apply_pronunciation`` adjust
   the prose so brand names / acronyms are spoken correctly.
3. **Optional** ``--ai-hints`` calls a local Ollama vision-or-text
   model per segment and enriches the hints with semantic context
   the structure alone cannot see (sarcasm, build-up before a
   punchline, pacing). Defaults to off — the deterministic
   structural path stays the baseline.
4. The chosen engine wrapper (``narrate_openvoice.py`` or
   ``narrate_chatterbox.py``) runs as a subprocess and synthesises
   one WAV per segment, then concatenates with the requested pauses.
5. A manifest entry is written to ``out/audio/manifest.json``
   recording source path, audio path, engine, voice, sha256, and
   measured duration so subsequent runs short-circuit on unchanged
   posts.

Usage
-----
::

    # Default engine (openvoice), default base voice, no LLM enrichment
    python3 sprezzature-publish/scripts/narrate_post.py posts/hello.md

    # ChatterboxTTS with a custom voice sample (designer's own voice)
    python3 sprezzature-publish/scripts/narrate_post.py \\
        --engine chatterbox \\
        --voice-sample voices/me.wav \\
        posts/hello.md

    # Enrich segment hints via local Ollama (qwen3-vl:8b, the one model)
    python3 sprezzature-publish/scripts/narrate_post.py \\
        --engine openvoice --voice base-en-default \\
        --ai-hints \\
        posts/hello.md

    # Debug: just print the (enriched) hints, do not call the engine
    python3 sprezzature-publish/scripts/narrate_post.py \\
        --ai-hints --ai-hints-only posts/hello.md

Requirements
------------
* Python 3.10+; PyYAML is optional (pronunciation override + frontmatter
  parsing degrade silently when missing).
* One of the engine wrappers installed:
  - ``pip install -r sprezzature-publish/scripts/requirements-narrate-openvoice.txt``
  - ``pip install -r sprezzature-publish/scripts/requirements-narrate-chatterbox.txt``
* A running Ollama daemon if ``--ai-hints`` is passed (the same
  daemon ``alt_from_ollama.py`` and ``meta_from_ollama.py`` use).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Every LLM/VLM call across sprezzature-* routes through this one function —
# no script imports an Ollama/OpenAI/LangChain client directly. It resolves
# the backend and model tag from the SPREZZATURE_LLM_* environment variables
# (SPREZZATURE_LLM_BACKEND defaults to "ollama"); the `model` argument passed
# at each call site below is a per-call override on top of that.
from best_engine_ai_helper.llm import chat as _llm_chat

# Local helpers — pure-Python, no heavy ML deps.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _narrate import (  # noqa: E402
    LLM_SYSTEM_PROMPT,
    NarrationManifestEntry,
    Segment,
    apply_pronunciation,
    extract_segments,
    load_pronunciation,
    merge_llm_hint,
    read_manifest,
    segments_to_text,
    source_sha256,
    write_manifest,
)


# ── Module-level configuration ──────────────────────────────────────────────

#: Engines we know how to dispatch to. Both wrappers ship in this
#: folder and are invoked as subprocesses so their heavy ML imports
#: never leak into the orchestrator's import graph.
ENGINES: tuple[str, ...] = ("openvoice", "chatterbox")

#: The one authorized LLM for ``--ai-hints`` — ``qwen3-vl:8b`` (via Ollama), the
#: same model :mod:`alt_from_ollama` uses, so the user only ever pulls one. Not
#: user-selectable; ``OLLAMA_MODEL`` is honoured only as a test seam.
DEFAULT_LLM_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen3-vl:8b")

#: Ollama daemon URL (shared default with alt_from_ollama / meta_from_ollama).
OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")


# ── LLM enrichment (optional, opt-in via --ai-hints) ──────────────────────

def _llm_classify_segment(
    seg: Segment,
    *,
    prev_text: str,
    next_text: str,
    model: str,
    timeout_s: float,
) -> dict[str, Any]:
    """
    Ask the local Ollama model to annotate one segment.

    Returns an empty dict on any error (network, timeout, JSON parse
    failure) so the caller falls back to structural defaults — fail
    soft everywhere.

    Parameters
    ----------
    seg : Segment
        Segment with structural defaults already filled in.
    prev_text, next_text : str
        Adjacent segment text, used as context.
    model : str
        Ollama model tag (e.g. ``qwen3-vl:8b``).
    timeout_s : float
        Per-call wall-clock budget.

    Returns
    -------
    dict
        Parsed JSON object on success, ``{}`` on any failure.
    """
    # Concise prompt — engine wrappers consume the structured JSON.
    user_prompt: str = (
        f"Previous segment: {prev_text!r}\n"
        f"Segment to annotate: {seg['text']!r}\n"
        f"Next segment: {next_text!r}\n"
        f"Segment kind: {seg['kind']}\n"
        f"Baseline emotion: {seg['emotion']}; baseline pace: {seg['pace']}.\n"
        "Reply with the JSON object only."
    )
    try:
        text: str = str(_llm_chat(user_prompt, system=LLM_SYSTEM_PROMPT, model=model)).strip()
        return json.loads(text) if text else {}
    except Exception:
        # ConnectionError, Timeout, JSONDecodeError — fail soft.
        return {}


def enrich_with_llm(
    segments: list[Segment],
    *,
    model: str = DEFAULT_LLM_MODEL,
    timeout_s: float = 30.0,
) -> list[Segment]:
    """
    Walk every segment, ask the LLM for hints, merge with structural baseline.

    A failed LLM call leaves the structural defaults untouched. The
    caller never crashes because the daemon is missing.

    Parameters
    ----------
    segments : list of Segment
    model : str
        Ollama model tag.
    timeout_s : float
        Per-segment wall-clock budget.

    Returns
    -------
    list of Segment
        Same length as the input; one merged segment per input.
    """
    out: list[Segment] = []
    for i, seg in enumerate(segments):
        prev_text: str = segments[i - 1]["text"] if i > 0 else ""
        next_text: str = segments[i + 1]["text"] if i < len(segments) - 1 else ""
        hint = _llm_classify_segment(
            seg,
            prev_text=prev_text,
            next_text=next_text,
            model=model,
            timeout_s=timeout_s,
        )
        out.append(merge_llm_hint(seg, hint) if hint else seg)
    return out


# ── Engine dispatch ────────────────────────────────────────────────────────

def _engine_script_path(engine: str) -> Path:
    """Resolve the wrapper script for the chosen engine."""
    here: Path = Path(__file__).resolve().parent
    return here / f"narrate_{engine}.py"


def _engine_is_available(engine: str, python: str = sys.executable) -> bool:
    """
    Probe whether the engine's Python dependencies are importable.

    Each wrapper exposes a ``--check`` flag that imports the heavy
    module and exits 0 / 1 accordingly. We invoke it as a subprocess
    so the import never enters the orchestrator's address space.
    """
    script = _engine_script_path(engine)
    if not script.is_file():
        return False
    try:
        proc = subprocess.run(
            [python, str(script), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def run_engine(
    engine: str,
    *,
    segments: list[Segment],
    voice: str,
    voice_sample: Path | None,
    out_dir: Path,
    python: str = sys.executable,
) -> dict[str, Any]:
    """
    Hand off to the engine wrapper.

    Communication is by JSON: orchestrator writes
    ``segments.json`` + invocation flags; wrapper writes
    ``out_dir/<slug>.wav`` (or .mp3) and prints a JSON summary on
    stdout (``{"audio": "...", "duration_seconds": ...}``).

    Parameters
    ----------
    engine : str
        One of :data:`ENGINES`.
    segments : list of Segment
        Output of :func:`extract_segments` (optionally LLM-enriched).
    voice : str
        Engine-specific built-in voice name. Ignored when
        ``voice_sample`` is set.
    voice_sample : Path or None
        Path to a reference WAV for voice cloning. None → use the
        engine's built-in voice ``voice``.
    out_dir : Path
        Directory to write the audio into.

    Returns
    -------
    dict
        ``{"audio": str, "duration_seconds": float}`` — caller writes
        this into the manifest.

    Raises
    ------
    RuntimeError
        When the engine wrapper exits non-zero. The wrapper's stderr
        is included in the message for debuggability.
    """
    script = _engine_script_path(engine)
    if not script.is_file():
        raise RuntimeError(f"unknown engine: {engine}")

    out_dir.mkdir(parents=True, exist_ok=True)
    segments_file: Path = out_dir / ".segments.json"
    segments_file.write_text(
        json.dumps(segments, ensure_ascii=False),
        encoding="utf-8",
    )

    cmd: list[str] = [
        python, str(script),
        "--segments", str(segments_file),
        "--out-dir", str(out_dir),
    ]
    if voice_sample:
        cmd += ["--voice-sample", str(voice_sample)]
    else:
        cmd += ["--voice", voice]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Clean the segments scratch file regardless of outcome.
    try:
        segments_file.unlink()
    except OSError:
        pass
    if proc.returncode != 0:
        raise RuntimeError(
            f"{engine} wrapper exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    # The wrapper prints one JSON object on the last non-empty line.
    last_line: str = next(
        (l for l in reversed(proc.stdout.splitlines()) if l.strip()),
        "",
    )
    try:
        return json.loads(last_line)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{engine} wrapper returned non-JSON output:\n{proc.stdout}"
        ) from e


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="narrate_post",
        description="Narrate a Markdown post via a local OSS TTS engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "post",
        type=Path,
        help="Path to the Markdown post to narrate.",
    )
    parser.add_argument(
        "--engine",
        choices=ENGINES,
        default="openvoice",
        help="TTS engine wrapper (default: openvoice).",
    )
    parser.add_argument(
        "--voice",
        default="base-en-default",
        help="Engine built-in voice name (default: base-en-default). "
             "Ignored if --voice-sample is set.",
    )
    parser.add_argument(
        "--voice-sample",
        type=Path,
        default=None,
        help="Path to a reference WAV for voice cloning. Overrides --voice.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out/audio"),
        help="Where to write the audio file + manifest (default: out/audio/).",
    )
    parser.add_argument(
        "--ai-hints",
        action="store_true",
        help="Enrich segment hints via local Ollama (off by default).",
    )
    parser.add_argument(
        "--ai-hints-only",
        action="store_true",
        help="Print the enriched segment hints as JSON and exit. "
             "Useful for review before invoking the TTS engine.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-narrate even when the manifest sha256 matches the source.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint. Returns ``0`` on success."""
    args = parse_args()
    if not args.post.is_file():
        print(f"FAIL post not found: {args.post}", file=sys.stderr)
        return 1

    markdown: str = args.post.read_text(encoding="utf-8")
    segments: list[Segment] = extract_segments(markdown)
    if not segments:
        print(f"FAIL post is empty (no narrate-able segments): {args.post}",
              file=sys.stderr)
        return 1

    # Pronunciation overrides applied before LLM enrichment so the
    # LLM sees what the engine will actually speak.
    segments = apply_pronunciation(segments, load_pronunciation(args.post))

    if args.ai_hints:
        # The model is fixed at qwen3-vl:8b (the one authorized LLM); not a CLI
        # knob. ``enrich_with_llm`` defaults to ``DEFAULT_LLM_MODEL``.
        segments = enrich_with_llm(segments)

    if args.ai_hints_only:
        print(json.dumps(segments, indent=2, ensure_ascii=False))
        return 0

    # Cache check — skip when nothing changed.
    manifest_path: Path = args.out_dir / "manifest.json"
    manifest: dict[str, NarrationManifestEntry] = read_manifest(manifest_path)
    source_key: str = args.post.as_posix()
    digest: str = source_sha256(segments_to_text(segments))
    if not args.force:
        existing = manifest.get(source_key)
        if (
            existing is not None
            and existing.source_sha256 == digest
            and existing.engine == args.engine
            and existing.voice == (
                args.voice_sample.as_posix()
                if args.voice_sample else args.voice
            )
            and Path(existing.audio).is_file()
        ):
            print(f"OK cache hit: {existing.audio}")
            return 0

    if not _engine_is_available(args.engine):
        print(
            f"FAIL engine '{args.engine}' is not installed.\n"
            f"  Install: pip install -r sprezzature-publish/scripts/"
            f"requirements-narrate-{args.engine}.txt\n"
            f"  Then run: python sprezzature-publish/scripts/install_narrate.py "
            f"--engine {args.engine}",
            file=sys.stderr,
        )
        return 2

    started: float = time.monotonic()
    result: dict[str, Any] = run_engine(
        args.engine,
        segments=segments,
        voice=args.voice,
        voice_sample=args.voice_sample,
        out_dir=args.out_dir,
    )
    elapsed: float = time.monotonic() - started

    manifest[source_key] = NarrationManifestEntry(
        source=source_key,
        audio=str(Path(result["audio"]).relative_to(args.out_dir.parent))
        if str(result["audio"]).startswith(str(args.out_dir.parent))
        else str(result["audio"]),
        engine=args.engine,
        voice=args.voice_sample.as_posix() if args.voice_sample else args.voice,
        source_sha256=digest,
        duration_seconds=float(result.get("duration_seconds", -1)),
    )
    write_manifest(manifest_path, manifest)
    print(
        f"OK narrated {source_key} in {elapsed:.1f}s → {result['audio']} "
        f"({result.get('duration_seconds', 0):.1f}s audio)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
