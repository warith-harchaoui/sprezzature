"""
test_narrate — deterministic coverage for the narration pipeline.

The Ollama LLM enrichment and the engine wrappers (OpenVoice v2,
ChatterboxTTS) require heavy ML dependencies and network access; both
are out of scope for the default test lane. This module covers the
pure-Python parts:

* ``_narrate.extract_segments`` — Markdown → typed segment list with
  structural hints (headings, lists, blockquotes, paragraphs, emoji
  emotion, frontmatter ``narration.tone``, inline ``[emotion: X]``).
* ``_narrate.apply_pronunciation`` — token substitution applied per
  segment, longest-token-wins.
* ``_narrate.load_pronunciation`` — per-post then project-root lookup.
* ``_narrate.source_sha256`` — stable across re-runs, sensitive to
  edits.
* ``_narrate.read_manifest`` / ``write_manifest`` — round-trip + soft
  failure on corrupt input.
* ``_narrate.merge_llm_hint`` — clamping + key preservation.
* ``narrate_chatterbox.emotion_to_exaggeration`` — emotion + intensity
  → engine dial in [0, 2].
* ``site_indexes.load_audio_manifest`` — narration manifest → feed
  enclosure mapping.
* ``site_indexes.render_rss`` / ``render_atom`` — feed gains
  ``<enclosure>`` rows when an audio manifest is supplied.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import _narrate
import narrate_chatterbox
import site_indexes


# ── extract_segments ──────────────────────────────────────────────────────


class TestExtractSegments:
    def test_empty_input_yields_empty_list(self):
        assert _narrate.extract_segments("") == []
        assert _narrate.extract_segments("   \n  \n") == []

    def test_paragraph_basic(self):
        segs = _narrate.extract_segments("Hello, world.")
        assert len(segs) == 1
        assert segs[0]["kind"] == "paragraph"
        assert segs[0]["text"] == "Hello, world."
        assert segs[0]["heading_level"] == 0
        assert segs[0]["pause_after_ms"] == _narrate.PAUSE_PARAGRAPH_MS

    def test_heading_levels_get_different_pauses(self):
        md = "# H1\n\n## H2\n\n### H3\n\nbody"
        segs = _narrate.extract_segments(md)
        kinds = [s["kind"] for s in segs]
        assert kinds == ["heading", "heading", "heading", "paragraph"]
        # H1 should pause longer than H2 which pauses longer than H3.
        h1, h2, h3 = segs[0], segs[1], segs[2]
        assert h1["pause_after_ms"] > h2["pause_after_ms"] > h3["pause_after_ms"]
        assert h1["heading_level"] == 1
        assert h2["heading_level"] == 2
        assert h3["heading_level"] == 3

    def test_list_items_one_segment_per_item(self):
        md = "- first\n- second\n- third\n"
        segs = _narrate.extract_segments(md)
        assert [s["text"] for s in segs] == ["first", "second", "third"]
        assert all(s["kind"] == "list_item" for s in segs)
        # Non-final items: short pause. Final item: paragraph-length pause.
        assert segs[0]["pause_after_ms"] == _narrate.PAUSE_LIST_ITEM_MS
        assert segs[1]["pause_after_ms"] == _narrate.PAUSE_LIST_ITEM_MS
        assert segs[-1]["pause_after_ms"] == _narrate.PAUSE_PARAGRAPH_MS

    def test_blockquote_wrapped_and_lower_intensity(self):
        md = "> A pithy citation.\n> Second line."
        segs = _narrate.extract_segments(md)
        assert len(segs) == 1
        assert segs[0]["kind"] == "blockquote"
        assert segs[0]["text"].startswith("Quote: ")
        assert segs[0]["text"].endswith(" End quote.")
        # Intensity is lowered vs the default 0.5.
        assert segs[0]["intensity"] < _narrate.DEFAULT_INTENSITY

    def test_code_block_stripped(self):
        md = "Before.\n\n```python\nignore = True\n```\n\nAfter."
        segs = _narrate.extract_segments(md)
        assert [s["text"] for s in segs] == ["Before.", "After."]

    def test_inline_markup_cleaned(self):
        md = "Use `sprezzature-ui` and see [the docs](https://example.com/docs)."
        segs = _narrate.extract_segments(md)
        assert segs[0]["text"] == "Use sprezzature-ui and see the docs."

    def test_image_keeps_alt_drops_url(self):
        md = "![the logo](assets/logo.png)"
        segs = _narrate.extract_segments(md)
        assert segs[0]["text"] == "the logo"

    def test_html_tags_stripped(self):
        md = "Plain <em>emphasis</em> and <span>span</span>."
        segs = _narrate.extract_segments(md)
        assert segs[0]["text"] == "Plain emphasis and span."

    def test_frontmatter_tone_applied_as_baseline(self):
        md = (
            "---\n"
            "title: hello\n"
            "narration:\n"
            "  tone: cheerful\n"
            "  pace: slow\n"
            "---\n\n"
            "Hello, world.\n"
        )
        segs = _narrate.extract_segments(md)
        assert segs[0]["emotion"] == "cheerful"
        assert segs[0]["pace"] == "slow"

    def test_emoji_overrides_baseline_emotion(self):
        md = "⚠️ Be careful with this step."
        segs = _narrate.extract_segments(md)
        assert segs[0]["emotion"] == "cautious"

    def test_inline_emotion_marker_overrides_following_segments(self):
        md = (
            "Neutral paragraph.\n\n"
            "[emotion: cheerful]\n\n"
            "This one should be cheerful.\n\n"
            "And this one too.\n\n"
            "[emotion: default]\n\n"
            "Back to neutral."
        )
        segs = _narrate.extract_segments(md)
        emotions = [s["emotion"] for s in segs]
        assert emotions[0] == _narrate.DEFAULT_EMOTION
        assert emotions[1] == "cheerful"
        assert emotions[2] == "cheerful"
        assert emotions[3] == _narrate.DEFAULT_EMOTION

    def test_heading_resets_sticky_emotion(self):
        md = (
            "[emotion: angry]\n\n"
            "Angry paragraph.\n\n"
            "# New section\n\n"
            "Back to neutral.\n"
        )
        segs = _narrate.extract_segments(md)
        # Order: angry paragraph, heading (reset), neutral paragraph.
        assert segs[0]["emotion"] == "angry"
        assert segs[1]["kind"] == "heading"
        assert segs[2]["emotion"] == _narrate.DEFAULT_EMOTION


# ── pronunciation overrides ─────────────────────────────────────────────────


class TestPronunciation:
    def test_apply_pronunciation_whole_word(self):
        segs = [_narrate.make_segment("Check WCAG and OKLCH.")]
        overrides = {"WCAG": "wuh-cag", "OKLCH": "oh-K-L-C-H"}
        out = _narrate.apply_pronunciation(segs, overrides)
        assert out[0]["text"] == "Check wuh-cag and oh-K-L-C-H."

    def test_apply_pronunciation_longest_wins(self):
        segs = [_narrate.make_segment("WCAG 2.2 and WCAG conformance.")]
        overrides = {"WCAG": "wuh-cag", "WCAG 2.2": "wuh-cag two two"}
        out = _narrate.apply_pronunciation(segs, overrides)
        assert "wuh-cag two two" in out[0]["text"]
        assert "wuh-cag conformance" in out[0]["text"]

    def test_empty_overrides_is_noop(self):
        segs = [_narrate.make_segment("hello")]
        assert _narrate.apply_pronunciation(segs, {}) == segs

    def test_load_pronunciation_per_post(self, tmp_path: Path):
        pytest.importorskip("yaml")
        post = tmp_path / "post.md"
        post.write_text("body", encoding="utf-8")
        (tmp_path / "pronunciation.yaml").write_text(
            "WCAG: wuh-cag\n", encoding="utf-8",
        )
        overrides = _narrate.load_pronunciation(post)
        assert overrides == {"WCAG": "wuh-cag"}

    def test_load_pronunciation_missing_file_yields_empty(
        self, tmp_path: Path,
    ):
        post = tmp_path / "post.md"
        post.write_text("body", encoding="utf-8")
        assert _narrate.load_pronunciation(post) == {}


# ── source_sha256 + manifest round-trip ────────────────────────────────────


class TestManifest:
    def test_source_sha256_stable_for_same_input(self):
        a = _narrate.source_sha256("hello world")
        b = _narrate.source_sha256("hello world")
        assert a == b
        assert len(a) == 64

    def test_source_sha256_sensitive_to_edits(self):
        assert (
            _narrate.source_sha256("hello world")
            != _narrate.source_sha256("hello  world")
        )

    def test_manifest_round_trip(self, tmp_path: Path):
        path = tmp_path / "manifest.json"
        entries = {
            "posts/a.md": _narrate.NarrationManifestEntry(
                source="posts/a.md", audio="audio/a.wav",
                engine="chatterbox", voice="default",
                source_sha256="a" * 64, duration_seconds=12.3,
            ),
        }
        _narrate.write_manifest(path, entries)
        loaded = _narrate.read_manifest(path)
        assert "posts/a.md" in loaded
        assert loaded["posts/a.md"].audio == "audio/a.wav"
        assert loaded["posts/a.md"].duration_seconds == pytest.approx(12.3)

    def test_corrupt_manifest_treated_as_missing(self, tmp_path: Path):
        path = tmp_path / "manifest.json"
        path.write_text("not json", encoding="utf-8")
        assert _narrate.read_manifest(path) == {}

    def test_manifest_skips_malformed_rows(self, tmp_path: Path):
        path = tmp_path / "manifest.json"
        path.write_text(
            json.dumps([
                {"source": "ok.md", "audio": "ok.wav", "engine": "x",
                 "voice": "v", "source_sha256": "h", "duration_seconds": 1.0},
                {"missing": "fields"},
                "not a dict",
            ]),
            encoding="utf-8",
        )
        loaded = _narrate.read_manifest(path)
        assert set(loaded.keys()) == {"ok.md"}


# ── LLM hint merge ─────────────────────────────────────────────────────────


class TestMergeLLMHint:
    def test_empty_hint_leaves_segment_unchanged(self):
        seg = _narrate.make_segment("hi", emotion="neutral")
        out = _narrate.merge_llm_hint(seg, {})
        assert out == seg

    def test_emotion_string_applied(self):
        seg = _narrate.make_segment("hi", emotion="neutral")
        out = _narrate.merge_llm_hint(seg, {"emotion": "Cheerful"})
        assert out["emotion"] == "cheerful"

    def test_clamps_out_of_range(self):
        seg = _narrate.make_segment("hi", pause_after_ms=500)
        out = _narrate.merge_llm_hint(seg, {
            "intensity": 99.0,
            "pause_after_ms": 999_999,
        })
        assert out["intensity"] == _narrate.INTENSITY_MAX
        assert out["pause_after_ms"] == _narrate.PAUSE_MAX_MS

    def test_garbage_intensity_falls_back(self):
        seg = _narrate.make_segment("hi", intensity=0.4)
        out = _narrate.merge_llm_hint(seg, {"intensity": "not a number"})
        assert out["intensity"] == pytest.approx(0.4)

    def test_unknown_pace_ignored(self):
        seg = _narrate.make_segment("hi", pace="normal")
        out = _narrate.merge_llm_hint(seg, {"pace": "very-slow"})
        assert out["pace"] == "normal"


# ── chatterbox emotion → exaggeration mapping ──────────────────────────────


class TestChatterboxEmotionMap:
    def test_neutral_at_half_intensity_is_base(self):
        v = narrate_chatterbox.emotion_to_exaggeration("neutral", 0.5)
        assert v == pytest.approx(0.5)

    def test_cheerful_intensity_dial(self):
        low = narrate_chatterbox.emotion_to_exaggeration("cheerful", 0.0)
        mid = narrate_chatterbox.emotion_to_exaggeration("cheerful", 0.5)
        high = narrate_chatterbox.emotion_to_exaggeration("cheerful", 1.0)
        assert low < mid < high
        assert 0.0 <= low <= 2.0
        assert 0.0 <= high <= 2.0

    def test_unknown_emotion_falls_back_to_neutral(self):
        v = narrate_chatterbox.emotion_to_exaggeration("nope", 0.5)
        assert v == pytest.approx(0.5)

    def test_extreme_intensity_clamped(self):
        v = narrate_chatterbox.emotion_to_exaggeration("angry", 999.0)
        assert 0.0 <= v <= 2.0


# ── site_indexes audio enclosure ───────────────────────────────────────────


class TestSiteIndexesAudio:
    def test_load_audio_manifest_missing_file(self, tmp_path: Path):
        assert site_indexes.load_audio_manifest(tmp_path / "nope.json") == {}

    def test_load_audio_manifest_basic(self, tmp_path: Path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps([
            {"source": "posts/hello.md", "audio": "audio/hello.wav",
             "engine": "chatterbox", "voice": "default",
             "source_sha256": "x", "duration_seconds": 10.0},
        ]), encoding="utf-8")
        out = site_indexes.load_audio_manifest(manifest)
        assert "posts/hello" in out
        entry = out["posts/hello"]
        assert entry.path == "audio/hello.wav"
        assert entry.mime_type == "audio/wav"

    def test_load_audio_manifest_with_root_populates_length(
        self, tmp_path: Path,
    ):
        # Create the audio file so the stat() call succeeds.
        audio = tmp_path / "audio" / "hello.mp3"
        audio.parent.mkdir()
        audio.write_bytes(b"\x00" * 1024)
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps([
            {"source": "posts/hello.md", "audio": "audio/hello.mp3",
             "engine": "chatterbox", "voice": "default",
             "source_sha256": "x", "duration_seconds": 10.0},
        ]), encoding="utf-8")
        out = site_indexes.load_audio_manifest(manifest, audio_root=tmp_path)
        assert out["posts/hello"].mime_type == "audio/mpeg"
        assert out["posts/hello"].length_bytes == 1024

    def test_render_rss_injects_enclosure_when_manifest_passed(self):
        posts = [(Path("posts/a.html"), "Title A",
                  "2026-06-21T00:00:00Z", "Summary A")]
        audio = {"posts/a": site_indexes.AudioEntry(
            path="audio/a.wav", mime_type="audio/wav", length_bytes=2048,
        )}
        xml = site_indexes.render_rss(
            "https://example.com",
            feed_title="Sprezzature",
            feed_description="...",
            posts=posts,
            audio_entries=audio,
        )
        assert "<enclosure" in xml
        assert 'url="https://example.com/audio/a.wav"' in xml
        assert 'type="audio/wav"' in xml
        assert 'length="2048"' in xml

    def test_render_rss_without_manifest_has_no_enclosure(self):
        posts = [(Path("posts/a.html"), "Title A",
                  "2026-06-21T00:00:00Z", "Summary A")]
        xml = site_indexes.render_rss(
            "https://example.com",
            feed_title="Sprezzature",
            feed_description="...",
            posts=posts,
        )
        assert "<enclosure" not in xml

    def test_render_atom_injects_enclosure_link(self):
        posts = [(Path("posts/a.html"), "Title A",
                  "2026-06-21T00:00:00Z", "Summary A")]
        audio = {"posts/a": site_indexes.AudioEntry(
            path="audio/a.mp3", mime_type="audio/mpeg", length_bytes=4096,
        )}
        xml = site_indexes.render_atom(
            "https://example.com",
            feed_id="tag:example.com,2026:feed",
            feed_title="Sprezzature",
            posts=posts,
            audio_entries=audio,
        )
        assert 'rel="enclosure"' in xml
        assert 'type="audio/mpeg"' in xml
        assert 'length="4096"' in xml
        assert "audio/a.mp3" in xml


# ── narrate_post: cache short-circuit ──────────────────────────────────────


class TestNarratePostCache:
    """
    The orchestrator should not invoke the engine wrapper when the
    manifest already contains a matching sha256. We verify this by
    pre-populating the manifest with a matching entry and asserting
    the script reports the cache hit without trying to call any
    engine (no engine is installed in the test environment).
    """

    def test_cache_hit_skips_engine(self, tmp_path: Path):
        import subprocess
        import sys
        # Build a fake post + its expected sha (via the same extractor
        # the orchestrator uses).
        post = tmp_path / "post.md"
        post.write_text("# Hello\n\nA paragraph.\n", encoding="utf-8")
        segs = _narrate.extract_segments(post.read_text())
        digest = _narrate.source_sha256(_narrate.segments_to_text(segs))
        # Pre-populate the manifest with the matching entry, pointing at
        # an audio file we also create so the path-exists check passes.
        out_dir = tmp_path / "out" / "audio"
        out_dir.mkdir(parents=True)
        audio_file = out_dir / "narration.wav"
        audio_file.write_bytes(b"\x00")
        manifest_path = out_dir / "manifest.json"
        _narrate.write_manifest(manifest_path, {
            post.as_posix(): _narrate.NarrationManifestEntry(
                source=post.as_posix(),
                audio=str(audio_file),
                engine="chatterbox",
                voice="default",
                source_sha256=digest,
                duration_seconds=1.0,
            )
        })
        # Invoke the orchestrator. Since the manifest matches, it
        # should print "cache hit" and exit 0 without calling any
        # engine wrapper.
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1]
                    / "sprezzature-publish" / "scripts" / "narrate_post.py"),
                "--engine", "chatterbox",
                "--voice", "default",
                "--out-dir", str(out_dir),
                str(post),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            f"orchestrator exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        assert "cache hit" in proc.stdout
