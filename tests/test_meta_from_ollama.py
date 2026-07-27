"""
test_meta_from_ollama — coverage for ``sprezzature-publish/scripts/meta_from_ollama.py``.

The Ollama call is mocked; cache directory redirected per test.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

import meta_from_ollama as meta


@pytest.fixture
def fresh_cache(tmp_path, monkeypatch):
    """Redirect cache dir to tmp_path; re-enable cache (autouse fixture sets env)."""
    cache_dir = tmp_path / "meta"
    monkeypatch.setattr(meta, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(meta, "NO_CACHE", False)
    return cache_dir


# ── extract_text ────────────────────────────────────────────────────────────

class TestExtractText:
    def test_strips_script_style_svg_noscript(self):
        html = (
            "<html><head>"
            "<style>body { color: red; }</style>"
            "<script>var x = 1;</script>"
            "</head><body>"
            "<svg><circle r='1'/></svg>"
            "<noscript>JS off</noscript>"
            "<p>Real content here.</p>"
            "</body></html>"
        )
        text = meta.extract_text(html)
        assert "Real content here." in text
        # None of the noise blocks leak through.
        assert "color: red" not in text
        assert "var x" not in text
        assert "circle" not in text
        assert "JS off" not in text

    def test_collapses_whitespace(self):
        html = "<p>One.\n\n\n   Two.    Three.</p>"
        text = meta.extract_text(html)
        # Multiple whitespace runs collapse to a single space.
        assert "One. Two. Three." in text
        assert "  " not in text

    def test_truncates_at_limit(self):
        html = "<p>" + ("x " * 5000) + "</p>"
        text = meta.extract_text(html, limit=100)
        assert len(text) == 100


# ── extract_json ────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_clean_json(self):
        obj = meta.extract_json('{"title": "Hello"}')
        assert obj == {"title": "Hello"}

    def test_handles_noisy_preamble_and_postamble(self):
        noisy = 'Here is your answer: {"title": "Hello"}\nThanks.'
        obj = meta.extract_json(noisy)
        assert obj == {"title": "Hello"}

    def test_raises_when_no_braces(self):
        with pytest.raises(ValueError):
            meta.extract_json("no JSON at all")

    def test_raises_on_invalid_json(self):
        # Braces present but contents are not valid JSON.
        with pytest.raises(json.JSONDecodeError):
            meta.extract_json("{ not valid json }")


# ── build_prompt ────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_always_includes_schema_hint(self):
        p = meta.build_prompt(goal="A blog", page_text="", site_name="", lang="en")
        # The JSON schema (per-key contract) is part of every prompt.
        assert "title" in p
        assert "description" in p
        assert "schema_type" in p

    def test_brand_block_only_when_supplied(self):
        with_brand = meta.build_prompt(goal="", page_text="", site_name="Acme", lang="en")
        without = meta.build_prompt(goal="", page_text="", site_name="", lang="en")
        assert "Acme" in with_brand
        assert "Acme" not in without

    def test_goal_block_only_when_supplied(self):
        with_goal = meta.build_prompt(goal="FAQ page", page_text="", site_name="", lang="en")
        assert "FAQ page" in with_goal

    def test_page_text_block_only_when_supplied(self):
        with_text = meta.build_prompt(goal="", page_text="Real body text.", site_name="", lang="en")
        assert "Real body text." in with_text

    def test_lang_line_in_french(self):
        p = meta.build_prompt(goal="", page_text="", site_name="", lang="fr")
        # The French opener leads the prompt.
        assert "français" in p


# ── _cache_key + round-trip ────────────────────────────────────────────────

class TestCache:
    def test_cache_key_deterministic(self):
        k1 = meta._cache_key("goal", "page", "site", "en", "m:tag")
        k2 = meta._cache_key("goal", "page", "site", "en", "m:tag")
        assert k1 == k2
        assert len(k1) == 32

    def test_cache_key_changes_with_inputs(self):
        base = meta._cache_key("g", "p", "s", "en", "m")
        assert meta._cache_key("OTHER", "p", "s", "en", "m") != base
        assert meta._cache_key("g", "OTHER", "s", "en", "m") != base
        assert meta._cache_key("g", "p", "OTHER", "en", "m") != base
        assert meta._cache_key("g", "p", "s", "fr", "m") != base
        assert meta._cache_key("g", "p", "s", "en", "OTHER") != base

    def test_round_trip(self, fresh_cache):
        meta._cache_set("k1", {"title": "Hi"})
        assert meta._cache_get("k1") == {"title": "Hi"}

    def test_corrupt_cache_file_returns_none(self, fresh_cache):
        # A corrupt JSON entry is treated as a miss so the model can refresh.
        fresh_cache.mkdir(parents=True)
        (fresh_cache / "abc.json").write_text("not valid json", encoding="utf-8")
        assert meta._cache_get("abc") is None

    def test_miss_returns_none(self, fresh_cache):
        assert meta._cache_get("never-set") is None


# ── End-to-end main() ──────────────────────────────────────────────────────

def _mock_ollama_response(payload_str: str) -> MagicMock:
    """Build a MagicMock that mimics ``requests.Response``."""
    mock = MagicMock()
    mock.json.return_value = {"response": payload_str}
    mock.raise_for_status = MagicMock()
    return mock


class TestMain:
    def test_full_run_from_html_file(self, fresh_cache, tmp_path, monkeypatch, capsys):
        # Source HTML on disk.
        html_path = tmp_path / "page.html"
        html_path.write_text("<title>Demo</title><p>Real content here.</p>", encoding="utf-8")

        # Mock the model reply.
        reply = json.dumps({
            "title": "Demo title",
            "description": "Short description.",
            "og_title": "Demo",
            "og_description": "Short.",
            "og_image_alt": "",
            "twitter_title": "Demo",
            "twitter_description": "Short.",
            "schema_type": "WebSite",
            "keywords_hint": ["demo", "test"],
        })
        mock_resp = _mock_ollama_response(reply)
        monkeypatch.setattr(sys, "argv", [
            "meta", str(html_path),
            "--site-name", "Acme",
            "--lang", "en",
            "--canonical", "https://example.com/demo",
        ])

        with patch.object(meta.requests, "post", return_value=mock_resp):
            rc = meta.main()
        assert rc == 0

        # Stdout carries the JSON object with the canonical URL added.
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["title"] == "Demo title"
        assert parsed["canonical"] == "https://example.com/demo"

    def test_no_source_no_goal_errors(self, fresh_cache, monkeypatch):
        # argparse error path → SystemExit (code 2 is argparse default).
        monkeypatch.setattr(sys, "argv", ["meta"])
        with pytest.raises(SystemExit):
            meta.main()

    def test_json_parse_failure_returns_one(self, fresh_cache, tmp_path, monkeypatch):
        html_path = tmp_path / "page.html"
        html_path.write_text("<p>Body.</p>", encoding="utf-8")
        # Reply with no braces → extract_json raises → main returns 1.
        mock_resp = _mock_ollama_response("the model forgot to return JSON")
        monkeypatch.setattr(sys, "argv", ["meta", str(html_path), "--lang", "en"])
        with patch.object(meta.requests, "post", return_value=mock_resp):
            rc = meta.main()
        assert rc == 1

    def test_connection_error_returns_two(self, fresh_cache, tmp_path, monkeypatch):
        import requests as real_requests
        html_path = tmp_path / "page.html"
        html_path.write_text("<p>Body.</p>", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["meta", str(html_path), "--lang", "en"])
        with patch.object(meta.requests, "post",
                          side_effect=real_requests.exceptions.ConnectionError()):
            rc = meta.main()
        assert rc == 2
