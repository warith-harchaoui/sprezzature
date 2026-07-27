"""
test_alt_from_ollama — coverage for ``sprezzature-accessibility/scripts/alt_from_ollama.py``.

The Ollama network call is mocked everywhere. The cache directory is
redirected per-test via a monkeypatched module-level constant — the
autouse ``isolate_cache`` fixture in conftest sets ``SPREZZATURE_CACHE_DIR``
but the module's ``CACHE_DIR`` is computed at import time, so we have
to point the module at the tmp_path explicitly.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import alt_from_ollama as alt


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_cache(tmp_path, monkeypatch):
    """Redirect the module's cache dir at the tmp_path and re-enable caching."""
    cache_dir = tmp_path / "alt"
    monkeypatch.setattr(alt, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(alt, "NO_CACHE", False)
    return cache_dir


@pytest.fixture
def tiny_png(tmp_path):
    """Write a 1×1 PNG and return its path."""
    # The minimal PNG byte sequence for a 1×1 transparent image.
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c63000100000005000156a1a8000000000049454e44ae426082"
    )
    path = tmp_path / "tiny.png"
    path.write_bytes(png_bytes)
    return path


# ── compose_vocabulary_hint ────────────────────────────────────────────────

class TestComposeVocabularyHint:
    def test_empty_input_returns_empty(self):
        assert alt.compose_vocabulary_hint([]) == ""

    def test_terms_appear_in_output(self):
        out = alt.compose_vocabulary_hint(["Tailwind", "Montserrat"])
        assert "Tailwind" in out
        assert "Montserrat" in out
        # Mentions the hallucination guard.
        assert "Do NOT include" in out

    def test_truncates_at_60_terms(self):
        many = [f"term{i}" for i in range(100)]
        out = alt.compose_vocabulary_hint(many)
        # Only the first 60 terms make it into the prompt.
        assert "term59" in out
        assert "term60" not in out


# ── pick_default_model ─────────────────────────────────────────────────────

class TestPickDefaultModel:
    def test_env_seam_wins(self, monkeypatch):
        # OLLAMA_MODEL is a TEST SEAM only (so the suite can point the resolver
        # at a stub without a live daemon) — never a user-facing model choice.
        monkeypatch.setenv("OLLAMA_MODEL", "custom:tag")
        assert alt.pick_default_model() == "custom:tag"

    def test_default_is_registry_base_no_mlx(self, monkeypatch):
        # qwen3-vl:8b is registry-standard and multimodal; no ``-mlx`` auto-suffix
        # (that only named a maintainer-local build and 404'd on a fresh box).
        # With the seam unset the one authorized model is used.
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        assert alt.pick_default_model() == alt.DEFAULT_BASE
        assert not alt.pick_default_model().endswith("-mlx")


# ── prompt_for ─────────────────────────────────────────────────────────────

class TestPromptFor:
    @pytest.mark.parametrize("kind", ["informative", "functional", "text", "complex", "group"])
    def test_each_kind_produces_a_prompt(self, kind):
        p = alt.prompt_for(kind, "en", context="hero photo")
        assert isinstance(p, str)
        assert len(p) > 0
        # The English language line shows up.
        assert "English" in p or "alt text" in p.lower()

    def test_text_kind_uses_verbatim_phrasing(self):
        # The 'text' purpose extracts the text verbatim — the prompt should
        # reflect that, not the generic "match meaning" framing.
        p = alt.prompt_for("text", "en")
        # Either it mentions extracting text, or it omits the
        # "match meaning, not pixels" rule. Both shape the result.
        assert "text" in p.lower()

    def test_complex_mentions_long_description(self):
        # The complex purpose's short prompt nudges toward a brief alt that
        # is meant to pair with a longer description elsewhere.
        p = alt.prompt_for("complex", "en")
        assert isinstance(p, str) and len(p) > 0

    def test_context_appended(self):
        p = alt.prompt_for("informative", "en", context="Marketing landing")
        assert "Marketing landing" in p

    def test_french_lang_line(self):
        p = alt.prompt_for("informative", "fr")
        # The French opener leads with the French instruction sentence.
        assert "français" in p


# ── post_process ───────────────────────────────────────────────────────────

class TestPostProcess:
    def test_strips_straight_quotes(self):
        assert alt.post_process('"A teacher leading a class"', "en") == "A teacher leading a class"

    def test_strips_straight_singles(self):
        # The current implementation only strips pairs whose first and last
        # characters are *identical*, so mismatched curly quotes pass through
        # unchanged. Straight single quotes do get stripped.
        assert alt.post_process("'Teacher'", "en") == "Teacher"

    def test_mismatched_curly_quotes_pass_through(self):
        # Asymmetric typographic pairs are intentionally left alone to avoid
        # corrupting verbatim ``text``-kind output.
        assert alt.post_process("“Teacher”", "en") == "“Teacher”"

    @pytest.mark.parametrize("raw,lang", [
        ("Image of a teacher", "en"),
        ("Picture of a chart", "en"),
        ("Photo of: a dog", "en"),
        ("Illustration of — a chart", "en"),
        ("Image de la salle", "fr"),
        ("Imagen de un perro", "es"),
        ("Bild von einem Hund", "de"),
    ])
    def test_strips_banned_prefixes(self, raw, lang):
        out = alt.post_process(raw, lang)
        # The cleaned text never starts with the banned phrase.
        assert not out.lower().startswith(("image of", "picture of", "photo of",
                                            "illustration of", "image de",
                                            "imagen de", "bild von"))

    def test_hard_cap_at_max_chars(self):
        # 200 chars of a single repeated word — well over the 150-char cap.
        raw = "Teacher " * 30
        out = alt.post_process(raw, "en")
        assert len(out) <= alt.MAX_CHARS
        # Truncation must happen at a word boundary; the trailing trim
        # strips dangling punctuation.
        assert not out.endswith(",") and not out.endswith("…")


# ── _cache_key + cache round-trip ──────────────────────────────────────────

class TestCacheKey:
    def test_deterministic_for_same_inputs(self):
        k1 = alt._cache_key(b"img-bytes", "informative", "en", "ctx", "model:tag")
        k2 = alt._cache_key(b"img-bytes", "informative", "en", "ctx", "model:tag")
        assert k1 == k2
        assert len(k1) == 32

    @pytest.mark.parametrize("attr,value", [
        ("kind", "functional"),
        ("lang", "fr"),
        ("context", "different"),
        ("model", "other:tag"),
    ])
    def test_key_changes_with_any_input(self, attr, value):
        base = dict(image_bytes=b"img-bytes", kind="informative", lang="en",
                    context="ctx", model="model:tag")
        modified = dict(base)
        modified[attr] = value
        assert alt._cache_key(**base) != alt._cache_key(**modified)


class TestCacheRoundTrip:
    def test_set_then_get(self, fresh_cache):
        alt._cache_set("abc123", "stored alt text")
        assert alt._cache_get("abc123") == "stored alt text"

    def test_miss_returns_none(self, fresh_cache):
        assert alt._cache_get("nonexistent") is None

    def test_no_cache_disables_both_directions(self, fresh_cache, monkeypatch):
        monkeypatch.setattr(alt, "NO_CACHE", True)
        alt._cache_set("k", "v")
        # Cache writes are skipped entirely.
        assert not (fresh_cache / "k.txt").exists()
        # And reads always miss.
        assert alt._cache_get("k") is None


# ── describe ──────────────────────────────────────────────────────────────

class TestDescribe:
    def test_decorative_short_circuits(self, fresh_cache):
        # No network call, no Pillow check, just "".
        with patch.object(alt.requests, "post") as mock_post:
            out = alt.describe("/no/such/path.jpg", kind="decorative")
        assert out == ""
        mock_post.assert_not_called()

    def test_informative_calls_model_and_caches(self, fresh_cache, tiny_png):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "  Teacher leading a class  "}
        mock_response.raise_for_status = MagicMock()
        with patch.object(alt.requests, "post", return_value=mock_response) as mock_post:
            out = alt.describe(str(tiny_png), kind="informative", lang="en",
                                model="m:tag")
        # Output is post-processed (whitespace stripped).
        assert out == "Teacher leading a class"
        mock_post.assert_called_once()
        # Second call hits the cache; the mock must not be called again.
        with patch.object(alt.requests, "post") as mock_post2:
            second = alt.describe(str(tiny_png), kind="informative", lang="en",
                                    model="m:tag")
        assert second == out
        mock_post2.assert_not_called()

    def test_banned_prefix_stripped_from_response(self, fresh_cache, tiny_png):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Image of a teacher"}
        mock_response.raise_for_status = MagicMock()
        with patch.object(alt.requests, "post", return_value=mock_response):
            out = alt.describe(str(tiny_png), kind="informative", lang="en", model="m")
        # The "Image of" prefix is gone after post_process.
        assert not out.lower().startswith("image of")

    def test_connection_error_exits_two(self, fresh_cache, tiny_png):
        import requests as real_requests
        with patch.object(alt.requests, "post",
                          side_effect=real_requests.exceptions.ConnectionError()):
            with pytest.raises(SystemExit) as excinfo:
                alt.describe(str(tiny_png), kind="informative", lang="en", model="m")
        assert excinfo.value.code == 2


# ── describe_long ─────────────────────────────────────────────────────────

class TestDescribeLong:
    def test_does_not_post_process(self, fresh_cache, tiny_png):
        # Long descriptions preserve Markdown — a bullet list survives.
        markdown = "- Chart type: bar chart\n- X axis: weeks\n- Takeaway: growth."
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": markdown}
        mock_response.raise_for_status = MagicMock()
        with patch.object(alt.requests, "post", return_value=mock_response):
            out = alt.describe_long(str(tiny_png), kind="complex", lang="en", model="m")
        # Markdown structure preserved verbatim.
        assert out == markdown

    def test_distinct_cache_key_from_short(self, fresh_cache, tiny_png):
        # A long-description call must not hit a short-alt cache entry, and
        # vice versa, since the outputs are not interchangeable.
        long_resp = MagicMock()
        long_resp.json.return_value = {"response": "long body"}
        long_resp.raise_for_status = MagicMock()
        short_resp = MagicMock()
        short_resp.json.return_value = {"response": "short alt"}
        short_resp.raise_for_status = MagicMock()

        with patch.object(alt.requests, "post", return_value=long_resp):
            long_out = alt.describe_long(str(tiny_png), kind="complex", lang="en", model="m")
        with patch.object(alt.requests, "post", return_value=short_resp):
            short_out = alt.describe(str(tiny_png), kind="complex", lang="en", model="m")
        assert long_out == "long body"
        assert short_out == "short alt"


# ── Pillow-disabled fallback ──────────────────────────────────────────────

class TestPillowDisabled:
    def test_maybe_resize_returns_input_when_pillow_missing(self, monkeypatch):
        # When Pillow is unavailable the helper forwards the bytes unchanged
        # rather than failing the whole call.
        monkeypatch.setattr(alt, "HAVE_PILLOW", False)
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert alt.maybe_resize(data, max_edge=64) is data

    def test_maybe_resize_skips_with_zero_max_edge(self):
        # ``--resize 0`` disables resizing even when Pillow is available.
        data = b"image-bytes"
        assert alt.maybe_resize(data, max_edge=0) is data
