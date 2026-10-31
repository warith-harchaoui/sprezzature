"""
Every pronunciation in the film lexicon must reach a grapheme-input engine.

The defect this is shaped after
-------------------------------
``brag-output/lexicon.yaml`` has two tiers. ``ipa:`` states exact phonemes and
is honoured only by an engine that phonemises text itself; ``respelling:`` is
an orthographic rewrite ("GitHub" to "guite-heube") that any engine reads,
because it is just letters.

Until 2026-10-29 the films were narrated by an engine with a phoneme input,
and six entries were written with phonemes and nothing else: ``WCAG``,
``Ollama``, ``TitaNet``, ``Yablonski``, and the suite's own name in both
languages. They were correct, and they were correct *about one engine*.

The engine then changed, which is the normal thing for it to do: it is
``speaker-helper`` that decides which voice reads which language, and it
decided chatterbox in both. Chatterbox tokenises graphemes. It never sees an
IPA string, so those six pronunciations stopped applying. With ``llm: false``
refusing to derive a respelling, the respelling tier falls back to the word as
written and says nothing about it, so nothing would have failed: the films
would simply have mispronounced their own vocabulary, including the word that
closes all twenty-two of them.

The guard is therefore about the class rather than the six: a lexicon entry
whose only pronunciation is phonemic is a pronunciation that works until
somebody changes a voice, and which engine speaks is deliberately not this
repository's decision.

What this does not check
------------------------
Whether a respelling is *right*. "oh-lah-muh" is a judgement about English
that no test can settle, and the only instrument for it is listening to the
cut. This checks that a pronunciation was stated in the tier that survives,
which is the half a machine can decide.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "brag-output" / "lexicon.yaml"


def _entries() -> list[dict]:
    """The lexicon's entries, or an empty list when there is no lexicon."""
    if not LEXICON.is_file():
        return []
    loaded = yaml.safe_load(LEXICON.read_text(encoding="utf-8")) or {}
    return list(loaded.get("entries") or [])


def test_the_lexicon_is_there_and_has_entries() -> None:
    """A precondition that cannot quietly become false.

    Without this, a renamed or emptied lexicon turns the check below into a
    loop over nothing, which passes. A guard whose precondition is impossible
    is a guard that never runs.
    """
    assert LEXICON.is_file(), f"no lexicon at {LEXICON}"
    assert len(_entries()) >= 20, "the film lexicon has lost most of its entries"


def test_every_entry_states_a_respelling() -> None:
    """Phonemes are an optimisation; letters are the floor."""
    naked = [
        f"{entry.get('word')!r} [{entry.get('language', '*')}]"
        for entry in _entries()
        if not str(entry.get("respelling") or "").strip()
    ]
    assert not naked, (
        f"{len(naked)} lexicon entry/entries carry no `respelling:`, so an "
        f"engine without a phoneme input reads them as written and reports "
        f"nothing. Add the orthographic tier beside the phonemes.\n  "
        + "\n  ".join(naked)
    )


def test_the_lexicon_refuses_to_guess() -> None:
    """``llm: false`` is what makes the tier above load-bearing.

    With derivation on, a missing respelling is filled in by a local model and
    the test above would be checking a formality. With it off, a missing
    respelling is a word said wrong, which is why it is worth a test at all.
    """
    loaded = yaml.safe_load(LEXICON.read_text(encoding="utf-8")) or {}
    assert loaded.get("llm") is False, (
        "the film lexicon derives missing pronunciations again; a film is a "
        "claim, and a pronunciation nobody chose is a claim nobody made"
    )
