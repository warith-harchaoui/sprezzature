#!/usr/bin/env python3
"""
install_narrate
===============

One-stop install / model-pull helper for the narration engines
(``openvoice``, ``chatterbox``). Mirrors the pattern of
``install_alt_ai.py`` and ``install_captions.py`` from sprezzature-accessibility:
the script does the boring downloads so the user does not have to
read the upstream README.

What it does, per engine
------------------------
``openvoice``
    1. Verifies the package is importable (``pip install`` instructions
       on the bare-machine path).
    2. Downloads the OpenVoice v2 base-speaker and tone-converter
       checkpoints from the official release artifact into
       ``~/.cache/sprezzature-skill/openvoice/``.
    3. Writes a tiny ``config.json`` pointing at the local files so
       ``narrate_openvoice.py`` finds them.

``chatterbox``
    1. Verifies the package is importable.
    2. Triggers the model's lazy ``from_pretrained`` so the
       Hugging Face weights cache (under ``~/.cache/huggingface/``)
       is populated.
    3. Creates the voices library directory
       ``~/.cache/sprezzature-skill/chatterbox/voices/`` ready to receive
       custom WAVs for built-in-by-filename voice selection.

The script never installs the heavy ML library itself — pip is the
canonical channel and we don't want to wrap it. Install with:

::

    pip install -r sprezzature-publish/scripts/requirements-narrate-openvoice.txt
    # or
    pip install -r sprezzature-publish/scripts/requirements-narrate-chatterbox.txt

Then run:

::

    python3 sprezzature-publish/scripts/install_narrate.py --engine openvoice
    python3 sprezzature-publish/scripts/install_narrate.py --engine chatterbox

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path


# ── Module-level configuration ──────────────────────────────────────────────

#: Where engine checkpoints / configs live, per-user. Mirrors the
#: ``~/.cache/sprezzature-skill/`` convention used by alt_from_ollama.
CACHE_ROOT: Path = Path.home() / ".cache" / "sprezzature-skill"

#: OpenVoice v2 checkpoint bundle. Tagged stable release on GitHub.
#: Kept as a single configurable URL so the maintainer can pin a new
#: version without editing logic.
OPENVOICE_CHECKPOINT_URL: str = (
    "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/"
    "checkpoints_v2_0417.zip"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _download(url: str, dest: Path) -> None:
    """
    Download ``url`` to ``dest`` with a tiny progress line.

    Stdlib only — no ``requests`` so install_narrate.py runs before
    the user has installed any extras.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"→ downloading {url}")
    print(f"  into {dest}")
    with urllib.request.urlopen(url) as resp:  # noqa: S310 — trusted upstream
        total: int = int(resp.headers.get("Content-Length", "0"))
        chunk: int = 1 << 20  # 1 MiB
        read: int = 0
        with open(dest, "wb") as out:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                read += len(buf)
                if total:
                    pct: float = 100.0 * read / total
                    print(f"  …{pct:5.1f}%  ({read / 1e6:.1f} / "
                          f"{total / 1e6:.1f} MB)", end="\r")
    print()


def _check_importable(modules: tuple[str, ...]) -> bool:
    """Return True iff every ``modules`` entry imports cleanly."""
    for name in modules:
        try:
            importlib.import_module(name)
        except ImportError:
            return False
    return True


# ── OpenVoice v2 installer ─────────────────────────────────────────────────

def install_openvoice() -> int:
    """
    Download OpenVoice v2 checkpoints into the local cache.

    Returns
    -------
    int
        ``0`` on success; ``1`` when the package isn't installed yet
        (the script prints the pip command and exits).
    """
    if not _check_importable(("openvoice",)):
        print(
            "openvoice not installed; run\n"
            "  pip install -r sprezzature-publish/scripts/"
            "requirements-narrate-openvoice.txt",
            file=sys.stderr,
        )
        return 1

    target_dir: Path = CACHE_ROOT / "openvoice"
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path: Path = target_dir / "checkpoints_v2.zip"

    if not zip_path.is_file():
        _download(OPENVOICE_CHECKPOINT_URL, zip_path)
    else:
        print(f"→ checkpoint archive already present: {zip_path}")

    extract_dir: Path = target_dir / "checkpoints"
    if not extract_dir.is_dir():
        print(f"→ extracting into {extract_dir}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
    else:
        print(f"→ checkpoints already extracted: {extract_dir}")

    # The exact directory layout of the OpenVoice v2 zip is documented
    # in the upstream README; we point the wrapper config at the
    # canonical filenames.
    base_speakers_dir: Path = extract_dir / "checkpoints_v2" / "base_speakers" / "ses"
    converter_ckpt: Path = (
        extract_dir / "checkpoints_v2" / "converter" / "checkpoint.pth"
    )
    config: dict[str, object] = {
        "device": "cpu",
        "default_language": "English",
        "base_speakers_dir": str(base_speakers_dir),
        "converter_ckpt": str(converter_ckpt),
        "default_source_se": str(base_speakers_dir / "en-default.pth"),
        "sdp_ratio": 0.2,
        "tau": 0.3,
    }
    (target_dir / "config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8",
    )
    print(f"✓ openvoice ready (config: {target_dir / 'config.json'})")
    return 0


# ── ChatterboxTTS installer ────────────────────────────────────────────────

def install_chatterbox() -> int:
    """
    Trigger ChatterboxTTS' lazy weight pull + set up the voices dir.

    Returns
    -------
    int
        ``0`` on success; ``1`` when the package isn't installed yet.
    """
    try:
        mod = importlib.import_module("chatterbox.tts")
    except ImportError:
        try:
            mod = importlib.import_module("chatterbox_tts")
        except ImportError:
            print(
                "chatterbox-tts not installed; run\n"
                "  pip install -r sprezzature-publish/scripts/"
                "requirements-narrate-chatterbox.txt",
                file=sys.stderr,
            )
            return 1

    target_dir: Path = CACHE_ROOT / "chatterbox" / "voices"
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"→ voices library: {target_dir}")
    print("  drop custom WAVs here to use them as --voice <filename-no-ext>")

    # Trigger the lazy download. ``from_pretrained`` populates
    # ~/.cache/huggingface and prints HF's own progress.
    print("→ pulling ChatterboxTTS weights (first time only, ~1 GB)")
    mod.ChatterboxTTS.from_pretrained(device="cpu")
    print("✓ chatterbox ready")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="install_narrate",
        description=(
            "Download model checkpoints for the narration engines "
            "(openvoice, chatterbox). The Python packages themselves "
            "are installed via pip — see the per-engine requirements "
            "files in sprezzature-publish/scripts/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--engine",
        choices=("openvoice", "chatterbox", "all"),
        default="all",
        help="Engine to install (default: all).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    engines = (
        ("openvoice", "chatterbox")
        if args.engine == "all" else (args.engine,)
    )
    failed: int = 0
    for engine in engines:
        if engine == "openvoice":
            failed += install_openvoice()
        else:
            failed += install_chatterbox()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
