#!/usr/bin/env python3
"""
server
======

Tiny HTTP + Server-Sent-Events proxy for the cli-gui-demo example.

The server fronts the mock CLI (``cli/imgconvert.py``) over HTTP:

* ``GET  /``           — serves the static GUI under ``public/``.
* ``POST /run``        — spawns the CLI with the JSON-encoded payload and
                         streams stdout / stderr back as SSE events.

The implementation uses only ``http.server`` and ``subprocess`` so it
runs without ``pip install`` on any host with Python 3.9+. It is meant
for local demonstration only — no authentication, no logging, no TLS.

Usage
-----
::

    cd sprezzature-cli-gui/assets/examples/cli-gui-demo
    python server.py
    open http://localhost:8787

Notes
-----
* Python 3.9+, stdlib only.
* The server uses a thread per request so the SSE stream and any
  concurrent static-asset fetches do not block each other.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


# ── Configuration ────────────────────────────────────────────────────────────

#: Port the server listens on.
PORT: int = int(os.environ.get("PORT", "8787"))

#: Directory containing the static front-end files.
PUBLIC_DIR: Path = Path(__file__).resolve().parent / "public"

#: Path to the mock CLI executable.
CLI: Path = Path(__file__).resolve().parent / "cli" / "imgconvert.py"

#: Hard cap on a request body. The GUI only ever POSTs a tiny JSON payload, so
#: anything larger is malformed or hostile — reject before reading into memory.
MAX_BODY_BYTES: int = 1 << 20  # 1 MiB

#: Wall-clock ceiling on a wrapped-CLI run. A wedged child must not pin a server
#: thread (and its SSE connection) forever.
MAX_RUN_SECONDS: float = 120.0


# ── Helpers ─────────────────────────────────────────────────────────────────

def static_path(rel: str) -> Path | None:
    """
    Resolve a URL path to a file under :data:`PUBLIC_DIR`, safely.

    Parameters
    ----------
    rel : str
        URL path (e.g. ``/index.html`` or ``/app.js``). A trailing slash
        is treated as ``index.html``.

    Returns
    -------
    Path or None
        The resolved file path, or ``None`` if the resolution escapes
        :data:`PUBLIC_DIR` or the file does not exist.
    """
    if rel.endswith("/"):
        rel = rel + "index.html"
    # Strip a leading slash so ``Path`` does not treat it as an absolute path.
    candidate = (PUBLIC_DIR / rel.lstrip("/")).resolve()
    try:
        # Guard against path-traversal — the resolved path must live inside
        # PUBLIC_DIR.
        candidate.relative_to(PUBLIC_DIR)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def mime_type(path: Path) -> str:
    """
    Return a content-type for ``path`` based on its extension.

    Parameters
    ----------
    path : Path
        File whose MIME type is requested.

    Returns
    -------
    str
        A reasonable ``Content-Type`` header value.
    """
    ext = path.suffix.lower()
    return {
        ".html": "text/html; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg":  "image/svg+xml",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
        ".ico":  "image/x-icon",
    }.get(ext, "application/octet-stream")


# ── Request handler ─────────────────────────────────────────────────────────

class DemoHandler(BaseHTTPRequestHandler):
    """
    Serve static files from :data:`PUBLIC_DIR` and route ``POST /run`` to the CLI.
    """

    # Quieter than the default — only log errors.
    def log_message(self, fmt: str, *args) -> None:  # noqa: D401
        """Silence per-request logging (only errors surface)."""
        return

    # ── GET → static files ─────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802 — http.server requires this name.
        # GET '/' or '/index.html' both serve the page.
        """Serve the demo's static files (``/`` maps to ``index.html``)."""
        target = static_path(self.path or "/")
        if target is None:
            self.send_error(404, "Not Found")
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type(target))
        self.send_header("Content-Length", str(len(data)))
        # Disable caching during a live demo so file edits take effect.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ── POST → run the CLI and stream the output ──────────────────────────

    def do_POST(self) -> None:  # noqa: N802
        """Run the wrapped CLI for ``/run`` and stream its output back."""
        if self.path != "/run":
            self.send_error(404, "Not Found")
            return

        # Read the JSON body. ``Content-Length`` is required for a clean read;
        # a malformed or oversized value is a client error, not a 500.
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length <= 0:
            self.send_error(400, "Missing JSON body")
            return
        if length > MAX_BODY_BYTES:
            self.send_error(413, "Request body too large")
            return
        try:
            req: dict = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        # Translate the JSON payload into an imgconvert argv. The GUI sends
        # ``{ cmd, args }`` where ``args`` is already a list of strings.
        cmd: str = req.get("cmd", "")
        argv: list[str] = list(req.get("args") or [])
        if cmd not in {"resize", "convert", "optimize"}:
            self.send_error(400, "Unknown command")
            return

        # Send the SSE response header. The browser keeps the connection
        # open and surfaces each ``data:`` block as an ``onmessage`` event.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            proc = subprocess.Popen(
                [sys.executable, str(CLI), cmd, *argv],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as e:
            self._sse("error", str(e))
            return

        # A watchdog kills a wedged child so it can never pin this thread past
        # MAX_RUN_SECONDS. ``kill()`` unblocks the streaming loop below (EOF).
        watchdog = threading.Timer(MAX_RUN_SECONDS, proc.kill)
        watchdog.start()
        try:
            # Stream stdout line by line. ``bufsize=1`` + ``text=True`` gives us
            # line-buffered output without manual decoding.
            assert proc.stdout is not None
            for line in proc.stdout:
                self._sse("line", line.rstrip("\n"))
            proc.wait()
            self._sse("done", {"exit_code": proc.returncode})
        finally:
            # Always reap the child — on normal completion, on a client
            # disconnect (BrokenPipeError bubbles out of ``_sse``), or on the
            # watchdog kill. Leaving it running would leak a process per request.
            watchdog.cancel()
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    # ── SSE helper ────────────────────────────────────────────────────────

    def _sse(self, event: str, payload) -> None:
        """
        Emit a single SSE record on the open response.

        Parameters
        ----------
        event : str
            ``event:`` tag the browser will see on ``EventSource.addEventListener``.
        payload : str or dict
            Serialized as JSON when not a plain string.
        """
        body = payload if isinstance(payload, str) else json.dumps(payload)
        try:
            self.wfile.write(f"event: {event}\n".encode("utf-8"))
            self.wfile.write(f"data: {body}\n\n".encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # The client closed the tab; nothing to do.
            pass


# ── Bootstrap ──────────────────────────────────────────────────────────────

def main() -> int:
    """
    Bind the server and run forever (or until Ctrl-C).

    Returns
    -------
    int
        Process exit code. ``0`` on clean Ctrl-C.
    """
    print(f"→ Serving {PUBLIC_DIR} on http://localhost:{PORT}")
    print(f"→ Running CLI at {CLI}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), DemoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n→ Stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
