#!/usr/bin/env python3
"""
readalong — add a sentence-by-sentence read-along to a page that already exists.

The companion to ``md_to_html.py --readalong``, for the case that matters
more: a page nobody can regenerate. A hand-written HTML file, a template
exported from a design tool, a page that has been live for three years — none
of them has a Markdown source, and none of them should have to be rewritten
to gain an accessibility feature.

What it does
------------
Given a page and the output of a narration run, it returns the same page with

* ``<span class="ra-s" id="ra-12">`` around every narrated sentence;
* the player — ``<audio controls>`` plus ``<track kind="metadata">`` — at the
  top of the article;
* a reading time beside the measured listening time;
* ``readalong.css`` / ``readalong.js`` linked from the document head and
  copied next to the page.

Everything else comes back byte for byte. The page is rebuilt from a parse of
itself, so its own markup, attribute order and entities survive untouched.

Narrate first
-------------
::

    narrate_post.py page.html --scope article --out-dir audio/
    readalong.py page.html --narration audio/ --scope article --out built/

``narrate_post.py`` reads HTML directly: the structural hints come from the
page's own elements, so an ``<h2>`` earns the same pause a ``##`` would.

Why ``--scope``
---------------
A page written by hand carries a header, a navigation bar and a footer. A
reader who asked to hear *this article* did not ask for the navigation. Pass
``article``, ``#post`` or ``.entry-content`` and only that element is read.
Without it the whole document is, which is right for a page this project
rendered and wrong for almost any page it did not.

Why it can refuse
-----------------
The cues the narration wrote are compared, one by one, against the sentences
the page shows. They match, or this exits non-zero and names the first one
that differs. A highlight that is off by one tells a reader with confidence
to look at the wrong line, which is worse than no highlight at all.

On a page narrated through ``narrate_post.py``, the two come from a *single*
parse of that page, so they agree by construction. The comparison still runs,
because the page may have been edited since the recording — and then the
honest answer is that the recording is stale, not that the reader should be
pointed at the wrong sentence.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _narrate  # noqa: E402
import _readalong  # noqa: E402
from _argparse import make_parser  # noqa: E402
from _lang import detect_text_language  # noqa: E402


def build(page: Path, narration_dir: Path, out_dir: Path, *,
          scope: str | None, lang: str) -> Path:
    """Write `page` with its read-along into `out_dir`; return the new path.

    Parameters
    ----------
    page : Path
        The HTML document to wire up.
    narration_dir : Path
        A narration run: ``narration.vtt`` plus the audio named for the page.
    out_dir : Path
        Where the finished page and the two asset files go. The input is never
        modified in place -- a page that is live somewhere is not a draft.
    scope : str or None
        ``article``, ``#id`` or ``.class``: the element to read.
    lang : str
        BCP-47 language tag, for the player's accessible name and the wording
        of the two durations.

    Raises
    ------
    FileNotFoundError
        If the narration directory holds no recording for this page.
    _readalong.ReadAlongMismatch
        If the page and the recording disagree about the sentences.
    """
    source = page.read_text(encoding="utf-8")
    found = _readalong.narration_sources(narration_dir, page.stem)
    if found is None:
        raise FileNotFoundError(
            f"no narration for {page.name} in {narration_dir}: expected "
            f"narration.vtt and {page.stem}<audio suffix>. "
            f"Run narrate_post.py on the page first."
        )
    audio, cues = found
    out_dir.mkdir(parents=True, exist_ok=True)

    vtt_text = cues.read_text(encoding="utf-8")
    player = _readalong.player_html(
        audio_src=_readalong.href_from(audio, out_dir),
        vtt_src=_readalong.href_from(cues, out_dir),
        label=_readalong.player_label(lang),
        lang=lang,
    )
    meta = _readalong.reading_meta_html(
        words=len(_readalong.page_words(source, scope=scope)),
        spoken_seconds=_readalong.spoken_seconds(vtt_text),
        lang=lang,
    )
    built = _readalong.inject_into_page(
        source,
        _readalong.parse_vtt(vtt_text),
        split=_narrate.split_sentences,
        opening=_narrate.QUOTE_OPENING,
        closing=_narrate.QUOTE_CLOSING,
        scope=scope,
        head=_readalong.head_markup(),
        player=f"{player}\n{meta}",
    )

    _readalong.copy_assets(out_dir)
    destination = out_dir / f"{page.stem}.html"
    destination.write_text(built, encoding="utf-8")
    return destination


def main() -> int:
    """CLI entry point; returns a process exit code."""
    parser = make_parser(
        prog="sprezzature-publish-readalong",
        description="Add a sentence-by-sentence read-along to an existing HTML page.",
        epilog="Examples:\n"
               "  narrate_post.py page.html --scope article --out-dir audio/\n"
               "  readalong.py page.html --narration audio/ --scope article --out built/\n",
    )
    parser.add_argument("page", type=Path, help="HTML page to wire up.")
    parser.add_argument(
        "--narration", type=Path, required=True, dest="narration_dir",
        help="Directory holding the narration run (narration.vtt + the audio).",
    )
    parser.add_argument(
        "--out", type=Path, required=True, dest="out_dir",
        help="Output directory. The input page is never modified in place.",
    )
    parser.add_argument(
        "--scope", default=None,
        help="Element to read: 'article', '#id' or '.class'. Without it the "
             "whole document is read, navigation and footer included.",
    )
    parser.add_argument(
        "--lang", default="auto",
        help="BCP-47 language tag. Default: auto = detect from the page's text.",
    )
    args = parser.parse_args()

    if not args.page.is_file():
        print(f"readalong: no such page: {args.page}", file=sys.stderr)
        return 2

    lang = args.lang
    if lang in ("", "auto"):
        # Detected from what the page *says*, not from a `lang` attribute: a
        # template exported from a design tool often carries the wrong one,
        # and the wording of "3 min listen" is the reader's, not the tool's.
        words = _readalong.page_words(
            args.page.read_text(encoding="utf-8"), scope=args.scope
        )
        lang = detect_text_language(" ".join(words))

    try:
        destination = build(
            args.page, args.narration_dir, args.out_dir,
            scope=args.scope, lang=lang,
        )
    except (FileNotFoundError, _readalong.ReadAlongMismatch) as failure:
        print(f"readalong: {failure}", file=sys.stderr)
        return 1

    sentences = len(_readalong.page_sentences(
        args.page.read_text(encoding="utf-8"),
        split=_narrate.split_sentences, scope=args.scope,
    ))
    print(f"{args.page} → {destination}: {sentences} sentences wrapped, lang={lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
