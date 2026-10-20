"""
A rule a reference teaches has to be one the emitted runtime can obey.

``sprezzature-publish/references/i18n.md`` has taught, for as long as it has
existed, that plural forms come from CLDR through ``Intl.PluralRules``: "English
has two forms, French has two but with different rules, Russian has three,
Arabic has six. Don't try to encode this with ``if (n === 1)``." It has a
checklist line for it. An agent reads that reference and follows it.

The runtime ``sprezzature-ui`` writes into the reader's project had no plural
handling at all. Not a wrong implementation — none. ``t(id)`` returned
``entry[locale] ?? entry[src] ?? id``, so a counting message could not be
expressed in the catalogue the same suite tells you to put every string in. The
rule was right, the reference was right, and the one runtime that had to carry
it could not.

That is a defect neither repository can see on its own. The reference lives in
``sprezzature-publish``, the runtime is emitted by ``sprezzature-ui``, and each
is internally consistent: publish teaches a browser API, ui emits a message
lookup. Only from here are both visible at once, which is the same reason the
driver-routing and the skill-command guards live here.

Scope, deliberately narrow
--------------------------

This does not try to check every claim in every reference against every piece
of emitted code — that is a research project, and a guard that tries to prove
too much either fails on prose or proves nothing. It checks the specific,
machine-checkable pairs where a reference names an API and a runtime in another
brick is the thing that would use it. One pair today. Adding a pair means
writing it down below, which is the point: the list is the inventory of claims
somebody has actually verified.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent

#: Each entry pairs a reference that teaches a mechanism with the emitted
#: runtime that has to carry it.
#:
#: ``reference`` and ``runtime`` are repo-relative paths inside the bricks;
#: ``teaches`` must appear in the reference (or the pair is stale and the guard
#: is checking a rule nobody states any more); ``carries`` must appear in the
#: emitted runtime; ``forbids`` must not.
#:
#: ``symbol`` names the string literal the runtime is kept in, because the
#: thing under test is the code the tool *writes into the reader's project*,
#: not the tool. The first version of this guard read the whole generator and
#: failed on its own prose: ``i18n_make``'s docstring quotes the prohibition —
#: "don't encode this with ``if (n === 1)``" — and a file that documents a
#: mistake is not a file that makes it.
PAIRS: tuple[dict[str, object], ...] = (
    {
        "what": "plural forms come from CLDR, not from a count check",
        "reference": "sprezzature-publish/references/i18n.md",
        "runtime": "sprezzature-ui/scripts/i18n_make.py",
        "symbol": "_LOADER_JS",
        "teaches": ("Intl.PluralRules",),
        "carries": ("new Intl.PluralRules(",),
        # The exact comparison the reference tells readers not to write. A
        # runtime that names the API in a comment and branches on the count
        # underneath would pass a `carries` check alone.
        "forbids": ("count === 1", "count == 1", "n === 1", "n == 1"),
    },
)


def _read(brick_relative: str) -> str | None:
    """A file inside a sibling brick, or None when that brick is not here."""
    path = SIBLINGS / brick_relative
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _emitted(source: str, symbol: str) -> str | None:
    """The triple-quoted literal `symbol` holds, or None when it is not there.

    Read out of the text rather than by importing the module: the generator
    needs PyYAML and inserts its own folder on ``sys.path``, and this
    repository has no business arranging either to read one string out of it.
    """
    match = re.search(
        rf"^{re.escape(symbol)}\s*=\s*(?P<quote>'''|\"\"\")(?P<body>.*?)(?P=quote)",
        source,
        re.M | re.S,
    )
    return match.group("body") if match else None


def test_there_are_pairs_to_check() -> None:
    """An empty list would make the cases below collect nothing."""
    assert PAIRS, (
        "PAIRS is empty, so this file checks nothing while looking like it does"
    )


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: str(p["what"]))
def test_the_reference_still_teaches_it(pair: dict[str, object]) -> None:
    """A pair whose reference stopped saying this is checking a dead rule.

    Guarding a claim nobody makes any more is worse than not guarding it: the
    runtime is then held to a shape for a reason that has been deleted, and the
    next person to read this file cannot tell why.
    """
    text = _read(str(pair["reference"]))
    if text is None:
        pytest.skip(f"{pair['reference']}'s brick is not checked out beside this repository")
    missing = [token for token in pair["teaches"] if token not in text]  # type: ignore[union-attr]
    assert not missing, (
        f"{pair['reference']} no longer mentions {missing}. Either the rule "
        f"moved and this pair needs its new home, or it was dropped and this "
        f"pair should go with it."
    )


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: str(p["what"]))
def test_the_emitted_runtime_can_obey_it(pair: dict[str, object]) -> None:
    """The half that was false: taught in one brick, impossible in another."""
    generator = _read(str(pair["runtime"]))
    if generator is None:
        pytest.skip(f"{pair['runtime']}'s brick is not checked out beside this repository")
    source = _emitted(generator, str(pair["symbol"]))
    assert source is not None, (
        f"{pair['runtime']} no longer holds a {pair['symbol']} literal, so there "
        f"is no emitted runtime to check. Either it was renamed or the runtime "
        f"is built some other way now — either way this pair is blind until "
        f"somebody looks."
    )

    absent = [token for token in pair["carries"] if token not in source]  # type: ignore[union-attr]
    assert not absent, (
        f"{pair['reference']} teaches {pair['what']}, and the runtime emitted by "
        f"{pair['runtime']} does not contain {absent}. A reader following the "
        f"reference has nothing to follow it with."
    )

    present = [token for token in pair["forbids"] if token in source]  # type: ignore[union-attr]
    assert not present, (
        f"{pair['runtime']} contains {present}, which {pair['reference']} "
        f"tells readers not to write. The suite would be shipping the mistake "
        f"it documents."
    )


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: str(p["what"]))
def test_the_pair_names_files_that_exist(pair: dict[str, object]) -> None:
    """Both halves resolve, or the skips above hide a renamed file for ever.

    Checked against this repository's own skill folders rather than the sibling
    checkouts: the brick name is visible here whether or not the brick is
    cloned, so a pair pointing at a brick that no longer exists fails even on a
    machine with no siblings — where every other case in this file skips.
    """
    for role in ("reference", "runtime"):
        brick = str(pair[role]).split("/", 1)[0]
        assert (REPO_ROOT / brick).is_dir(), (
            f"the {role} of {pair['what']!r} is in {brick}, which this "
            f"repository does not ship"
        )
