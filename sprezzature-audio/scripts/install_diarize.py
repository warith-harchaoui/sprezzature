#!/usr/bin/env python3
"""
install_diarize
===============

Cross-platform installer for the speaker-diarization / speaker-ID tier.

Installs (or verifies) the ``nemo_toolkit[asr]`` PyPI package and
pre-downloads the two NVIDIA NeMo checkpoints used by the skill:

* ``nvidia/diar_sortformer_4spk-v1`` — Sortformer, end-to-end speaker
  diarization for up to 4 concurrent speakers.
* ``nvidia/speakerverification_en_titanet_large`` — TitaNet-Large
  speaker-verification embeddings (192-D).

Torch is intentionally **not** pinned here — CPU / CUDA / Apple-silicon
MPS builds all differ; installing NeMo pulls a sensible default. If you
need a specific torch build (CUDA 12.x, ROCm, …), install it *before*
running this script.

Usage
-----
::

    # Full install (nemo + both checkpoints)
    python install_diarize.py

    # Skip the model prefetch — download at first use instead
    python install_diarize.py --no-download

    # Only download the checkpoints (nemo already installed)
    python install_diarize.py --no-install

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path as _PathHelper
from pathlib import Path
from typing import List

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402


#: Where NeMo caches downloaded checkpoints; the diarize scripts export
#: the same env var so the two agree on the location.
NEMO_DIR: Path = Path(
    (os.environ.get("SPREZZATURE_CACHE_DIR") or os.environ.get("FRONT_CACHE_DIR") or Path.home() / ".cache" / "sprezzature-skill")
) / "nemo"


#: Hugging Face id for the diarization model.
SORTFORMER_MODEL: str = "nvidia/diar_sortformer_4spk-v1"


#: Hugging Face id for the speaker-embedding model.
TITANET_MODEL: str = "nvidia/speakerverification_en_titanet_large"


def _is_installed(pkg: str) -> bool:
    """Return True when ``pkg`` is importable in the active interpreter.

    Uses :func:`importlib.util.find_spec` — no side effects.

    Parameters
    ----------
    pkg : str
        Top-level package name to probe.
    """
    return importlib.util.find_spec(pkg) is not None


def ensure_nemo() -> None:
    """Install ``nemo_toolkit[asr]`` if it isn't already importable.

    NeMo has heavy transitive dependencies (torch, torchaudio,
    pytorch-lightning, hydra-core, sentencepiece, tqdm, …). Installation
    can take several minutes on a fresh venv; the script prints progress
    so the caller does not think it hung.

    Raises
    ------
    SystemExit
        On any pip failure or if the post-install probe cannot find NeMo.
    """
    if _is_installed("nemo"):
        print("→ nemo_toolkit already installed.")
        return

    print("→ Installing nemo_toolkit[asr] via pip (this can take several minutes)…")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "nemo_toolkit[asr]"],
    )
    if proc.returncode != 0:
        sys.exit(
            f"pip install nemo_toolkit[asr] failed (exit {proc.returncode}).\n"
            "Common causes:\n"
            "  * python < 3.10 — NeMo dropped 3.9 in a recent release; upgrade Python.\n"
            "  * torch already pinned to a non-matching CUDA build; install torch first.\n"
            "  * A very old pip; run `python -m pip install --upgrade pip` and retry."
        )
    if not _is_installed("nemo"):
        sys.exit(
            "nemo_toolkit installed by pip but cannot be located in the active "
            "interpreter's import path. Check virtualenv / PYTHONPATH."
        )


def prefetch_models(models: List[str]) -> None:
    """Pre-download NeMo checkpoints into :data:`NEMO_DIR`.

    Uses ``EncDecSpeakerLabelModel.from_pretrained`` for TitaNet and
    ``SortformerEncLabelModel.from_pretrained`` for Sortformer. NeMo
    handles the Hugging Face mirror + resume-on-interruption itself.

    Parameters
    ----------
    models : list of str
        Hugging Face ids to prefetch.

    Raises
    ------
    SystemExit
        On any download failure.
    """
    NEMO_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NEMO_CACHE_DIR", str(NEMO_DIR))

    for tag in models:
        print(f"→ Pre-downloading {tag} into {NEMO_DIR}…")
        try:
            if tag == SORTFORMER_MODEL:
                from nemo.collections.asr.models import SortformerEncLabelModel  # type: ignore
                SortformerEncLabelModel.from_pretrained(tag)
            elif tag == TITANET_MODEL:
                from nemo.collections.asr.models import EncDecSpeakerLabelModel  # type: ignore
                EncDecSpeakerLabelModel.from_pretrained(tag)
            else:
                print(f"[warn] unknown model tag '{tag}' — skipping.", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"Download failed for {tag}: {exc}")

    print(f"→ Cache populated at {NEMO_DIR}.")


def main() -> int:
    """Run pip-install + checkpoint-prefetch. Returns 0 on success."""
    p = make_parser(
        prog="sprezzature-audio-install-diarize",
        description=(
            "Install nemo_toolkit[asr] and pre-download the Sortformer + "
            "TitaNet checkpoints so `sprezzature-audio-diarize` / "
            "`sprezzature-audio-identify` run offline."
        ),
    )
    p.add_argument("--no-install", action="store_true", help="Skip the pip install step.")
    p.add_argument("--no-download", action="store_true", help="Skip the model prefetch step.")
    p.add_argument("--only", choices=("sortformer", "titanet"), default=None,
                   help="Prefetch just one of the two checkpoints.")
    args = p.parse_args()

    if not args.no_install:
        ensure_nemo()

    if not args.no_download:
        models: List[str] = []
        if args.only in (None, "sortformer"):
            models.append(SORTFORMER_MODEL)
        if args.only in (None, "titanet"):
            models.append(TITANET_MODEL)
        prefetch_models(models)

    print()
    print("→ Ready. Try:")
    print("    python scripts/diarize_from_nemo.py path/to/interview.mp4")
    print("    python scripts/identify_from_titanet.py <diar.json> --audio <audio> --refs ./voices/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
