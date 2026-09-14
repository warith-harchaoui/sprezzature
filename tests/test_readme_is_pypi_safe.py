"""
README.md is the ``sprezzature`` package's long description, so it is read on
PyPI as often as on GitHub — and PyPI has no repository to resolve a relative
link against. ``[docs/](docs/)`` renders there as a link to
``pypi.org/project/sprezzature/docs/``, which is a 404.

Every link therefore has to be absolute, or an anchor into the page itself.
The two are the only forms that survive both renderings.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Markdown inline links: the target between the parentheses of ``[text](target)``.
_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")

#: Forms that render correctly wherever the README is shown.
_PORTABLE_PREFIXES = ("https://", "http://", "#", "mailto:")


def test_readme_has_no_repository_relative_links() -> None:
    """Nothing in README.md points at a path only a git checkout can resolve."""
    readme = REPO_ROOT / "README.md"
    targets = _LINK_RE.findall(readme.read_text(encoding="utf-8"))
    relative = sorted({t for t in targets if not t.startswith(_PORTABLE_PREFIXES)})
    assert not relative, (
        "README.md is the PyPI long description, where a relative link 404s. "
        "Point these at https://github.com/warith-harchaoui/sprezzature/blob/main/… "
        "instead:\n  " + "\n  ".join(relative)
    )
