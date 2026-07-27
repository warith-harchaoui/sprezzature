#!/usr/bin/env python3
"""
narrate_chatterbox
==================

ChatterboxTTS engine wrapper for ``narrate_post.py``. Invoked as a
subprocess so the heavy ML imports (torch, chatterbox_tts) never enter
the orchestrator's address space.

The script understands two modes:

* ``--check`` — exit 0 when ``chatterbox_tts`` is importable, 1
  otherwise. Used by the orchestrator to detect installation without
  crashing.
* synthesis mode — reads a segments JSON file, runs ChatterboxTTS
  over each segment, concatenates the WAVs with the requested
  pauses, and prints one JSON object on stdout:
  ``{"audio": "<path>", "duration_seconds": <float>}``.

Why ChatterboxTTS
-----------------
- MIT-licensed code AND weights (genuinely OSS, unlike F5-TTS / XTTS
  whose weights are non-commercial).
- More expressive than OpenVoice v2 — has a continuous
  ``exaggeration`` dial (0.0–2.0) for emotional intensity and
  ``cfg_weight`` for stability/creativity. Maps cleanly to the
  segment ``intensity`` and ``pace`` hints.
- Zero-shot cloning from a 5–30 s reference clip.

Emotion → exaggeration mapping
------------------------------
``ChatterboxTTS`` does not have named emotion categories; we translate
the segment's ``emotion`` + ``intensity`` to its native two-dial
control. The mapping is conservative — exaggeration over 1.2 is
audibly theatrical and rarely suits long-form narration.

Usage
-----
::

    # Capability probe
    python3 narrate_chatterbox.py --check

    # Synthesis (driven by narrate_post.py — not usually invoked by hand)
    python3 narrate_chatterbox.py \\
        --segments segments.json \\
        --out-dir out/audio \\
        --voice-sample voices/me.wav

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import wave
from pathlib import Path
from typing import Any


# ── Module-level configuration ──────────────────────────────────────────────

#: ChatterboxTTS native sample rate (24 kHz mono).
SAMPLE_RATE_HZ: int = 24_000

#: Map (emotion, intensity 0..1) → exaggeration value (0..2). The
#: base is 0.5 (neutral conversational). The intensity 0..1 dial
#: scales the offset.
EMOTION_EXAGGERATION_BASE: dict[str, float] = {
    "neutral":        0.50,
    "cheerful":       0.80,
    "sad":            0.35,
    "cautious":       0.45,
    "enthusiastic":   1.00,
    "contemplative":  0.40,
    "warm":           0.65,
    "calm":           0.40,
    "angry":          1.20,
    "whispering":     0.20,
    "friendly":       0.70,
    "terrified":      1.10,
}

#: Default cfg_weight per pace. Higher = more stable / predictable;
#: lower = more expressive variation.
PACE_CFG_WEIGHT: dict[str, float] = {
    "slow":   0.7,
    "normal": 0.5,
    "fast":   0.3,
}


# ── Capability probe ───────────────────────────────────────────────────────

def check_install() -> int:
    """
    Exit 0 if ``chatterbox_tts`` is importable, 1 otherwise.

    The orchestrator uses this to decide whether the engine is
    available without paying the import cost itself.
    """
    try:
        importlib.import_module("chatterbox.tts")
        return 0
    except ImportError:
        try:
            importlib.import_module("chatterbox_tts")
            return 0
        except ImportError:
            return 1


# ── Emotion → engine dial mapping ──────────────────────────────────────────

def emotion_to_exaggeration(emotion: str, intensity: float) -> float:
    """
    Map a segment's ``emotion`` + ``intensity`` to the engine dial.

    Clamps to [0.0, 2.0] so a hallucinated LLM intensity never blows
    the dial.

    Parameters
    ----------
    emotion : str
        One of :data:`EMOTION_EXAGGERATION_BASE` keys; unknown
        emotions fall back to ``neutral``.
    intensity : float
        0.0 (flat) … 1.0 (full effect of the emotion).

    Returns
    -------
    float
        Exaggeration value in [0.0, 2.0].
    """
    base: float = EMOTION_EXAGGERATION_BASE.get(emotion, 0.50)
    # Intensity 0.5 == use base; <0.5 pulls towards neutral 0.5;
    # >0.5 pushes towards 2× the offset from neutral.
    offset: float = (intensity - 0.5) * 2.0   # -1..+1
    if base >= 0.5:
        value: float = 0.5 + (base - 0.5) * (1.0 + offset)
    else:
        value = 0.5 - (0.5 - base) * (1.0 + offset)
    return max(0.0, min(2.0, value))


# ── Synthesis (heavy path) ─────────────────────────────────────────────────

def synthesise(
    segments: list[dict[str, Any]],
    *,
    voice: str,
    voice_sample: Path | None,
    out_dir: Path,
) -> dict[str, Any]:
    """
    Run ChatterboxTTS over the segments and write the concatenated audio.

    Imports happen inside this function so ``--check`` mode never
    triggers the torch / chatterbox import path.

    Parameters
    ----------
    segments : list of dict
        Same shape as ``_narrate.Segment``.
    voice : str
        Engine built-in voice. ChatterboxTTS ships a small default
        speaker; the wrapper treats ``voice = "default"`` as
        "no reference, use the bundled speaker". Any other value
        is treated as a voice-sample path lookup under
        ``~/.cache/sprezzature-skill/chatterbox/voices/``.
    voice_sample : Path or None
        Reference WAV for voice cloning, 5–30 s recommended.
        When set, ``voice`` is ignored.
    out_dir : Path
        Where to write the final audio file.

    Returns
    -------
    dict
        ``{"audio": <path>, "duration_seconds": <float>}``.

    Raises
    ------
    RuntimeError
        On synth failure. The orchestrator surfaces the message.
    """
    try:
        # ChatterboxTTS ships its public API as ``chatterbox.tts.ChatterboxTTS``
        # (or ``chatterbox_tts`` depending on the release packaging).
        try:
            mod = importlib.import_module("chatterbox.tts")
        except ImportError:
            mod = importlib.import_module("chatterbox_tts")
    except ImportError as e:
        raise RuntimeError(
            "chatterbox-tts not installed; "
            "pip install -r requirements-narrate-chatterbox.txt"
        ) from e

    # Resolve the reference audio path. When neither --voice-sample
    # nor a built-in voice is supplied, ChatterboxTTS uses its
    # bundled default speaker.
    ref_audio: Path | None
    if voice_sample is not None:
        ref_audio = voice_sample
    elif voice and voice != "default":
        # Treat ``voice`` as a filename under the project's voice
        # library (see install_narrate.py for the layout).
        cache_root: Path = Path.home() / ".cache" / "sprezzature-skill" / "chatterbox"
        candidate: Path = cache_root / "voices" / f"{voice}.wav"
        ref_audio = candidate if candidate.is_file() else None
    else:
        ref_audio = None

    model = mod.ChatterboxTTS.from_pretrained(device="cpu")  # auto-detects GPU

    out_dir.mkdir(parents=True, exist_ok=True)
    final_path: Path = out_dir / "narration.wav"

    import numpy as np
    pieces: list[np.ndarray] = []
    for seg in segments:
        text: str = seg.get("text", "").strip()
        if not text:
            continue
        exaggeration: float = emotion_to_exaggeration(
            seg.get("emotion", "neutral"),
            float(seg.get("intensity", 0.5)),
        )
        cfg_weight: float = PACE_CFG_WEIGHT.get(seg.get("pace", "normal"), 0.5)
        # Pass the reference for every chunk (the model handles
        # voice consistency internally via the cached embedding).
        wav = model.generate(
            text=text,
            audio_prompt_path=str(ref_audio) if ref_audio else None,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )
        # ChatterboxTTS returns a torch tensor at SAMPLE_RATE_HZ.
        # Convert to int16 numpy for the wave writer.
        wav_np = wav.squeeze().detach().cpu().numpy()
        # Normalise + scale to int16 range.
        wav_np = np.clip(wav_np, -1.0, 1.0)
        pieces.append((wav_np * 32_767).astype(np.int16))

        pause_samples: int = int(
            SAMPLE_RATE_HZ * float(seg.get("pause_after_ms", 0)) / 1000.0
        )
        if pause_samples > 0:
            pieces.append(np.zeros(pause_samples, dtype=np.int16))

    if not pieces:
        raise RuntimeError("no non-empty segments to synthesise")

    full = np.concatenate(pieces)
    with wave.open(str(final_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE_HZ)
        wf.writeframes(full.astype(np.int16).tobytes())

    duration_s: float = len(full) / float(SAMPLE_RATE_HZ)
    return {"audio": str(final_path), "duration_seconds": duration_s}


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse the wrapper's command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="narrate_chatterbox",
        description="ChatterboxTTS engine wrapper for narrate_post.py.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Probe whether chatterbox-tts is importable; exit 0/1.",
    )
    parser.add_argument("--segments", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--voice", default="default")
    parser.add_argument("--voice-sample", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    if args.check:
        return check_install()
    if not args.segments or not args.out_dir:
        print("FAIL --segments and --out-dir are required", file=sys.stderr)
        return 1
    segments: list[dict[str, Any]] = json.loads(
        args.segments.read_text(encoding="utf-8"),
    )
    try:
        result = synthesise(
            segments,
            voice=args.voice,
            voice_sample=args.voice_sample,
            out_dir=args.out_dir,
        )
    except RuntimeError as e:
        print(f"FAIL {e}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
