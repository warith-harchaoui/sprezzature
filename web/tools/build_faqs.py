#!/usr/bin/env python3
"""
build_faqs — write each page's visible FAQ and its FAQPage markup from one file.

The questions and answers live in ``web/faq/<page>.yaml``, one file per page
with an ``en`` and an ``fr`` list. This script renders both halves of what an
answer engine reads, from that one source: the visible section at the bottom
of ``<main>``, and the ``FAQPage`` JSON-LD right after it. They cannot drift,
because neither is ever written by hand; Google requires marked-up questions
to be visible, and `sprezzature-publish-faq --audit` checks that they are.

Each answer is plain text with two inline marks: ``code`` in backticks and
``[text](url)`` links. The JSON-LD carries the same answer as plain text.

The block sits between ``<!-- faq:start -->`` and ``<!-- faq:end -->``, so a
second run replaces it rather than adding another. ``--check`` writes nothing
and exits 1 when a page differs from what its data says.

Usage
-----
    python tools/build_faqs.py           # write every page
    python tools/build_faqs.py --check   # exit 1 on drift

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml

WEB = Path(__file__).resolve().parent.parent
DATA = WEB / "faq"

START = "<!-- faq:start (web/tools/build_faqs.py writes this block from web/faq/) -->"
END = "<!-- faq:end -->"
_BLOCK = re.compile(r"\n?[ \t]*<!-- faq:start[^>]*-->.*?<!-- faq:end -->", re.S)

HEADING = {"en": "Frequently asked questions", "fr": "Questions fréquentes"}

_CODE = "rounded bg-neutral-100 px-1 text-sm dark:bg-neutral-800"
_LINK = (
    "underline hover:text-brand-linktext focus:outline-none "
    "focus-visible:ring-2 focus-visible:ring-brand-blue"
)
_INLINE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)")


def _to_html(text: str) -> str:
    """Escape the answer, then turn its two inline marks into markup."""
    out, last = [], 0
    for m in _INLINE.finditer(text):
        out.append(html.escape(text[last : m.start()], quote=False))
        if m.group(1) is not None:
            out.append(f'<code class="{_CODE}">{html.escape(m.group(1), quote=False)}</code>')
        else:
            label, url = m.group(2), m.group(3)
            out.append(f'<a class="{_LINK}" href="{html.escape(url)}">{html.escape(label, quote=False)}</a>')
        last = m.end()
    out.append(html.escape(text[last:], quote=False))
    return "".join(out)


def _to_text(text: str) -> str:
    """The same answer with its marks removed, for the JSON-LD."""
    return _INLINE.sub(lambda m: m.group(1) if m.group(1) is not None else m.group(2), text)


def render(items: list[dict], lang: str) -> str:
    """The block: the visible section, then the FAQPage markup built from it."""
    rows = [
        f"    {START}",
        '    <section id="faq" aria-labelledby="faq-title" '
        'class="border-t border-neutral-200/70 dark:border-neutral-800">',
        '      <div class="mx-auto max-w-4xl px-5 py-12">',
        f'        <h2 id="faq-title" class="text-lg font-bold">{HEADING[lang]}</h2>',
    ]
    for item in items:
        rows.append(f'        <h3 class="mt-6 font-semibold">{html.escape(item["q"], quote=False)}</h3>')
        rows.append(
            f'        <p class="mt-2 text-neutral-600 dark:text-neutral-300">{_to_html(item["a"])}</p>'
        )
    rows += ["      </div>", "    </section>"]
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": lang,
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": _to_text(item["a"])},
            }
            for item in items
        ],
    }
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    rows.append('    <script type="application/ld+json">')
    rows += ["    " + line for line in body.splitlines()]
    rows += ["    </script>", f"    {END}"]
    return "\n".join(rows)


def apply(page: str, block: str) -> str:
    """The page with its FAQ block replaced, or inserted before ``</main>``."""
    if _BLOCK.search(page):
        return _BLOCK.sub(lambda _m: "\n" + block, page, count=1)
    head, sep, tail = page.rpartition("  </main>")
    if not sep:
        raise ValueError("no </main> to put the FAQ above")
    return head.rstrip("\n") + "\n" + block + "\n" + sep + tail


def targets() -> list[tuple[Path, list[dict], str]]:
    """Every (page, items, lang) the data files describe."""
    out = []
    for path in sorted(DATA.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = f"{path.stem}.html"
        for lang, page in (("en", WEB / name), ("fr", WEB / "fr" / name)):
            items = data.get(lang) or []
            for item in items:
                if set(item) != {"q", "a"}:
                    raise ValueError(f"{path.name} [{lang}]: an item needs exactly q and a")
            if items:
                out.append((page, items, lang))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--check", action="store_true", help="Write nothing; exit 1 on drift.")
    args = parser.parse_args(argv)
    drift = []
    for page, items, lang in targets():
        before = page.read_text(encoding="utf-8")
        after = apply(before, render(items, lang))
        if after != before:
            drift.append(page.relative_to(WEB))
            if not args.check:
                page.write_text(after, encoding="utf-8")
    verb = "differ from their data" if args.check else "written"
    for rel in drift:
        print(f"  {rel}")
    print(f"{len(drift)} page(s) {verb}.")
    return 1 if (args.check and drift) else 0


if __name__ == "__main__":
    sys.exit(main())
