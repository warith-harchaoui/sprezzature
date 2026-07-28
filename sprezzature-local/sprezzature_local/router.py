"""
router — classify a user request to the right skill and action.

Skeleton for Phase 5 (the ui generator).  The decision-tree table from
LOCAL.md §3 will become code here once Phase 5 is implemented.  For now,
all calls return ``None`` so the CLI can detect the unimplemented state and
surface a useful message.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from typing import Any


def classify(request: str) -> dict[str, Any] | None:
    """
    Classify a natural-language request to a skill and action pair.

    Parameters
    ----------
    request : str
        Free-form user request, e.g. "build a bar chart for this CSV".

    Returns
    -------
    dict or None
        A dict with ``skill`` and ``action`` keys when the request is
        recognized, or ``None`` when classification is not yet implemented.
        Phase 5 will replace this stub with a real decision-tree classifier.

    Examples
    --------
    >>> classify("make a bar chart") is None
    True
    """
    # Phase 5 placeholder.  Returns None so callers can check and inform the
    # user that the router is not yet functional.
    return None
