"""
Tests for ``cli_to_gui`` — the sprezzature-cli-gui make-side primary that
introspects an :mod:`argparse` parser and emits a single-page
vanilla-JS + Tailwind GUI.

Covers:

* Parser-spec resolution from a Python file path (``file.py:factory``).
* JSON shape of :func:`walk_parser` against a small fixture parser
  exercising every action kind (``str``, ``int``, ``float``,
  ``store_true``, ``choices``, sub-parsers, positionals).
* HTML emission shape — correct tag for each field kind, default
  values preserved, required marker present.
* Integration: emitted HTML passes both the sprezzature-ux-laws static
  auditor AND the sprezzature-accessibility lint with zero findings. The
  emitter is its own customer.
* CLI surface: ``--version``, ``--help``, ``--json``, ``--out``,
  and a bad spec exits 1 with a useful stderr message.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = (
    REPO_ROOT / "sprezzature-cli-gui" / "scripts" / "cli_to_gui.py"
)
AUDIT_LAWS: Path = (
    REPO_ROOT / "sprezzature-ux-laws" / "scripts" / "audit_laws_of_ux.py"
)
LINT_A11Y: Path = (
    REPO_ROOT / "sprezzature-accessibility" / "scripts" / "lint_a11y.py"
)


# Imported lazily so conftest can add the scripts dir to sys.path first.
from cli_to_gui import (  # noqa: E402
    load_parser_from_spec,
    render_html,
    walk_parser,
)


# ── Fixture builder ────────────────────────────────────────────────────────


@pytest.fixture
def sample_cli(tmp_path: Path) -> Path:
    """
    Write a self-contained Python CLI exposing ``make_parser()``.

    Covers every action kind the emitter knows about so each test gets
    end-to-end coverage from a single fixture.
    """
    src: str = textwrap.dedent('''
        """Sample CLI for cli_to_gui tests."""
        import argparse

        def make_parser():
            p = argparse.ArgumentParser(
                prog="sample",
                description="Sample CLI used by the test suite.",
            )
            sub = p.add_subparsers(dest="cmd")
            a = sub.add_parser(
                "encode",
                description="Encode a file (exercises every field kind).",
            )
            a.add_argument("--input", required=True, help="Input path.")
            a.add_argument("--bitrate", type=int, default=128,
                           help="Bitrate in kbps.")
            a.add_argument("--gain", type=float, default=1.5)
            a.add_argument("--format", choices=["mp3", "ogg", "flac"],
                           default="mp3")
            a.add_argument("--verbose", action="store_true")
            b = sub.add_parser("decode", description="Positional fixture.")
            b.add_argument("path", help="Positional input.")
            return p

        if __name__ == "__main__":
            # ``--from-help`` needs the script to actually invoke
            # argparse so the help banner reaches stdout.
            make_parser().parse_args()
    ''').lstrip()
    p: Path = tmp_path / "sample_cli.py"
    p.write_text(src, encoding="utf-8")
    return p


# ── In-process walker ──────────────────────────────────────────────────────


def test_load_parser_from_file_spec(sample_cli: Path) -> None:
    """A ``file.py:factory`` spec resolves to a real ArgumentParser."""
    parser = load_parser_from_spec(f"{sample_cli}:make_parser")
    assert parser.prog == "sample"


def test_walk_parser_covers_every_action_kind(sample_cli: Path) -> None:
    """Every form-field kind appears in the walked tree."""
    parser = load_parser_from_spec(f"{sample_cli}:make_parser")
    tree = walk_parser(parser)
    assert tree["prog"] == "sample"
    # Two sub-commands.
    assert set(tree["sub_commands"]) == {"encode", "decode"}
    # ``encode`` has all the kinds.
    by_dest: dict[str, dict] = {
        a["dest"]: a for a in tree["sub_commands"]["encode"]["actions"]
    }
    assert by_dest["input"]["required"] is True
    assert by_dest["bitrate"]["kind"] == "int"
    assert by_dest["bitrate"]["default"] == 128
    assert by_dest["gain"]["kind"] == "float"
    assert by_dest["gain"]["default"] == 1.5
    assert by_dest["format"]["kind"] == "choice"
    assert set(by_dest["format"]["choices"]) == {"mp3", "ogg", "flac"}
    assert by_dest["verbose"]["kind"] == "bool"
    # ``decode`` has the positional.
    decode_actions = tree["sub_commands"]["decode"]["actions"]
    assert any(a["dest"] == "path" for a in decode_actions)


def test_walk_parser_skips_help_and_version(sample_cli: Path) -> None:
    """``-h`` / ``-V`` actions must not leak into the tree."""
    parser = load_parser_from_spec(f"{sample_cli}:make_parser")
    parser.add_argument(
        "-V", "--version", action="version", version="1.0",
    )
    tree = walk_parser(parser)
    for action in tree["actions"]:
        assert action["dest"] != "help"
        assert action["dest"] != "version"


# ── HTML emission shape ───────────────────────────────────────────────────


def test_render_html_includes_subcommands(sample_cli: Path) -> None:
    """The HTML contains a <details> per sub-command and proper input types."""
    parser = load_parser_from_spec(f"{sample_cli}:make_parser")
    html: str = render_html(walk_parser(parser))
    assert "<!doctype html>" in html
    # Sub-command summaries.
    assert ">encode<" in html
    assert ">decode<" in html
    # Field kinds.
    assert 'type="number"' in html       # bitrate + gain
    assert 'type="checkbox"' in html      # verbose
    assert "<select" in html              # format choice
    # Default preserved.
    assert 'value="128"' in html
    # Required marker rendered.
    assert "text-brand-red" in html


def test_emitted_html_passes_both_audit_gates(
    sample_cli: Path, tmp_path: Path
) -> None:
    """The emitter is its own customer: zero findings from both auditors."""
    parser = load_parser_from_spec(f"{sample_cli}:make_parser")
    html_out: Path = tmp_path / "gui.html"
    html_out.write_text(render_html(walk_parser(parser)), encoding="utf-8")

    laws_proc = subprocess.run(
        [sys.executable, str(AUDIT_LAWS), str(html_out)],
        capture_output=True, text=True,
    )
    a11y_proc = subprocess.run(
        [sys.executable, str(LINT_A11Y), str(html_out)],
        capture_output=True, text=True,
    )
    assert laws_proc.returncode == 0, laws_proc.stdout + laws_proc.stderr
    assert a11y_proc.returncode == 0, a11y_proc.stdout + a11y_proc.stderr


# ── CLI surface ───────────────────────────────────────────────────────────


def test_version_flag() -> None:
    """``--version`` exits 0 and names the script."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "sprezzature-cli-gui-to-html" in proc.stdout


def test_help_flag_advertises_spec_and_flags() -> None:
    """``--help`` exits 0 and documents the spec syntax + flags."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    collapsed: str = " ".join(proc.stdout.split())
    assert "module:factory" in collapsed or ":factory" in collapsed
    assert "--out" in collapsed
    assert "--json" in collapsed


def test_json_output_round_trips(sample_cli: Path) -> None:
    """``--json`` emits a parsable JSON document matching walk_parser."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), f"{sample_cli}:make_parser", "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["prog"] == "sample"
    assert "encode" in payload["sub_commands"]


def test_out_flag_writes_file(sample_cli: Path, tmp_path: Path) -> None:
    """``--out PATH`` writes a complete HTML document and exits 0."""
    target: Path = tmp_path / "out.html"
    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            f"{sample_cli}:make_parser", "--out", str(target),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = target.read_text(encoding="utf-8")
    assert body.startswith("<!doctype html>")
    assert "</html>" in body


def test_bad_spec_exits_one(tmp_path: Path) -> None:
    """A missing factory exits 1 and surfaces a useful stderr message."""
    src: Path = tmp_path / "no_factory.py"
    src.write_text("def something_else(): return None\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), f"{src}:no_such_factory"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "no_such_factory" in proc.stderr


def test_malformed_spec_exits_one(tmp_path: Path) -> None:
    """A spec missing the ``:`` separator exits 1."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "no_colon_here"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "module:factory" in proc.stderr


# ── Click adapter ──────────────────────────────────────────────────────────


# Skip the Click block entirely when Click is not importable — the
# adapter is opt-in and the rest of the file must work without it.
click = pytest.importorskip("click")
from cli_to_gui import walk, walk_click  # noqa: E402


@pytest.fixture
def sample_click_cli(tmp_path: Path) -> Path:
    """
    Write a self-contained Click CLI exposing ``get_cli()``.

    Mirrors the argparse fixture's coverage: a group with two
    sub-commands, one exercising every parameter kind (option +
    flag + Choice + int + path + positional argument), so each
    test can hit the same shape via either adapter.
    """
    src: str = textwrap.dedent('''
        """Sample Click CLI for cli_to_gui tests."""
        import click

        @click.group()
        def cli():
            """Sample Click CLI used by the test suite."""
            pass

        @cli.command()
        @click.option("--input", "-i", required=True, help="Input path.")
        @click.option("--bitrate", type=int, default=128, help="Bitrate in kbps.")
        @click.option("--gain", type=float, default=1.5)
        @click.option(
            "--format", "fmt",
            type=click.Choice(["mp3", "ogg", "flac"]),
            default="mp3",
        )
        @click.option("--verbose", is_flag=True)
        def encode(input, bitrate, gain, fmt, verbose):
            """Encode a file (exercises every field kind)."""
            pass

        @cli.command()
        @click.argument("path", type=click.Path())
        def decode(path):
            """Decode a file."""
            pass

        def get_cli():
            return cli
    ''').lstrip()
    p: Path = tmp_path / "click_cli.py"
    p.write_text(src, encoding="utf-8")
    return p


def test_walk_click_dispatches_via_walk(sample_click_cli: Path) -> None:
    """The public :func:`walk` dispatches a Click app to the Click adapter."""
    from cli_to_gui import load_parser_from_spec

    cli_obj = load_parser_from_spec(f"{sample_click_cli}:get_cli")
    tree = walk(cli_obj)
    assert tree["prog"] == "cli"
    assert set(tree["sub_commands"]) == {"encode", "decode"}


def test_walk_click_covers_every_param_kind(sample_click_cli: Path) -> None:
    """Click adapter normalises options into the same canonical kinds."""
    from cli_to_gui import load_parser_from_spec

    cli_obj = load_parser_from_spec(f"{sample_click_cli}:get_cli")
    tree = walk_click(cli_obj)
    by_dest: dict[str, dict] = {
        a["dest"]: a for a in tree["sub_commands"]["encode"]["actions"]
    }
    assert by_dest["input"]["required"] is True
    assert by_dest["bitrate"]["kind"] == "int"
    assert by_dest["bitrate"]["default"] == 128
    assert by_dest["gain"]["kind"] == "float"
    assert by_dest["gain"]["default"] == 1.5
    assert by_dest["fmt"]["kind"] == "choice"
    assert set(by_dest["fmt"]["choices"]) == {"mp3", "ogg", "flac"}
    assert by_dest["verbose"]["kind"] == "bool"
    # Sub-command positional surfaces as kind=file (click.Path).
    decode_kinds = [
        a["kind"] for a in tree["sub_commands"]["decode"]["actions"]
    ]
    assert "file" in decode_kinds


def test_click_emitted_html_passes_both_audit_gates(
    sample_click_cli: Path, tmp_path: Path
) -> None:
    """Same dogfood claim as argparse: zero findings from both auditors."""
    from cli_to_gui import load_parser_from_spec, render_html

    cli_obj = load_parser_from_spec(f"{sample_click_cli}:get_cli")
    html_out: Path = tmp_path / "click.html"
    html_out.write_text(render_html(walk(cli_obj)), encoding="utf-8")
    laws_proc = subprocess.run(
        [sys.executable, str(AUDIT_LAWS), str(html_out)],
        capture_output=True, text=True,
    )
    a11y_proc = subprocess.run(
        [sys.executable, str(LINT_A11Y), str(html_out)],
        capture_output=True, text=True,
    )
    assert laws_proc.returncode == 0, laws_proc.stdout + laws_proc.stderr
    assert a11y_proc.returncode == 0, a11y_proc.stdout + a11y_proc.stderr


def test_walk_rejects_unsupported_objects() -> None:
    """``walk()`` raises TypeError on anything other than argparse/Click."""
    with pytest.raises(TypeError):
        walk("not a parser")


# ── --from-help adapter ────────────────────────────────────────────────────


from cli_to_gui import walk_from_help  # noqa: E402


def test_from_help_walks_argparse_cli(
    sample_cli: Path, tmp_path: Path
) -> None:
    """--from-help against an argparse CLI extracts the prog + sub-commands."""
    tree = walk_from_help(f"{sys.executable} {sample_cli}")
    assert tree["prog"] in {"sample", sample_cli.stem}
    # argparse's ``{encode,decode}`` positional gets parsed as
    # sub-commands; both should appear.
    assert "encode" in tree["sub_commands"]
    assert "decode" in tree["sub_commands"]


def test_from_help_preserves_choice_metadata(sample_cli: Path) -> None:
    """argparse renders ``{mp3,ogg,flac}`` in --help; we extract the list."""
    tree = walk_from_help(f"{sys.executable} {sample_cli}")
    encode = tree["sub_commands"]["encode"]
    by_dest = {a["dest"]: a for a in encode["actions"]}
    # ``format`` has a choice set surfaced in argparse's --help.
    fmt = by_dest.get("format")
    assert fmt is not None
    assert fmt["kind"] == "choice"
    assert set(fmt["choices"]) == {"mp3", "ogg", "flac"}


def test_from_help_html_passes_both_audit_gates(
    sample_cli: Path, tmp_path: Path
) -> None:
    """Same dogfood claim as the introspection adapters."""
    from cli_to_gui import render_html

    tree = walk_from_help(f"{sys.executable} {sample_cli}")
    html_out: Path = tmp_path / "fh.html"
    html_out.write_text(render_html(tree), encoding="utf-8")
    laws_proc = subprocess.run(
        [sys.executable, str(AUDIT_LAWS), str(html_out)],
        capture_output=True, text=True,
    )
    a11y_proc = subprocess.run(
        [sys.executable, str(LINT_A11Y), str(html_out)],
        capture_output=True, text=True,
    )
    assert laws_proc.returncode == 0, laws_proc.stdout + laws_proc.stderr
    assert a11y_proc.returncode == 0, a11y_proc.stdout + a11y_proc.stderr


def test_from_help_strips_python_wrapper_from_prog(
    sample_cli: Path,
) -> None:
    """``python3 script.py`` resolves to the script's own prog, not python3."""
    tree = walk_from_help(f"{sys.executable} {sample_cli}")
    assert tree["prog"] != "python"
    assert tree["prog"] != "python3"
    assert tree["prog"] != sys.executable


def test_from_help_cli_flag(sample_cli: Path) -> None:
    """The ``--from-help`` flag routes the spec through the subprocess path."""
    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--from-help", f"{sys.executable} {sample_cli}",
            "--json",
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["prog"] == "sample"
    assert "encode" in payload["sub_commands"]


def test_from_help_cli_help_advertises_the_flag() -> None:
    """``--help`` documents the ``--from-help`` flag."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    collapsed: str = " ".join(proc.stdout.split())
    assert "--from-help" in collapsed


def test_argparse_and_click_trees_have_same_shape(
    sample_cli: Path, sample_click_cli: Path
) -> None:
    """
    Both adapters emit dicts with the same top-level keys.

    Catches regressions where one adapter starts adding (or losing)
    a field the renderer reaches for — that would silently break
    the other side without firing a type error.
    """
    from cli_to_gui import load_parser_from_spec

    argp = walk(load_parser_from_spec(f"{sample_cli}:make_parser"))
    clk = walk(load_parser_from_spec(f"{sample_click_cli}:get_cli"))
    assert set(argp) == set(clk)
    # And the per-action shape must match too.
    argp_action = argp["sub_commands"]["encode"]["actions"][0]
    clk_action = clk["sub_commands"]["encode"]["actions"][0]
    assert set(argp_action) == set(clk_action)
