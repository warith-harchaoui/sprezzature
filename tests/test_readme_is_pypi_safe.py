"""
README.md is this package's long description, so it is read on PyPI as often
as on GitHub — and PyPI has no repository to resolve a relative target
against. ``[EXAMPLES.md](EXAMPLES.md)`` renders there as a link to
``pypi.org/project/sprezzature/EXAMPLES.md``, a 404, and a relative image
source is a broken image on the page a reader lands on.

Every link and every image therefore has to be absolute, or an anchor into
the page itself. Those two forms are the only ones that survive both
renderings. Markdown and inline HTML are both checked: a README that uses
``<img src="assets/logo.png">`` fails the same way.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: ``[text](target)`` — and ``![alt](source)``, which ends the same way.
_MD_TARGET_RE = re.compile(r"\]\(([^)\s]+)\)")

#: ``src="…"`` / ``href="…"`` in the inline HTML a README may carry.
_HTML_TARGET_RE = re.compile(r'(?i)\b(?:src|href)="([^"]+)"')

#: Forms that render correctly wherever the README is shown.
_PORTABLE_PREFIXES = ("https://", "http://", "#", "mailto:", "data:")


def test_readme_targets_are_absolute() -> None:
    """No link or image in README.md needs a git checkout to resolve."""
    readme = REPO_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    targets = _MD_TARGET_RE.findall(text) + _HTML_TARGET_RE.findall(text)
    relative = sorted({t for t in targets if not t.startswith(_PORTABLE_PREFIXES)})
    assert not relative, (
        "README.md is the PyPI long description, where a relative target 404s. "
        "Point these at https://github.com/warith-harchaoui/sprezzature/blob/main/… "
        "instead:\n  " + "\n  ".join(relative)
    )
