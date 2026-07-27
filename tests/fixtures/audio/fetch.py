#!/usr/bin/env python3
"""
fetch.py — populate ``tests/fixtures/audio/`` with WAV clips for the
captions eval suite.

Run once locally:

    python3 tests/fixtures/audio/fetch.py

The script is **stdlib-only** (urllib + hashlib + json + subprocess).
``ffmpeg`` is invoked as a subprocess to trim / resample / downmix the
source files into the 16 kHz mono PCM-WAV shape ``captions_from_whisper``
prefers. If ``ffmpeg`` is missing, the script exits with a clear error
and a one-line install hint.

Idempotency
-----------

Each clip in ``CLIPS`` declares an expected ``sha256`` (of the original
source file bytes — *before* the ffmpeg conversion). On re-run:

1. If ``<name>.wav`` already exists AND the manifest records a matching
   source ``sha256`` for that name, the clip is skipped.
2. Otherwise the source is downloaded, hash-verified, then converted.

The ``MANIFEST.json`` written alongside the WAVs records, per clip:

- ``source_url``
- ``source_sha256``       (32-byte hex string)
- ``sample_rate_hz``
- ``channels``
- ``duration_seconds_approx``
- ``license``
- ``ground_truth_txt``    (sibling .txt path, relative)

Source policy
-------------

We deliberately prefer **LibriVox / archive.org** for English and French
because:

- Public domain — no licence headache for a public test fixture.
- Stable URLs — archive.org has kept its `/download/<item>/<file>`
  scheme stable for over a decade.
- Solo readers — clean speech, far easier to score WER against than
  multi-voice casts.

The third clip (``vocab-biasing-clip.wav``) is the awkward one. The
glossary in ``tests/fixtures/vocab/glossary.txt`` contains project-brand
terms (``pywhispercpp``, ``VisionCell``, ``Acme Robotics``, ``Tailwind``,
``WebVTT``, ``Ollama``) which no LibriVox reader uttered. The honest
move is to provide a **user-supplied recording** path — see the
``USER_SUPPLIED`` block below for the manual workflow.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "MANIFEST.json"
TARGET_SAMPLE_RATE_HZ = 16_000
TARGET_CHANNELS = 1
TARGET_BIT_DEPTH = "pcm_s16le"
TARGET_DURATION_SEC_CAP = 30   # safety cap; per-clip ``trim_seconds`` overrides this


# ─── Clip catalogue ─────────────────────────────────────────────────────────
#
# Each entry is intentionally conservative on the URL choice: prefer
# `archive.org/download/<item>/<file>.<ext>` where the item is a
# LibriVox solo-reader recording. The `sha256` field MUST match the
# source bytes (not the converted WAV). The first time you run this
# script, set the hash to the empty string `""` and the script will
# print the observed hash so you can pin it.

@dataclass(frozen=True)
class Clip:
    name: str                  # output basename (without .wav)
    source_url: str            # http(s) URL to a stable public-domain source
    source_sha256: str         # 32-byte hex digest of the downloaded bytes
    trim_start_sec: float      # ffmpeg -ss start
    trim_duration_sec: float   # ffmpeg -t length
    license_id: str            # short SPDX-ish label
    description: str           # human note for MANIFEST


CLIPS: tuple[Clip, ...] = (
    # English — LibriVox solo reader, ~30 seconds.
    # Replace `source_url` with a verified archive.org file before
    # committing a non-empty `source_sha256`.
    Clip(
        name="en-clean-30s",
        source_url="https://archive.org/download/REPLACE_WITH_LIBRIVOX_ITEM/REPLACE.mp3",
        source_sha256="",   # pin after first successful fetch
        trim_start_sec=10.0,
        trim_duration_sec=30.0,
        license_id="public-domain (LibriVox)",
        description="Clean English speech, solo reader, ~30 s; "
                    "ground truth in en-clean-30s.txt.",
    ),
    # French — LibriVox French solo reader, ~30 seconds.
    Clip(
        name="fr-clean-30s",
        source_url="https://archive.org/download/REPLACE_WITH_LIBRIVOX_FR_ITEM/REPLACE.mp3",
        source_sha256="",
        trim_start_sec=10.0,
        trim_duration_sec=30.0,
        license_id="public-domain (LibriVox)",
        description="Clean French speech, solo reader, ~30 s; "
                    "ground truth in fr-clean-30s.txt.",
    ),
    # Vocab-biasing — special-cased. See USER_SUPPLIED note.
    # If the URL is the literal placeholder, the script skips this entry
    # with an informative message rather than failing the whole run.
    Clip(
        name="vocab-biasing-clip",
        source_url="USER_SUPPLIED",   # record locally; see README
        source_sha256="",
        trim_start_sec=0.0,
        trim_duration_sec=10.0,
        license_id="user-supplied",
        description="~10 s recording of you saying at least one term from "
                    "tests/fixtures/vocab/glossary.txt (e.g. 'pywhispercpp'). "
                    "Ground truth in vocab-biasing-clip.txt.",
    ),
)


# ─── ffmpeg discovery ───────────────────────────────────────────────────────

def _ffmpeg_or_exit() -> str:
    """Return the path to ``ffmpeg``; exit 1 with install hint if missing."""
    path = shutil.which("ffmpeg")
    if not path:
        print(
            "error: 'ffmpeg' not on PATH.\n"
            "  macOS:   brew install ffmpeg\n"
            "  Debian:  sudo apt-get install ffmpeg\n"
            "  Windows: winget install Gyan.FFmpeg",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


# ─── HTTP helpers ───────────────────────────────────────────────────────────

def _download_to(url: str, dest: Path) -> bytes:
    """
    Download ``url`` to ``dest`` and return the raw bytes for hashing.

    archive.org occasionally redirects through HTTPS variants — urllib
    follows them by default. We set a polite User-Agent so the request
    is not throttled as a generic bot.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sprezzature-skill-fetch/1.0 (+https://github.com/warith-harchaoui/sprezzature)",
        },
    )
    print(f"  downloading {url}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data: bytes = resp.read()
    except urllib.error.URLError as e:
        print(f"  download failed: {e}", file=sys.stderr)
        raise
    dest.write_bytes(data)
    return data


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─── ffmpeg conversion ──────────────────────────────────────────────────────

def _ffmpeg_to_wav(
    ffmpeg: str, src: Path, dest: Path, start_sec: float, duration_sec: float
) -> None:
    """
    Trim ``src`` from ``start_sec`` for ``duration_sec`` and re-encode
    as 16 kHz mono PCM WAV at ``dest``. Overwrites ``dest`` if present.
    """
    cmd = [
        ffmpeg,
        "-y",                                    # overwrite
        "-loglevel", "error",
        "-ss", f"{start_sec:.3f}",               # seek BEFORE -i for speed
        "-i", str(src),
        "-t", f"{duration_sec:.3f}",
        "-ac", str(TARGET_CHANNELS),
        "-ar", str(TARGET_SAMPLE_RATE_HZ),
        "-c:a", TARGET_BIT_DEPTH,
        str(dest),
    ]
    subprocess.run(cmd, check=True)


# ─── Manifest I/O ───────────────────────────────────────────────────────────

def _load_manifest() -> dict:
    if MANIFEST_PATH.is_file():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"warning: {MANIFEST_PATH.name} is corrupt; regenerating",
                  file=sys.stderr)
    return {"clips": {}}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ─── Per-clip pipeline ──────────────────────────────────────────────────────

def _process_clip(
    clip: Clip, ffmpeg: str, manifest: dict, tmp_dir: Path
) -> tuple[bool, Optional[str]]:
    """
    Returns ``(success, reason)`` where ``reason`` is a short status
    string ("skipped: already-have", "skipped: USER_SUPPLIED", …) used
    for the run summary.
    """
    wav_path = HERE / f"{clip.name}.wav"
    txt_path = HERE / f"{clip.name}.txt"

    # USER_SUPPLIED → never download; just verify the user already put a
    # WAV + truth file in place.
    if clip.source_url == "USER_SUPPLIED":
        if wav_path.is_file() and txt_path.is_file():
            manifest["clips"][clip.name] = {
                "source_url": "USER_SUPPLIED",
                "source_sha256": _sha256_hex(wav_path.read_bytes()),
                "sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
                "channels": TARGET_CHANNELS,
                "duration_seconds_approx": clip.trim_duration_sec,
                "license": clip.license_id,
                "ground_truth_txt": txt_path.name,
                "description": clip.description,
            }
            return True, "ok (user-supplied present)"
        return False, (
            f"USER_SUPPLIED: record {wav_path.name} + write {txt_path.name} "
            f"yourself (see README)"
        )

    # Refuse the placeholder URL — fail loud so users notice they need
    # to pick a real source first.
    if "REPLACE" in clip.source_url:
        return False, (
            "source_url is still the placeholder — edit fetch.py and pin a "
            "verified archive.org URL before re-running"
        )

    # Fast path: existing WAV + manifest hash match → no work.
    prev = manifest["clips"].get(clip.name)
    if (
        wav_path.is_file()
        and prev
        and prev.get("source_sha256") == clip.source_sha256
        and clip.source_sha256                       # never trust ""
    ):
        return True, "skipped (cache hit)"

    # Download → verify → convert.
    src_ext = clip.source_url.rsplit(".", 1)[-1].lower() or "bin"
    src_tmp = tmp_dir / f"{clip.name}.{src_ext}"
    data = _download_to(clip.source_url, src_tmp)
    observed = _sha256_hex(data)
    print(f"  downloaded {len(data):,} bytes → sha256 {observed}")

    if not clip.source_sha256:
        print(
            f"  NOTE: no expected sha256 pinned for '{clip.name}'.\n"
            f"        Edit fetch.py and set source_sha256={observed!r} "
            "to lock the source.",
            file=sys.stderr,
        )
    elif observed != clip.source_sha256:
        return False, (
            f"sha256 mismatch: expected {clip.source_sha256}, got {observed} "
            f"(refusing to convert untrusted bytes)"
        )

    _ffmpeg_to_wav(
        ffmpeg, src_tmp, wav_path, clip.trim_start_sec, clip.trim_duration_sec
    )

    manifest["clips"][clip.name] = {
        "source_url": clip.source_url,
        "source_sha256": observed,
        "sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
        "channels": TARGET_CHANNELS,
        "duration_seconds_approx": clip.trim_duration_sec,
        "license": clip.license_id,
        "ground_truth_txt": txt_path.name,
        "description": clip.description,
    }

    return True, "ok (fetched + converted)"


# ─── Main ───────────────────────────────────────────────────────────────────

def main() -> int:
    ffmpeg = _ffmpeg_or_exit()
    manifest = _load_manifest()

    tmp_dir = HERE / ".cache"
    tmp_dir.mkdir(exist_ok=True)

    failed: list[str] = []
    print(f"→ writing into {HERE}")
    for clip in CLIPS:
        print(f"\n• {clip.name}")
        try:
            ok, reason = _process_clip(clip, ffmpeg, manifest, tmp_dir)
        except Exception as e:
            ok, reason = False, f"{type(e).__name__}: {e}"
        marker = "  ✓" if ok else "  ✗"
        print(f"{marker} {reason}")
        if not ok:
            failed.append(f"{clip.name}: {reason}")

    _save_manifest(manifest)
    print(f"\n→ MANIFEST: {MANIFEST_PATH}")

    # Best-effort cleanup of the source cache. Keep on failure so the user
    # can inspect what came down the wire.
    if not failed:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if failed:
        print("\nSome clips were not produced:", file=sys.stderr)
        for line in failed:
            print(f"  - {line}", file=sys.stderr)
        print(
            "\nThis is OK — eval tests `pytest.skip()` when a WAV is "
            "missing. Fix the items above and re-run if you want full "
            "captions coverage.",
            file=sys.stderr,
        )
        return 1
    print("\nAll clips ready. Run `pytest -m eval` to use them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
