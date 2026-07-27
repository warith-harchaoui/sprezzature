"""
test_install_alt_ai — coverage for ``sprezzature-accessibility/scripts/install_alt_ai.py``.

Every shell-out is mocked. Covers the model picker, the three platform
install paths (brew on Darwin, official installer on Linux, winget on
Windows), and the daemon-up retry loop.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import install_alt_ai as ia


def _ok_proc() -> SimpleNamespace:
    """Build a successful ``CompletedProcess`` stand-in."""
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _fail_proc(code: int = 1) -> SimpleNamespace:
    return SimpleNamespace(returncode=code, stdout="", stderr="")


# ── pick_model ─────────────────────────────────────────────────────────────

class TestPickModel:
    def test_env_seam_wins(self, monkeypatch):
        # OLLAMA_MODEL is a TEST SEAM only (never a user-facing model choice).
        monkeypatch.setenv("OLLAMA_MODEL", "explicit:tag")
        assert ia.pick_model() == "explicit:tag"

    def test_default_is_registry_base_no_mlx(self, monkeypatch):
        # No ``-mlx`` auto-suffix on any platform — that only ever named a
        # maintainer-local build and 404'd on a fresh box. With the seam unset
        # the one authorized model (qwen3-vl:8b) is used.
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        assert ia.pick_model() == ia.BASE
        assert not ia.pick_model().endswith("-mlx")


# ── install_ollama paths ───────────────────────────────────────────────────

class TestInstallOllama:
    def test_no_op_when_already_installed(self, monkeypatch, capsys):
        monkeypatch.setattr(ia, "has", lambda c: c == "ollama")
        ia.install_ollama()
        out = capsys.readouterr().out
        assert "already installed" in out

    def test_darwin_uses_brew_when_present(self, monkeypatch):
        # Pretend ollama is missing but brew is on PATH.
        monkeypatch.setattr(ia, "has", lambda c: c == "brew")
        monkeypatch.setattr(ia.platform, "system", lambda: "Darwin")
        calls: list[list[str]] = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _ok_proc()
        monkeypatch.setattr(ia, "run", fake_run)
        ia.install_ollama()
        assert calls == [["brew", "install", "ollama"]]

    def test_darwin_without_brew_exits(self, monkeypatch):
        monkeypatch.setattr(ia, "has", lambda c: False)
        monkeypatch.setattr(ia.platform, "system", lambda: "Darwin")
        with pytest.raises(SystemExit) as excinfo:
            ia.install_ollama()
        # The exit message names the install path explicitly.
        assert "Homebrew" in str(excinfo.value)

    def test_linux_pipes_curl_to_sh(self, monkeypatch):
        # Pretend ollama missing but curl present.
        monkeypatch.setattr(ia, "has", lambda c: c == "curl")
        monkeypatch.setattr(ia.platform, "system", lambda: "Linux")

        # Stub urllib.urlopen to return a fixed installer script.
        class FakeResp:
            def __init__(self): self._data = b"#!/bin/sh\necho ok\n"
            def read(self): return self._data
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr(ia.urllib.request, "urlopen", lambda *a, **kw: FakeResp())

        # Stub subprocess.run for the ``sh`` invocation; capture stdin.
        seen: dict = {}
        def fake_run(argv, **kw):
            seen["argv"] = argv
            seen["input"] = kw.get("input")
            return _ok_proc()
        monkeypatch.setattr(ia.subprocess, "run", fake_run)

        ia.install_ollama()
        assert seen["argv"] == ["sh"]
        # The installer script bytes flow through stdin.
        assert "echo ok" in seen["input"]

    def test_linux_without_curl_exits(self, monkeypatch):
        monkeypatch.setattr(ia, "has", lambda c: False)
        monkeypatch.setattr(ia.platform, "system", lambda: "Linux")
        with pytest.raises(SystemExit) as excinfo:
            ia.install_ollama()
        assert "curl" in str(excinfo.value)

    def test_windows_uses_winget(self, monkeypatch):
        monkeypatch.setattr(ia, "has", lambda c: c == "winget")
        monkeypatch.setattr(ia.platform, "system", lambda: "Windows")
        calls: list[list[str]] = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _ok_proc()
        monkeypatch.setattr(ia, "run", fake_run)
        ia.install_ollama()
        assert calls[0][0] == "winget"
        assert "Ollama.Ollama" in calls[0]

    def test_unknown_platform_exits(self, monkeypatch):
        monkeypatch.setattr(ia, "has", lambda c: False)
        monkeypatch.setattr(ia.platform, "system", lambda: "Plan9")
        with pytest.raises(SystemExit):
            ia.install_ollama()


# ── daemon_up + ensure_daemon ─────────────────────────────────────────────

class TestDaemonUp:
    def test_true_when_ollama_list_succeeds(self, monkeypatch):
        monkeypatch.setattr(ia.subprocess, "run",
                            lambda *a, **kw: _ok_proc())
        assert ia.daemon_up() is True

    def test_false_when_missing_binary(self, monkeypatch):
        def boom(*a, **kw):
            raise FileNotFoundError
        monkeypatch.setattr(ia.subprocess, "run", boom)
        assert ia.daemon_up() is False

    def test_false_on_timeout(self, monkeypatch):
        def boom(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="ollama", timeout=10)
        monkeypatch.setattr(ia.subprocess, "run", boom)
        assert ia.daemon_up() is False


class TestEnsureDaemon:
    def test_no_op_when_already_up(self, monkeypatch):
        monkeypatch.setattr(ia, "daemon_up", lambda: True)
        # If Popen were called, the test would surface that as an unexpected
        # MagicMock activation; instead we just verify no exception is raised.
        ia.ensure_daemon()

    def test_starts_then_waits_until_up(self, monkeypatch):
        # First probe says "no daemon", second says "yes" — emulating start.
        states = iter([False, True])
        monkeypatch.setattr(ia, "daemon_up", lambda: next(states))
        popen_calls: list = []
        monkeypatch.setattr(ia.subprocess, "Popen",
                            lambda *a, **kw: popen_calls.append((a, kw)))
        # Speed up the polling loop.
        monkeypatch.setattr(ia.time, "sleep", lambda s: None)
        ia.ensure_daemon()
        assert len(popen_calls) == 1
        # The spawn uses ``start_new_session=True`` so the daemon outlives
        # the installer's terminal session.
        assert popen_calls[0][1].get("start_new_session") is True

    def test_exits_after_ten_failed_retries(self, monkeypatch):
        # Daemon never comes up — every probe returns False.
        monkeypatch.setattr(ia, "daemon_up", lambda: False)
        monkeypatch.setattr(ia.subprocess, "Popen",
                            lambda *a, **kw: MagicMock())
        monkeypatch.setattr(ia.time, "sleep", lambda s: None)
        with pytest.raises(SystemExit) as excinfo:
            ia.ensure_daemon()
        # The exit message names the 10 s budget.
        assert "10 seconds" in str(excinfo.value)
