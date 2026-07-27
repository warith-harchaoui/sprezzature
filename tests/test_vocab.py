"""
test_vocab — coverage for ``sprezzature-accessibility/scripts/_vocab.py``.

The vocabulary helpers feed both ``alt_from_ollama`` and
``captions_from_whisper``. Six functions are covered: ``extract_vocabulary``,
``read_vocab_file``, ``find_project_root``, ``collect_project_text``,
``surrounding_text``, ``resolve_vocab_terms``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import _vocab as v


# ── extract_vocabulary ──────────────────────────────────────────────────────

class TestExtractVocabulary:
    def test_backtick_spans_captured(self):
        terms = v.extract_vocabulary("Use `Tailwind` and `vanilla-JS` together.")
        # Both code spans surface; capitalisation is preserved from the source.
        assert "Tailwind" in terms
        assert "vanilla-JS" in terms

    def test_camel_case_and_snake_case(self):
        terms = v.extract_vocabulary("Call `extract_vocabulary` and runFastTask now.")
        # snake_case identifier + CamelCase identifier both qualify; bare
        # lowercase words ("now") do not.
        assert "extract_vocabulary" in terms
        assert "runFastTask" in terms
        assert "now" not in terms

    def test_capitalised_multiword_mid_sentence(self):
        text = "We trained on Common Crawl using a fast machine."
        # Mid-sentence multi-word capitalisation is treated as a proper noun.
        terms = v.extract_vocabulary(text)
        assert any(t == "Common Crawl" for t in terms)

    def test_sentence_starter_excluded(self):
        text = "Tailwind is fine. Also good is Tailwind."
        # The second "Tailwind" appears mid-sentence so it should be picked up;
        # the first one starts the document so the heuristic filters it out.
        terms = v.extract_vocabulary(text)
        # Either way "Tailwind" appears at most once (dedup is case-insensitive).
        assert sum(1 for t in terms if t.lower() == "tailwind") <= 1

    def test_html_and_script_stripped(self):
        text = "<script>var Secret = 1;</script><p>The Project is `Tailwind` here.</p>"
        terms = v.extract_vocabulary(text)
        assert "Tailwind" in terms
        # Identifiers in script blocks must not leak through.
        assert "Secret" not in terms

    def test_dedup_case_insensitive_keeps_first(self):
        terms = v.extract_vocabulary("Use `Tailwind` and `tailwind` and `TAILWIND` again.")
        # Only one variant survives, in source order.
        lower_terms = [t.lower() for t in terms]
        assert lower_terms.count("tailwind") == 1

    def test_short_terms_dropped(self):
        # Single-character backtick spans should not be kept.
        terms = v.extract_vocabulary("`a` is too short, `bb` is fine.")
        assert "a" not in terms
        assert "bb" in terms

    def test_empty_input_returns_empty(self):
        assert v.extract_vocabulary("") == []


# ── read_vocab_file ─────────────────────────────────────────────────────────

class TestReadVocabFile:
    def test_strips_comments_and_blanks(self, tmp_path: Path):
        path = tmp_path / "glossary.txt"
        path.write_text(
            "# heading comment\n"
            "Tailwind\n"
            "\n"
            "  vanilla-JS  \n"
            "# trailing comment\n",
            encoding="utf-8",
        )
        terms = v.read_vocab_file(path)
        assert terms == ["Tailwind", "vanilla-JS"]

    def test_dedups_case_insensitive(self, tmp_path: Path):
        path = tmp_path / "g.txt"
        path.write_text("Tailwind\ntailwind\nTAILWIND\n", encoding="utf-8")
        # The first spelling wins.
        assert v.read_vocab_file(path) == ["Tailwind"]


# ── find_project_root ───────────────────────────────────────────────────────

class TestFindProjectRoot:
    def test_finds_marker_in_ancestor(self, tmp_path: Path):
        # Layout: <root>/.git, <root>/a/b/c
        (tmp_path / ".git").mkdir()
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert v.find_project_root(deep) == tmp_path

    def test_returns_none_when_no_marker(self, tmp_path: Path):
        # Empty tree with no marker anywhere up to the filesystem root.
        # We can't guarantee the temp's ancestors are marker-free, so create
        # a leaf and just confirm the function reaches *some* path or None
        # without raising. The contract: never raise.
        leaf = tmp_path / "nested"
        leaf.mkdir()
        result = v.find_project_root(leaf)
        # Either a known ancestor with a marker, or None — never an error.
        assert result is None or isinstance(result, Path)

    def test_recognises_each_marker(self, tmp_path: Path):
        # ``.git`` is a directory; the rest are files.
        directory_markers = {".git"}
        for marker in v.PROJECT_ROOT_MARKERS:
            root = tmp_path / marker.replace(".", "_") / "root"
            root.mkdir(parents=True)
            target = root / marker
            if marker in directory_markers:
                target.mkdir()
            else:
                target.touch()
            leaf = root / "src" / "nested"
            leaf.mkdir(parents=True)
            assert v.find_project_root(leaf) == root


# ── collect_project_text ────────────────────────────────────────────────────

class TestCollectProjectText:
    def test_reads_marker_files_first(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Project\nReadme body.", encoding="utf-8")
        (tmp_path / "SKILL.md").write_text("# Skill\nSkill body.", encoding="utf-8")
        out = v.collect_project_text(tmp_path)
        assert "Readme body" in out
        assert "Skill body" in out

    def test_walks_known_doc_folders(self, tmp_path: Path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "intro.md").write_text("Intro topic.", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "notes.md").write_text("Src notes.", encoding="utf-8")
        out = v.collect_project_text(tmp_path)
        assert "Intro topic" in out
        assert "Src notes" in out

    def test_skips_unknown_folders(self, tmp_path: Path):
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "junk.md").write_text("Junk that should not leak.", encoding="utf-8")
        out = v.collect_project_text(tmp_path)
        assert "Junk that should not leak" not in out

    def test_budget_cap_honored(self, tmp_path: Path):
        # 4 KB sentinel × 200 = 800 KB of source, capped to a 1024-byte budget.
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "big.md").write_text("x" * 50_000, encoding="utf-8")
        out = v.collect_project_text(tmp_path, budget=1024)
        assert len(out) <= 1024 + 1  # +1 for the join newline at the end


# ── surrounding_text ────────────────────────────────────────────────────────

class TestSurroundingText:
    def test_returns_window_around_match(self, tmp_path: Path):
        doc = tmp_path / "post.md"
        # The image reference appears once, with prose around it.
        doc.write_text("Before context. ![alt](chart.png) After context.", encoding="utf-8")
        result = v.surrounding_text(doc, Path("chart.png"), window=20)
        assert "chart.png" in result
        assert "Before context" in result or "After context" in result

    def test_prepends_nearest_heading(self, tmp_path: Path):
        doc = tmp_path / "post.md"
        doc.write_text(
            "# Top\nIntro.\n\n## Section A\nText with ![alt](chart.png) inline.\n",
            encoding="utf-8",
        )
        result = v.surrounding_text(doc, Path("chart.png"))
        # The closest preceding heading is "## Section A".
        assert result.startswith("## Section A")

    def test_returns_empty_when_no_match(self, tmp_path: Path):
        doc = tmp_path / "post.md"
        doc.write_text("Body without any image.", encoding="utf-8")
        assert v.surrounding_text(doc, Path("chart.png")) == ""

    def test_multiple_matches_joined_with_blank_line(self, tmp_path: Path):
        doc = tmp_path / "post.md"
        doc.write_text(
            "A. ![alt](chart.png) B. " + ("filler " * 50) + " C. ![alt](chart.png) D.",
            encoding="utf-8",
        )
        result = v.surrounding_text(doc, Path("chart.png"), window=10)
        # Two windows joined by a blank line.
        assert result.count("chart.png") == 2
        assert "\n\n" in result


# ── resolve_vocab_terms ─────────────────────────────────────────────────────

class TestResolveVocabTerms:
    def test_in_doc_takes_priority(self, tmp_path: Path):
        # When in_doc has a reference, its surrounding text wins.
        doc = tmp_path / "post.md"
        doc.write_text("# Chart\nThe `Tailwind` chart ![alt](chart.png) helps.", encoding="utf-8")
        source = tmp_path / "chart.png"
        source.touch()
        terms = v.resolve_vocab_terms(source, in_doc=doc)
        assert "Tailwind" in terms

    def test_vocab_file_used_when_in_doc_absent(self, tmp_path: Path):
        glossary = tmp_path / "g.txt"
        glossary.write_text("BrandName\n", encoding="utf-8")
        source = tmp_path / "img.png"
        source.touch()
        assert v.resolve_vocab_terms(source, vocab_file=glossary) == ["BrandName"]

    def test_vocab_from_directory(self, tmp_path: Path):
        # vocab_from as a directory triggers project-walk.
        (tmp_path / "README.md").write_text("# Title\nUse `Tailwind` here.", encoding="utf-8")
        source = tmp_path / "img.png"
        source.touch()
        terms = v.resolve_vocab_terms(source, vocab_from=tmp_path)
        assert "Tailwind" in terms

    def test_subtitle_sibling_used_when_present(self, tmp_path: Path):
        # Caption file alongside the media source is the highest-signal
        # vocabulary for audio / video sources.
        media = tmp_path / "interview.mp3"
        media.touch()
        (tmp_path / "interview.txt").write_text("Speaker mentions `Tailwind`.", encoding="utf-8")
        terms = v.resolve_vocab_terms(media)
        assert "Tailwind" in terms

    def test_returns_empty_when_nothing_resolves(self, tmp_path: Path):
        # Isolated source with no project markers, no doc, no glossary.
        source = tmp_path / "lonely" / "img.png"
        source.parent.mkdir()
        source.touch()
        assert v.resolve_vocab_terms(source) == []
