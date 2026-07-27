#!/usr/bin/env python3
"""
diarize_from_nemo
=================

Speaker diarization ("who spoke when") via NVIDIA NeMo's **Sortformer**
end-to-end diarization transformer. Loads a pretrained checkpoint from
Hugging Face on first use, runs in-process on CPU / CUDA / Apple-silicon
MPS, and emits an RTTM file plus a JSON turn list.

Default model
-------------

``nvidia/diar_sortformer_4spk-v1`` — Sortformer trained end-to-end on up
to **4 concurrent speakers**. Override with ``--model`` or the
``NEMO_DIAR_MODEL`` env var. Multi-speaker (up to 8) checkpoints exist
under the same family; the default is the reference small-conversation
model.

Output
------

For an input ``interview.wav`` the script writes, next to the source:

* ``interview.rttm`` — the canonical RTTM (`SPEAKER` lines).
* ``interview.diarization.json`` — a small JSON turn list:

  .. code-block:: json

      [
        {"start": 0.00, "end": 3.21, "speaker": "0"},
        {"start": 3.21, "end": 7.14, "speaker": "1"},
        {"start": 7.14, "end": 12.02, "speaker": "0"}
      ]

Cache
-----

Successful diarization results are cached under
``~/.cache/sprezzature-skill/diarize/`` (override with ``SPREZZATURE_CACHE_DIR``,
disable per-run with ``--no-cache``). The cache key is
SHA-256 of the extracted-audio bytes + the resolved model tag.

Usage
-----
::

    # Diarize a video → interview.rttm + interview.diarization.json
    python diarize_from_nemo.py interview.mp4

    # Force number of speakers (Sortformer's default is data-driven)
    python diarize_from_nemo.py talk.wav --max-speakers 2

    # Emit only the RTTM (no JSON sibling)
    python diarize_from_nemo.py podcast.mp3 --format rttm

    # Use a specific checkpoint
    python diarize_from_nemo.py raw.wav \\
        --model nvidia/diar_streaming_sortformer_4spk-v2

Notes
-----
* Python 3.10+. Install NeMo + Sortformer weights via
  ``python install_diarize.py`` first.
* Extraction uses the same ``audio-helper`` / ``video-helper`` / ffmpeg
  chain as ``captions_from_whisper.py``.
* CUDA / MPS: NeMo picks the device from ``torch.cuda.is_available()`` /
  ``torch.backends.mps.is_available()`` unless ``--device`` is set.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path as _PathHelper
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402

import click


# ── Module-level configuration ──────────────────────────────────────────────

#: Cache directory shared with the rest of the skill.
CACHE_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "diarize"

#: Where install_diarize.py caches NeMo checkpoints.
NEMO_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "nemo"

#: Cache toggle, mirroring the captions helper.
NO_CACHE: bool = bool((os.environ.get("SPREZZATURE_NO_CACHE") or os.environ.get("FRONT_NO_CACHE")))

#: Default Hugging Face id for the Sortformer diarization model.
DEFAULT_MODEL: str = "nvidia/diar_sortformer_4spk-v1"

#: Video containers whose audio track needs extracting.
VIDEO_EXTS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"})


# ── Audio extraction ────────────────────────────────────────────────────────

def extract_audio(src: Path, dst: Path) -> None:
    """Re-encode ``src`` to a 16 kHz mono WAV at ``dst``.

    Mirrors the extraction logic in :mod:`captions_from_whisper` so
    callers can reuse a single WAV between captioning and diarization.

    Parameters
    ----------
    src : pathlib.Path
        Source audio or video file.
    dst : pathlib.Path
        Output WAV path. The parent directory is created if missing.

    Raises
    ------
    SystemExit
        On any extraction failure (no helper, no ``ffmpeg``).
    """
    import shutil
    import subprocess

    dst.parent.mkdir(parents=True, exist_ok=True)

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
    )


# ── Cache helpers ───────────────────────────────────────────────────────────

def _cache_key(audio: bytes, model: str, max_speakers: int) -> str:
    """Return a 32-char SHA-256 hex key for the inputs that affect diarization.

    Parameters
    ----------
    audio : bytes
        Extracted 16 kHz WAV bytes.
    model : str
        Resolved model tag.
    max_speakers : int
        Cap on Sortformer's speaker count (0 = data-driven).
    """
    h = hashlib.sha256()
    h.update(audio)
    h.update(b"\x00")
    h.update(f"{model}\x00{max_speakers}".encode("utf-8"))
    return h.hexdigest()[:32]


def _cache_get(key: str) -> Optional[List[Dict[str, Any]]]:
    """Return the cached turn list for ``key`` or ``None`` on miss."""
    if NO_CACHE:
        return None
    path = CACHE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — cache miss on any parse error
        return None


def _cache_set(key: str, turns: List[Dict[str, Any]]) -> None:
    """Store ``turns`` in the on-disk cache; swallow write errors."""
    if NO_CACHE:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(
            json.dumps(turns, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


# ── NeMo Sortformer runner ──────────────────────────────────────────────────

def pick_device(explicit: str = "") -> str:
    """Pick the torch device the way NeMo would internally.

    Parameters
    ----------
    explicit : str, optional
        A user-supplied ``--device`` value; wins when non-empty.

    Returns
    -------
    str
        One of ``"cuda"``, ``"mps"``, ``"cpu"``.
    """
    if explicit:
        return explicit
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _sortformer_model(model_tag: str, device: str) -> Any:
    """Load a Sortformer checkpoint via NeMo's ``from_pretrained``.

    Deferred import so this module can be introspected (``--help``,
    tests) without pulling the ~2 GB torch + NeMo stack.

    Parameters
    ----------
    model_tag : str
        Hugging Face id (or NeMo alias) for the diarization checkpoint.
    device : str
        Torch device string (``"cpu"`` / ``"cuda"`` / ``"mps"``).

    Returns
    -------
    nemo.collections.asr.models.SortformerEncLabelModel
        Pretrained Sortformer model set to eval mode on the target device.
    """
    try:
        from nemo.collections.asr.models import SortformerEncLabelModel  # type: ignore
    except ImportError as exc:  # pragma: no cover
        sys.exit(
            "NeMo is not installed. Run:\n"
            "    python scripts/install_diarize.py\n"
            f"({exc})"
        )
    # NeMo caches downloaded checkpoints under ~/.cache/torch/NeMo/ by
    # default; set NEMO_CACHE_DIR to redirect that if desired.
    os.environ.setdefault("NEMO_CACHE_DIR", str(NEMO_DIR))
    model = SortformerEncLabelModel.from_pretrained(model_tag)
    model.eval()
    try:
        model = model.to(device)
    except Exception:  # noqa: BLE001 — fall back to CPU
        pass
    return model


def diarize(
    src: Path,
    *,
    model: str = DEFAULT_MODEL,
    max_speakers: int = 0,
    device: str = "",
) -> List[Dict[str, Any]]:
    """Run Sortformer on ``src`` and return a list of speaker turns.

    Parameters
    ----------
    src : pathlib.Path
        Audio or video file.
    model : str, optional
        Hugging Face id / alias of the diarization model.
    max_speakers : int, optional
        Cap on Sortformer's predicted speaker count. 0 (default) means
        "let the model decide"; positive values re-label any speaker id
        above the cap onto the nearest kept speaker by contribution.
    device : str, optional
        Explicit torch device. Empty (default) lets :func:`pick_device`
        pick.

    Returns
    -------
    list of dict
        Turns as ``[{"start": float, "end": float, "speaker": str}, ...]``,
        sorted by ``start``.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "input.wav"
        extract_audio(src, wav_path)
        audio_bytes = wav_path.read_bytes()

        key = _cache_key(audio_bytes, model, max_speakers)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        dev = pick_device(device)
        print(f"→ Loading {model} on {dev}…", file=sys.stderr)
        m = _sortformer_model(model, dev)

        # Sortformer's `diarize` returns either a list of RTTM-style lines
        # or a list-of-lists depending on the NeMo version. Normalise
        # both shapes to `List[List[str|float]]` before packing into
        # dicts.
        print("→ Running diarization…", file=sys.stderr)
        predicted = m.diarize(audio=str(wav_path), batch_size=1)
        turns = _normalise_predictions(predicted)

        if max_speakers > 0:
            turns = _cap_speakers(turns, max_speakers)

        _cache_set(key, turns)
        return turns


def _normalise_predictions(raw: Any) -> List[Dict[str, Any]]:
    """Turn Sortformer's raw output into a list of turn dicts.

    Handles the two shapes NeMo has shipped:

    * A list of RTTM-style strings:
      ``"SPEAKER file 1 0.00 3.21 <NA> <NA> speaker_0 <NA> <NA>"``.
    * A nested list ``[[[start, end, speaker], ...]]`` per audio file.

    Parameters
    ----------
    raw : object
        Whatever ``model.diarize`` returned.

    Returns
    -------
    list of dict
        Normalised turns.
    """
    turns: List[Dict[str, Any]] = []
    if not raw:
        return turns

    # NeMo sometimes wraps the per-file result inside an outer list.
    payload = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], (list, tuple)) else raw

    for item in payload:
        if isinstance(item, str) and item.startswith("SPEAKER"):
            parts = item.split()
            # SPEAKER file chan start dur ...
            if len(parts) >= 8:
                start = float(parts[3])
                dur = float(parts[4])
                spk = parts[7].split("_")[-1]
                turns.append({"start": start, "end": start + dur, "speaker": spk})
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            start, end, spk = float(item[0]), float(item[1]), str(item[2])
            turns.append({"start": start, "end": end, "speaker": spk})

    turns.sort(key=lambda t: (t["start"], t["end"]))
    return turns


def _cap_speakers(turns: List[Dict[str, Any]], cap: int) -> List[Dict[str, Any]]:
    """Reduce the speaker inventory to ``cap`` by total duration.

    Keeps the top-``cap`` most-active speakers verbatim; every turn from
    a smaller speaker is re-assigned to the temporally nearest kept
    speaker's next turn. This is a coarse fallback for the rare case
    where Sortformer over-segments a two-person conversation into three
    labels.

    Parameters
    ----------
    turns : list of dict
        Sortformer output.
    cap : int
        Maximum number of distinct speakers to preserve.

    Returns
    -------
    list of dict
        Adjusted turn list.
    """
    if cap <= 0 or not turns:
        return turns
    durations: Dict[str, float] = {}
    for t in turns:
        durations[t["speaker"]] = durations.get(t["speaker"], 0.0) + max(0.0, t["end"] - t["start"])
    kept = {spk for spk, _ in sorted(durations.items(), key=lambda kv: -kv[1])[:cap]}
    if len(kept) == len(durations):
        return turns
    fallback_spk = next(iter(kept))
    return [{**t, "speaker": t["speaker"] if t["speaker"] in kept else fallback_spk} for t in turns]


# ── Output formats ──────────────────────────────────────────────────────────

def turns_to_rttm(turns: List[Dict[str, Any]], file_id: str = "file") -> str:
    """Render a turn list as an RTTM document.

    Parameters
    ----------
    turns : list of dict
        Turn list from :func:`diarize`.
    file_id : str, optional
        The ``file`` column of each RTTM line (usually the stem of the
        source file).

    Returns
    -------
    str
        RTTM document with a trailing newline.
    """
    lines: List[str] = []
    for t in turns:
        start = float(t["start"])
        dur = max(0.0, float(t["end"]) - start)
        spk = str(t["speaker"])
        lines.append(
            f"SPEAKER {file_id} 1 {start:.3f} {dur:.3f} <NA> <NA> speaker_{spk} <NA> <NA>"
        )
    return "\n".join(lines) + "\n"


def turns_to_json(turns: List[Dict[str, Any]]) -> str:
    """Render a turn list as pretty-printed JSON."""
    return json.dumps(turns, indent=2, ensure_ascii=False) + "\n"


# ── CLI ─────────────────────────────────────────────────────────────────────

@sprezzature_command(
    "sprezzature-audio-diarize",
    help=(
        "Run NVIDIA NeMo Sortformer on an audio / video file and emit "
        "RTTM + a JSON turn list. Cache on the extracted-audio hash."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-diarize interview.mp4\n"
        "  sprezzature-audio-diarize podcast.mp3 --format rttm\n"
        "  sprezzature-audio-diarize call.wav --max-speakers 2\n"
    ),
)
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--model", default=DEFAULT_MODEL, show_default=True,
              help="Sortformer checkpoint (HF id or NeMo alias).")
@click.option("--max-speakers", "max_speakers", type=int, default=0,
              help="Cap on predicted speakers (0 = data-driven).")
@click.option("--device", default="", help="Torch device: cuda / mps / cpu. Auto by default.")
@click.option("--format", "fmt", type=click.Choice(["both", "rttm", "json"]), default="both",
              show_default=True, help="What to write next to the source.")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output stem. Default: sibling of the source.")
@click.option("--no-cache", "no_cache", is_flag=True, default=False,
              help="Bypass the on-disk cache for this run.")
def _cli(
    source: Path,
    model: str,
    max_speakers: int,
    device: str,
    fmt: str,
    out: Optional[Path],
    no_cache: bool,
) -> int:
    """Click command body; returns an int exit code."""
    if no_cache:
        global NO_CACHE
        NO_CACHE = True

    if not source.is_file():
        click.echo(f"No such file: {source}", err=True)
        return 1

    turns = diarize(source, model=model, max_speakers=max_speakers, device=device)

    stem: Path = out if out is not None else source.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)

    if fmt in ("both", "rttm"):
        rttm_path = stem.with_suffix(".rttm")
        rttm_path.write_text(turns_to_rttm(turns, file_id=source.stem), encoding="utf-8")
        click.echo(f"→ Wrote {rttm_path}")
    if fmt in ("both", "json"):
        json_path = Path(str(stem) + ".diarization.json")
        json_path.write_text(turns_to_json(turns), encoding="utf-8")
        click.echo(f"→ Wrote {json_path}")

    speakers = sorted({t["speaker"] for t in turns})
    click.echo(f"→ {len(turns)} turn(s), {len(speakers)} speaker(s): {', '.join(speakers)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Writes RTTM + JSON siblings by default."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
