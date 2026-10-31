#!/usr/bin/env python3
"""
splice_film — put one rewritten film back into the two files that hold them.

Why a script and not an edit
----------------------------
Eleven films were rewritten at once, each by somebody who could not touch
``build_films.py`` or ``make_captions.py`` without overwriting ten others. So
each one wrote its entry to its own file and this puts them back, one at a
time, by locating the entry's exact span rather than by pattern-matching its
contents.

Finding the span is the whole correctness of this script, and the trap is
ordinary: a film entry contains dozens of ``)`` and ``}`` characters inside
its scenes, so "read to the next closing bracket" lands in the middle of a
scene and produces a file that still parses, with one film's tail married to
another's head. The span is therefore found by **bracket depth**, counting
from the entry's opening line until depth returns to zero, and string
literals are skipped so a bracket inside a caption never counts.

What it refuses to do
---------------------
Write a file that does not import afterwards. The replacement is made in
memory, the module is compiled, and only a module that compiles is written to
disk. A splice that half-lands is worse than one that does not: the first
leaves eleven films in an unknown state and the second leaves them alone.

Usage
-----
::

    python3 splice_film.py maps            # one film, both files
    python3 splice_film.py --all           # every film with a -spec.py ready
    python3 splice_film.py maps --dry-run  # say what would change

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
NOTES = ROOT / "notes"
BUILD = ROOT / "build_films.py"
CAPTIONS = ROOT / "make_captions.py"


def _code_positions(source: str, needle: str):
    """Yield offsets where ``needle`` occurs outside comments and strings.

    A note file explains itself before it holds its block, and the explanation
    quotes the very thing it is about. So "find the first occurrence" is not
    the same question as "find the entry", and on 2026-10-29 the two gave
    different answers for four films out of nine.
    """
    triples = ('"' * 3, "'" * 3)
    i = 0
    quote: str | None = None
    while i < len(source):
        if quote:
            if source[i] == "\\":
                i += 2
                continue
            if source.startswith(quote, i):
                i += len(quote)
                quote = None
                continue
            i += 1
            continue
        if source.startswith(triples, i):
            quote = source[i : i + 3]
            i += 3
            continue
        if source[i] == "#":
            nl = source.find("\n", i)
            if nl == -1:
                return
            i = nl + 1
            continue
        if source.startswith(needle, i):
            yield i
            i += len(needle)
            continue
        if source[i] in "\"'":
            quote = source[i]
            i += 1
            continue
        i += 1


def _entry_span(source: str, key: str, opener: str) -> tuple[int, int]:
    """Character span of ``"<key>": <opener>`` through its matching close.

    ``opener`` is ``"dict("`` in ``build_films`` and ``"{"`` in
    ``make_captions``: the two files spell the same structure differently and
    neither spelling is wrong, so the caller says which one it is reading.

    Counting is by depth over ``([{`` and ``)]}``, with quoted text skipped.
    A film entry holds hundreds of brackets inside its own strings, and a
    counter that reads them lands mid-scene while still producing a file that
    parses.
    """
    # Indentation is not part of the needle. Inside `build_films.py` the entry
    # sits at four spaces; inside a note file an author may have written it at
    # column zero, and that is not a different entry. A needle that insisted
    # on the indentation refused three perfectly good blocks on 2026-10-29.
    needle = f'"{key}": {opener}'

    # The needle has to be *code*, and the first match in a note file usually
    # is not. Four of them opened with a line like::
    #
    #     # Paste this over the existing `"audio": {...}` block.
    #
    # which contains the needle, so the span began inside a comment and ran to
    # the `}` of `{...}`. Every check passed: the span was found, the module
    # compiled, the diff looked plausible. The film was then the literal
    # `{Ellipsis}`, and the only thing that caught it was reading the data
    # back and finding a `set` where a `dict` belonged.
    found = next(_code_positions(source, needle), None)
    if found is None:
        raise LookupError(f'no entry `"{key}": {opener}` found in code')

    # Reach back to the start of the line so the replacement keeps whatever
    # indentation the destination uses, rather than inheriting the note's.
    start = found
    line_start = source.rfind("\n", 0, start) + 1
    if source[line_start:start].strip() == "":
        start = line_start

    i = found + len(needle) - len(opener)
    depth = 0
    quote: str | None = None
    while i < len(source):
        ch = source[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if source.startswith(quote, i):
                i += len(quote)
                quote = None
                continue
            i += 1
            continue
        if source.startswith(('"""', "'''"), i):
            quote = source[i : i + 3]
            i += 3
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        if ch == "#":  # a comment cannot close a bracket
            i = source.find("\n", i)
            if i == -1:
                break
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                end = i + 1
                # Take the trailing comma and newline with it, so the
                # replacement slots in as a peer rather than a continuation.
                if source[end : end + 1] == ",":
                    end += 1
                if source[end : end + 1] == "\n":
                    end += 1
                return start, end
        i += 1
    raise LookupError(f"entry for {key!r} never closes; refusing to guess")


def _entry_only(block: str, key: str, opener: str) -> str:
    """Just the ``"<key>": ...`` entry, out of whatever wraps it.

    The brief asked each film's author for "the entry", and several of them
    reasonably wrapped it in a module docstring, a row of ``--- BEGIN ---``
    markers, or a table of their beats. All of that is useful to a reader of
    the note and none of it may land inside a dict literal.

    Pasting a whole file was the first version of this and it is the kind of
    mistake that survives review: a stray docstring above an entry is a key
    with no value, which does not compile, so the splice is refused loudly.
    A stray *comment* above an entry compiles perfectly and silently moves
    somebody's prose into the data. One of those two failures is lucky.

    So the entry is located inside the block the same way it is located inside
    the file it is going to, by bracket depth, and everything around it is
    dropped.
    """
    start, end = _entry_span(block, key, opener)
    entry = block[start:end].rstrip()
    # Re-indent to the four spaces both destination files use. An author who
    # wrote the entry at column zero wrote the same entry, and the dict it
    # lands in does not care, but every human reading the diff does.
    if not entry.startswith("    "):
        entry = "\n".join(
            ("    " + line if line.strip() else line) for line in entry.splitlines()
        )
    # The entry has to end as a peer of the entries around it. A note file
    # whose block is the last thing in it has no trailing comma, and without
    # this the splice butts `)` straight against the next `"key":` and the
    # module stops compiling. Four films landed that way on 2026-10-29.
    if not entry.rstrip().endswith(","):
        entry = entry.rstrip() + ","
    return entry + "\n"


def _compiles(source: str, name: str) -> str | None:
    """``None`` when the text is valid Python, else the error to report."""
    try:
        compile(source, name, "exec")
    except SyntaxError as exc:
        return f"{name}:{exc.lineno}: {exc.msg}"
    return None


def splice(key: str, *, dry_run: bool = False) -> int:
    """Put one film's two blocks back. Returns a process exit code."""
    spec = NOTES / f"{key}-spec.py"
    caps = NOTES / f"{key}-captions.py"
    missing = [p.name for p in (spec, caps) if not p.is_file()]
    if missing:
        print(f"--  {key}: not ready, missing {', '.join(missing)}", file=sys.stderr)
        return 1

    plan: list[tuple[pathlib.Path, str]] = []
    for path, block_file, opener in (
        (BUILD, spec, "dict("),
        (CAPTIONS, caps, "{"),
    ):
        source = path.read_text(encoding="utf-8")
        try:
            block = _entry_only(block_file.read_text(encoding="utf-8"), key, opener)
        except LookupError as exc:
            print(f"!!  {key}: {block_file.name}: {exc}", file=sys.stderr)
            return 1
        try:
            start, end = _entry_span(source, key, opener)
        except LookupError as exc:
            print(f"!!  {key}: {path.name}: {exc}", file=sys.stderr)
            return 1
        updated = source[:start] + block + source[end:]
        problem = _compiles(updated, path.name)
        if problem:
            print(f"!!  {key}: {path.name} would not compile: {problem}", file=sys.stderr)
            return 1
        was, now = end - start, len(block)
        print(f"ok  {key}: {path.name} {was} -> {now} characters")
        plan.append((path, updated))

    if dry_run:
        print(f"--  {key}: dry run, nothing written")
        return 0
    for path, updated in plan:
        path.write_text(updated, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="splice_film",
        description="Put a rewritten film back into build_films and make_captions.",
    )
    parser.add_argument("films", nargs="*", help="Film keys.")
    parser.add_argument("--all", action="store_true", help="Every film that is ready.")
    parser.add_argument("--dry-run", action="store_true", help="Report, write nothing.")
    args = parser.parse_args(argv)

    keys = list(args.films)
    if args.all:
        keys = sorted(p.name[: -len("-spec.py")] for p in NOTES.glob("*-spec.py"))
    if not keys:
        parser.error("name a film, or pass --all")

    bad = sum(splice(key, dry_run=args.dry_run) for key in keys)
    print(f"\n{len(keys) - bad}/{len(keys)} film(s) spliced")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
