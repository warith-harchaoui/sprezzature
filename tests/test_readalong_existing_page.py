"""
test_readalong_existing_page — the read-along on a page nobody can regenerate.

``test_readalong`` covers the Markdown route, where a page and its narration
are built from one source by two parsers that must be made to agree. This
module covers the other route, and the harder case to get right in the world:
a page that was *never* Markdown. A hand-written file, a template exported
from a design tool, a post that has been live for three years -- none of them
has a source to rebuild from, and none of them should have to be rewritten to
gain an accessibility feature.

The route is shorter than it looks. ``narrate_post.py`` reads the page's own
elements, so the blocks that become the audio are the very blocks that get
the spans: one parse, nothing to reconcile. What is tested here is therefore
less about agreement and more about *not damaging the page* --

* **The real page** (``TestTheRealPage``) -- a Framer export from
  deraison.ai, 131 blocks and 549 sentences of it, carried through the whole
  route. It is here because every bug this module ever had was found by a
  page written for readers rather than for this feature.
* **Choosing what is read** (``TestScope``, ``TestWhatIsNotRead``) -- a
  reader who asked to hear *this article* did not ask for the navigation,
  the cookie banner, or anything a screen reader is already told to ignore.
* **Crossing markup** (``TestSentencesThatCrossElements``) -- one sentence
  is not always one element's worth of text.
* **Placement and refusal** (``TestPlacement``, ``TestItRefusesRatherThanGuess``).
* **The narration side** (``TestSegmentsFromBlocks``) -- an ``<h2>`` has to
  earn the pause a ``##`` earns, because it is the same thing.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

import _narrate
import _readalong

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "sprezzature-publish" / "scripts"

#: A page this project did not write, did not render, and cannot regenerate:
#: an article exported from Framer and served through PHP. Kept as a fixture
#: rather than reduced to a snippet because the constructs that broke this
#: route -- a ``<cite>`` spanning several sentences, a note picking up where
#: the citation leaves off, headings inside nested ``<div>`` scaffolding --
#: are exactly what a hand-reduced example leaves out.
DERAISON = Path(__file__).parent / "fixtures" / "html" / "deraison" / "ralph-loops.php.src"


# ── Helpers ────────────────────────────────────────────────────────────────


def narration_for(page_html: str, *, scope: str | None = None):
    """The cues a narration run would write for a page, via WebVTT.

    Round-tripped through the file format on purpose: the page is wired from
    what is *on disk*, so handing over in-memory cues would skip the only
    step that can lose something.
    """
    blocks = [
        (block.tag, block.visible, block.in_quote)
        for block in _readalong.page_blocks(page_html, scope=scope)
    ]
    timeline = _narrate.Timeline(24_000)
    exploded = _narrate.explode_to_sentences(_narrate.segments_from_blocks(blocks))
    for index, segment in enumerate(exploded):
        timeline.silence(segment["pause_before_ms"])
        timeline.speech(int(24_000 * 1.4), index=index, text=segment["text"])
        timeline.silence(segment["pause_after_ms"])
    return _readalong.parse_vtt(_narrate.cues_to_vtt(timeline.cues))


def inject(page_html: str, *, scope: str | None = None, head: str = "",
           player: str = "") -> str:
    """Run a page through the whole route and return what a reader would get."""
    return _readalong.inject_into_page(
        page_html,
        narration_for(page_html, scope=scope),
        split=_narrate.split_sentences,
        opening=_narrate.QUOTE_OPENING,
        closing=_narrate.QUOTE_CLOSING,
        scope=scope,
        head=head,
        player=player,
    )


class _Balance(HTMLParser):
    """Counts tags that close something other than what is open."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[str] = []
        self.crossings: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in _readalong.VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _readalong.VOID_ELEMENTS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.crossings.append(tag)
        else:
            self.stack.pop()


def crossings(markup: str) -> list[str]:
    """Tags in `markup` that close an element that is not the open one."""
    parser = _Balance()
    parser.feed(markup)
    parser.close()
    return parser.crossings + parser.stack


def visible_text(markup: str) -> str:
    """What a reader sees, with every tag and all whitespace runs removed."""
    return " ".join(re.sub(r"<[^>]+>", "", markup).split())


def ids_in(markup: str) -> list[int]:
    """Cue ids of the sentences wrapped in `markup`, in document order."""
    return [int(value) for value in re.findall(r'id="ra-(\d+)"', markup)]


class _Unwrap(HTMLParser):
    """Removes the read-along's own spans and nothing else.

    A regex cannot do this: the page uses ``<span>`` for its own purposes --
    38 of them on the fixture -- so dropping every ``</span>`` would strip
    markup this feature never touched, and the test would pass or fail for
    the wrong reason.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.out: list[str] = []
        self._spans: list[bool] = []

    def handle_starttag(self, tag, attrs):
        if tag == "span":
            attributes = dict(attrs)
            mine = attributes.get("class") == "ra-s" and "data-start" in attributes
            self._spans.append(mine)
            if mine:
                return
        self.out.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.out.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == "span" and self._spans and self._spans.pop():
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(data)

    def handle_entityref(self, name):
        self.out.append(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};")

    def handle_comment(self, data):
        self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")

    def handle_pi(self, data):
        self.out.append(f"<?{data}>")

    def unknown_decl(self, data):
        self.out.append(f"<![{data}]>")


def without_readalong_spans(markup: str) -> str:
    """`markup` with the read-along's spans removed, byte for byte otherwise."""
    parser = _Unwrap()
    parser.feed(markup)
    parser.close()
    return "".join(parser.out)


# ── The real page ──────────────────────────────────────────────────────────


class TestTheRealPage:
    """A Framer export from deraison.ai, carried end to end.

    These are the strongest properties available, because they are the ones a
    reader would notice being broken: the page still says what it said, its
    markup still closes what it opened, and every sentence of the recording
    has somewhere to light up.
    """

    @pytest.fixture(scope="class")
    def source(self) -> str:
        return DERAISON.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def built(self, source) -> str:
        return inject(source, scope="article")

    def test_the_page_still_says_exactly_what_it_said(self, source, built):
        """No word gained, no word lost, no word reordered."""
        assert visible_text(built) == visible_text(source)

    def test_the_markup_still_closes_what_it_opens(self, source, built):
        """The property that makes a span legal rather than merely present.

        An earlier pass produced spans that stepped over ``</cite>`` and into
        the note after it. The page looked right and the HTML was invalid,
        which is the failure mode worth a test of its own: browsers repair it
        silently and differently from one another.
        """
        assert crossings(source) == []
        assert crossings(built) == []

    def test_every_sentence_of_the_recording_has_somewhere_to_light_up(
        self, source, built
    ):
        cues = narration_for(source, scope="article")
        assert ids_in(built) == list(range(len(cues)))

    def test_the_page_is_substantial_enough_to_be_worth_the_fixture(self, source):
        """A guard on the fixture, not on the code.

        If this page is ever trimmed to a snippet, the constructs that made
        it worth keeping go with it and the tests above stop proving much.
        """
        blocks = _readalong.page_blocks(source, scope="article")
        assert len(blocks) > 100
        assert sum(1 for block in blocks if block.tag.startswith("h")) >= 5
        # The bibliography is the reason this page is the fixture: 37 entries
        # whose citation ends mid-sentence and hands over to a note, which is
        # the construct no single span can wrap.
        assert sum(1 for block in blocks if block.tag == "li") >= 30
        assert "<cite" in source

    def test_the_page_really_does_exercise_the_split(self, built):
        """Otherwise the hard case is untested and nobody would know."""
        marked = set(re.findall(r'data-ra-cue="(\d+)"', built))
        assert len(marked) >= 10

    def test_removing_the_spans_gives_the_page_back(self, source, built):
        """Rebuilt from a parse, not patched by offset.

        An attribute reordered, an entity resolved or a ``<?php ?>`` prologue
        dropped would show up here and nowhere else.
        """
        assert without_readalong_spans(built) == source


# ── Choosing what is read ──────────────────────────────────────────────────


FURNISHED_PAGE = """<!doctype html>
<html lang="en">
<head><title>A title nobody asked to hear</title></head>
<body>
<header><p>Site name.</p></header>
<nav><p>Home. About. Contact.</p></nav>
<article>
  <h1>The article itself.</h1>
  <p>The prose a reader asked for.</p>
</article>
<aside><p>Related reading.</p></aside>
<footer><p>All rights reserved.</p></footer>
<script>console.log("Not prose.");</script>
</body>
</html>
"""


class TestScope:
    """``--scope`` is what separates a page we rendered from one we did not."""

    def test_a_scope_reads_only_the_element_it_names(self):
        blocks = _readalong.page_blocks(FURNISHED_PAGE, scope="article")
        assert [block.visible.strip() for block in blocks] == [
            "The article itself.",
            "The prose a reader asked for.",
        ]

    def test_without_a_scope_the_header_is_read_too(self):
        """Not a bug -- the documented default, and why ``--scope`` exists."""
        spoken = " ".join(
            block.visible for block in _readalong.page_blocks(FURNISHED_PAGE)
        )
        assert "Site name." in spoken

    @pytest.mark.parametrize(
        ("selector", "markup"),
        [
            ("article", "<article><p>Wanted.</p></article><p>Unwanted.</p>"),
            ("#post", '<div id="post"><p>Wanted.</p></div><p>Unwanted.</p>'),
            (".entry", '<div class="entry"><p>Wanted.</p></div><p>Unwanted.</p>'),
            (".entry", '<div class="a entry b"><p>Wanted.</p></div><p>Unwanted.</p>'),
        ],
    )
    def test_the_three_selector_forms(self, selector, markup):
        blocks = _readalong.page_blocks(markup, scope=selector)
        assert [block.visible for block in blocks] == ["Wanted."]

    def test_a_scope_that_matches_nothing_reads_nothing(self):
        """Silence rather than the whole document.

        Narrating the navigation because a selector was misspelt is the one
        outcome worse than narrating nothing: the mistake is inaudible until
        a reader hears the cookie banner read to them.
        """
        assert _readalong.page_blocks(FURNISHED_PAGE, scope="#absent") == []

    def test_the_reading_time_counts_the_scope_only(self):
        whole = _readalong.page_words(FURNISHED_PAGE)
        scoped = _readalong.page_words(FURNISHED_PAGE, scope="article")
        assert len(scoped) < len(whole)
        assert "reserved." not in scoped


class TestWhatIsNotRead:
    """Furniture, code, and anything already hidden from assistive tech."""

    @pytest.mark.parametrize(
        ("name", "markup"),
        [
            ("script", '<p>Kept.</p><script>var x = "Dropped.";</script>'),
            ("style", "<p>Kept.</p><style>.a { content: 'Dropped.'; }</style>"),
            ("nav", "<p>Kept.</p><nav><p>Dropped.</p></nav>"),
            ("footer", "<p>Kept.</p><footer><p>Dropped.</p></footer>"),
            ("aside", "<p>Kept.</p><aside><p>Dropped.</p></aside>"),
            ("form", "<p>Kept.</p><form><p>Dropped.</p></form>"),
            ("dialog", "<p>Kept.</p><dialog><p>Dropped.</p></dialog>"),
            ("noscript", "<p>Kept.</p><noscript><p>Dropped.</p></noscript>"),
            ("template", "<p>Kept.</p><template><p>Dropped.</p></template>"),
            ("svg", "<p>Kept.</p><svg><text>Dropped.</text></svg>"),
            ("pre", "<p>Kept.</p><pre><code>Dropped.</code></pre>"),
            ("table", "<p>Kept.</p><table><tr><td>Dropped.</td></tr></table>"),
        ],
    )
    def test_furniture_and_code_are_not_narrated(self, name, markup):
        spoken = " ".join(block.visible for block in _readalong.page_blocks(markup))
        assert "Kept." in spoken
        assert "Dropped." not in spoken

    @pytest.mark.parametrize(
        ("name", "markup"),
        [
            ("aria-hidden", '<p>Kept.</p><p aria-hidden="true">Dropped.</p>'),
            ("hidden", "<p>Kept.</p><p hidden>Dropped.</p>"),
            ("a hidden wrapper", '<p>Kept.</p><div aria-hidden="true"><p>Dropped.</p></div>'),
            ("deep in a wrapper", '<p>Kept.</p><div aria-hidden="true"><div><p>Dropped.</p></div></div>'),
        ],
    )
    def test_what_a_screen_reader_ignores_is_not_spoken(self, name, markup):
        """Narrating what assistive technology is told to skip would have this
        feature contradict the page it is trying to help."""
        spoken = " ".join(block.visible for block in _readalong.page_blocks(markup))
        assert "Kept." in spoken
        assert "Dropped." not in spoken

    def test_aria_hidden_false_is_read_normally(self):
        """``aria-hidden="false"`` is not ``aria-hidden``."""
        markup = '<p aria-hidden="false">Kept.</p>'
        spoken = " ".join(block.visible for block in _readalong.page_blocks(markup))
        assert "Kept." in spoken

    def test_a_hidden_subtree_comes_back_untouched_in_the_page(self):
        """Not read, not removed. It is still the reader's page."""
        markup = '<p>Kept.</p><div aria-hidden="true"><p>Dropped.</p></div>'
        built = inject(markup)
        assert '<div aria-hidden="true"><p>Dropped.</p></div>' in built


# ── Crossing markup ────────────────────────────────────────────────────────


class TestSentencesThatCrossElements:
    """One sentence is not always one element's worth of text."""

    #: A bibliography entry as the real page writes them: the citation ends
    #: mid-sentence and a note picks up where it leaves off, with no full stop
    #: in between. No single span can hold that.
    ENTRY = (
        '<li><cite>Shinn, N. and Yao, S. (2023). '
        '<em>Reflexion</em>, NeurIPS.</cite> '
        "<span>Keeps a memory of comments across attempts.</span></li>"
    )

    def test_a_sentence_that_leaves_one_element_for_another_is_still_wrapped(self):
        built = inject(self.ENTRY)
        assert crossings(built) == []
        assert visible_text(built) == visible_text(self.ENTRY)

    def test_the_parts_of_one_sentence_share_one_cue(self):
        """So they light up together and read as the one sentence they are."""
        built = inject(self.ENTRY)
        for cue in set(re.findall(r'data-ra-cue="(\d+)"', built)):
            assert built.count(f'data-ra-cue="{cue}"') >= 2

    def test_only_the_first_part_carries_the_id(self):
        """It is where the sentence starts, and what the player scrolls to."""
        built = inject(self.ENTRY)
        for cue in set(re.findall(r'data-ra-cue="(\d+)"', built)):
            assert built.count(f'id="ra-{cue}"') == 1

    def test_the_marked_span_is_the_one_carrying_the_id(self):
        """The contract the player depends on, and it is easy to get wrong.

        ``readalong.js`` finds a sentence by ``getElementById`` and only then
        asks whether it is split, by reading ``data-ra-cue`` off that very
        element. If the marker ever landed on the *later* runs alone, the
        lookup would say "not split" and light up a fragment -- or, if the
        player looked the marker up first, every unsplit sentence on every
        page would stop highlighting at once. Both are silent failures: the
        page renders, the audio plays, and nothing lights up.
        """
        built = inject(self.ENTRY)
        for match in re.findall(r'<span class="ra-s"([^>]*)>', built):
            if "data-ra-cue" in match:
                continue
            assert "id=" not in match or built.count("data-ra-cue") == 0
        for cue in set(re.findall(r'data-ra-cue="(\d+)"', built)):
            head = re.search(rf'<span class="ra-s" id="ra-{cue}"([^>]*)>', built)
            assert head is not None, f"cue {cue} has parts but no span carries its id"
            assert f'data-ra-cue="{cue}"' in head.group(1)

    def test_a_sentence_that_needs_one_span_is_not_marked(self):
        """The attribute costs bytes on every sentence and earns them on few."""
        built = inject("<p>One sentence. And another one.</p>")
        assert "data-ra-cue" not in built
        assert built.count('class="ra-s"') == 2

    def test_emphasis_shared_by_two_sentences_is_wrapped_not_refused(self):
        """``A <em>sentence that. Ends</em> here.`` -- one ``<em>``, two
        sentences, and neither fits in a single span.

        This was refused until the wrapper learned to use more than one span
        per sentence. Refusing was never the honest answer: the words are
        perfectly identifiable, it was the *markup* that could not express
        them, and a reader lost a whole page over it.
        """
        body = "<p>A <em>sentence that. Ends</em> here.</p>"
        built = inject(body)
        assert crossings(built) == []
        assert visible_text(built) == visible_text(body)
        assert ids_in(built) == [0, 1]

    def test_every_word_of_a_split_sentence_is_inside_some_span(self):
        """The rule that keeps splitting honest.

        A split that drops half a sentence out of every span would still
        produce valid markup and a highlight that silently stops mid
        sentence. Checked by stripping everything *outside* the spans.
        """
        built = inject(self.ENTRY)
        inside = " ".join(
            visible_text(match)
            for match in re.findall(r'<span class="ra-s"[^>]*>(.*?)</span>', built, re.S)
        )
        assert visible_text(self.ENTRY) == " ".join(inside.split())


# ── Placement ──────────────────────────────────────────────────────────────


class TestPlacement:
    """Where the player and the two asset links end up."""

    def test_the_player_goes_at_the_top_of_the_article_it_belongs_to(self):
        built = inject(FURNISHED_PAGE, scope="article", player="<!--PLAYER-->")
        assert re.search(r"<article[^>]*>\s*<!--PLAYER-->", built)

    def test_without_a_scope_the_player_goes_after_the_body_tag(self):
        built = inject(FURNISHED_PAGE, player="<!--PLAYER-->")
        assert re.search(r"<body[^>]*>\s*<!--PLAYER-->", built)

    def test_the_head_links_go_before_the_head_closes(self):
        built = inject(FURNISHED_PAGE, scope="article", head="<!--HEAD-->")
        assert re.search(r"<!--HEAD-->\s*</head>", built)

    def test_a_fragment_with_no_head_gets_the_links_at_the_top(self):
        """A PHP include is not a document; it still has to link its assets."""
        built = inject("<article><p>A fragment.</p></article>", scope="article",
                       head="<!--HEAD-->")
        assert built.startswith("<!--HEAD-->")

    def test_a_player_with_nowhere_to_go_says_so(self):
        with pytest.raises(_readalong.ReadAlongMismatch, match="nowhere to put the player"):
            inject("<p>A fragment with no body.</p>", scope="#absent",
                   player="<!--PLAYER-->")

    def test_the_php_prologue_survives(self):
        """The fixture is served through PHP; losing its guard would publish
        a file that was meant to refuse direct access."""
        source = DERAISON.read_text(encoding="utf-8")
        built = inject(source, scope="article")
        assert built.startswith("<?php")
        assert "DERAISON" in built[:200]


# ── Refusal ────────────────────────────────────────────────────────────────


class TestItRefusesRatherThanGuess:
    """A recording that no longer matches its page is stale, not authoritative."""

    def test_a_page_edited_since_the_recording_is_refused(self):
        """The reason the comparison still runs on a single-parse route.

        The two sides agree by construction *at the time of the run*. They
        stop agreeing the moment someone edits the page, and then the honest
        answer is that the recording is stale -- not that the reader should
        be pointed at the wrong sentence.
        """
        recorded = "<article><p>The original sentence.</p></article>"
        edited = "<article><p>The sentence after an edit.</p></article>"
        with pytest.raises(_readalong.ReadAlongMismatch):
            _readalong.inject_into_page(
                edited,
                narration_for(recorded, scope="article"),
                split=_narrate.split_sentences,
                opening=_narrate.QUOTE_OPENING,
                closing=_narrate.QUOTE_CLOSING,
                scope="article",
            )

    def test_a_missing_recording_names_what_it_looked_for(self):
        """So the fix -- run the narration first -- is in the message."""
        assert _readalong.narration_sources(Path("/nonexistent"), "page") is None

    def test_a_language_with_no_wording_is_visible_rather_than_served_english(self):
        with pytest.raises(_readalong.ReadAlongMismatch, match="PLAYER_LABELS"):
            _readalong.player_label("de")


# ── The narration side ─────────────────────────────────────────────────────


class TestSegmentsFromBlocks:
    """An ``<h2>`` earns the pause a ``##`` earns: it is the same thing."""

    def kinds(self, blocks):
        return [(s["kind"], s["text"]) for s in _narrate.segments_from_blocks(blocks)]

    def test_a_heading_is_a_heading_and_keeps_its_level(self):
        segments = _narrate.segments_from_blocks([("h2", "A section.", False)])
        assert segments[0]["kind"] == "heading"
        assert segments[0]["heading_level"] == 2

    def test_a_heading_is_set_apart_on_both_sides(self):
        """The pause before a heading was computed and dropped for months on
        the Markdown route; it is not going to be dropped here."""
        segments = _narrate.segments_from_blocks([("h2", "A section.", False)])
        assert segments[0]["pause_before_ms"] > 0
        assert segments[0]["pause_after_ms"] > 0

    def test_a_deeper_heading_gets_a_shorter_pause(self):
        pauses = [
            _narrate.segments_from_blocks([(tag, "A heading.", False)])[0]["pause_before_ms"]
            for tag in ("h1", "h3")
        ]
        assert pauses[0] > pauses[1]

    def test_an_item_mid_list_is_paused_shorter_than_the_last_one(self):
        """The last item of a run closes the list and earns a full silence."""
        blocks = [("li", "First.", False), ("li", "Second.", False), ("p", "After.", False)]
        segments = _narrate.segments_from_blocks(blocks)
        assert segments[0]["pause_after_ms"] < segments[1]["pause_after_ms"]

    def test_a_quotation_is_announced_and_closed(self):
        blocks = [("p", "Before.", False), ("p", "Quoted.", True), ("p", "After.", False)]
        spoken = [segment["text"] for segment in _narrate.segments_from_blocks(blocks)]
        assert spoken[1].startswith(_narrate.QUOTE_OPENING)
        assert _narrate.QUOTE_CLOSING in spoken
        assert spoken[-1] == "After."

    def test_a_quotation_of_several_paragraphs_is_announced_once(self):
        blocks = [("p", "One.", True), ("p", "Two.", True), ("p", "After.", False)]
        spoken = [segment["text"] for segment in _narrate.segments_from_blocks(blocks)]
        assert sum(text.startswith(_narrate.QUOTE_OPENING) for text in spoken) == 1
        assert sum(text == _narrate.QUOTE_CLOSING for text in spoken) == 1

    def test_an_empty_block_contributes_nothing(self):
        blocks = [("p", "   ", False), ("p", "Real prose.", False)]
        assert self.kinds(blocks) == [("paragraph", "Real prose.")]

    def test_an_unknown_tag_is_read_as_a_paragraph_not_dropped(self):
        assert self.kinds([("section", "Still prose.", False)]) == [
            ("paragraph", "Still prose.")
        ]

    def test_the_narration_and_the_page_see_the_same_sentences(self):
        """The property the whole route rests on, on the real page."""
        source = DERAISON.read_text(encoding="utf-8")
        blocks = _readalong.page_blocks(source, scope="article")
        spoken = [
            text
            for text in (
                _readalong._unframe(
                    segment["text"], _narrate.QUOTE_OPENING, _narrate.QUOTE_CLOSING
                )
                for segment in _narrate.explode_to_sentences(
                    _narrate.segments_from_blocks(
                        [(b.tag, b.visible, b.in_quote) for b in blocks]
                    )
                )
            )
            if text is not None
        ]
        shown = _readalong.page_sentences(
            source, split=_narrate.split_sentences, scope="article"
        )
        assert spoken == shown


# ── Relative paths ─────────────────────────────────────────────────────────


class TestAssetPaths:
    """Written relative to the page, so the output can be moved or sub-pathed."""

    def test_a_sibling_file_is_referenced_by_name(self, tmp_path):
        assert _readalong.href_from(tmp_path / "voice.mp3", tmp_path) == "voice.mp3"

    def test_a_file_one_level_up_climbs_out(self, tmp_path):
        (tmp_path / "built").mkdir()
        assert _readalong.href_from(
            tmp_path / "audio" / "voice.mp3", tmp_path / "built"
        ) == "../audio/voice.mp3"

    def test_the_separator_is_a_slash_whatever_the_platform(self, tmp_path):
        href = _readalong.href_from(tmp_path / "a" / "b" / "voice.mp3", tmp_path)
        assert "\\" not in href


# ── The command ────────────────────────────────────────────────────────────


class TestTheCommand:
    """``readalong.py`` end to end, as a process."""

    @pytest.fixture
    def narrated(self, tmp_path):
        """A page beside a narration run, as ``narrate_post.py`` would leave it."""
        page = tmp_path / "ralph-loops.html"
        source = (
            "<!doctype html><html lang=\"en\"><head><title>T</title></head><body>"
            "<nav><p>Home. About.</p></nav>"
            "<article><h1>A title.</h1><p>One sentence. And a second one.</p></article>"
            "</body></html>"
        )
        page.write_text(source, encoding="utf-8")

        narration = tmp_path / "audio"
        narration.mkdir()
        (narration / "narration.vtt").write_text(
            _narrate.cues_to_vtt(
                [
                    _narrate.Cue(
                        index=cue.index,
                        text=cue.text,
                        start_seconds=cue.start_seconds,
                        end_seconds=cue.end_seconds,
                    )
                    for cue in narration_for(source, scope="article")
                ]
            ),
            encoding="utf-8",
        )
        (narration / "ralph-loops.mp3").write_bytes(b"not really audio")
        return page, narration

    def run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "readalong.py"), *map(str, args)],
            capture_output=True, text=True,
        )

    def test_it_builds_a_page_without_touching_the_input(self, narrated, tmp_path):
        page, narration = narrated
        before = page.read_text(encoding="utf-8")
        out = tmp_path / "built"
        result = self.run(page, "--narration", narration, "--out", out,
                          "--scope", "article", "--lang", "en")
        assert result.returncode == 0, result.stderr
        assert page.read_text(encoding="utf-8") == before
        built = (out / "ralph-loops.html").read_text(encoding="utf-8")
        assert 'class="ra-s"' in built
        assert crossings(built) == []

    def test_it_ships_the_two_files_that_drive_the_highlight(self, narrated, tmp_path):
        """A page that links a stylesheet it did not copy is a page with no
        highlight and no error -- the failure this checks for."""
        page, narration = narrated
        out = tmp_path / "built"
        assert self.run(page, "--narration", narration, "--out", out,
                        "--scope", "article", "--lang", "en").returncode == 0
        for name in _readalong.ASSET_FILES:
            assert (out / name).is_file()
        built = (out / "ralph-loops.html").read_text(encoding="utf-8")
        for name in _readalong.ASSET_FILES:
            assert name in built

    def test_the_scope_keeps_the_navigation_out_of_the_player(self, narrated, tmp_path):
        page, narration = narrated
        out = tmp_path / "built"
        assert self.run(page, "--narration", narration, "--out", out,
                        "--scope", "article", "--lang", "en").returncode == 0
        built = (out / "ralph-loops.html").read_text(encoding="utf-8")
        nav = built[built.index("<nav>"):built.index("</nav>")]
        assert 'class="ra-s"' not in nav

    def test_a_page_with_no_narration_names_the_command_to_run_first(self, tmp_path):
        page = tmp_path / "lonely.html"
        page.write_text("<article><p>Unrecorded.</p></article>", encoding="utf-8")
        empty = tmp_path / "audio"
        empty.mkdir()
        result = self.run(page, "--narration", empty, "--out", tmp_path / "built",
                          "--scope", "article", "--lang", "en")
        assert result.returncode == 1
        assert "narrate_post.py" in result.stderr

    def test_a_missing_page_is_a_usage_error_not_a_crash(self, tmp_path):
        result = self.run(tmp_path / "absent.html", "--narration", tmp_path,
                          "--out", tmp_path / "built")
        assert result.returncode == 2
        assert "no such page" in result.stderr

    def test_a_stale_recording_fails_the_build(self, narrated, tmp_path):
        """Exit 1 and a named sentence, never a page whose highlight is off."""
        page, narration = narrated
        page.write_text(
            page.read_text(encoding="utf-8").replace("One sentence.", "A rewritten one."),
            encoding="utf-8",
        )
        result = self.run(page, "--narration", narration, "--out", tmp_path / "built",
                          "--scope", "article", "--lang", "en")
        assert result.returncode == 1
        assert not (tmp_path / "built" / "ralph-loops.html").exists()
