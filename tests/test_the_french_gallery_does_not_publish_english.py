"""
``web/tools/audit_fr_patterns.py`` runs, instead of merely existing.

That script guards one trap, and its own docstring says the trap has bitten
four times: a pattern rule whose regex captures a *word* and whose template
writes it back as ``{n}`` publishes English in the middle of a French
sentence. Nothing signals it — the rule matched, so the "missing strings"
count calls it a success.

It exits non-zero when it finds one, and nothing ran it. Not the suite, not
the pre-push hook, not a workflow. A guard nobody runs is a note saying
somebody once cared, and the trap it describes had already found four ways in.

It is cheap — one YAML file, no network, no browser — so it belongs in the
default run rather than in a comment.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "web" / "tools"
sys.path.insert(0, str(TOOLS))

yaml = pytest.importorskip("yaml", reason="PyYAML is what the auditor reads with")

import audit_fr_patterns as audit  # noqa: E402


def _rules() -> list:
    return yaml.safe_load(audit.PATTERNS.read_text(encoding="utf-8")) or []


def _offenders() -> list[tuple[int, int, str, str, str]]:
    """Rules that copy a captured word through without declaring it.

    The auditor's own loop, called rather than re-implemented: a copy here
    would be one more place for the two to disagree, and the point of the
    file is that there should be one.
    """
    found = []
    for number, rule in enumerate(_rules(), 1):
        if not isinstance(rule, dict) or "match" not in rule or rule.get("verbatim"):
            continue
        match, write = rule["match"], rule.get("write", "")
        for index, source in enumerate(audit.capture_sources(match)):
            if audit.WORD.search(audit.literal(source)) and ("{%d}" % index) in write:
                found.append((number, index, source, match, write))
                break
    return found


def test_no_rule_copies_a_captured_word_without_saying_so() -> None:
    """The French gallery does not quietly publish an English word."""
    offenders = _offenders()
    assert not offenders, "\n".join(
        f"rule {number}, group {{{index}}} <- ({source[:60]}) : "
        f"match={match[:70]!r} write={write[:70]!r} — write {{{index}:tr}}, "
        f"or add `verbatim:` with the reason"
        for number, index, source, match, write in offenders
    )


def test_the_auditor_read_the_rules_it_audits() -> None:
    """A YAML file that moved would make the test above pass on nothing."""
    rules = _rules()
    assert audit.PATTERNS.is_file(), f"{audit.PATTERNS} does not exist"
    assert len(rules) >= 100, (
        f"{audit.PATTERNS.name} holds {len(rules)} rules; the French gallery "
        f"carries more than a thousand"
    )
    with_captures = [
        rule for rule in rules
        if isinstance(rule, dict) and audit.capture_sources(rule.get("match", ""))
    ]
    assert with_captures, (
        "no rule in the file has a capturing group at all, so the check above "
        "examined nothing. Either the format changed or capture_sources stopped "
        "matching."
    )
