"""
``scripts/check_all_extra_resolves.py`` asks PyPI whether the ``all`` extra's
floors exist. It has to ask the endpoint pip asks.

It did not. It read ``https://pypi.org/pypi/<package>/json`` -- the legacy
metadata API -- which is cached separately from the simple index and lags it.
Minutes after sprezzature-figures 2.7.0 was uploaded, that endpoint still
answered ``"latest": "2.6.0"`` while the simple index already listed both
2.7.0 files and ``pip install sprezzature-figures==2.7.0`` resolved fine.

So the guard reported **NOT PUBLISHED for a version that was published**, at
exactly the moment it is meant to be run: right after a release, before
tagging the umbrella. Acting on that report would have meant lowering a floor
that was correct. A guard that is wrong in the direction of "stop, something
is broken" is not harmlessly conservative -- it argues for an edit that makes
things worse.

The script now reads the PEP 691 simple index, which is both the one that
keeps up and the one pip actually consults, so agreeing with it is the
question being asked rather than a proxy for it.

The network half cannot run in CI, which is the whole reason the script is a
script and not a test (see ``test_all_extra_is_the_suite.py``). What *can* run
here is the parsing underneath it -- the two pure functions that turn a
distribution filename into a version and order those versions -- and those are
where the quiet errors live.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_all_extra_resolves.py"


def _module():
    """Load the script as a module -- it is a CLI, not an importable package."""
    spec = importlib.util.spec_from_file_location("check_all_extra_resolves", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("check_all_extra_resolves", module)
    spec.loader.exec_module(module)
    return module


def test_the_script_queries_the_simple_index_and_not_the_legacy_json_api() -> None:
    """The regression, pinned at the URL that gets built.

    Asserted against the source text rather than by mocking a request, because
    what went wrong was not the handling of a response -- it was asking the
    wrong server. A mock would have faithfully reproduced the bug.

    Both URLs are matched as the interpolated expressions the code actually
    writes, so the legacy endpoint can still be *named* in the prose that
    explains why it is not used, without that prose passing for a request.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'f"https://pypi.org/simple/{package}/"' in source, (
        "the check no longer builds a simple-index URL"
    )
    assert "vnd.pypi.simple.v1+json" in source, "the PEP 691 Accept header is gone"
    assert 'f"https://pypi.org/pypi/{package}/json"' not in source, (
        "the legacy /pypi/<pkg>/json endpoint is being requested again; it is cached "
        "separately from the simple index and lags it, which is the bug this pins"
    )


@pytest.mark.parametrize(
    ("filename", "package", "expected"),
    [
        # Wheels: name-version-pythontag-abi-platform.whl
        ("sprezzature_figures-2.7.0-py3-none-any.whl", "sprezzature-figures", "2.7.0"),
        ("sprezzature_maps-0.18.0-py3-none-any.whl", "sprezzature-maps", "0.18.0"),
        # Sdists: name-version.tar.gz
        ("sprezzature_figures-2.7.0.tar.gz", "sprezzature-figures", "2.7.0"),
        # Two separators in the project name, collapsed differently in the
        # filename than in the requirement -- PEP 503/427 normalisation.
        ("sprezzature_ux_laws-1.1.0.tar.gz", "sprezzature-ux-laws", "1.1.0"),
        ("sprezzature_cli_gui-1.1.0-py3-none-any.whl", "sprezzature-cli-gui", "1.1.0"),
    ],
)
def test_a_distribution_filename_yields_its_version(
    filename: str, package: str, expected: str
) -> None:
    """Every package in the ``all`` extra has an underscore-bearing name, so the
    normalisation is exercised by the real suite rather than by a corner case."""
    assert _module()._version_of(filename, package) == expected


def test_versions_are_ordered_numerically_not_as_strings() -> None:
    """``max()`` over strings calls 0.7.0 newer than 0.18.0, and the script uses
    the newest version to tell the reader what PyPI actually has. Getting that
    backwards would print a reassuring, wrong "latest"."""
    module = _module()
    versions = ["0.5.0", "0.6.0", "0.7.0", "0.12.0", "0.18.0"]
    assert max(versions, key=module._sort_key) == "0.18.0"
    assert max(versions) == "0.7.0", (
        "if this changes, string sorting is no longer the trap"
    )
    assert max(["2.4.0", "2.6.0", "2.7.0"], key=module._sort_key) == "2.7.0"
