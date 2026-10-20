"""
Validate the repo-root ``.pre-commit-hooks.yaml`` manifest.

The manifest is how external consumers wire the sprezzature-* audit gates
into their own ``.pre-commit-config.yaml``. If any entry drifts —
references a missing script, names a renamed hook, declares a path
that no longer exists — every downstream user breaks silently.
These tests guard against that.

Covers:

* The YAML parses.
* Every hook entry has the required fields (id, name, entry,
  language).
* Each entry's ``entry`` command names a script that exists on
  disk.
* Hook ids are kebab-case and unique.
* The hook list covers every shipped skill that has at least one
  audit-side script (mirrors ``SKILLS.txt`` minus the make-only
  skills).
* The folders a hook is told to check are the folders this repository
  ships. Mentioning a skill somewhere in the manifest is not the same
  as handing it to the validator: the list below named
  ``sprezzature-vision``, gone since it merged into
  ``sprezzature-accessibility``, and omitted ``sprezzature-maps``. The
  gate therefore exited 1 on a missing folder for every consumer, and
  had never once read the SKILL.md of a brick that was there.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
MANIFEST: Path = REPO_ROOT / ".pre-commit-hooks.yaml"


def _hooks() -> list[dict[str, str]]:
    """Parse the manifest and return its list of hook dicts."""
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


# ── Shape ─────────────────────────────────────────────────────────────────


def test_manifest_exists() -> None:
    """The manifest must live at repo root."""
    assert MANIFEST.is_file(), (
        f".pre-commit-hooks.yaml missing from repo root ({MANIFEST})"
    )


def test_manifest_parses_to_list() -> None:
    """The manifest must parse to a list (one entry per hook)."""
    data = _hooks()
    assert isinstance(data, list), (
        ".pre-commit-hooks.yaml must be a top-level list of hooks"
    )
    assert data, "manifest is empty"


# ── Per-hook fields ───────────────────────────────────────────────────────


REQUIRED_FIELDS: tuple[str, ...] = ("id", "name", "entry", "language")


@pytest.mark.parametrize("hook", _hooks(), ids=lambda h: h.get("id", "?"))
def test_each_hook_has_required_fields(hook: dict[str, str]) -> None:
    """Every hook entry must carry the pre-commit-spec required keys."""
    for field in REQUIRED_FIELDS:
        assert field in hook, (
            f"Hook '{hook.get('id')}' missing required field '{field}'"
        )


@pytest.mark.parametrize("hook", _hooks(), ids=lambda h: h.get("id", "?"))
def test_each_hook_id_is_kebab_case(hook: dict[str, str]) -> None:
    """Hook ids must match the kebab-case pattern used across the repo."""
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", hook["id"]), (
        f"Hook id '{hook['id']}' is not kebab-case"
    )


def test_hook_ids_are_unique() -> None:
    """Two hooks cannot share an id — pre-commit would error opaquely."""
    ids: list[str] = [h["id"] for h in _hooks()]
    assert len(set(ids)) == len(ids), (
        f"Duplicate hook ids in manifest: {ids}"
    )


@pytest.mark.parametrize("hook", _hooks(), ids=lambda h: h.get("id", "?"))
def test_each_hook_entry_script_exists(hook: dict[str, str]) -> None:
    """The script named in ``entry`` must exist on disk."""
    entry: str = hook["entry"]
    # ``entry`` may start with ``python `` (a wrapper); strip that to
    # find the actual script.
    tokens: list[str] = entry.split()
    # Look for the first token that looks like a script path inside
    # the repo (contains ``/`` and a ``.py`` suffix).
    script_path: str | None = next(
        (t for t in tokens if "/" in t and t.endswith(".py")),
        None,
    )
    if script_path is None:
        pytest.skip(
            f"Hook '{hook['id']}' has no recognisable script path "
            f"in its entry; skipping disk-existence check."
        )
    target: Path = REPO_ROOT / script_path
    assert target.is_file(), (
        f"Hook '{hook['id']}' references {target} which does not exist."
    )


# ── Coverage ──────────────────────────────────────────────────────────────


def test_every_audit_skill_has_a_hook() -> None:
    """
    Every shipped skill with at least one audit-side script must
    appear in the manifest.

    sprezzature-accessibility (make-only — alt-text drafting) and sprezzature-audio
    (make-only — caption drafting) are exempt; their audit-side
    is covered indirectly by ``sprezzature-accessibility``'s presence-of-alt
    and presence-of-track rules.
    """
    audit_skills: set[str] = set(SHIPPED_SKILLS) - {
        "sprezzature-accessibility", "sprezzature-audio",
        # sprezzature-cli-gui currently has no audit-side script — its
        # emitter's output is exercised through sprezzature-ux-laws +
        # sprezzature-accessibility hooks above.
        "sprezzature-cli-gui",
        # sprezzature-maps is make-only by design. What it emits is an SVG
        # figure, so sprezzature-figures' audit_figure.py already covers it;
        # a second SVG auditor here would drift from that one within a
        # release. One auditor, two producers — the maps SKILL.md says so in
        # its own "Two modes" table rather than leaving the cell blank.
        "sprezzature-maps",
    }
    hooks_text: str = MANIFEST.read_text(encoding="utf-8")
    for skill in audit_skills:
        assert skill in hooks_text, (
            f"Audit-side skill '{skill}' not referenced anywhere in "
            f".pre-commit-hooks.yaml. Either add a hook or extend "
            f"the exempt list with a justification."
        )


def test_the_folders_a_hook_checks_are_the_folders_this_repo_ships() -> None:
    """``args`` is a list of skill folders, and SKILLS.txt is the one list.

    Grepping the manifest for a skill name — which
    :func:`test_every_audit_skill_has_a_hook` does — cannot see this: the name
    can sit in a comment while the validator is handed a different set. Only
    the arguments say what actually gets checked.
    """
    for hook in _hooks():
        args = hook.get("args")
        if not args:
            continue
        folders = [a for a in args if a.startswith("sprezzature-")]
        if not folders:
            continue
        assert folders == list(SHIPPED_SKILLS), (
            f"Hook '{hook['id']}' checks {folders}; SKILLS.txt ships "
            f"{list(SHIPPED_SKILLS)}. A folder that is not there fails the "
            f"gate for every consumer, and one that is missing is never read."
        )
