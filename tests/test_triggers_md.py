"""
Tests for ``TRIGGERS.md`` — the generated trigger-phrase index.

The file is a deterministic projection of every shipped skill's
``SKILL.md`` description. Hand-editing it is forbidden by
convention; CI enforces that convention via these tests.

Covers:

* Every shipped skill in ``SKILLS.txt`` has an entry in
  ``build_triggers.STATUS`` and ``build_triggers.WHAT_IT_DOES``.
* The committed ``TRIGGERS.md`` matches what
  ``build_triggers.build()`` produces — no manual drift.
* Every shipped skill appears in the rendered table at least once.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from build_triggers import (
    CATALOGUE,
    ROUTES,
    SKIP_MARKER,
    STATUS,
    WHAT_IT_DOES,
    _description,
    _extract_skip,
    _extract_triggers,
    build,
    build_skill_reference,
)
from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
TRIGGERS: Path = REPO_ROOT / "TRIGGERS.md"


def test_triggers_md_exists() -> None:
    """The committed TRIGGERS.md must live at repo root."""
    assert TRIGGERS.is_file(), (
        f"TRIGGERS.md missing from repo root ({TRIGGERS}). "
        f"Run `python scripts/build_triggers.py`."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_status_map_covers_every_skill(skill: str) -> None:
    """Adding skill #9 forces a status decision at PR time."""
    assert skill in STATUS, (
        f"Skill '{skill}' missing from build_triggers.STATUS. "
        f"Add an entry before merging."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_routes_cover_every_skill(skill: str) -> None:
    """A skill missing from ROUTES is a skill an agent cannot find.

    The phrase table matches one phrase at a time; the routing table is what
    answers "which of these nine do I want", and a skill absent from it is
    invisible to that question. Adding skill #10 forces the decision here.
    """
    assert skill in ROUTES, (
        f"Skill '{skill}' missing from build_triggers.ROUTES. Say what the "
        f"user is holding when this skill is the answer, before merging."
    )
    holding, phrasing = ROUTES[skill]
    assert holding and phrasing, f"Skill '{skill}' has an empty ROUTES entry."


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_what_it_does_covers_every_skill(skill: str) -> None:
    """Each skill must carry a one-line ``what it does`` summary."""
    assert skill in WHAT_IT_DOES, (
        f"Skill '{skill}' missing from build_triggers.WHAT_IT_DOES. "
        f"Add a one-sentence summary before merging."
    )


def test_committed_file_matches_generator() -> None:
    """
    The committed ``TRIGGERS.md`` must equal the generator's output.

    If this fails, someone hand-edited the file or changed a
    SKILL.md description without re-running the generator. Run
    ``python scripts/build_triggers.py`` and commit both files
    together.
    """
    expected: str = build()
    actual: str = TRIGGERS.read_text(encoding="utf-8")
    assert actual == expected, (
        "TRIGGERS.md is out of sync with the generator. Run "
        "`python scripts/build_triggers.py` and commit the result. "
        "The diff lives in the test output above."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_every_skill_appears_in_the_table(skill: str) -> None:
    """Every shipped skill produces at least one row in the table."""
    body: str = TRIGGERS.read_text(encoding="utf-8")
    # ``**sprezzature-X**`` is the bolded skill name we render in the
    # Activates column. Match against that exact form.
    assert f"**{skill}**" in body, (
        f"Skill '{skill}' has no row in TRIGGERS.md — its SKILL.md "
        f"description likely lacks quoted trigger phrases."
    )


# ── The description itself ─────────────────────────────────────────────────
#
# TRIGGERS.md is for humans. The ``description`` is the only text an agent
# reads when it has to choose between ten siblings, so every property the
# routing depends on has to hold *there*, not only in the generated file.


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_description_says_when_not_to_fire(skill: str) -> None:
    """Ten siblings compete for every prompt; only this clause argues against.

    A skill that never says when *not* to answer is a skill that competes on
    every prompt it half-matches. This was true of nine of the ten before the
    clause was introduced, and it is the single property most likely to be
    dropped by someone editing a description for length.
    """
    skip = _extract_skip(_description(skill))
    assert skip, (
        f"'{skill}' has no '{SKIP_MARKER}' clause in its SKILL.md description. "
        f"Say which sibling owns the cases this skill should decline."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_a_skip_clause_names_skills_that_exist(skill: str) -> None:
    """A redirect to a skill that was renamed is worse than no redirect.

    The clause sends the agent somewhere by name. Nothing else checks those
    names, so a rename would quietly leave nine descriptions pointing at a
    skill nobody ships.
    """
    named = set(re.findall(r"sprezzature-[a-z-]+", _extract_skip(_description(skill))))
    unknown = {name for name in named if name not in SHIPPED_SKILLS}
    assert not unknown, (
        f"'{skill}' redirects to {sorted(unknown)}, which SKILLS.txt does not "
        f"ship. Fix the name, or the agent is sent nowhere."
    )
    assert skill not in named, f"'{skill}' redirects to itself."


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_description_routes_on_what_the_user_is_holding(skill: str) -> None:
    """Phrases cannot generalise; the thing in front of the user can.

    The ways to ask for a chart, a colour or a caption are unbounded and a
    user almost never names the tool. What is bounded is the kind of artefact
    they are holding, so each description has to say it.
    """
    description = _description(skill)
    assert re.search(r"Use it (when|whenever)|The trigger is", description), (
        f"'{skill}' lists phrases but never says what the user is holding "
        f"when it is the right answer."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_description_still_fits_the_spec(skill: str) -> None:
    """The Anthropic cap is 1024 chars, and these sit close to it.

    Routing and the skip clause earn their keep only if they survive the next
    edit; a description over the cap is silently truncated by the host, and
    the clause at the end is the first thing to go.
    """
    length = len(_description(skill))
    assert 50 <= length <= 1024, f"'{skill}' description is {length} chars"


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_description_still_carries_trigger_phrases(skill: str) -> None:
    """Routing replaced the redundant phrasings, not the phrases."""
    assert len(_extract_triggers(_description(skill))) >= 5, (
        f"'{skill}' has fewer than five quoted trigger phrases left."
    )


# ── The catalogue that ships inside each skill ─────────────────────────────
#
# The 1024-char cap buys routing, a skip clause and a handful of phrases. The
# rest lives in the skill's own references/triggers.md, generated from the
# same source so the two cannot say different things.


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_each_skill_ships_its_own_trigger_catalogue(skill: str) -> None:
    """The index at repo root is for humans reading ten skills at once.

    An installed skill is a folder on someone else's disk with no repo around
    it, so the exhaustive list has to travel inside it or it is unreachable
    exactly where it would be used.
    """
    path = REPO_ROOT / skill / "references" / "triggers.md"
    assert path.is_file(), (
        f"{skill} has no references/triggers.md. Run "
        f"`python scripts/build_triggers.py`."
    )
    assert path.read_text(encoding="utf-8") == build_skill_reference(skill), (
        f"{skill}/references/triggers.md drifted from the generator. Re-run "
        f"`python scripts/build_triggers.py` and commit both."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_description_points_at_the_catalogue(skill: str) -> None:
    """A catalogue nobody is told about is a catalogue nobody opens."""
    assert "references/triggers.md" in _description(skill), (
        f"{skill}'s description never mentions references/triggers.md, so the "
        f"exhaustive list ships and is never read."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_catalogue_is_a_superset_of_the_description(skill: str) -> None:
    """Trading a phrase for routing room must not lose it.

    Phrases were dropped from the descriptions to pay for the routing and
    skip clauses. That is only honest if they survive in the catalogue, so
    the catalogue has to cover every phrase any description still claims.
    """
    missing = set(_extract_triggers(_description(skill))) - set(CATALOGUE[skill])
    assert not missing, (
        f"{skill} claims {sorted(missing)} in its description but the "
        f"catalogue does not list them."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_catalogue_is_not_empty_and_has_no_duplicates(skill: str) -> None:
    phrases = CATALOGUE[skill]
    assert len(phrases) >= 8, f"{skill} catalogue has only {len(phrases)} phrases."
    assert len(phrases) == len(set(phrases)), f"{skill} catalogue repeats itself."
