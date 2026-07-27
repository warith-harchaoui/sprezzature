"""
test_install_captions — coverage for ``sprezzature-accessibility/scripts/install_captions.py``.

Mocks ``importlib.util.find_spec`` for the install-status probe, the
pip subprocess for the install step, and ``pywhispercpp.utils.download_model``
for the weights fetch.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

import install_captions as ic


def _ok_proc() -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _fail_proc(code: int = 1) -> SimpleNamespace:
    return SimpleNamespace(returncode=code, stdout="", stderr="")


# ── _is_installed ──────────────────────────────────────────────────────────

class TestIsInstalled:
    def test_true_for_stdlib(self):
        # ``os`` is always importable.
        assert ic._is_installed("os") is True

    def test_false_for_unknown(self):
        # An invented name is never importable.
        assert ic._is_installed("definitely_not_a_real_package_xyz123") is False


# ── ensure_captions_engine ─────────────────────────────────────────────────

class TestEnsureCaptionsEngine:
    def test_short_circuits_when_already_installed(self, monkeypatch, capsys):
        monkeypatch.setattr(ic, "_is_installed", lambda pkg: True)
        # If pip were invoked the test would fail because subprocess.run was
        # not mocked; the short-circuit must skip it entirely.
        ic.ensure_captions_engine()
        assert "already installed" in capsys.readouterr().out

    def test_runs_pip_when_missing(self, monkeypatch):
        # First probe: missing. Post-install probe: installed.
        states = iter([False, True])
        monkeypatch.setattr(ic, "_is_installed", lambda pkg: next(states))
        seen: list[list[str]] = []
        def fake_run(argv, **kw):
            seen.append(argv)
            return _ok_proc()
        monkeypatch.setattr(ic.subprocess, "run", fake_run)
        ic.ensure_captions_engine()
        # The active interpreter is invoked with ``-m pip install`` for the
        # pinned vocal-helper git spec (which pulls pywhispercpp).
        assert seen and seen[0][:3] == [sys.executable, "-m", "pip"]
        assert any("vocal-helper" in part for part in seen[0])

    def test_pip_failure_exits(self, monkeypatch):
        monkeypatch.setattr(ic, "_is_installed", lambda pkg: False)
        monkeypatch.setattr(ic.subprocess, "run", lambda *a, **kw: _fail_proc(1))
        with pytest.raises(SystemExit) as excinfo:
            ic.ensure_captions_engine()
        assert "pip install" in str(excinfo.value)

    def test_pip_succeeds_but_package_still_missing_exits(self, monkeypatch):
        # pip claims success but the post-install probe still fails — possibly
        # virtualenv shenanigans. The installer must not pretend it worked.
        states = iter([False, False])
        monkeypatch.setattr(ic, "_is_installed", lambda pkg: next(states))
        monkeypatch.setattr(ic.subprocess, "run", lambda *a, **kw: _ok_proc())
        with pytest.raises(SystemExit) as excinfo:
            ic.ensure_captions_engine()
        assert "import path" in str(excinfo.value)


# ── download_model ─────────────────────────────────────────────────────────

class TestDownloadModel:
    def test_unknown_alias_exits(self):
        with pytest.raises(SystemExit) as excinfo:
            ic.download_model("invented-alias")
        assert "Unknown model" in str(excinfo.value)

    def test_known_alias_invokes_downloader(self, tmp_path, monkeypatch):
        # Point the whisper dir at tmp_path.
        monkeypatch.setattr(ic, "WHISPER_DIR", tmp_path / "whisper")

        # Inject a fake ``pywhispercpp.utils.download_model`` that writes a
        # tiny file and returns its path.
        target_path = tmp_path / "whisper" / "ggml-small.bin"
        def fake_download(name, out_dir):
            # The function reports the absolute path of the downloaded weights.
            from pathlib import Path
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(b"x" * 2048)
            return str(target_path)
        fake_utils = types.ModuleType("pywhispercpp.utils")
        fake_utils.download_model = fake_download
        fake_root = types.ModuleType("pywhispercpp")
        fake_root.utils = fake_utils
        monkeypatch.setitem(sys.modules, "pywhispercpp", fake_root)
        monkeypatch.setitem(sys.modules, "pywhispercpp.utils", fake_utils)

        out = ic.download_model("small")
        assert out == target_path
        assert target_path.is_file()

    def test_download_exception_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ic, "WHISPER_DIR", tmp_path / "whisper")
        # Fake downloader that raises — main path surfaces the message via
        # ``sys.exit`` rather than letting the trace bubble.
        def boom(name, out_dir):
            raise RuntimeError("network down")
        fake_utils = types.ModuleType("pywhispercpp.utils")
        fake_utils.download_model = boom
        fake_root = types.ModuleType("pywhispercpp")
        fake_root.utils = fake_utils
        monkeypatch.setitem(sys.modules, "pywhispercpp", fake_root)
        monkeypatch.setitem(sys.modules, "pywhispercpp.utils", fake_utils)

        with pytest.raises(SystemExit) as excinfo:
            ic.download_model("small")
        assert "network down" in str(excinfo.value)
