"""
test_extract_cv_subset — deterministic tests for the Common Voice extractor.

Exercises the pure-function parts of ``extract_cv_subset.py`` (filtering,
stratified sampling, diversity stats) with synthetic ``CVRow`` data —
no tarball required. The tarball-dependent code paths
(``load_metadata``, ``extract_and_transcode``) are out of scope for the
deterministic suite; they're exercised in practice when a contributor
runs the extractor for real.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path



# The extractor lives under tests/fixtures/, not in any scripts/ dir on
# sys.path. Inject it explicitly for this module only.
_EXTRACTOR_DIR = Path(__file__).resolve().parent / "fixtures" / "audio"
if str(_EXTRACTOR_DIR) not in sys.path:
    sys.path.insert(0, str(_EXTRACTOR_DIR))

import extract_cv_subset as ecs  # noqa: E402


# ── Helpers ─────────────────────────────────────────────────────────────────


def make_row(
    *,
    client_id: str = "spk-default",
    path: str = "common_voice_en_1.mp3",
    sentence: str = "The quick brown fox jumps over the lazy dog every morning.",
    age: str = "thirties",
    gender: str = "male_masculine",
    accents: str = "United States English",
    variant: str = "",
    duration_ms: int = 5000,
) -> ecs.CVRow:
    return ecs.CVRow(
        client_id=client_id,
        path=path,
        sentence=sentence,
        age=age,
        gender=gender,
        accents=accents,
        variant=variant,
        duration_ms=duration_ms,
    )


def make_corpus(n: int, *, speakers: int = 50, genders=("male_masculine", "female_feminine"),
                ages=("twenties", "thirties", "forties", "fifties"),
                accents=("United States English", "England English",
                         "Indian English", "Australian English")) -> list[ecs.CVRow]:
    """Build ``n`` synthetic rows covering the metadata cross-product."""
    rows: list[ecs.CVRow] = []
    for i in range(n):
        rows.append(make_row(
            client_id=f"spk-{i % speakers:03d}",
            path=f"clip_{i:04d}.mp3",
            sentence=(
                "The session covered a wide range of subjects in detail today "
                f"and reached a clear conclusion at point number {i}."
            ),
            age=ages[i % len(ages)],
            gender=genders[i % len(genders)],
            accents=accents[i % len(accents)],
            duration_ms=4000 + (i % 11) * 1000,  # 4000–14000 ms range
        ))
    return rows


# ── filter_clips ────────────────────────────────────────────────────────────


def test_filter_clips_drops_too_short():
    rows = [make_row(duration_ms=2500)]  # below 3000 default
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert out == []


def test_filter_clips_drops_too_long():
    rows = [make_row(duration_ms=20000)]
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert out == []


def test_filter_clips_keeps_in_range():
    rows = [make_row(duration_ms=5000)]
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert len(out) == 1


def test_filter_clips_drops_short_text():
    rows = [make_row(sentence="Too short.")]
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert out == []


def test_filter_clips_drops_long_text():
    rows = [make_row(sentence="x" * 500)]
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert out == []


def test_filter_clips_keeps_unknown_duration():
    """duration_ms == 0 means metadata missing — keep, don't drop."""
    rows = [make_row(duration_ms=0)]
    out = ecs.filter_clips(
        rows, min_duration_ms=3000, max_duration_ms=15000,
        min_text_chars=30, max_text_chars=200,
    )
    assert len(out) == 1


# ── stratified_sample ──────────────────────────────────────────────────────


def test_stratified_sample_returns_requested_count_when_supply_is_ample():
    rows = make_corpus(500)
    picked = ecs.stratified_sample(rows, count=100, max_per_speaker=3, seed=0)
    assert len(picked) == 100


def test_stratified_sample_is_deterministic_with_same_seed():
    rows = make_corpus(500)
    a = ecs.stratified_sample(rows, count=50, max_per_speaker=3, seed=42)
    b = ecs.stratified_sample(rows, count=50, max_per_speaker=3, seed=42)
    assert [r.path for r in a] == [r.path for r in b]


def test_stratified_sample_differs_across_seeds():
    rows = make_corpus(500)
    a = ecs.stratified_sample(rows, count=50, max_per_speaker=3, seed=0)
    b = ecs.stratified_sample(rows, count=50, max_per_speaker=3, seed=99)
    # Could collide by chance on a tiny corpus; on 500 rows it shouldn't.
    assert [r.path for r in a] != [r.path for r in b]


def test_stratified_sample_respects_max_per_speaker():
    rows = make_corpus(500, speakers=10)
    picked = ecs.stratified_sample(rows, count=40, max_per_speaker=3, seed=0)
    counts = Counter(r.client_id for r in picked)
    assert max(counts.values()) <= 3


def test_stratified_sample_returns_partial_under_supply():
    """Asking for more than the speaker cap permits returns the partial."""
    # Two speakers, max 1 each → at most 2 clips.
    rows = [
        make_row(client_id="A", path="a1.mp3"),
        make_row(client_id="A", path="a2.mp3"),
        make_row(client_id="A", path="a3.mp3"),
        make_row(client_id="B", path="b1.mp3"),
        make_row(client_id="B", path="b2.mp3"),
    ]
    picked = ecs.stratified_sample(rows, count=10, max_per_speaker=1, seed=0)
    assert len(picked) == 2
    assert {r.client_id for r in picked} == {"A", "B"}


def test_stratified_sample_no_duplicate_paths():
    rows = make_corpus(500)
    picked = ecs.stratified_sample(rows, count=100, max_per_speaker=3, seed=0)
    paths = [r.path for r in picked]
    assert len(paths) == len(set(paths))


def test_stratified_sample_balances_gender_when_corpus_is_balanced():
    """On a 50/50 corpus, the sample should not be heavily skewed."""
    rows = make_corpus(400)  # genders alternate, ~50/50
    picked = ecs.stratified_sample(rows, count=100, max_per_speaker=10, seed=0)
    counts = Counter(r.gender for r in picked)
    male = counts.get("male_masculine", 0)
    female = counts.get("female_feminine", 0)
    # Allow up to 70/30 skew — the round-robin draws from buckets in
    # shuffled order so perfect 50/50 is not guaranteed.
    assert min(male, female) / max(male, female) >= 0.4, (
        f"Gender skew worse than 70/30: {counts}"
    )


def test_stratified_sample_handles_empty_metadata():
    rows = [make_row(client_id=f"s{i}", path=f"c{i}.mp3", age="", gender="", accents="")
            for i in range(20)]
    picked = ecs.stratified_sample(rows, count=10, max_per_speaker=2, seed=0)
    assert len(picked) == 10


# ── helpers ────────────────────────────────────────────────────────────────


def test_age_bracket_passthrough_and_unknown():
    assert ecs._age_bracket("twenties") == "twenties"
    assert ecs._age_bracket("FIFTIES") == "fifties"
    assert ecs._age_bracket("") == "unknown"


def test_accent_bucket_takes_first_and_lowercases():
    assert ecs._accent_bucket("United States English, Midwestern") == "united states english"
    assert ecs._accent_bucket("") == "unknown"


# ── compute_stats ──────────────────────────────────────────────────────────


def _clip(index, **kwargs):
    """Build a ManifestClip with sensible defaults."""
    defaults = dict(
        index=index, wav=f"clip-{index:03d}.wav", txt=f"clip-{index:03d}.txt",
        source_clip_id=f"src-{index}.mp3", source_sha256="aa" * 32,
        wav_sha256="bb" * 32, sentence="hello", duration_ms=5000,
        client_id=f"spk-{index}", age="thirties", gender="male_masculine",
        accents="United States English", variant="",
    )
    defaults.update(kwargs)
    return ecs.ManifestClip(**defaults)


def test_compute_stats_counts_correctly():
    clips = [
        _clip(1, gender="male_masculine", age="twenties", client_id="A"),
        _clip(2, gender="female_feminine", age="twenties", client_id="A"),
        _clip(3, gender="female_feminine", age="thirties", client_id="B"),
    ]
    stats = ecs.compute_stats(clips)
    assert stats["n_clips"] == 3
    assert stats["n_unique_speakers"] == 2
    assert stats["max_clips_per_speaker"] == 2
    assert stats["gender_counts"]["male_masculine"] == 1
    assert stats["gender_counts"]["female_feminine"] == 2
    assert stats["age_counts"]["twenties"] == 2
    assert stats["age_counts"]["thirties"] == 1


def test_compute_stats_handles_empty():
    stats = ecs.compute_stats([])
    assert stats["n_clips"] == 0
    assert stats["n_unique_speakers"] == 0
    assert stats["duration_ms"]["min"] == 0
