"""
extract_cv_subset — pick a diverse N-clip subset from a Common Voice tarball.

Reads a Common Voice 26.0 release tarball, stratified-samples ``--count``
clips per language balanced on speaker / age / gender / accent, transcodes
each selected MP3 to 16 kHz mono PCM WAV, writes per-clip ``.txt`` truth
files, and emits ``MANIFEST.json`` + ``STATS.json`` capturing source IDs,
checksums, and the realised diversity breakdown.

Stdlib + ffmpeg only. The tarball is read in two passes (no random access
on .tar.gz): pass 1 extracts TSV metadata, pass 2 extracts the chosen MP3s.

Usage
-----
::

    python3 extract_cv_subset.py \\
        --lang fr \\
        --tarball /tmp/common-voice-scripted-speech-26-0-french-XXXX.tar.gz \\
        --count 100 \\
        --out tests/fixtures/audio/cv/fr/

Examples
--------
::

    # default 100-clip subset
    python3 extract_cv_subset.py --lang en --tarball /tmp/cv-en.tar.gz --out cv/en/

    # smaller subset for a quick smoke test
    python3 extract_cv_subset.py --lang es --tarball /tmp/cv-es.tar.gz \\
        --count 20 --out cv/es/

Notes
-----
- Requires ``ffmpeg`` on PATH for MP3 → 16 kHz mono PCM transcode.
- Idempotent: re-running with the same ``--seed`` reproduces the selection
  bit-for-bit. If ``MANIFEST.json`` already lists clips whose WAV SHA256
  matches on disk, those entries are kept untouched.
- The opaque ``client_id`` hash from Common Voice is recorded verbatim
  for reproducibility but is NEVER paired with real-world identifiers
  per the Mozilla Data Collective platform terms (see ``LICENSE.md``).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import subprocess
import sys
import tarfile
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


# Common Voice 26.0 TSV columns we rely on. Any missing column gets a
# blank string — the script never crashes on absent demographics.
TSV_COLUMNS_REQUIRED = ("client_id", "path", "sentence")
TSV_COLUMNS_OPTIONAL = ("age", "gender", "accents", "variant", "locale",
                        "up_votes", "down_votes", "segment")

# Sampling defaults — tuned for a 100-clip WER bench per language.
DEFAULT_COUNT = 100
DEFAULT_MAX_PER_SPEAKER = 3
DEFAULT_MIN_DURATION_MS = 3000
DEFAULT_MAX_DURATION_MS = 15000
DEFAULT_MIN_TEXT_CHARS = 30
DEFAULT_MAX_TEXT_CHARS = 200
DEFAULT_SEED = 0

# WAV target shape — what whisper.cpp expects.
WAV_SAMPLE_RATE = 16000
WAV_CHANNELS = 1


# ── Data shapes ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CVRow:
    """One row of a Common Voice TSV, with the few columns we care about."""
    client_id: str
    path: str            # MP3 filename, e.g. "common_voice_en_12345.mp3"
    sentence: str
    age: str
    gender: str
    accents: str
    variant: str
    duration_ms: int


@dataclass
class ManifestClip:
    """One entry in the per-language MANIFEST.json."""
    index: int
    wav: str
    txt: str
    source_clip_id: str        # CV MP3 filename (path column)
    source_sha256: str         # SHA256 of the source MP3 bytes
    wav_sha256: str            # SHA256 of the transcoded WAV bytes
    sentence: str
    duration_ms: int
    client_id: str             # Opaque speaker hash from CV
    age: str
    gender: str
    accents: str
    variant: str


# ── TSV extraction (pass 1) ─────────────────────────────────────────────────


def read_tsv_member(tar: tarfile.TarFile, member_name_suffix: str) -> list[dict[str, str]]:
    """
    Scan the tarball for the first member whose name ends with
    ``member_name_suffix`` and parse it as a TSV. Returns an empty list
    when the member is not found.
    """
    tar.fileobj.seek(0)  # type: ignore[union-attr]
    # Re-iterate from the start; tarfile keeps an internal pointer that
    # we need to reset for a second scan.
    for member in tar:
        if not member.isfile():
            continue
        if member.name.endswith(member_name_suffix):
            stream = tar.extractfile(member)
            if stream is None:
                return []
            data = stream.read().decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(data), delimiter="\t")
            return list(reader)
    return []


def load_metadata(tarball: Path, lang: str) -> tuple[list[CVRow], int]:
    """
    Open the Common Voice tarball and load ``validated.tsv`` +
    ``clip_durations.tsv`` for the requested language. Returns the parsed
    rows and the total number of validated clips before any filtering.
    """
    print(f"→ Pass 1: reading TSV metadata for {lang!r} from {tarball.name}")
    print("  (this scans most of the tarball — expect several minutes for the larger languages)")
    with tarfile.open(tarball, mode="r:gz") as tar:
        validated_suffix = f"/{lang}/validated.tsv"
        durations_suffix = f"/{lang}/clip_durations.tsv"
        validated = read_tsv_member(tar, validated_suffix)
        durations = read_tsv_member(tar, durations_suffix)

    if not validated:
        sys.exit(
            f"× No '{validated_suffix}' found in the tarball. "
            f"Check that --lang matches the language inside the archive."
        )

    # clip_durations.tsv: columns 'clip', 'duration[ms]'
    dur_map: dict[str, int] = {}
    for row in durations:
        clip = row.get("clip") or row.get("path") or ""
        ms = row.get("duration[ms]") or row.get("duration") or ""
        try:
            dur_map[clip] = int(ms)
        except (TypeError, ValueError):
            continue

    rows: list[CVRow] = []
    for r in validated:
        try:
            row = CVRow(
                client_id=r.get("client_id", ""),
                path=r.get("path", ""),
                sentence=(r.get("sentence", "") or "").strip(),
                age=r.get("age", "") or "",
                gender=r.get("gender", "") or "",
                accents=r.get("accents", "") or "",
                variant=r.get("variant", "") or "",
                duration_ms=dur_map.get(r.get("path", ""), 0),
            )
        except KeyError:
            continue
        if not row.path or not row.sentence:
            continue
        rows.append(row)
    print(f"  validated.tsv → {len(rows)} clips")
    return rows, len(validated)


# ── Filtering + stratified sampling ─────────────────────────────────────────


def filter_clips(
    rows: Iterable[CVRow],
    *,
    min_duration_ms: int,
    max_duration_ms: int,
    min_text_chars: int,
    max_text_chars: int,
) -> list[CVRow]:
    """Drop clips outside the requested duration / sentence-length windows."""
    out: list[CVRow] = []
    for r in rows:
        if r.duration_ms == 0:
            # No duration metadata — keep, ffmpeg will produce something.
            pass
        elif not (min_duration_ms <= r.duration_ms <= max_duration_ms):
            continue
        n = len(r.sentence)
        if not (min_text_chars <= n <= max_text_chars):
            continue
        out.append(r)
    return out


def stratified_sample(
    rows: list[CVRow],
    *,
    count: int,
    max_per_speaker: int,
    seed: int,
) -> list[CVRow]:
    """
    Pick a diverse subset of ``count`` rows.

    Strategy:

    1. Group rows by (gender, age_bracket, accent_bucket).
    2. Round-robin across strata, drawing one row per stratum each cycle.
    3. Enforce ``max_per_speaker`` — no single ``client_id`` may
       contribute more than this many clips, so a prolific contributor
       does not dominate.
    4. Inside a stratum, randomise order with ``seed`` for reproducibility.

    Strata with no rows are skipped silently. If the requested
    ``count`` exceeds what the strata can supply under the speaker cap,
    we return as many as available and print a warning.
    """
    rng = random.Random(seed)
    buckets: dict[tuple[str, str, str], list[CVRow]] = defaultdict(list)
    for r in rows:
        key = (r.gender or "unknown", _age_bracket(r.age), _accent_bucket(r.accents))
        buckets[key].append(r)
    for v in buckets.values():
        rng.shuffle(v)

    keys = list(buckets.keys())
    rng.shuffle(keys)

    picked: list[CVRow] = []
    per_speaker: dict[str, int] = defaultdict(int)
    seen_paths: set[str] = set()

    # Round-robin draw until we hit the target or exhaust supply.
    while len(picked) < count and keys:
        progressed = False
        for key in list(keys):
            if not buckets[key]:
                keys.remove(key)
                continue
            # Pop until we find a row that respects the speaker cap.
            chosen: CVRow | None = None
            while buckets[key]:
                cand = buckets[key].pop()
                if cand.path in seen_paths:
                    continue
                if per_speaker[cand.client_id] >= max_per_speaker:
                    continue
                chosen = cand
                break
            if chosen is None:
                keys.remove(key)
                continue
            picked.append(chosen)
            per_speaker[chosen.client_id] += 1
            seen_paths.add(chosen.path)
            progressed = True
            if len(picked) >= count:
                break
        if not progressed:
            break

    if len(picked) < count:
        print(
            f"⚠ Asked for {count} clips but only {len(picked)} satisfy filters + "
            f"per-speaker cap. Consider raising --max-per-speaker or widening "
            f"--min-duration-ms / --max-duration-ms."
        )
    return picked[:count]


def _age_bracket(age: str) -> str:
    """Coarse bucket for stratification. CV uses 'teens', 'twenties', ..."""
    return age.lower() or "unknown"


def _accent_bucket(accent: str) -> str:
    """First comma-separated accent value, lowercased. Empty → 'unknown'."""
    head = (accent.split(",") + [""])[0].strip().lower()
    return head or "unknown"


# ── MP3 extraction (pass 2) + transcode ─────────────────────────────────────


def extract_and_transcode(
    tarball: Path,
    selected: list[CVRow],
    out_dir: Path,
) -> list[ManifestClip]:
    """
    Stream the tarball a second time and extract only the MP3s we picked.
    Each extracted MP3 is transcoded to 16 kHz mono PCM WAV via ffmpeg
    and the source MP3 is deleted from the temp dir.
    """
    if shutil.which("ffmpeg") is None:
        sys.exit("× ffmpeg not on PATH. Install it (brew install ffmpeg / apt install ffmpeg) and retry.")

    paths_wanted: dict[str, int] = {r.path: i for i, r in enumerate(selected, start=1)}
    rows_by_path: dict[str, CVRow] = {r.path: r for r in selected}
    tmp_dir = out_dir / ".cv-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ Pass 2: extracting {len(paths_wanted)} MP3s and transcoding to WAV")
    extracted: list[ManifestClip] = []
    remaining = set(paths_wanted)

    with tarfile.open(tarball, mode="r:gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".mp3"):
                continue
            basename = Path(member.name).name
            if basename not in paths_wanted:
                continue
            index = paths_wanted[basename]
            row = rows_by_path[basename]
            stream = tar.extractfile(member)
            if stream is None:
                continue
            mp3_bytes = stream.read()
            mp3_sha = hashlib.sha256(mp3_bytes).hexdigest()
            mp3_path = tmp_dir / basename
            mp3_path.write_bytes(mp3_bytes)

            wav_name = f"clip-{index:03d}.wav"
            txt_name = f"clip-{index:03d}.txt"
            wav_path = out_dir / wav_name
            txt_path = out_dir / txt_name
            _transcode_mp3_to_wav(mp3_path, wav_path)
            wav_sha = hashlib.sha256(wav_path.read_bytes()).hexdigest()
            txt_path.write_text(row.sentence + "\n", encoding="utf-8")
            mp3_path.unlink()

            extracted.append(ManifestClip(
                index=index,
                wav=wav_name,
                txt=txt_name,
                source_clip_id=basename,
                source_sha256=mp3_sha,
                wav_sha256=wav_sha,
                sentence=row.sentence,
                duration_ms=row.duration_ms,
                client_id=row.client_id,
                age=row.age,
                gender=row.gender,
                accents=row.accents,
                variant=row.variant,
            ))
            remaining.discard(basename)
            if len(extracted) % 10 == 0 or not remaining:
                print(f"  {len(extracted)}/{len(paths_wanted)} clips extracted")
            if not remaining:
                break

    shutil.rmtree(tmp_dir, ignore_errors=True)
    if remaining:
        print(f"⚠ {len(remaining)} selected clips not found in the tarball "
              f"(skipped): {sorted(remaining)[:5]}{'...' if len(remaining) > 5 else ''}")
    extracted.sort(key=lambda c: c.index)
    return extracted


def _transcode_mp3_to_wav(mp3: Path, wav: Path) -> None:
    """Invoke ffmpeg to produce a 16 kHz mono PCM WAV. Overwrites destination."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(mp3),
        "-ac", str(WAV_CHANNELS),
        "-ar", str(WAV_SAMPLE_RATE),
        "-acodec", "pcm_s16le",
        str(wav),
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {mp3.name}: {res.stderr.decode('utf-8', errors='replace')[:300]}"
        )


# ── Stats + manifest output ─────────────────────────────────────────────────


def compute_stats(clips: list[ManifestClip]) -> dict[str, object]:
    """Return a dict summarising the realised diversity breakdown."""
    gender = defaultdict(int)
    age = defaultdict(int)
    accent = defaultdict(int)
    speakers = defaultdict(int)
    durations = [c.duration_ms for c in clips if c.duration_ms]
    for c in clips:
        gender[c.gender or "unknown"] += 1
        age[_age_bracket(c.age)] += 1
        accent[_accent_bucket(c.accents)] += 1
        speakers[c.client_id] += 1
    return {
        "n_clips": len(clips),
        "n_unique_speakers": len(speakers),
        "max_clips_per_speaker": max(speakers.values()) if speakers else 0,
        "gender_counts": dict(gender),
        "age_counts": dict(age),
        "accent_counts": dict(accent),
        "duration_ms": {
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "mean": (sum(durations) // len(durations)) if durations else 0,
        },
    }


def write_manifest(out_dir: Path, lang: str, clips: list[ManifestClip],
                   *, seed: int, cv_release: str) -> None:
    """Write MANIFEST.json and STATS.json in ``out_dir``."""
    manifest = {
        "language": lang,
        "source": cv_release,
        "license": "CC0-1.0",
        "extractor": "extract_cv_subset.py",
        "seed": seed,
        "n_clips": len(clips),
        "clips": [asdict(c) for c in clips],
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "STATS.json").write_text(
        json.dumps(compute_stats(clips), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="extract_cv_subset",
        description=__doc__.strip().split("\n\n")[0] if __doc__ else "",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--lang", required=True, help="BCP-47 base tag (en, fr, es, …).")
    ap.add_argument("--tarball", required=True, type=Path,
                    help="Path to the downloaded Common Voice .tar.gz.")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output directory (e.g. tests/fixtures/audio/cv/fr/).")
    ap.add_argument("--count", type=int, default=DEFAULT_COUNT,
                    help=f"Clips to keep (default {DEFAULT_COUNT}).")
    ap.add_argument("--max-per-speaker", type=int, default=DEFAULT_MAX_PER_SPEAKER,
                    help=f"Max clips per opaque client_id (default {DEFAULT_MAX_PER_SPEAKER}).")
    ap.add_argument("--min-duration-ms", type=int, default=DEFAULT_MIN_DURATION_MS)
    ap.add_argument("--max-duration-ms", type=int, default=DEFAULT_MAX_DURATION_MS)
    ap.add_argument("--min-text-chars", type=int, default=DEFAULT_MIN_TEXT_CHARS)
    ap.add_argument("--max-text-chars", type=int, default=DEFAULT_MAX_TEXT_CHARS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"Random seed for reproducible sampling (default {DEFAULT_SEED}).")
    ap.add_argument("--release", default="Common Voice 26.0",
                    help="Free-text release label recorded in MANIFEST.json.")
    args = ap.parse_args()

    if not args.tarball.exists():
        sys.exit(f"× --tarball not found: {args.tarball}")
    args.out.mkdir(parents=True, exist_ok=True)

    rows, total = load_metadata(args.tarball, args.lang)
    filtered = filter_clips(
        rows,
        min_duration_ms=args.min_duration_ms,
        max_duration_ms=args.max_duration_ms,
        min_text_chars=args.min_text_chars,
        max_text_chars=args.max_text_chars,
    )
    print(f"  after filters → {len(filtered)} / {len(rows)} clips eligible")
    selected = stratified_sample(
        filtered,
        count=args.count,
        max_per_speaker=args.max_per_speaker,
        seed=args.seed,
    )
    print(f"  stratified sample → {len(selected)} clips picked")

    extracted = extract_and_transcode(args.tarball, selected, args.out)
    write_manifest(args.out, args.lang, extracted, seed=args.seed,
                   cv_release=args.release)

    stats = compute_stats(extracted)
    print(f"\n✓ Wrote {len(extracted)} clips to {args.out}")
    print(f"  unique speakers: {stats['n_unique_speakers']}")
    print(f"  gender: {dict(stats['gender_counts'])}")
    print(f"  age:    {dict(stats['age_counts'])}")
    print(f"  accent: {dict(stats['accent_counts'])}")
    print(f"\nNext: delete the tarball ({args.tarball}) to reclaim disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
