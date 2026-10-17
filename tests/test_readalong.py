"""
test_readalong — the page and its narration have to agree, or say so.

The read-along is a claim about *correspondence*: span ``ra-12`` highlights
while cue 12 plays. Nothing enforces that at runtime, so what is tested here
is the thing that makes it true -- that the sentences the renderer produces
are the sentences the narration spoke, construct by construct, and that a
disagreement raises instead of shipping a highlight that points at the wrong
line.

Three groups, in that order of importance:

* **Agreement** (``TestTheTwoRoutesAgree``) -- one Markdown document walks
  both routes, and the lists are compared. One case per construct that used
  to break it: emphasis, code spans, autolinks, comments, nested lists,
  code inside a list item, tables, thematic breaks, images, frontmatter.
* **Refusal** (``TestItRefusesRatherThanGuess``) -- the divergences that
  cannot be reconciled are named, not absorbed.
* **Markup** (``TestWrapping``, ``TestPlayer``, ``TestReadingMeta``) -- what
  lands in the page, including that the rebuild returns the page unchanged
  apart from its spans.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re

import pytest

import _narrate
import _readalong

markdown = pytest.importorskip("markdown", reason="md_to_html needs the markdown library")


# ── Helpers ────────────────────────────────────────────────────────────────


def render(source: str) -> str:
    """Render Markdown exactly as ``md_to_html.convert_one`` does."""
    source = _narrate.FRONTMATTER_RE.sub("", source, count=1)
    engine = markdown.Markdown(
        extensions=["extra", "toc", "tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    return engine.convert(source)


def cues_for(source: str) -> list[_readalong.VttCue]:
    """Cues as a narration run would write and read them back: through WebVTT.

    Round-tripped through the file format on purpose. The page is wired from
    what is *on disk*, so a test that handed over in-memory cues would skip
    the only step that can lose something.
    """
    timeline = _narrate.Timeline(24_000)
    for index, segment in enumerate(_narrate.explode_to_sentences(
            _narrate.extract_segments(source))):
        timeline.silence(segment["pause_before_ms"])
        timeline.speech(int(24_000 * 1.4), index=index, text=segment["text"])
        timeline.silence(segment["pause_after_ms"])
    return _readalong.parse_vtt(_narrate.cues_to_vtt(timeline.cues))


def wrap(source: str) -> str:
    """Build the read-along for a Markdown source, start to finish."""
    return _readalong.wrap_sentences(
        render(source), cues_for(source),
        split=_narrate.split_sentences,
        opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
    )


def page(source: str) -> list[str]:
    """The sentences the rendered page shows."""
    return _readalong.page_sentences(render(source), split=_narrate.split_sentences)


def unframed(source: str) -> list[str]:
    """What the narration says, with its quotation framing removed."""
    return [
        text
        for text in (
            _readalong._unframe(
                cue.text, _narrate.QUOTE_OPENING, _narrate.QUOTE_CLOSING
            )
            for cue in cues_for(source)
        )
        if text is not None
    ]


# ── Agreement ──────────────────────────────────────────────────────────────


class TestTheTwoRoutesAgree:
    """The renderer's sentences are the narration's sentences.

    Every case here is a construct that once produced a different answer on
    each side -- and on the narration side, that almost always meant a voice
    reading out a sigil.
    """

    @pytest.mark.parametrize(
        ("name", "source"),
        [
            ("emphasis", "Some **bold** and *em* and _under_ and ~~struck~~ words."),
            ("emphasis across a code span", "One **model: `qwen3-vl:8b`** exactly."),
            ("emphasis inside a link", "A [*linked phrase*](https://example.com) here."),
            ("code span with asterisks", "The pattern `a*b*c` matters."),
            ("double-backtick code span", "Call ``dialog.showModal()`` first."),
            ("placeholder in a code span", "Run `release.sh <version>` to build."),
            ("autolink", "Open an issue at <https://example.com/issues> please."),
            ("mail autolink", "Write to <mailto:someone@example.com> first."),
            ("html comment", "<!-- a note\nover two lines -->\n\nProse after it."),
            ("thematic break", "Before the rule.\n\n---\n\nAfter the rule."),
            ("table", "Before.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nAfter."),
            ("fenced code", "Before.\n\n```sh\ngit clone x\n```\n\nAfter."),
            ("heading after frontmatter", "---\nname: x\n---\n# The title\n\nProse."),
            ("quote after frontmatter", "---\nname: x\n---\n> A quoted note.\n"),
            ("markdown image", "![A chart of something](chart.png)"),
            ("html image", '<img src="logo.png" alt="A project logo">'),
            ("nested list", "- Parent item.\n    - Child item.\n- Second parent."),
            ("wrapped list item", "- An item that\n  wraps over lines.\n- Another."),
            ("wrapped emphasis in a list", "- The **local maximum of\n  the curve** here.\n- B."),
        ],
    )
    def test_the_page_and_the_narration_see_the_same_sentences(self, name, source):
        assert page(source) == unframed(source), name

    def test_a_fenced_block_of_its_own_is_in_neither(self):
        source = "Before it.\n\n```sh\ngit clone x\n```\n\nAfter it.\n"
        assert page(source) == unframed(source) == ["Before it.", "After it."]

    def test_a_fence_indented_into_a_list_item_is_in_both(self):
        """The renderer shows it, so the narration says it -- that is the point.

        A fence indented four spaces under a list item is not a fence to this
        renderer: it comes out as an inline ``<code>`` holding ``sh git clone
        x``, visible on the page. The narration has to keep what the page
        shows, or the two stop agreeing about a construct that appears
        throughout this repo's own documentation. Fixing the *rendering* is a
        separate matter, in the source Markdown.
        """
        source = (
            "- An item with code:\n\n"
            "    ```sh\n    git clone x\n    ```\n\n"
            "- A second item.\n"
        )
        assert page(source) == unframed(source)
        assert any("git clone x" in sentence for sentence in page(source))

    def test_a_nested_list_item_belongs_to_itself_not_to_its_parent(self):
        blocks = _readalong.page_blocks(render("- Parent item.\n    - Child item.\n"))
        assert [block.visible for block in blocks] == ["Parent item.", "Child item."]


class TestQuotationFraming:
    """"Quote:" and "End quote." are spoken and never written."""

    def test_the_framing_cues_attach_to_the_quotation(self):
        source = "> A quoted line. And a second one.\n"
        cues = cues_for(source)
        blocks = _readalong.page_blocks(render(source))
        assignment = _readalong.align(
            blocks, cues, split=_narrate.split_sentences,
            opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
        )
        # Two sentences on the page, three cues in the audio: the closing
        # cue rides along with the sentence it follows.
        assert [len(sentence) for sentence in assignment[0]] == [1, 2]
        assert assignment[0][1][-1].text == _narrate.QUOTE_CLOSING

    def test_a_cue_with_no_sentence_gets_no_span(self):
        out = wrap("> A quoted line.\n")
        ids = re.findall(r'id="ra-(\d+)"', out)
        # Cue 0 is "Quote: A quoted line.", cue 1 is "End quote." -- and only
        # the first has anything on the page to wrap.
        assert ids == ["0"]

    def test_unframe_reports_the_page_text_or_nothing(self):
        unframe = _readalong._unframe
        opening, closing = _narrate.QUOTE_OPENING, _narrate.QUOTE_CLOSING
        assert unframe("Quote: A line.", opening, closing) == "A line."
        assert unframe("End quote.", opening, closing) is None
        assert unframe("Plain prose.", opening, closing) == "Plain prose."


# ── Refusal ────────────────────────────────────────────────────────────────


class TestItRefusesRatherThanGuess:
    """A read-along that is wrong by one is worse than none at all."""

    def test_a_missing_cue_names_the_sentence_that_lost_it(self):
        source = "One sentence. Two sentences.\n"
        cues = cues_for(source)[:1]
        with pytest.raises(_readalong.ReadAlongMismatch) as raised:
            _readalong.wrap_sentences(
                render(source), cues, split=_narrate.split_sentences,
                opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
            )
        assert "Two sentences." in str(raised.value)
        assert "nothing left in the audio" in str(raised.value)

    def test_a_surplus_cue_is_counted_not_ignored(self):
        source = "Only one sentence.\n"
        cues = [
            *cues_for(source),
            _readalong.VttCue(index=9, text="A sentence nobody wrote.",
                              start_seconds=9.0, end_seconds=10.0),
        ]
        with pytest.raises(_readalong.ReadAlongMismatch) as raised:
            _readalong.wrap_sentences(
                render(source), cues, split=_narrate.split_sentences,
                opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
            )
        assert "A sentence nobody wrote." in str(raised.value)

    def test_a_changed_sentence_names_both_sides(self):
        source = "The first sentence. The second.\n"
        cues = cues_for(source)
        altered = [
            cues[0],
            _readalong.VttCue(index=1, text="Something else entirely.",
                              start_seconds=cues[1].start_seconds,
                              end_seconds=cues[1].end_seconds),
        ]
        with pytest.raises(_readalong.ReadAlongMismatch) as raised:
            _readalong.wrap_sentences(
                render(source), altered, split=_narrate.split_sentences,
                opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
            )
        message = str(raised.value)
        assert "The second." in message and "Something else entirely." in message

    def test_markup_that_straddles_a_sentence_boundary_is_split_not_refused(self):
        """One ``<em>``, two sentences, and no single span that fits either.

        The page says ``A <em>sentence that. Ends</em> here.`` -- emphasis
        holding the end of one sentence and the start of the next. This was
        refused for as long as a sentence had to be one span; it is now
        wrapped in two that carry the same cue and light up together.

        The change is a capability, not a loosening. What the refusal
        protected against was a highlight that points at the wrong words, and
        the split points at exactly the right ones -- checked here by putting
        the page back together from the spans alone. ``test_readalong_existing_page``
        covers the case that forced it: a citation that ends mid-sentence.
        """
        body = "<p>A <em>sentence that. Ends</em> here.</p>"
        sentences = _readalong.page_sentences(body, split=_narrate.split_sentences)
        cues = [
            _readalong.VttCue(index=i, text=text, start_seconds=i, end_seconds=i + 1)
            for i, text in enumerate(sentences)
        ]
        out = _readalong.wrap_sentences(
            body, cues, split=_narrate.split_sentences,
            opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
        )
        # One id per sentence, several spans for the one that needed them.
        assert len(SPAN_RE.findall(out)) == len(sentences)
        assert out.count('class="ra-s"') > len(sentences)
        # Every word is inside some span, and the emphasis is still emphasis.
        inside = " ".join(
            re.sub(r"<[^>]+>", "", match)
            for match in re.findall(r'<span class="ra-s"[^>]*>(.*?)</span>', out, re.S)
        )
        assert " ".join(inside.split()) == "A sentence that. Ends here."
        assert "<em>" in out and "</em>" in out

    def test_a_file_that_is_not_webvtt_is_rejected_on_sight(self):
        with pytest.raises(_readalong.ReadAlongMismatch, match="WEBVTT"):
            _readalong.parse_vtt('{"cues": []}')


# ── Markup ─────────────────────────────────────────────────────────────────


#: The opening tag of a wrapped sentence. Matches the span that carries the
#: *id*, so counting these counts sentences: a sentence that had to be split
#: across several spans still has exactly one id, on the run it starts at.
#: ``data-ra-cue`` is optional because it is written only when a sentence
#: needed more than one span.
SPAN_RE = re.compile(
    r'<span class="ra-s" id="ra-\d+"(?: data-ra-cue="\d+")? data-start="[\d.]+">'
)


class TestWrapping:
    """What the spans do to the page: as little as possible."""

    SOURCE = (
        "# A narrated post\n\n"
        "The opening paragraph. It carries *two* sentences.\n\n"
        "- A point with `code` in it.\n"
        "- A second point.\n\n"
        "> A quotation worth hearing.\n\n"
        "![A chart of something](chart.png)\n\n"
        "A closing line with [a link](https://example.com) in it.\n"
    )

    def test_the_page_is_unchanged_apart_from_its_spans(self):
        """The strongest property available: strip the spans, get the page back.

        Markup is rebuilt from a parse rather than patched by offset, so this
        is the check that the rebuild is faithful -- an attribute reordered or
        an entity resolved would show up here and nowhere else.
        """
        out = wrap(self.SOURCE)
        stripped = SPAN_RE.sub("", out).replace("</span>", "")
        assert stripped == render(self.SOURCE)

    def test_every_sentence_is_wrapped_once(self):
        out = wrap(self.SOURCE)
        assert len(SPAN_RE.findall(out)) == len(page(self.SOURCE))

    def test_inline_markup_survives_inside_the_span(self):
        out = wrap(self.SOURCE)
        assert "<em>two</em>" in out
        assert "<code>code</code>" in out
        assert '<a href="https://example.com">a link</a>' in out

    def test_the_span_id_is_the_cue_id_so_the_browser_can_find_it(self):
        out = wrap("One. Two.\n")
        assert 'id="ra-0"' in out and 'id="ra-1"' in out

    def test_data_start_matches_the_cue_the_span_belongs_to(self):
        source = "# A title\n\nA paragraph.\n"
        out = wrap(source)
        starts = [float(value) for value in re.findall(r'data-start="([\d.]+)"', out)]
        assert starts == [round(cue.start_seconds, 3) for cue in cues_for(source)]

    def test_a_picture_is_wrapped_whole_so_it_highlights_while_described(self):
        out = wrap("![A chart. With two sentences.](chart.png)")
        # Two cues describe it, one span holds it: a picture cannot be cut in
        # half, and the highlight belongs on the picture either way.
        assert len(SPAN_RE.findall(out)) == 1
        assert "<img" in out

    def test_a_sentence_that_opens_with_markup_keeps_it_inside_the_span(self):
        body = "<p><strong>Do not</strong> commit this.</p>"
        cues = [_readalong.VttCue(index=0, text="Do not commit this.",
                                  start_seconds=0.0, end_seconds=1.0)]
        out = _readalong.wrap_sentences(
            body, cues, split=_narrate.split_sentences,
            opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
        )
        assert "<span" in out.split("<strong>")[0]

    def test_a_heading_that_is_entirely_a_link_is_wrapped_inside_it(self):
        body = '<h2 id="x"><a href="y.md">Approach: the ideas</a></h2>'
        cues = [_readalong.VttCue(index=0, text="Approach: the ideas",
                                  start_seconds=0.0, end_seconds=1.0)]
        out = _readalong.wrap_sentences(
            body, cues, split=_narrate.split_sentences,
            opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
        )
        assert out.count("<span") == 1
        assert SPAN_RE.sub("", out).replace("</span>", "") == body

    def test_a_hard_line_break_does_not_push_the_rest_of_the_block_deeper(self):
        """``<br>`` has no closing tag, so it must not count as nesting.

        It did, once: every piece after a line break was recorded one level
        deeper, and the crossing check then refused sentences that crossed
        nothing. A hard break inside a paragraph is ordinary prose.
        """
        body = "<p>Line one.<br>Line two.</p>"
        cues = [
            _readalong.VttCue(index=0, text="Line one.", start_seconds=0.0, end_seconds=1.0),
            _readalong.VttCue(index=1, text="Line two.", start_seconds=1.0, end_seconds=2.0),
        ]
        out = _readalong.wrap_sentences(
            body, cues, split=_narrate.split_sentences,
            opening=_narrate.QUOTE_OPENING, closing=_narrate.QUOTE_CLOSING,
        )
        assert out.count("<span") == 2


class TestVttRoundTrip:
    """Cues survive the file they are written to."""

    def test_what_the_narration_wrote_is_what_the_page_reads(self):
        cues = [
            _narrate.Cue(index=0, text="First sentence.", start_seconds=1.5, end_seconds=3.25),
            _narrate.Cue(index=7, text="Later sentence.", start_seconds=61.0, end_seconds=62.5),
        ]
        back = _readalong.parse_vtt(_narrate.cues_to_vtt(cues))
        assert [(c.index, c.text) for c in back] == [(0, "First sentence."), (7, "Later sentence.")]
        assert [(c.start_seconds, c.end_seconds) for c in back] == [(1.5, 3.25), (61.0, 62.5)]

    def test_a_short_timestamp_is_read_as_minutes_and_seconds(self):
        cues = _readalong.parse_vtt("WEBVTT\n\n0\n01:30.000 --> 01:31.500\nA line.\n")
        assert (cues[0].start_seconds, cues[0].end_seconds) == (90.0, 91.5)

    def test_the_spoken_length_is_the_end_of_the_last_cue(self):
        text = _narrate.cues_to_vtt([
            _narrate.Cue(index=0, text="A.", start_seconds=0.0, end_seconds=2.0),
            _narrate.Cue(index=1, text="B.", start_seconds=2.5, end_seconds=9.75),
        ])
        assert _readalong.spoken_seconds(text) == 9.75
        assert _readalong.spoken_seconds("WEBVTT\n") == 0.0


class TestPlayer:
    """The audio element, and what it declares about its file."""

    def test_the_source_type_comes_from_the_extension(self):
        for name, declared in [("a.wav", "audio/wav"), ("a.mp3", "audio/mpeg"),
                               ("a.m4a", "audio/mp4"), ("a.flac", "audio/flac")]:
            out = _readalong.player_html(audio_src=name, vtt_src="a.vtt",
                                         label="Listen", lang="en")
            assert f'type="{declared}"' in out

    def test_an_unknown_extension_raises_rather_than_being_guessed(self):
        with pytest.raises(_readalong.ReadAlongMismatch, match="no audio type known"):
            _readalong.player_html(audio_src="a.aiff", vtt_src="a.vtt",
                                   label="Listen", lang="en")

    def test_the_cue_track_is_metadata_not_captions(self):
        out = _readalong.player_html(audio_src="a.wav", vtt_src="a.vtt",
                                     label="Listen", lang="en")
        assert 'kind="metadata"' in out
        assert 'kind="captions"' not in out

    def test_the_player_has_an_accessible_name(self):
        out = _readalong.player_html(audio_src="a.wav", vtt_src="a.vtt",
                                     label="Listen to this page", lang="en")
        assert 'aria-labelledby="ra-label"' in out
        assert "Listen to this page" in out

    def test_the_assets_that_drive_the_highlight_are_shipped(self):
        for name in ("readalong.css", "readalong.js"):
            assert (_readalong.assets_dir() / name).is_file()


class TestReadingMeta:
    """Two durations of different kinds, shown together on purpose."""

    def test_reading_is_estimated_and_listening_is_measured(self):
        out = _readalong.reading_meta_html(words=400, spoken_seconds=180.0, lang="en")
        assert "2 min read" in out      # 400 words at 200 wpm
        assert "3 min listen" in out    # the narration's own length
        assert 'datetime="PT2M"' in out and 'datetime="PT3M"' in out

    def test_it_never_claims_zero_minutes(self):
        out = _readalong.reading_meta_html(words=3, spoken_seconds=2.0, lang="en")
        assert "1 min read" in out and "1 min listen" in out

    def test_french_is_french(self):
        out = _readalong.reading_meta_html(words=400, spoken_seconds=180.0, lang="fr")
        assert "2 min de lecture" in out
        assert "3 min d" in out  # d’écoute, with a typographic apostrophe
        assert "min read" not in out

    def test_an_unknown_language_is_visible_rather_than_served_english(self):
        with pytest.raises(_readalong.ReadAlongMismatch, match="no reading-time wording"):
            _readalong.reading_meta_html(words=100, spoken_seconds=30.0, lang="de")

    def test_the_word_count_skips_what_the_narration_skipped(self):
        source = "Four words right here.\n\n```sh\nnot counted at all\n```\n"
        assert _readalong.page_words(render(source)) == ["Four", "words", "right", "here."]
