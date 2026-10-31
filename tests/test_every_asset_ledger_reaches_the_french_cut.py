"""
A ledger the French cut was never told to read.

`films_fr.french_asset` offers a French plate only when the ledger declares
one, and `_declared()` builds that set from a list of ledger names in
`restore_assets`. Four times now a new ledger has been added there and the
list has not been extended, and the failure has no symptom: `french_asset`
returns the English path, the build succeeds, and the French cut shows an
English plate for as long as nobody watches it.

Nothing about a ledger's shape says which kind it is — `TRACKED` and
`SEED_ONLY` are both ``dict[str, str]`` mapping an asset path to a sentence.
So this does not try to guess. It requires that every path-keyed ledger be
named in one of two lists, and that the second one carry a reason.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brag-output"))

import films_fr  # noqa: E402
import restore_assets  # noqa: E402


def _path_keyed_ledgers() -> dict[str, dict]:
    """Every module-level mapping in `restore_assets` keyed by asset path."""
    found = {}
    for name in dir(restore_assets):
        if name.startswith("_") or not name.isupper():
            continue
        value = getattr(restore_assets, name)
        if not isinstance(value, dict) or not value:
            continue
        keys = list(value)
        if all(isinstance(k, str) and "/" in k and pathlib.Path(k).suffix for k in keys):
            found[name] = value
    return found


def test_every_path_keyed_ledger_is_classified() -> None:
    """Read by the French cut, or excluded on purpose with the reason said."""
    classified = set(films_fr.LEDGERS_READ) | set(films_fr.LEDGERS_NOT_READ)
    unclassified = sorted(set(_path_keyed_ledgers()) - classified)
    assert not unclassified, (
        "asset ledgers in restore_assets that films_fr has never been told "
        "about:\n  " + "\n  ".join(unclassified) + "\n\nAdd each to "
        "films_fr.LEDGERS_READ, or to LEDGERS_NOT_READ with the reason its "
        "assets cannot have a French twin. Left out, french_asset() quietly "
        "returns the English path and the French cut shows an English plate."
    )


def test_the_lists_name_ledgers_that_exist() -> None:
    """A renamed ledger leaves a name behind, and the name stops matching."""
    ledgers = _path_keyed_ledgers()
    missing = sorted(
        name
        for name in (*films_fr.LEDGERS_READ, *films_fr.LEDGERS_NOT_READ)
        if name not in ledgers
    )
    assert not missing, (
        "films_fr names ledgers restore_assets no longer has: " + ", ".join(missing)
    )


def test_the_two_lists_do_not_overlap() -> None:
    """Read and not-read is a decision, so it is made once."""
    both = sorted(set(films_fr.LEDGERS_READ) & set(films_fr.LEDGERS_NOT_READ))
    assert not both, f"ledgers in both lists: {both}"


def test_every_excluded_ledger_says_why() -> None:
    """An exclusion without a reason is an exclusion nobody can review."""
    thin = sorted(n for n, why in films_fr.LEDGERS_NOT_READ.items() if len(why) < 40)
    assert not thin, f"excluded with no real reason given: {thin}"


def test_the_readalong_plate_resolves_to_its_french_twin() -> None:
    """The case that prompted all of the above, pinned."""
    assert films_fr.french_asset("shots/readalong.png") == "shots/fr/readalong.png"
