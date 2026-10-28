"""
The numbers the films put on screen, checked against the code that decides them.

``sprezzature-video`` exists because of this exact failure: a number burned
into a keyframe that nobody re-reads. Its own film tells the story — the suite
said "127 chart kinds" for months after the catalogue held 167.

The suite owned that tool and never pointed it at its own films. ``pitch`` ran
in ``test_the_films_pass_the_suites_own_pitch_checker``; ``poster`` ran in
``install_films``; ``verify``, ``scan``, ``assets`` and ``prose`` ran nowhere,
because there was no spec for them to read. On 2026-10-28 the ``figures`` film
was found quoting a count measured on a CSV that existed on one machine, which
is what a declared claim prevents — the tool to catch it had been in the suite
for four days.

So ``brag-output/films.yaml`` declares them, and this file runs the check.

Three halves, deliberately
--------------------------
The **shape** half needs nothing and therefore runs everywhere: the spec
parses, and every claim points into a brick this suite actually has. A claim
whose path is a typo would otherwise fail only where the sibling is cloned,
and read as a missing checkout rather than a broken spec.

The **verify** half needs ``sprezzature-video`` installed and the sibling
whose file decides the claim. That is a developer's machine and the brick's
own CI, not this repository's runner.

The **asset** half needs ``_assets/``, which git does not track: a WAV does
not delta-compress and none of it belongs in a clone. ``restore_assets.py`` is
the ledger that says how each file comes back, and it is the only thing that
can produce the total the ``video`` film puts on screen.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAG = REPO_ROOT / "brag-output"
SPEC = BRAG / "films.yaml"
#: Claim paths are relative to the directory holding the clones, so a film
#: about the suite can reach into the brick that decides each claim.
SIBLING_ROOT = REPO_ROOT.parent

sys.path.insert(0, str(BRAG))


def _raw_claims() -> list[dict]:
    """The spec as written, read without the brick that interprets it."""
    yaml = pytest.importorskip("yaml", reason="PyYAML is in requirements-dev.txt")
    doc = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{SPEC.name} is not a mapping"
    return list(doc.get("claims") or [])


def test_the_spec_is_a_spec_and_points_at_real_bricks() -> None:
    """Every claim names a brick of this suite, and names it the same way."""
    claims = _raw_claims()
    assert claims, f"{SPEC.name} declares nothing, so nothing is checked"

    bricks = {
        line.split("sprezzature-")[1].split("/")[0]
        for line in [str(c["source"]["path"]) for c in claims]
        if line.startswith("sprezzature-")
    }
    wrong: list[str] = []
    for claim in claims:
        source = claim["source"]
        first = str(source["path"]).split("/")[0]
        if not first.startswith("sprezzature-"):
            wrong.append(f"{claim['text']!r}: {source['path']} leaves the suite")
        if source["method"] in ("regex_count", "json_key_len", "literal") and not source.get("selector"):
            wrong.append(f"{claim['text']!r}: {source['method']} with no selector")
    assert not wrong, "\n  ".join(["", *wrong])
    assert bricks, "no claim reaches into a brick, so none of them check anything"


def test_every_declared_claim_still_matches_the_code() -> None:
    """``sprezzature-video verify``, on this suite's own films."""
    claims_mod = pytest.importorskip(
        "sprezzature_video.claims", reason="pip install sprezzature-video"
    )
    spec_mod = pytest.importorskip(
        "sprezzature_video.spec", reason="pip install sprezzature-video"
    )

    spec = spec_mod.load(SPEC)
    missing = sorted(
        {
            str(claim.source.path).split("/")[0]
            for claim in spec.claims
            if not (SIBLING_ROOT / claim.source.path).exists()
        }
    )
    if missing:
        pytest.skip(f"no checkout for {', '.join(missing)}")

    broken = [v for v in claims_mod.verify_all(spec.claims, SIBLING_ROOT) if not v.ok]
    assert not broken, (
        f"{len(broken)} claim(s) the films make are no longer true:\n  "
        + "\n  ".join(v.detail for v in broken)
    )


def test_the_asset_count_on_screen_is_the_ledger_total() -> None:
    """The ``video`` film says how many assets the films render from.

    ``_assets/`` is gitignored on purpose, so this number cannot be read off a
    clone — which is the reason it is checked here rather than declared in the
    spec beside the others.
    """
    import build_films

    scene = next(
        s for s in build_films.FILMS["video"]["scenes"] if s["type"] == "verify"
    )
    on_screen = int(
        next(
            value for label, value in scene["claims"]
            if isinstance(label, dict) and "asset" in label["en"]
        )
    )

    if not (BRAG / "_assets").is_dir():
        pytest.skip("brag-output/_assets is gitignored and absent from this clone")

    report = subprocess.run(
        [sys.executable, "restore_assets.py"],
        cwd=BRAG, capture_output=True, text=True, timeout=300,
    )
    total = re.search(r"(\d+)/(\d+) files present", report.stdout)
    assert total, (
        "restore_assets.py no longer reports a total:\n" + report.stdout[-500:]
    )
    assert int(total.group(2)) == on_screen, (
        f"the film says {on_screen} assets; the ledger counts {total.group(2)}"
    )
