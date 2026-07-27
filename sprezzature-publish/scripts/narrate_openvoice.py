#!/usr/bin/env python3
"""
narrate_openvoice
=================

OpenVoice v2 engine wrapper for ``narrate_post.py``. Invoked as a
subprocess so the heavy ML imports (torch, librosa, openvoice) never
enter the orchestrator's address space.

The script understands two modes:

* ``--check`` — exit 0 when ``openvoice`` is importable, 1 otherwise.
  Used by the orchestrator to detect installation without crashing.
* synthesis mode — reads a segments JSON file, runs OpenVoice v2 over
  each segment, concatenates the WAVs with the requested pauses, and
  prints one JSON object on stdout:
  ``{"audio": "<path>", "duration_seconds": <float>}``.

Built-in voices
---------------
OpenVoice v2 ships with a small base-speaker set
(``base-en-default``, ``base-en-friendly``, ``base-en-cheerful``,
``base-en-sad``, ``base-en-whispering``, ``base-es-default``,
``base-fr-default``). The ``--voice`` flag selects one. Pass
``--voice-sample <path>`` to clone instead — OpenVoice v2 extracts
the speaker embedding from a 6–60 s reference WAV.

Why OpenVoice v2
----------------
- MIT-licensed code AND weights (genuinely OSS, unlike F5-TTS / XTTS
  whose weights are non-commercial).
- Zero-shot cloning from a short reference.
- Cross-lingual: an English reference can speak French text.
- Project ethics line: clone only your own voice, or a voice whose
  owner consented in writing. See
  ``sprezzature-publish/references/audio-narration.md`` § "Voice cloning
  ethics".

Usage
-----
::

    # Capability probe
    python3 narrate_openvoice.py --check

    # Synthesis (driven by narrate_post.py — not usually invoked by hand)
    python3 narrate_openvoice.py \\
        --segments segments.json \\
        --out-dir out/audio \\
        --voice base-en-default

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

#: PCM sample rate of the concatenated output. OpenVoice v2 produces
#: 24 kHz mono by default; we keep that.
SAMPLE_RATE_HZ: int = 24_000

#: OpenVoice v2 emotion category mapping. Maps the segment ``emotion``
#: hint (set by structure or LLM) onto the values the base speaker
#: model recognises. Anything outside this set falls back to
#: ``default``.
EMOTION_MAP: dict[str, str] = {
    "neutral":        "default",
    "cheerful":       "cheerful",
    "sad":            "sad",
    "cautious":       "default",
    "enthusiastic":   "cheerful",
    "contemplative":  "default",
    "warm":           "friendly",
    "calm":           "default",
    "angry":          "angry",
    "whispering":     "whispering",
    "friendly":       "friendly",
    "terrified":      "terrified",
}


# ── Capability probe ───────────────────────────────────────────────────────

def check_install() -> int:
    """
    Exit 0 if OpenVoice v2 is importable, 1 otherwise.

    The orchestrator uses this to decide whether the engine is
    available without paying the import cost itself.
    """
    try:
        importlib.import_module("openvoice")
        return 0
    except ImportError:
        return 1


# ── Synthesis (heavy path) ─────────────────────────────────────────────────

def synthesise(
    segments: list[dict[str, Any]],
    *,
    voice: str,
    voice_sample: Path | None,
    out_dir: Path,
) -> dict[str, Any]:
    """
    Run OpenVoice v2 over the segments and write the concatenated audio.

    Imports happen inside this function so ``--check`` mode never
    triggers the torch / openvoice import path.

    Parameters
    ----------
    segments : list of dict
        Same shape as ``_narrate.Segment`` (string text + hint fields).
    voice : str
        Built-in base-speaker name. Ignored when ``voice_sample`` set.
    voice_sample : Path or None
        Reference WAV for voice cloning, 6–60 s recommended.
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
    # Heavy imports — only reached when the orchestrator confirms
    # the user actually wants synthesis.
    try:
        # The exact OpenVoice v2 public API surface (BaseSpeakerTTS,
        # ToneColorConverter, se_extractor) lives under
        # ``openvoice``; we late-import to keep ``--check`` cheap.
        importlib.import_module("openvoice")  # availability check (raises if absent)
        base_tts = importlib.import_module("openvoice.api")  # BaseSpeakerTTS
        tone_converter_mod = importlib.import_module("openvoice.api")
        se_extractor_mod = importlib.import_module("openvoice.se_extractor")
    except ImportError as e:
        raise RuntimeError(
            "openvoice not installed; "
            "pip install -r requirements-narrate-openvoice.txt"
        ) from e

    # OpenVoice v2 requires checkpoint paths discovered at install
    # time. The orchestrator's install_narrate.py downloads them
    # into ``~/.cache/sprezzature-skill/openvoice/`` and writes a tiny
    # config pointing at the files; we read that here.
    cache_root: Path = Path.home() / ".cache" / "sprezzature-skill" / "openvoice"
    config_path: Path = cache_root / "config.json"
    if not config_path.is_file():
        raise RuntimeError(
            f"OpenVoice v2 checkpoints not found at {cache_root}. "
            "Run: python3 sprezzature-publish/scripts/install_narrate.py "
            "--engine openvoice"
        )
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    device: str = cfg.get("device", "cpu")
    base_speakers_dir: Path = Path(cfg["base_speakers_dir"])
    converter_ckpt: Path = Path(cfg["converter_ckpt"])

    base = base_tts.BaseSpeakerTTS(
        str(base_speakers_dir / "config.json"), device=device,
    )
    base.load_ckpt(str(base_speakers_dir / "checkpoint.pth"))

    tone_converter = tone_converter_mod.ToneColorConverter(
        str(converter_ckpt.parent / "config.json"), device=device,
    )
    tone_converter.load_ckpt(str(converter_ckpt))

    # Source embedding: either built-in or extracted from sample.
    if voice_sample is not None:
        source_se, _ = se_extractor_mod.get_se(
            str(voice_sample), tone_converter, vad=True,
        )
        # Reuse the "default" base voice as the prosody driver when
        # cloning — the tone converter then morphs it to the sample.
        base_voice: str = "default"
    else:
        # Voice name shape: "base-<lang>-<style>" → use the matching
        # built-in speaker embedding shipped with the checkpoints.
        try:
            _, lang, style = voice.split("-", 2)
        except ValueError as e:
            raise RuntimeError(
                f"voice {voice!r} not in 'base-<lang>-<style>' shape"
            ) from e
        emb_path: Path = base_speakers_dir / "se" / f"{style}_{lang}.pth"
        if not emb_path.is_file():
            raise RuntimeError(f"built-in voice not found: {emb_path}")
        import torch  # local — already imported transitively above
        source_se = torch.load(str(emb_path), map_location=device)
        base_voice = style

    # Concatenate per-segment WAVs into a single file. We write raw
    # 16-bit PCM via the stdlib ``wave`` module so we don't need
    # ``soundfile`` / ``librosa`` purely for I/O.
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path: Path = out_dir / "narration.wav"

    import numpy as np  # local
    pieces: list[np.ndarray] = []
    for seg in segments:
        text: str = seg.get("text", "").strip()
        if not text:
            continue
        emotion: str = EMOTION_MAP.get(seg.get("emotion", "neutral"), "default")
        speed: float = {"slow": 0.85, "normal": 1.0, "fast": 1.15}.get(
            seg.get("pace", "normal"), 1.0,
        )
        # base.tts returns numpy int16 at SAMPLE_RATE_HZ.
        audio_np = base.tts(
            text=text,
            speaker=base_voice,
            language=cfg.get("default_language", "English"),
            style=emotion,
            speed=speed,
            sdp_ratio=cfg.get("sdp_ratio", 0.2),
        )
        # Apply the tone converter to morph the prosody onto the
        # source speaker embedding (the clone or the built-in voice).
        morphed = tone_converter.convert(
            audio_src_path=None,  # in-memory path
            src_se=cfg["default_source_se"],
            tgt_se=source_se,
            output_path=None,
            tau=cfg.get("tau", 0.3),
            audio_np=audio_np,
        )
        pieces.append(morphed)
        # Append silence for pause_after_ms.
        pause_samples: int = int(
            SAMPLE_RATE_HZ * float(seg.get("pause_after_ms", 0)) / 1000.0
        )
        if pause_samples > 0:
            pieces.append(np.zeros(pause_samples, dtype=np.int16))

    if not pieces:
        raise RuntimeError("no non-empty segments to synthesise")

    full: np.ndarray = np.concatenate(pieces)
    with wave.open(str(final_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)              # 16-bit PCM
        wf.setframerate(SAMPLE_RATE_HZ)
        wf.writeframes(full.astype(np.int16).tobytes())

    duration_s: float = len(full) / float(SAMPLE_RATE_HZ)
    return {"audio": str(final_path), "duration_seconds": duration_s}


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse the wrapper's command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="narrate_openvoice",
        description="OpenVoice v2 engine wrapper for narrate_post.py.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Probe whether openvoice is importable; exit 0/1 without doing work.",
    )
    parser.add_argument("--segments", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--voice", default="base-en-default")
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
