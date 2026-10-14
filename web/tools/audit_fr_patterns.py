#!/usr/bin/env python3
"""Garde-fou sur les règles de motif de la galerie française.

Le piège, qui a mordu quatre fois : une règle dont l'expression capture un
*mot* et dont le gabarit le réécrit en ``{n}`` publie de l'anglais. Rien ne
le signale — la règle a accroché, donc le compte de « chaînes manquantes »
la tient pour un succès — et l'anglais sort au milieu d'une phrase française.

L'invariant tenu ici : un groupe qui capture un mot est soit envoyé à la
table plate (``{n:tr}``), soit recopié *en le déclarant*, avec la raison :

    - match: '(accel|disp|hp|mpg|wt) x (accel|disp|hp|mpg|wt)'
      write: '{0} × {1}'
      verbatim: 'noms de colonnes du jeu mtcars : des identifiants, pas des mots'

Sortie non nulle s'il reste une règle qui recopie sans le dire.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

PATTERNS = Path(__file__).resolve().parents[1] / "i18n" / "figures.fr.patterns.yaml"

WORD = re.compile(r"[A-Za-z]{2,}")
CLASS = re.compile(r"\[[^\]]*\]")
ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}|\\.")


def literal(source: str) -> str:
    """La source d'un groupe, débarrassée de ce qui n'est pas une lettre voulue.

    ``([-+\\d.,\\u202f ]+)`` ne capture pas un mot : ses lettres sont celles de
    ``\\d`` et de ``\\u202f``. ``([A-Za-z ]+)``, lui, en capture un — une classe
    qui porte une plage de lettres compte donc comme un mot.
    """

    def one_class(m: re.Match[str]) -> str:
        body = m.group(0)
        return "Xx" if ("a-z" in body or "A-Z" in body or "\\w" in body) else ""

    return ESCAPE.sub("", CLASS.sub(one_class, source))


def capture_sources(regex: str) -> list[str]:
    """Le contenu de chaque groupe capturant, dans l'ordre, groupes nommés exclus."""
    out: list[list[int | None]] = []
    stack: list[int | None] = []
    i = 0
    while i < len(regex):
        c = regex[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = i + 1
            while j < len(regex) and regex[j] != "]":
                j += 2 if regex[j] == "\\" else 1
            i = j + 1
            continue
        if c == "(":
            if regex[i : i + 2] == "(?":
                stack.append(None)
            else:
                stack.append(len(out))
                out.append([i, None])
            i += 1
            continue
        if c == ")":
            k = stack.pop() if stack else None
            if k is not None:
                out[k][1] = i
            i += 1
            continue
        i += 1
    return [regex[a + 1 : b] for a, b in out if b is not None]


def main() -> int:
    rules = yaml.safe_load(PATTERNS.read_text(encoding="utf-8")) or []
    offenders = []
    for n, rule in enumerate(rules, 1):
        if not isinstance(rule, dict) or "match" not in rule or rule.get("verbatim"):
            continue
        match, write = rule["match"], rule.get("write", "")
        for idx, source in enumerate(capture_sources(match)):
            if WORD.search(literal(source)) and ("{%d}" % idx) in write:
                offenders.append((n, idx, source, match, write))
                break

    if not offenders:
        print(f"{len(rules)} règles : aucune ne recopie un mot capturé sans le déclarer.")
        return 0

    print(f"{len(offenders)} règles recopient un mot capturé sans le déclarer :\n")
    for n, idx, source, match, write in offenders:
        print(f"  règle {n}, groupe {{{idx}}} ← ({source[:60]})")
        print(f"    match: {match[:100]}")
        print(f"    write: {write[:100]}")
        print(f"    → écrire {{{idx}:tr}}, ou ajouter `verbatim:` avec la raison.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
