#!/usr/bin/env python3
"""
pick_voice
==========

Help the designer pick a narration voice — either from an engine's
built-in library, or by recording a 6–30 s sample of their own voice
for zero-shot cloning.

For each engine the orchestrator supports (``openvoice``,
``chatterbox``), the script:

1. Probes whether the engine is installed.
2. Lists its built-in voices.
3. Optionally generates a one-line demo clip per voice into
   ``out/voice-samples/<engine>/<voice>.wav`` so the designer can
   listen and choose.

The script never auto-downloads model checkpoints — that's
``install_narrate.py``'s job. Without checkpoints, sampling skips
gracefully with a one-line install hint.

Usage
-----
::

    # List voices for every installed engine
    python3 sprezzature-publish/scripts/pick_voice.py

    # Generate a 1-sentence sample per voice for the chosen engine
    python3 sprezzature-publish/scripts/pick_voice.py \\
        --engine openvoice --sample

    # Custom sample text (defaults to a Lorem-ipsum-ish neutral line)
    python3 sprezzature-publish/scripts/pick_voice.py \\
        --engine chatterbox --sample \\
        --text "This is how my narrator sounds reading a typical sentence."

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ── Module-level configuration ──────────────────────────────────────────────

#: Engines the script knows about, in display order.
ENGINES: tuple[str, ...] = ("openvoice", "chatterbox")

#: Default sample line. Designed to exercise a range of phonemes plus
#: one comma + one period so prosody is audible.
DEFAULT_SAMPLE_TEXT: str = (
    "Hello, this is how my narrator sounds reading a normal sentence."
)

#: Built-in voices per engine. Kept in code (not auto-discovered from
#: the checkpoint) so the picker works even when the engine isn't yet
#: installed — the user sees what they would get.
BUILTIN_VOICES: dict[str, tuple[str, ...]] = {
    "openvoice": (
        "base-en-default", "base-en-friendly", "base-en-cheerful",
        "base-en-sad", "base-en-whispering",
        "base-es-default", "base-fr-default",
    ),
    "chatterbox": (
        "default",  # the bundled speaker; clones go through --voice-sample
    ),
}


# ── Engine probe ───────────────────────────────────────────────────────────

def engine_is_available(engine: str) -> bool:
    """
    Subprocess-probe the engine wrapper's ``--check`` mode.

    Mirrors the behaviour of ``narrate_post._engine_is_available``
    so the two callers stay in lock-step without sharing state.
    """
    script: Path = Path(__file__).resolve().parent / f"narrate_{engine}.py"
    if not script.is_file():
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


# ── Sampling ───────────────────────────────────────────────────────────────

def sample_one_voice(
    engine: str, voice: str, text: str, out_dir: Path,
) -> Path | None:
    """
    Generate one demo clip via the engine wrapper.

    Builds a one-segment JSON, calls the wrapper, and returns the
    resulting WAV path on success or ``None`` on any failure.

    Parameters
    ----------
    engine : str
        ``"openvoice"`` or ``"chatterbox"``.
    voice : str
        Built-in voice name to demonstrate.
    text : str
        Single sentence to narrate.
    out_dir : Path
        Per-engine subdirectory under ``out/voice-samples/``.

    Returns
    -------
    Path or None
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target: Path = out_dir / f"{voice}.wav"
    # The wrapper concatenates per-segment WAVs into one file named
    # ``narration.wav``; we move it to the voice-named target.
    script: Path = Path(__file__).resolve().parent / f"narrate_{engine}.py"
    segments_payload: list[dict[str, object]] = [{
        "text": text,
        "kind": "paragraph",
        "heading_level": 0,
        "pause_before_ms": 0,
        "pause_after_ms": 0,
        "emotion": "neutral",
        "intensity": 0.5,
        "pace": "normal",
        "emphasis_word": "",
    }]
    work: Path = out_dir / ".segments.json"
    work.write_text(json.dumps(segments_payload, ensure_ascii=False), encoding="utf-8")
    try:
        proc = subprocess.run(
            [
                sys.executable, str(script),
                "--segments", str(work),
                "--out-dir", str(out_dir),
                "--voice", voice,
            ],
            capture_output=True,
            text=True,
        )
    finally:
        try:
            work.unlink()
        except OSError:
            pass
    if proc.returncode != 0:
        return None
    last_line: str = next(
        (l for l in reversed(proc.stdout.splitlines()) if l.strip()), "",
    )
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    produced: Path = Path(result["audio"])
    if produced != target and produced.is_file():
        produced.replace(target)
    return target if target.is_file() else None


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="pick_voice",
        description="List narration engine voices and optionally sample them.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--engine",
        choices=ENGINES + ("all",),
        default="all",
        help="Engine to list / sample (default: all).",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate a demo clip for each listed voice.",
    )
    parser.add_argument(
        "--text",
        default=DEFAULT_SAMPLE_TEXT,
        help=f"Sample text (default: {DEFAULT_SAMPLE_TEXT!r}).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out/voice-samples"),
        help="Where to write the demo clips (default: out/voice-samples/).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    engines: tuple[str, ...] = ENGINES if args.engine == "all" else (args.engine,)

    for engine in engines:
        installed: bool = engine_is_available(engine)
        marker: str = "✓" if installed else "✗ (not installed)"
        print(f"\n[{engine}] {marker}")
        for voice in BUILTIN_VOICES[engine]:
            print(f"  • {voice}")
        if not args.sample:
            continue
        if not installed:
            print(
                f"  → samples skipped: pip install -r sprezzature-publish/scripts/"
                f"requirements-narrate-{engine}.txt"
            )
            continue
        for voice in BUILTIN_VOICES[engine]:
            out: Path | None = sample_one_voice(
                engine, voice, args.text, args.out_dir / engine,
            )
            print(f"    → {voice}: {out if out else 'FAILED'}")

    print(
        "\nUse one of the voices above with:\n"
        "  python3 sprezzature-publish/scripts/narrate_post.py "
        "--engine <engine> --voice <voice> <post.md>\n"
        "Or clone your own voice with:\n"
        "  python3 sprezzature-publish/scripts/narrate_post.py "
        "--engine <engine> --voice-sample your-voice.wav <post.md>"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
