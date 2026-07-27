"""
test_captions — coverage for ``sprezzature-accessibility/scripts/captions_from_whisper.py``.

The vocal-helper STT seam, the audio-helper WAV decode, and the ffmpeg
subprocess are mocked out. Tests cover timestamp formatting, segment-to-
format renderers, the local-model-arg resolver, prompt composition, vocab
resolution, and the top-level transcribe() with a stubbed transcription
seam (cap._run_whisper_stage).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


import captions_from_whisper as cap


def _seg(t0: int, t1: int, text: str) -> SimpleNamespace:
    """Build a pywhispercpp-shaped segment for the renderers to consume."""
    return SimpleNamespace(t0=t0, t1=t1, text=text)


# ── _format_timestamp ──────────────────────────────────────────────────────

class TestFormatTimestamp:
    def test_zero_vtt(self):
        # Centiseconds == 0 → 00:00:00.000 in VTT form.
        assert cap._format_timestamp(0) == "00:00:00.000"

    def test_zero_srt(self):
        assert cap._format_timestamp(0, srt=True) == "00:00:00,000"

    def test_one_and_half_seconds_vtt(self):
        # 1.5 s in 10-ms units == 150 → 00:00:01.500.
        assert cap._format_timestamp(150) == "00:00:01.500"

    def test_one_and_half_seconds_srt_uses_comma(self):
        assert cap._format_timestamp(150, srt=True) == "00:00:01,500"

    def test_hours_minutes_seconds_ms(self):
        # 1h + 1m + 2.5s = 3662.5 s → 366250 centiseconds.
        out = cap._format_timestamp(366_250)
        assert out == "01:01:02.500"

    def test_negative_clamped_to_zero(self):
        assert cap._format_timestamp(-50) == "00:00:00.000"


# ── segments_to_vtt / srt / text ───────────────────────────────────────────

class TestSegmentsToVtt:
    def test_starts_with_webvtt_header(self):
        out = cap.segments_to_vtt([_seg(0, 100, "Hello")])
        assert out.startswith("WEBVTT")

    def test_empty_segments_dropped(self):
        out = cap.segments_to_vtt([_seg(0, 50, ""), _seg(50, 100, "kept")])
        assert "kept" in out
        # The empty segment must not produce a timestamp line of its own.
        assert out.count("-->") == 1

    def test_blank_line_between_entries(self):
        out = cap.segments_to_vtt([
            _seg(0, 50, "first"),
            _seg(60, 100, "second"),
        ])
        # ``WEBVTT\n\n…\n\nfirst\n\n…\n\nsecond\n`` — two distinct cues
        # separated by a blank line.
        assert "first" in out and "second" in out
        assert "\n\n" in out


class TestSegmentsToSrt:
    def test_numbers_from_one(self):
        out = cap.segments_to_srt([
            _seg(0, 50, "a"),
            _seg(60, 100, "b"),
        ])
        # SRT cue numbering is 1-indexed.
        lines = out.splitlines()
        assert "1" in lines
        assert "2" in lines

    def test_uses_comma_decimal(self):
        out = cap.segments_to_srt([_seg(0, 150, "x")])
        assert ",500" in out
        assert ".500" not in out


class TestSegmentsToText:
    def test_paragraph_break_on_long_pause(self):
        # 200 cs (= 2 s) gap exceeds the 1.5 s threshold → blank line.
        out = cap.segments_to_text([
            _seg(0, 50, "first."),
            _seg(250, 300, "second."),
        ])
        # Blank line separates the two paragraphs.
        assert "first.\n\nsecond." in out

    def test_no_break_on_short_pause(self):
        # 100 cs (= 1 s) gap is below threshold → adjacent lines.
        out = cap.segments_to_text([
            _seg(0, 50, "first."),
            _seg(140, 200, "second."),
        ])
        assert "first.\nsecond." in out

    def test_ends_with_single_newline(self):
        out = cap.segments_to_text([_seg(0, 50, "only")])
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


# ── _resolve_model_arg ─────────────────────────────────────────────────────

class TestResolveModelArg:
    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("SPREZZATURE_WHISPER_MODEL", "/abs/path/to/model.bin")
        assert cap._resolve_model_arg("large-v3-turbo") == "/abs/path/to/model.bin"

    def test_cached_model_file_used(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SPREZZATURE_WHISPER_MODEL", raising=False)
        whisper_dir = tmp_path / "whisper"
        whisper_dir.mkdir()
        (whisper_dir / "ggml-small.bin").write_bytes(b"fake")
        monkeypatch.setattr(cap, "WHISPER_DIR", whisper_dir)
        out = cap._resolve_model_arg("small")
        assert out == str(whisper_dir / "ggml-small.bin")

    def test_bare_alias_when_no_local_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SPREZZATURE_WHISPER_MODEL", raising=False)
        monkeypatch.setattr(cap, "WHISPER_DIR", tmp_path / "empty")
        # Nothing cached and no env override → pywhispercpp will download.
        assert cap._resolve_model_arg("small") == "small"


# ── compose_prompt ─────────────────────────────────────────────────────────

class TestComposePrompt:
    def test_empty_vocab_returns_empty(self):
        assert cap.compose_prompt([], "en") == ""

    def test_english_opener(self):
        out = cap.compose_prompt(["Tailwind"], "en")
        assert out.startswith("The following terms may appear")
        assert "Tailwind" in out

    def test_french_opener(self):
        out = cap.compose_prompt(["Tailwind"], "fr")
        # The French opener leads in French.
        assert "Les termes" in out

    def test_truncates_at_word_budget(self):
        # MAX_PROMPT_WORDS == 150. Stuff far more single-word terms than
        # the budget allows; the helper stops once budget is consumed.
        terms = [f"term{i}" for i in range(500)]
        out = cap.compose_prompt(terms, "en")
        words = out.split()
        # Soft upper bound — the opener + truncated terms fit under the cap.
        assert len(words) <= cap.MAX_PROMPT_WORDS + 5


# ── resolve_vocab ──────────────────────────────────────────────────────────

class TestResolveVocab:
    def test_explicit_prompt_wins(self, tmp_path):
        src = tmp_path / "input.mp3"
        src.touch()
        out = cap.resolve_vocab(
            src,
            prompt="verbatim text",
            vocab_file=None,
            vocab_from=None,
            auto_project=False,
            lang="en",
        )
        assert out == "verbatim text"

    def test_falls_back_to_compose_from_glossary(self, tmp_path):
        src = tmp_path / "input.mp3"
        src.touch()
        glossary = tmp_path / "g.txt"
        glossary.write_text("Tailwind\nMontserrat\n", encoding="utf-8")
        out = cap.resolve_vocab(
            src,
            prompt="",
            vocab_file=glossary,
            vocab_from=None,
            auto_project=False,
            lang="en",
        )
        assert "Tailwind" in out
        assert "Montserrat" in out


# ── transcribe (with mocked vocal-helper seam) ─────────────────────────────

class TestTranscribe:
    def _stub_seams(self, monkeypatch, segments):
        """Stub the audio-extraction, PCM-decode, and vocal-helper STT seams.

        ``transcribe`` now delegates the actual speech-to-text to
        ``vocal-helper``'s ``WhisperStage`` behind ``cap._run_whisper_stage``,
        and the WAV decode to ``audio-helper`` behind ``cap._pcm_from_wav``.
        Both are stubbed so the test needs neither heavy package.
        """
        def fake_extract(src, dst):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(b"fake-wav-bytes")
        monkeypatch.setattr(cap, "extract_audio", fake_extract)
        monkeypatch.setattr(cap, "_pcm_from_wav", lambda wav: (b"pcm", 16000))
        stt = MagicMock(return_value=segments)
        monkeypatch.setattr(cap, "_run_whisper_stage", stt)
        return stt

    def test_vtt_output_through_cache(self, tmp_path, monkeypatch):
        # Cache dir → tmp.
        monkeypatch.setattr(cap, "CACHE_DIR", tmp_path / "captions")
        monkeypatch.setattr(cap, "NO_CACHE", False)

        stt = self._stub_seams(monkeypatch, [_seg(0, 100, "Hello world")])

        src = tmp_path / "input.mp3"
        src.write_bytes(b"original")
        out = cap.transcribe(src, model="small", lang="en", fmt="vtt")
        assert out.startswith("WEBVTT")
        assert "Hello world" in out

        # Second call: cache should serve. Make the STT seam raise if called —
        # proving the cache short-circuit runs before any transcription.
        stt.side_effect = AssertionError("should not transcribe")
        cached = cap.transcribe(src, model="small", lang="en", fmt="vtt")
        assert cached == out

    def test_srt_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cap, "CACHE_DIR", tmp_path / "captions")
        monkeypatch.setattr(cap, "NO_CACHE", False)
        self._stub_seams(monkeypatch, [_seg(0, 150, "Hello")])

        src = tmp_path / "input.mp3"
        src.write_bytes(b"x")
        out = cap.transcribe(src, model="small", lang="en", fmt="srt")
        # SRT has numeric cue ids and comma decimal seconds.
        assert "1\n" in out
        assert "," in out and ".500" not in out

    def test_text_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cap, "CACHE_DIR", tmp_path / "captions")
        monkeypatch.setattr(cap, "NO_CACHE", False)
        self._stub_seams(monkeypatch, [_seg(0, 50, "Hello there.")])

        src = tmp_path / "input.mp3"
        src.write_bytes(b"x")
        out = cap.transcribe(src, model="small", lang="en", fmt="text")
        # Plain transcript — no WEBVTT header, no cue numbering.
        assert not out.startswith("WEBVTT")
        assert "Hello there." in out
