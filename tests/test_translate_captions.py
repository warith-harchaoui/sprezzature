"""
test_translate_captions — coverage for ``sprezzature-audio/scripts/translate_captions.py``.

The Ollama call is injected as a seam (``translate_batch`` / the module-level
``make_ollama_translator`` factory), so every test runs offline. Coverage:
timestamp formatting, VTT rendering, language resolution, the batched
translate-cues core (windowing, 1:1 remap, count-mismatch per-cue fallback,
fail-loud on unrecoverable mismatch), the two-track snippet, and the CLI
(skip-when-same-language, happy path, unreachable daemon, missing file).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

import translate_captions as tc


def _cue(start: float, end: float, text: str) -> dict:
    """Build a parsed-cue dict shaped like ``parse_caption_cues`` output."""
    return {"start": start, "end": end, "text": text}


_EN_VTT = (
    "WEBVTT\n\n"
    "00:00:00.000 --> 00:00:01.500\n"
    "Hello everyone and welcome.\n\n"
    "00:00:01.500 --> 00:00:03.000\n"
    "Today we talk about the weather.\n"
)


# ── _format_timestamp ──────────────────────────────────────────────────────

class TestFormatTimestamp:
    def test_zero(self) -> None:
        assert tc._format_timestamp(0.0) == "00:00:00.000"

    def test_one_and_half(self) -> None:
        assert tc._format_timestamp(1.5) == "00:00:01.500"

    def test_hours_minutes(self) -> None:
        # 1h 01m 01.234s.
        assert tc._format_timestamp(3661.234) == "01:01:01.234"

    def test_negative_clamped(self) -> None:
        assert tc._format_timestamp(-5.0) == "00:00:00.000"


# ── render_vtt ─────────────────────────────────────────────────────────────

class TestRenderVtt:
    def test_header_and_cue(self) -> None:
        out = tc.render_vtt([_cue(0.0, 1.5, "Bonjour")])
        assert out.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:01.500" in out
        assert "Bonjour" in out

    def test_skips_empty_text(self) -> None:
        out = tc.render_vtt([_cue(0.0, 1.0, ""), _cue(1.0, 2.0, "Salut")])
        assert "00:00:00.000 --> 00:00:01.000" not in out
        assert "Salut" in out


# ── language resolution ────────────────────────────────────────────────────

class TestLanguageResolution:
    def test_explicit_target_wins(self) -> None:
        assert tc.resolve_target_language("FR", "some english context") == "fr"

    def test_target_fallback_when_no_signal(self) -> None:
        assert tc.resolve_target_language(None, "", fallback="en") == "en"

    def test_target_detected_returns_two_letters(self) -> None:
        code = tc.resolve_target_language(None, "Ceci est un texte en français clair.")
        assert isinstance(code, str) and len(code) == 2

    def test_source_language_two_letters(self) -> None:
        code = tc.detect_source_language([_cue(0.0, 1.0, "Hello there, this is English.")])
        assert isinstance(code, str) and len(code) == 2


# ── translate_cues (batched core) ──────────────────────────────────────────

class TestTranslateCues:
    def test_identity_preserves_timestamps_and_order(self) -> None:
        cues = [_cue(0.0, 1.0, "a"), _cue(1.0, 2.0, "b"), _cue(2.0, 3.0, "c")]
        out = tc.translate_cues(cues, translate_batch=lambda w: list(w), batch_size=2)
        assert [c["text"] for c in out] == ["a", "b", "c"]
        assert [(c["start"], c["end"]) for c in out] == [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]

    def test_batching_translates_all(self) -> None:
        cues = [_cue(float(i), float(i + 1), str(i)) for i in range(5)]
        out = tc.translate_cues(cues, translate_batch=lambda w: [t.upper() for t in w], batch_size=2)
        # 5 cues over windows of 2 → still 5, order preserved.
        assert [c["text"] for c in out] == ["0", "1", "2", "3", "4"]
        assert len(out) == 5

    def test_count_mismatch_falls_back_per_cue(self) -> None:
        # Batch call collapses the window to one line (wrong count); a
        # single-item call behaves. The core must retry per-cue and recover.
        def flaky(window: list) -> list:
            if len(window) > 1:
                return [" | ".join(window)]  # wrong count
            return [f"T:{window[0]}"]

        cues = [_cue(0.0, 1.0, "x"), _cue(1.0, 2.0, "y"), _cue(2.0, 3.0, "z")]
        out = tc.translate_cues(cues, translate_batch=flaky, batch_size=3)
        assert [c["text"] for c in out] == ["T:x", "T:y", "T:z"]

    def test_unrecoverable_mismatch_raises(self) -> None:
        # Even a single-cue call returns the wrong count → fail loud.
        cues = [_cue(0.0, 1.0, "x"), _cue(1.0, 2.0, "y")]
        with pytest.raises(tc.TranslationError):
            tc.translate_cues(cues, translate_batch=lambda w: [], batch_size=8)


# ── two_track_snippet ──────────────────────────────────────────────────────

class TestTwoTrackSnippet:
    def test_has_both_tracks(self) -> None:
        html = tc.two_track_snippet(
            media="talk.mp4",
            native_vtt="talk.vtt",
            translated_vtt="talk.fr.vtt",
            audio_lang="en",
            target_lang="fr",
        )
        assert 'kind="captions"' in html and "default" in html
        assert 'kind="subtitles"' in html
        assert 'srclang="en"' in html and 'srclang="fr"' in html
        assert "talk.mp4" in html and "talk.vtt" in html and "talk.fr.vtt" in html


# ── CLI ────────────────────────────────────────────────────────────────────

class TestCli:
    def test_missing_file(self, tmp_path: Path) -> None:
        rc = tc.main([str(tmp_path / "nope.vtt")])
        assert rc == 1

    def test_skip_when_source_equals_target(self, tmp_path: Path, capsys) -> None:
        src = tmp_path / "clip.vtt"
        src.write_text(_EN_VTT, encoding="utf-8")
        # English captions + explicit English target → nothing to translate.
        rc = tc.main([str(src), "--lang", "en"])
        assert rc == 0
        assert not (tmp_path / "clip.en.vtt").exists()
        assert "no translation track needed" in capsys.readouterr().err.lower()

    def test_unreachable_daemon(self, tmp_path: Path, monkeypatch) -> None:
        src = tmp_path / "clip.vtt"
        src.write_text(_EN_VTT, encoding="utf-8")
        monkeypatch.setattr(tc, "_reachable", lambda url: False)
        rc = tc.main([str(src), "--lang", "fr"])
        assert rc == 1

    def test_happy_path_writes_translation_and_snippet(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        src = tmp_path / "clip.vtt"
        src.write_text(_EN_VTT, encoding="utf-8")
        monkeypatch.setattr(tc, "_reachable", lambda url: True)
        # Inject a deterministic translator instead of hitting Ollama.
        monkeypatch.setattr(
            tc, "make_ollama_translator",
            lambda **kw: (lambda window: [f"FR:{t}" for t in window]),
        )
        rc = tc.main([str(src), "--lang", "fr", "--media", "clip.mp4"])
        assert rc == 0
        out_file = tmp_path / "clip.fr.vtt"
        assert out_file.exists()
        body = out_file.read_text(encoding="utf-8")
        assert "FR:Hello everyone and welcome." in body
        assert body.startswith("WEBVTT")
        # The two-track snippet is printed to stdout.
        stdout = capsys.readouterr().out
        assert 'kind="captions"' in stdout and 'kind="subtitles"' in stdout
