"""
test_plain_language — coverage for ``sprezzature-publish/scripts/plain_language.py``.

The Ollama call is mocked. Tests cover cache-key stability against
``preserve`` order, the empty-input short-circuit, the build_prompt
contract, the over-long retry path, and main()'s stdin / file inputs.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock, patch

import pytest

import plain_language as pl


@pytest.fixture
def fresh_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "plain"
    monkeypatch.setattr(pl, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(pl, "NO_CACHE", False)
    return cache_dir


# ── _cache_key ──────────────────────────────────────────────────────────────

class TestCacheKey:
    def test_preserve_order_does_not_change_key(self):
        # ``preserve`` is sorted before hashing so callers can pass terms in
        # any order without invalidating the cache.
        k1 = pl._cache_key("text", 8, "en", ["Brand", "Product"], "m:tag")
        k2 = pl._cache_key("text", 8, "en", ["Product", "Brand"], "m:tag")
        assert k1 == k2

    def test_different_preserve_yields_different_key(self):
        k1 = pl._cache_key("text", 8, "en", ["Brand"], "m:tag")
        k2 = pl._cache_key("text", 8, "en", ["Other"], "m:tag")
        assert k1 != k2

    @pytest.mark.parametrize("attr,value", [
        ("text", "different"),
        ("grade", 6),
        ("lang", "fr"),
        ("model", "other:tag"),
    ])
    def test_each_input_invalidates_key(self, attr, value):
        base = dict(text="text", grade=8, lang="en", preserve=["X"], model="m:tag")
        modified = dict(base)
        modified[attr] = value
        assert pl._cache_key(**base) != pl._cache_key(**modified)


# ── build_prompt ────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_preserve_clause_only_when_terms_present(self):
        with_preserve = pl.build_prompt("text", 8, "en", ["Brand"])
        without = pl.build_prompt("text", 8, "en", [])
        assert "Brand" in with_preserve
        assert "Brand" not in without
        # The "Keep these tokens verbatim" sentence only appears when
        # there are tokens to keep.
        assert "verbatim" in with_preserve

    def test_per_language_opener(self):
        en = pl.build_prompt("text", 8, "en", [])
        fr = pl.build_prompt("text", 8, "fr", [])
        assert "English" in en
        assert "français" in fr

    def test_grade_appears_in_prompt(self):
        p = pl.build_prompt("text", 6, "en", [])
        assert "6" in p


# ── rewrite ─────────────────────────────────────────────────────────────────

class TestRewrite:
    def test_empty_input_short_circuits(self, fresh_cache):
        # No model call, no transformation, no cache lookup.
        with patch.object(pl.requests, "post") as mock_post:
            assert pl.rewrite("") == ""
            assert pl.rewrite("   \n  ") == "   \n  "
        mock_post.assert_not_called()

    def test_caches_result(self, fresh_cache):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Get more done."}
        mock_resp.raise_for_status = MagicMock()
        with patch.object(pl.requests, "post", return_value=mock_resp) as mock_post:
            first = pl.rewrite("Boost your productivity", lang="en", model="m")
        # Second call hits the cache; no extra model invocation.
        with patch.object(pl.requests, "post") as mock_post2:
            second = pl.rewrite("Boost your productivity", lang="en", model="m")
        assert first == "Get more done."
        assert second == first
        mock_post.assert_called_once()
        mock_post2.assert_not_called()

    def test_length_retry_when_overshoot(self, fresh_cache):
        # First reply is way too long (> 1.1× the source); the helper re-asks
        # with a tighter instruction and returns the second response.
        source = "Boost productivity"
        long_reply = "a" * (len(source) * 10)
        short_reply = "Be productive."

        first_resp = MagicMock()
        first_resp.json.return_value = {"response": long_reply}
        first_resp.raise_for_status = MagicMock()
        second_resp = MagicMock()
        second_resp.json.return_value = {"response": short_reply}
        second_resp.raise_for_status = MagicMock()

        with patch.object(pl.requests, "post",
                          side_effect=[first_resp, second_resp]) as mock_post:
            out = pl.rewrite(source, lang="en", model="m")
        # The retry's response wins.
        assert out == short_reply
        assert mock_post.call_count == 2

    def test_connection_error_exits_two(self, fresh_cache):
        import requests as real_requests
        with patch.object(pl.requests, "post",
                          side_effect=real_requests.exceptions.ConnectionError()):
            with pytest.raises(SystemExit) as excinfo:
                pl.rewrite("text", lang="en", model="m")
        assert excinfo.value.code == 2


# ── main() ──────────────────────────────────────────────────────────────────

class TestMain:
    def test_stdin_tty_prints_hint_and_exits(self, monkeypatch, capsys):
        # Simulate ``sys.stdin.isatty() is True`` and no --input flag.
        fake_stdin = io.StringIO("")
        fake_stdin.isatty = lambda: True  # type: ignore[assignment]
        monkeypatch.setattr(sys, "stdin", fake_stdin)
        monkeypatch.setattr(sys, "argv", ["plain"])
        rc = pl.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "input" in err.lower()

    def test_file_input_routes_through_model(self, fresh_cache, tmp_path, monkeypatch, capsys):
        src = tmp_path / "copy.md"
        src.write_text("Boost your productivity", encoding="utf-8")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Get more done."}
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr(sys, "argv", [
            "plain", "--input", str(src), "--lang", "en", "--no-cache",
        ])
        with patch.object(pl.requests, "post", return_value=mock_resp):
            rc = pl.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "Get more done." in out

    def test_preserve_flag_parsed_and_passed(self, fresh_cache, tmp_path, monkeypatch):
        # When --preserve is set, the tokens should reach build_prompt.
        src = tmp_path / "copy.md"
        src.write_text("Some marketing copy.", encoding="utf-8")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Plain copy."}
        mock_resp.raise_for_status = MagicMock()
        monkeypatch.setattr(sys, "argv", [
            "plain", "--input", str(src), "--lang", "en",
            "--preserve", "Tailwind, Montserrat",
        ])
        # Spy on build_prompt to confirm the preserve list arrives parsed.
        seen: list[list[str]] = []
        original = pl.build_prompt
        def spy(text, grade, lang, preserve):
            seen.append(preserve)
            return original(text, grade, lang, preserve)
        monkeypatch.setattr(pl, "build_prompt", spy)
        with patch.object(pl.requests, "post", return_value=mock_resp):
            rc = pl.main()
        assert rc == 0
        # Whitespace-trimmed, comma-split, in order.
        assert seen == [["Tailwind", "Montserrat"]]
