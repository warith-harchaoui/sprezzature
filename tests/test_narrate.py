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
* the voices moved to ``sprezzature-audio``; what they borrowed from this
  module — the clock and the cue — moved with them, and the tests that
  read their source moved to that package too
  → engine dial in [0, 2].
* ``site_indexes.load_audio_manifest`` — narration manifest → feed
  enclosure mapping.
* ``site_indexes.render_rss`` / ``render_atom`` — feed gains
  ``<enclosure>`` rows when an audio manifest is supplied.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import _narrate
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


# ── Timeline: pauses honoured, and where each segment landed ──────────────


class TestTimeline:
    """The object that fixed two things at once.

    ``pause_before_ms`` was computed by everything and applied by nothing:
    ``extract_segments`` sets it from the structural baselines,
    ``prompts/narration_emotion.yaml`` asks the model for it by name, and
    ``merge_llm_hint`` clamps the answer -- while both engine wrappers
    appended silence for ``pause_after_ms`` alone. Each wrapper carried its
    own copy of the same loop, which is how one omission became two.

    And nothing recorded *where* a segment ended up in the audio, so a page
    could play the narration but never follow it. Both offsets were already
    known at concatenation time; they are simply kept now.
    """

    def test_silence_advances_the_clock_and_reports_its_samples(self):
        timeline = _narrate.Timeline(1000)
        assert timeline.silence(500) == 500
        assert timeline.total_seconds == 0.5

    def test_a_cue_spans_exactly_the_samples_that_speak_it(self):
        timeline = _narrate.Timeline(1000)
        timeline.silence(500)
        timeline.speech(2000, index=0, text="Hello.")
        (cue,) = timeline.cues
        assert (cue.start_seconds, cue.end_seconds) == (0.5, 2.5)

    def test_a_cue_keeps_the_original_segment_index(self):
        """Not its position in the audio.

        Segments whose text is empty after cleaning are skipped rather than
        synthesised, so the two counts drift. A page highlighting block *n*
        for cue *n* would land on the wrong paragraph the moment a post
        contains one -- a code block, say, stripped to nothing.
        """
        timeline = _narrate.Timeline(1000)
        timeline.speech(1000, index=0, text="First.")
        timeline.speech(1000, index=7, text="Eighth, after six empty ones.")
        assert [cue.index for cue in timeline.cues] == [0, 7]

    def test_negative_or_zero_pauses_cost_nothing(self):
        timeline = _narrate.Timeline(1000)
        assert timeline.silence(0) == 0
        assert timeline.silence(-250) == 0
        assert timeline.total_seconds == 0.0


class TestWebVTT:
    def test_timestamps_use_the_only_form_webvtt_accepts(self):
        assert _narrate.format_timestamp(0) == "00:00:00.000"
        assert _narrate.format_timestamp(1.5) == "00:00:01.500"
        assert _narrate.format_timestamp(3723.456) == "01:02:03.456"

    def test_milliseconds_truncate_rather_than_round(self):
        """A cue must never claim to start before the sample that starts it."""
        assert _narrate.format_timestamp(0.9999) == "00:00:00.999"

    def test_a_cue_carries_its_segment_index_as_the_webvtt_identifier(self):
        """The identifier line is how a page finds the block to highlight,
        rather than matching on the cue's text -- which repeats, and which
        the page may have rendered with different markup."""
        cues = [_narrate.Cue(index=4, text="Hello.", start_seconds=0.0, end_seconds=1.0)]
        vtt = _narrate.cues_to_vtt(cues)
        assert vtt.splitlines()[:4] == [
            "WEBVTT",
            "",
            "4",
            "00:00:00.000 --> 00:00:01.000",
        ]

    def test_a_wrapped_payload_cannot_split_its_own_cue(self):
        """A blank line ends a cue in WebVTT, so text carrying one would
        silently truncate the cue and turn the rest into a parse error."""
        cues = [
            _narrate.Cue(
                index=0,
                text="First line.\n\nSecond line.",
                start_seconds=0.0,
                end_seconds=1.0,
            )
        ]
        body = _narrate.cues_to_vtt(cues).split("00:00:01.000\n", 1)[1]
        assert body.strip() == "First line. Second line."

    def test_the_file_starts_with_the_required_magic(self):
        """A WebVTT file that does not begin with `WEBVTT` is rejected
        outright by every parser, and a `<track>` that fails to parse fails
        silently -- no captions, no error."""
        assert _narrate.cues_to_vtt([]).startswith("WEBVTT")




# ── Sentences: the unit the read-along follows ────────────────────────────


class TestSplitSentences:
    """Sentence is the granularity the highlight is built on.

    A paragraph is too coarse to follow with the eye past three lines; a word
    would need forced alignment against audio this pipeline generated itself,
    which is a statistical guess at something already known exactly. A
    sentence is precise enough to follow *and* exact, because each one is
    synthesised alone and therefore measured rather than estimated.

    Which makes the splitter load-bearing: it has to give the same answer for
    the page and for the audio, or the highlight lands on the wrong words.
    """

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("One. Two! Three?", ["One.", "Two!", "Three?"]),
            ("No terminator here", ["No terminator here"]),
            ("Fin.", ["Fin."]),
            ("", []),
            ("   \n  ", []),
        ],
    )
    def test_the_plain_cases(self, text, expected):
        assert _narrate.split_sentences(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Dr. Rosling said so. Then he left.",
             ["Dr. Rosling said so.", "Then he left."]),
            ("M. Dupont est venu. Il est reparti.",
             ["M. Dupont est venu.", "Il est reparti."]),
            ("J. R. R. Tolkien a écrit. Beaucoup.",
             ["J. R. R. Tolkien a écrit.", "Beaucoup."]),
        ],
    )
    def test_an_abbreviation_does_not_end_a_sentence(self, text, expected):
        """Splitting on every full stop cuts "Dr. Rosling" in half and the
        highlight jumps mid-phrase, which reads worse than no highlight."""
        assert _narrate.split_sentences(text) == expected

    def test_the_french_and_english_abbreviation_lists_are_not_translations(self):
        """`M.` abbreviates *Monsieur* in French and ends a sentence in
        English ("...the M."). The list holds both because this suite writes
        both languages, not because one was translated into the other."""
        assert "mme" in _narrate._ABBREVIATIONS
        assert "mrs" in _narrate._ABBREVIATIONS

    def test_a_decimal_point_cannot_split_a_number(self):
        assert _narrate.split_sentences("It cost 3.14 euros. Exactly.") == [
            "It cost 3.14 euros.",
            "Exactly.",
        ]

    def test_a_page_number_still_ends_its_sentence(self):
        """The regression from guarding decimals too eagerly.

        An earlier version treated any stop preceded by a digit as a decimal
        separator, which left "Voir p. 12. Puis la suite." as one sentence.
        A real decimal has a digit straight after the stop and the splitter
        requires whitespace, so numbers never needed the guard at all.
        """
        assert _narrate.split_sentences("Voir p. 12. Puis la suite.") == [
            "Voir p. 12.",
            "Puis la suite.",
        ]

    @pytest.mark.parametrize(
        "text,expected",
        [
            ('He said "Yes." Then left.', ['He said "Yes."', "Then left."]),
            ("Elle a dit : « Non. » Il est parti.",
             ["Elle a dit : « Non. »", "Il est parti."]),
        ],
    )
    def test_a_closing_quote_stays_with_the_sentence_it_closes(self, text, expected):
        """French typography puts a space before `»`, English puts nothing
        before `"`. Requiring the closer to sit flush against the terminator
        handled English and orphaned the French one onto the next sentence."""
        assert _narrate.split_sentences(text) == expected

    def test_an_ellipsis_is_one_terminator_not_three(self):
        assert _narrate.split_sentences("Attends... Vraiment ?") == [
            "Attends...",
            "Vraiment ?",
        ]

    @pytest.mark.parametrize(
        "text",
        [
            "Des pommes, des poires, etc. Puis je pars.",
            "Il travaille chez Dupont Inc. Il part demain.",
        ],
    )
    def test_an_abbreviation_that_really_did_end_a_sentence_joins_instead(self, text):
        """A known limit, pinned rather than hidden.

        `etc.` and `Inc.` genuinely end sentences about as often as they do
        not, and no rule set settles it without reading the next word's
        meaning. The splitter joins, which errs toward a highlight that lags
        over one that cuts a phrase in half -- the failure a reader forgives.
        """
        assert len(_narrate.split_sentences(text)) == 1

    def test_whitespace_is_collapsed_so_a_cue_is_one_line(self):
        """A blank line inside a cue's payload ends the cue in WebVTT."""
        assert _narrate.split_sentences("One.\n\n  Two.") == ["One.", "Two."]


class TestExplodeToSentences:
    def test_each_sentence_becomes_its_own_segment(self):
        blocks = _narrate.extract_segments("One. Two.\n\nThree.")
        assert [s["text"] for s in _narrate.explode_to_sentences(blocks)] == [
            "One.",
            "Two.",
            "Three.",
        ]

    def test_the_block_pauses_are_redistributed_not_repeated(self):
        """The part that is easy to get wrong.

        A block's `pause_before_ms` belongs to its first sentence and its
        `pause_after_ms` to its last. Copying both onto every sentence would
        put a heading-sized silence *inside* a paragraph and make prose read
        like a list of unrelated statements.
        """
        blocks = _narrate.extract_segments("First. Second. Third.")
        pieces = _narrate.explode_to_sentences(blocks)
        assert [p["pause_after_ms"] for p in pieces] == [
            _narrate.PAUSE_SENTENCE_MS,
            _narrate.PAUSE_SENTENCE_MS,
            blocks[0]["pause_after_ms"],
        ]
        assert [p["pause_before_ms"] for p in pieces] == [
            blocks[0]["pause_before_ms"],
            0,
            0,
        ]

    def test_a_breath_between_sentences_is_shorter_than_one_between_blocks(self):
        assert _narrate.PAUSE_SENTENCE_MS < _narrate.PAUSE_PARAGRAPH_MS

    def test_voice_characteristics_are_inherited_unchanged(self):
        """Emotion and pace describe how a block sounds; a sentence does not
        change its mind halfway through a paragraph."""
        blocks = _narrate.extract_segments("> Sombre. Très sombre.")
        pieces = _narrate.explode_to_sentences(blocks)
        assert {p["kind"] for p in pieces} == {blocks[0]["kind"]}
        assert {p["emotion"] for p in pieces} == {blocks[0]["emotion"]}
        assert {p["intensity"] for p in pieces} == {blocks[0]["intensity"]}

    def test_a_block_with_no_sentence_contributes_nothing(self):
        """Which is why the page must be built from this list and not from the
        blocks: the two lengths differ, so block *n* is not sentence *n*."""
        blocks = [_narrate.make_segment("")]
        assert _narrate.explode_to_sentences(blocks) == []

    def test_the_result_is_a_copy_and_leaves_its_input_alone(self):
        blocks = _narrate.extract_segments("One. Two.")
        before = [dict(b) for b in blocks]
        _narrate.explode_to_sentences(blocks)
        assert [dict(b) for b in blocks] == before


class TestTheVoicesLiveNextDoor:
    """The seam left behind when the voices moved to ``sprezzature-audio``.

    Captions turn sound into timed text and narration turns text into timed
    sound; one package owns that modality in both directions, and this one
    owns the document and the page. What stayed here is the orchestrator,
    and what it has to get right is finding an engine it no longer ships.

    The failure this guards against is specific: a path that resolved when
    the wrappers sat in the same folder, and silently stops resolving once
    they do not. A narration that cannot find its voice must say so, not
    return a command that fails later with a stranger message.
    """

    def test_an_installed_engine_resolves_to_a_module_invocation(self):
        """`python -m` against the installed package is the normal path."""
        import narrate_post

        command = narrate_post._engine_command("openvoice")
        assert command is not None
        assert command[1:] == ["-m", "sprezzature_audio_scripts.narrate_openvoice"]

    def test_an_unknown_engine_resolves_to_nothing(self):
        """Not an exception, and not a command that fails later."""
        import narrate_post

        assert narrate_post._engine_command("harmonica") is None

    def test_this_package_no_longer_ships_a_voice(self):
        """
        The move has to be complete, or both copies drift.

        Two engine wrappers once carried the same hand-rolled loop, and one
        omission became two. A leftover copy here would be the same shape of
        mistake with a folder boundary added.
        """
        here = Path(__file__).resolve().parent.parent / "sprezzature-publish" / "scripts"
        left_behind = sorted(
            p.name for p in here.glob("*.py")
            if p.stem in {"narrate_openvoice", "narrate_chatterbox", "pick_voice", "install_narrate"}
        )
        assert left_behind == [], (
            f"{left_behind} should have moved to sprezzature-audio with the "
            f"rest of the sound modality"
        )

    def test_the_orchestrator_names_the_install_command_when_it_cannot_find_one(self):
        """
        A missing engine is a thing the reader can fix, if they are told how.

        The message has to name the package and the command, because the
        reader's mental model is "narration is part of publish" and the
        answer is in a different package now.
        """
        import inspect

        import narrate_post

        source = inspect.getsource(narrate_post)
        assert "sprezzature-audio[narrate]" in source
        assert "sprezzature-audio-install-voice" in source
