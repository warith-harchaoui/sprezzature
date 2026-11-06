"""
The site breaks a sentence where the films do, and every page asks for it.

The rule lives once, in ``scripts/semantic_breaks.py``: the films apply it in
Python when they are built, the site in the reader's browser through
``web/js/phrases.js``, which that module generates. Two implementations of one
rule drift the day somebody edits one of them, so this runs both on the same
sentences, the films' on-screen prose and the site's own headings, and
requires the same phrases, no-break spaces included.

It also checks the two ways the site half can be present and do nothing: a
generated script older than its generator, and a page that never loads it.

Author
------
Project maintainers.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "brag-output"))

import semantic_breaks as sb  # noqa: E402

WEB = ROOT / "web"
PAGES = sorted([*WEB.glob("*.html"), *WEB.glob("fr/*.html")])


def _headings() -> list[str]:
    out = []
    for page in PAGES:
        for m in re.finditer(r"<h[1-4][^>]*>(.*?)</h[1-4]>", page.read_text(encoding="utf-8"), re.S):
            text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
            text = " ".join(text.split())
            if text:
                out.append(text)
    return out


def _corpus() -> list[str]:
    import build_films

    texts = set(_headings())
    for film, lang in build_films.cuts():
        spec = build_films.in_language(build_films.FILMS[film], lang, film)
        for scene in spec["scenes"]:
            for key in ("line", "caption", "eyebrow", "tagline"):
                if isinstance(scene.get(key), str):
                    texts.add(" ".join(scene[key].split()))
    return sorted(texts)


def test_the_generated_script_is_in_step_with_its_generator() -> None:
    script = WEB / "js/phrases.js"
    assert script.is_file(), "web/js/phrases.js is missing: python3 scripts/semantic_breaks.py --write-js"
    assert script.read_text(encoding="utf-8") == sb.js(), (
        "web/js/phrases.js is older than scripts/semantic_breaks.py: "
        "python3 scripts/semantic_breaks.py --write-js"
    )


def test_python_and_the_browser_cut_every_sentence_the_same_way() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; CI runners have it")
    corpus = _corpus()
    assert len(corpus) > 300, f"only {len(corpus)} sentences; the walk is wrong"
    js = (
        "const p=require(process.argv[1]);"
        "const t=JSON.parse(require('fs').readFileSync(0,'utf8'));"
        "process.stdout.write(JSON.stringify(t.map(p.phrases)));"
    )
    run = subprocess.run(
        [node, "-e", js, str(WEB / "js/phrases.js")],
        input=json.dumps(corpus), capture_output=True, text=True, check=True,
    )
    browser = json.loads(run.stdout)
    differ = [
        f"{text!r}\n    py: {sb.phrases(text)!r}\n    js: {got!r}"
        for text, got in zip(corpus, browser)
        if sb.phrases(text) != got
    ]
    assert not differ, f"{len(differ)} sentence(s) cut differently:\n  " + "\n  ".join(differ[:8])


def test_every_page_loads_the_script() -> None:
    missing = [
        p.relative_to(WEB).as_posix()
        for p in PAGES
        if p.name != "head.html" and not re.search(r'src="(?:\.\./)?js/phrases\.js', p.read_text(encoding="utf-8"))
    ]
    assert not missing, "these pages never break by meaning: " + ", ".join(missing)


def test_the_stylesheet_shares_the_breaks_out() -> None:
    """The script says where a line may break; balance and pretty say how."""
    css = (WEB / "css/app.css").read_text(encoding="utf-8")
    assert re.search(r"h1[^{]*\{text-wrap:balance", css) or "h1,h2,h3,h4,h5,h6,summary,th{text-wrap:balance" in css
    assert "text-wrap:pretty" in css


def test_the_clitic_rule_names_its_pairs() -> None:
    """``l'AEO`` is an article and a noun; ``l'a`` and ``n'y`` lean on a verb."""
    assert sb.NBSP not in sb.phrases("l'AEO et llms.txt")[0]
    assert f"n'y{sb.NBSP}a{sb.NBSP}pas" in sb.bind("Il n'y a pas")
