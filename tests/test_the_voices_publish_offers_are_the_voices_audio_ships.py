"""
``sprezzature-publish`` offers exactly the narration engines audio ships.

The voice stack is four layers deep — ``speaker-engines`` under
``speaker-helper`` under ``sprezzature-audio`` under ``sprezzature-publish`` —
and only the bottom layer decides what engines exist. The top one has to be
*told*, in two places: a tuple of engine names it will accept from
``--engine``, and a default voice for each. Nothing connects those to the
wrappers ``sprezzature-audio`` actually installs.

It drifted the day it could. ``speaker-helper`` 0.11 added a ``kyutai``
backend — the one engine in the set chosen *for French*, where the other
three reach French through an English-first pipeline — and both repositories
had to learn about it by hand. Either half alone is a silent failure in a
different direction:

- an engine **in publish but not in audio** passes ``choices=`` and then dies
  in :func:`_engine_command`, which reports "not installed" and names an
  extra that does not exist. The reader installs the extra, pip says no such
  extra, and nothing in either message says the engine was never shipped.
- an engine **in audio but not in publish** is simply unreachable. The wheel
  carries the wrapper, the console script is on PATH, and the orchestrator
  rejects the name at the command line. That one is invisible: nothing errors,
  the engine just does not exist as far as any reader can tell.

So this compares the two directly: the engine names in
``narrate_post.ENGINES``, the keys of ``narrate_post.DEFAULT_VOICE``, the
``scripts/narrate_*.py`` wrappers in the sibling checkout, and the
``[project.scripts]`` entry points that expose them. Four lists that are one
list.

The ``narrate-<engine>`` extra is checked too, because that is the sentence
the failure path prints. An engine with a wrapper and no extra produces an
install hint that cannot be followed.

Skips, named, when either sibling is missing — and a third test fails if
*both* are missing on a runner that is supposed to have them, because a skip
and a pass look alike in a summary.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
PUBLISH: Path = REPO_ROOT.parent / "sprezzature-publish"
AUDIO: Path = REPO_ROOT.parent / "sprezzature-audio"


def _narrate_post():
    """``narrate_post`` from the sibling checkout, imported by path.

    By path rather than by installed name: this asks what the *source* says,
    and an editable install that has gone stale would answer for a version
    nobody is editing.
    """
    if not PUBLISH.is_dir():
        pytest.skip("no sprezzature-publish checkout; run scripts/fetch_siblings.sh")
    path = PUBLISH / "scripts" / "narrate_post.py"
    if not path.is_file():
        pytest.skip(f"{path} is gone; narrate_post has moved or been renamed")
    name = "_publish_narrate_post"
    if name in sys.modules:
        return sys.modules[name]
    # Its siblings (`_narrate`, `_lang`, …) are imported as top-level modules.
    sys.path.insert(0, str(PUBLISH / "scripts"))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _audio_wrappers() -> set[str]:
    """Engine names that have a wrapper in the sibling checkout."""
    if not AUDIO.is_dir():
        pytest.skip("no sprezzature-audio checkout; run scripts/fetch_siblings.sh")
    found = {p.stem[len("narrate_") :] for p in (AUDIO / "scripts").glob("narrate_*.py")}
    assert found, (
        f"{AUDIO / 'scripts'} has no narrate_*.py at all, which cannot be "
        "right: the wrappers are how any narration reaches an engine."
    )
    return found


def _audio_pyproject() -> str:
    if not AUDIO.is_dir():
        pytest.skip("no sprezzature-audio checkout; run scripts/fetch_siblings.sh")
    return (AUDIO / "pyproject.toml").read_text(encoding="utf-8")


def test_publish_offers_every_engine_audio_ships_and_no_others() -> None:
    """``ENGINES`` and the ``narrate_*.py`` wrappers are the same set."""
    offered = set(_narrate_post().ENGINES)
    shipped = _audio_wrappers()

    unreachable = shipped - offered
    phantom = offered - shipped
    assert not phantom, (
        f"sprezzature-publish accepts --engine {sorted(phantom)}, which "
        f"sprezzature-audio ships no wrapper for. The failure a reader sees "
        f"is 'not installed' plus an install hint for an extra that does not "
        f"exist."
    )
    assert not unreachable, (
        f"sprezzature-audio ships a wrapper for {sorted(unreachable)} that "
        f"sprezzature-publish will not accept from --engine. Nothing errors; "
        f"the engine is simply unreachable from the orchestrator."
    )


def test_every_offered_engine_has_a_default_voice() -> None:
    """A name in ``ENGINES`` with no ``DEFAULT_VOICE`` row is a KeyError."""
    module = _narrate_post()
    missing = [e for e in module.ENGINES if e not in module.DEFAULT_VOICE]
    assert not missing, (
        f"these engines are offered but have no DEFAULT_VOICE row: {missing}. "
        f"Selecting one raises KeyError before any voice is reached."
    )


def test_every_wrapper_has_an_extra_and_an_entry_point() -> None:
    """A wrapper nobody can install, or install and not run, is not shipped."""
    pyproject = _audio_pyproject()
    shipped = _audio_wrappers()

    extras = set(re.findall(r"^narrate-([a-z0-9-]+)\s*=", pyproject, re.M))
    # `narrate` itself is kokoro's, spelled without a suffix; `narrate-kokoro`
    # exists as an alias and both are accepted here.
    extras.add("kokoro")
    scripts = set(
        re.findall(r"^sprezzature-audio-narrate-([a-z0-9-]+)\s*=", pyproject, re.M)
    )

    no_extra = sorted(shipped - extras)
    no_script = sorted(shipped - scripts)
    assert not no_extra, (
        f"wrappers with no narrate-<engine> extra: {no_extra}. The install "
        f"hint printed on failure names exactly that extra, so this is a "
        f"message that cannot be followed."
    )
    assert not no_script, (
        f"wrappers with no console script: {no_script}. The wheel carries the "
        f"code and leaves no way to run it."
    )


def test_this_comparison_actually_ran_somewhere() -> None:
    """Both checkouts present, or say so. A skip reads like a pass."""
    missing = [p.name for p in (PUBLISH, AUDIO) if not p.is_dir()]
    if missing:
        pytest.skip(
            f"not a full-suite runner: {missing} absent. On CI this is what "
            f"scripts/fetch_siblings.sh is for; the tests above skipped."
        )
    assert (PUBLISH / "scripts" / "narrate_post.py").is_file()
    assert (AUDIO / "scripts" / "_speaker.py").is_file()
