#!/usr/bin/env python3
"""
identify_from_titanet
=====================

Attach **names** to Sortformer-generated speaker labels using TitaNet
speaker embeddings.

Pipeline
--------

1. Load a Sortformer turn list (``*.diarization.json`` from
   :mod:`diarize_from_nemo`).
2. For each anonymous speaker id, average the TitaNet embeddings of a
   few of that speaker's own turns → one 192-D centroid per speaker.
3. Load a directory of reference clips (one WAV per known speaker,
   filename ≙ speaker name) and compute a centroid per reference.
4. Cosine-match every anonymous centroid to the closest reference above
   ``--threshold`` (default 0.55). Unmatched speakers keep their
   anonymous id.
5. Emit a small ``speakers.json`` mapping ``{"0": "Alice", "1": "Bob",
   "2": "2"}`` that ``caption_diarize.py`` picks up.

Default model
-------------

``nvidia/speakerverification_en_titanet_large`` — TitaNet-Large trained
for speaker verification. English-first but usable cross-lingually for
short-form conversational audio. Override with ``--model`` or the
``NEMO_TITANET_MODEL`` env var.

Reference-clip layout
---------------------

Pass ``--refs <DIR>`` where ``<DIR>`` contains one WAV per known
speaker::

    refs/
      Alice.wav      # ~5–15 s of clean speech
      Bob.wav
      Charlie.wav

The stem of each file becomes the label written to ``speakers.json``.

Usage
-----
::

    # Label an existing diarization JSON with known reference clips
    python identify_from_titanet.py interview.diarization.json \\
        --audio interview.wav \\
        --refs ./voices/ \\
        --out interview.speakers.json

    # No refs: still writes speakers.json with self-embeddings so a
    # downstream renaming step can be applied later
    python identify_from_titanet.py interview.diarization.json \\
        --audio interview.wav \\
        --out interview.speakers.json

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path as _PathHelper
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# numpy is imported lazily inside the functions below (heavy; only needed on the
# identify path). Declare it for type-checkers/ruff only, via TYPE_CHECKING
# (False at runtime), so the "numpy.ndarray" string annotations resolve without
# paying the import cost at module load.
if TYPE_CHECKING:
    import numpy

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
from diarize_from_nemo import extract_audio, pick_device  # noqa: E402

import click


#: Where install_diarize.py caches NeMo checkpoints.
NEMO_DIR: Path = Path(
    os.environ.get("SPREZZATURE_CACHE_DIR", Path.home() / ".cache" / "sprezzature-skill")
) / "nemo"

#: Default TitaNet checkpoint.
DEFAULT_MODEL: str = "nvidia/speakerverification_en_titanet_large"

#: Cosine threshold above which a reference match is accepted. Empirical
#: TitaNet paper thresholds are ~0.5–0.7 for the same-speaker decision;
#: 0.55 is a conservative middle ground.
DEFAULT_THRESHOLD: float = 0.55


# ── NeMo TitaNet runner ────────────────────────────────────────────────────

def _titanet_model(model_tag: str, device: str) -> Any:
    """Load a TitaNet checkpoint via NeMo.

    Deferred import so ``--help`` works without pulling torch + NeMo.

    Parameters
    ----------
    model_tag : str
        Hugging Face id (or NeMo alias) for the speaker-embedding model.
    device : str
        Torch device string.

    Returns
    -------
    nemo.collections.asr.models.EncDecSpeakerLabelModel
        Pretrained TitaNet model set to eval mode on the target device.
    """
    try:
        from nemo.collections.asr.models import EncDecSpeakerLabelModel  # type: ignore
    except ImportError as exc:  # pragma: no cover
        sys.exit(
            "NeMo is not installed. Run:\n"
            "    python scripts/install_diarize.py\n"
            f"({exc})"
        )
    os.environ.setdefault("NEMO_CACHE_DIR", str(NEMO_DIR))
    model = EncDecSpeakerLabelModel.from_pretrained(model_tag)
    model.eval()
    try:
        model = model.to(device)
    except Exception:  # noqa: BLE001
        pass
    return model


# ── Embedding helpers ──────────────────────────────────────────────────────

def embed_clip(model: Any, wav_path: Path) -> "numpy.ndarray":
    """Return the TitaNet embedding of a WAV clip.

    Parameters
    ----------
    model : NeMo speaker model
        Loaded via :func:`_titanet_model`.
    wav_path : pathlib.Path
        Path to a 16 kHz mono WAV file.

    Returns
    -------
    numpy.ndarray
        L2-normalised 192-D speaker embedding.
    """
    import numpy as np
    emb = model.get_embedding(str(wav_path))
    if hasattr(emb, "cpu"):
        emb = emb.cpu().numpy()
    emb = np.asarray(emb).squeeze()
    norm = float((emb ** 2).sum() ** 0.5) or 1.0
    return emb / norm


def slice_wav(src_wav: Path, dst_wav: Path, start: float, end: float) -> None:
    """Cut ``[start, end]`` (seconds) from ``src_wav`` into ``dst_wav``.

    Uses stdlib ``wave`` — no ffmpeg needed at this point (the caller
    already produced 16 kHz mono PCM via :func:`extract_audio`).

    Parameters
    ----------
    src_wav : pathlib.Path
        Source 16 kHz mono WAV.
    dst_wav : pathlib.Path
        Output WAV path (created).
    start : float
        Slice start in seconds.
    end : float
        Slice end in seconds (clipped to file length).
    """
    import wave
    with wave.open(str(src_wav), "rb") as fin:
        fr = fin.getframerate()
        nch = fin.getnchannels()
        sw = fin.getsampwidth()
        n_frames = fin.getnframes()
        s = max(0, int(start * fr))
        e = min(n_frames, int(end * fr))
        fin.setpos(s)
        frames = fin.readframes(max(0, e - s))
    with wave.open(str(dst_wav), "wb") as fout:
        fout.setnchannels(nch)
        fout.setsampwidth(sw)
        fout.setframerate(fr)
        fout.writeframes(frames)


def build_speaker_centroids(
    model: Any,
    wav_path: Path,
    turns: List[Dict[str, Any]],
    *,
    max_clips_per_speaker: int = 5,
    min_clip_seconds: float = 1.5,
) -> Dict[str, "numpy.ndarray"]:
    """Compute one TitaNet centroid per anonymous speaker id.

    Parameters
    ----------
    model : NeMo speaker model
    wav_path : pathlib.Path
        Full extracted 16 kHz mono WAV.
    turns : list of dict
        Sortformer turns.
    max_clips_per_speaker : int, optional
        Cap on turns sampled per speaker (defaults to the 5 longest).
    min_clip_seconds : float, optional
        Skip turns shorter than this (too short for stable embedding).

    Returns
    -------
    dict of str to numpy.ndarray
        ``{speaker_id: centroid}``.
    """
    import numpy as np

    by_speaker: Dict[str, List[Tuple[float, float]]] = {}
    for t in turns:
        dur = float(t["end"]) - float(t["start"])
        if dur < min_clip_seconds:
            continue
        by_speaker.setdefault(str(t["speaker"]), []).append((float(t["start"]), float(t["end"])))

    centroids: Dict[str, "numpy.ndarray"] = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for spk, intervals in by_speaker.items():
            # Sort by duration (longest first) and cap.
            intervals.sort(key=lambda ab: -(ab[1] - ab[0]))
            selected = intervals[:max_clips_per_speaker]
            embs: List[np.ndarray] = []
            for i, (s, e) in enumerate(selected):
                clip = tmp_dir / f"spk{spk}_clip{i}.wav"
                slice_wav(wav_path, clip, s, e)
                embs.append(embed_clip(model, clip))
            if embs:
                stacked = np.stack(embs, axis=0)
                mean = stacked.mean(axis=0)
                norm = float((mean ** 2).sum() ** 0.5) or 1.0
                centroids[spk] = mean / norm
    return centroids


def build_reference_centroids(model: Any, refs_dir: Path) -> Dict[str, "numpy.ndarray"]:
    """Load reference clips and return one centroid per stem.

    Parameters
    ----------
    model : NeMo speaker model
    refs_dir : pathlib.Path
        Directory of one WAV per known speaker; the file stem is used
        as the label.

    Returns
    -------
    dict of str to numpy.ndarray
        ``{name: centroid}``.
    """
    out: Dict[str, "numpy.ndarray"] = {}
    if not refs_dir.is_dir():
        return out
    for wav in sorted(refs_dir.glob("*.wav")):
        try:
            out[wav.stem] = embed_clip(model, wav)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to embed {wav}: {exc}", file=sys.stderr)
    return out


def match_speakers(
    centroids: Dict[str, "numpy.ndarray"],
    refs: Dict[str, "numpy.ndarray"],
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[str, str]:
    """Assign each anonymous speaker to the nearest reference name.

    Speakers whose best match falls below ``threshold`` keep their
    anonymous id verbatim.

    Parameters
    ----------
    centroids : dict of str to numpy.ndarray
        Anonymous-speaker centroids from :func:`build_speaker_centroids`.
    refs : dict of str to numpy.ndarray
        Reference-speaker centroids from :func:`build_reference_centroids`.
    threshold : float, optional
        Cosine threshold. Default 0.55.

    Returns
    -------
    dict of str to str
        Mapping ``{anon_id: name}``. Names include a trailing
        ``" (0.87)"`` confidence score in verbose mode; here we keep
        the raw name for downstream renderers.
    """
    import numpy as np
    labels: Dict[str, str] = {}
    for spk, c in centroids.items():
        if not refs:
            labels[spk] = spk
            continue
        best_name = spk
        best_sim = -1.0
        for name, ref in refs.items():
            sim = float(np.dot(c, ref))
            if sim > best_sim:
                best_sim = sim
                best_name = name
        labels[spk] = best_name if best_sim >= threshold else spk
    return labels


# ── CLI ────────────────────────────────────────────────────────────────────

@sprezzature_command(
    "sprezzature-audio-identify",
    help=(
        "Attach names to Sortformer speakers using TitaNet embeddings and "
        "a folder of reference clips (one WAV per known speaker)."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-identify interview.diarization.json --audio interview.wav --refs ./voices/\n"
        "  sprezzature-audio-identify podcast.diarization.json --audio podcast.wav --threshold 0.6\n"
    ),
)
@click.argument("diarization_json", type=click.Path(path_type=Path))
@click.option("--audio", "audio_path", type=click.Path(path_type=Path), required=True,
              help="Source audio / video the diarization was computed on.")
@click.option("--refs", "refs_dir", type=click.Path(path_type=Path), default=None,
              help="Directory of reference WAVs (filename stem = speaker name).")
@click.option("--model", default=DEFAULT_MODEL, show_default=True,
              help="TitaNet checkpoint.")
@click.option("--threshold", type=float, default=DEFAULT_THRESHOLD, show_default=True,
              help="Cosine threshold for accepting a reference match.")
@click.option("--device", default="", help="Torch device: cuda / mps / cpu. Auto by default.")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output JSON. Default: sibling '<stem>.speakers.json'.")
def _cli(
    diarization_json: Path,
    audio_path: Path,
    refs_dir: Optional[Path],
    model: str,
    threshold: float,
    device: str,
    out: Optional[Path],
) -> int:
    """Click command body; returns an int exit code."""
    if not diarization_json.is_file():
        click.echo(f"No such file: {diarization_json}", err=True)
        return 1
    if not audio_path.is_file():
        click.echo(f"No such file: {audio_path}", err=True)
        return 1

    turns: List[Dict[str, Any]] = json.loads(diarization_json.read_text(encoding="utf-8"))

    dev = pick_device(device)
    print(f"→ Loading {model} on {dev}…", file=sys.stderr)
    m = _titanet_model(model, dev)

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "input.wav"
        extract_audio(audio_path, wav_path)

        print("→ Building speaker centroids…", file=sys.stderr)
        speaker_centroids = build_speaker_centroids(m, wav_path, turns)

        refs: Dict[str, Any] = {}
        if refs_dir is not None:
            print(f"→ Loading reference clips from {refs_dir}…", file=sys.stderr)
            refs = build_reference_centroids(m, refs_dir)

        labels = match_speakers(speaker_centroids, refs, threshold=threshold)

    out_path = out or (diarization_json.with_name(diarization_json.stem.replace(".diarization", "") + ".speakers.json"))
    out_path.write_text(json.dumps(labels, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    click.echo(f"→ Wrote {out_path}")
    for spk, name in labels.items():
        marker = "✓" if name != spk else "•"
        click.echo(f"  {marker} {spk} → {name}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Writes ``<stem>.speakers.json`` next to the input."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
