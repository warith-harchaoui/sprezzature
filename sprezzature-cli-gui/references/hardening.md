# Hardening notes — `sprezzature-cli-gui` host

The skill scaffolds the GUI. **You wire and harden the host.** This
file is the opinionated checklist for promoting the
`assets/examples/cli-gui-demo/server.py` SSE proxy (or any equivalent
host: FastAPI, Express, Tauri `invoke`) from "runs on my laptop" to
"safe on a shared machine or internal network".

Scope: hosts that spawn subprocesses on behalf of HTTP requests. If
your host is Tauri / Electron with `invoke()`-style IPC, only the
*subprocess sandbox* and *input validation* sections apply.

## Threat model in one line

A request arriving at `/run` becomes a `subprocess` call. The
question is always: **what can the request author do that the
operator did not intend?** Five concrete answers below, each with the
smallest fix that closes it.

## 1. Bind to loopback by default

The demo binds `127.0.0.1`; keep it that way for any host that
spawns subprocesses. If you need LAN access, put the GUI behind a
reverse proxy you already trust (Caddy, nginx, Tailscale) and keep
the Python process on `127.0.0.1`.

```python
# good — only the host's loopback interface
server = ThreadingHTTPServer(("127.0.0.1", PORT), DemoHandler)

# bad — accepts requests from anyone who can route to this port
server = ThreadingHTTPServer(("0.0.0.0", PORT), DemoHandler)
```

If you must bind a non-loopback interface, *every other section below
becomes mandatory*, not optional.

## 2. Authentication on `/run`

Loopback binding stops outsiders. It does **not** stop other
processes on the same host (browser extensions, another user's
session, malware) from posting to `/run` and getting the same
subprocess execution. Add a shared secret:

```python
import os

# Read once at startup so an unset token fails loudly before the first
# request arrives, not silently after deploy.
EXPECTED_TOKEN: str = os.environ["SPREZZATURE_CLI_GUI_TOKEN"]


def do_POST(self) -> None:
    """
    Reject any POST that does not present the shared bearer token.

    Notes
    -----
    Loopback binding stops outsiders. The bearer token stops other
    processes on the same host (browser extensions, another user's
    session, malware) from posting to ``/run`` and getting the same
    subprocess execution.
    """
    if self.path != "/run":
        return self.send_error(404)
    # Constant-time comparison would be nicer; for a single-secret
    # bearer this is the minimum bar.
    if self.headers.get("Authorization") != f"Bearer {EXPECTED_TOKEN}":
        return self.send_error(401)
    # … existing logic
```

Front-end sends the token from a config snippet your installer wrote
to `localStorage`. Rotate by restarting the server with a new
`SPREZZATURE_CLI_GUI_TOKEN`. For multi-user, swap to per-session tokens
issued at login.

Tauri equivalent: register the `invoke` handler with an explicit
allowlist (`tauri.conf.json` → `"allowlist"` → narrow `"shell.scope"`
to specific binaries + arguments). Tauri's IPC is process-local;
authentication is the binary trust boundary.

## 3. Validate the command and the args

The demo already restricts `cmd` to `{"resize", "convert", "optimize"}`.
Generalize: **never pass user-controlled strings as the first
subprocess argument**, and **never pass a list whose first element
is `bash`/`sh`/`cmd.exe`**. Two rules cover most of the surface.

```python
from pathlib import Path

#: Sub-commands the host will spawn. Anything else is an error.
ALLOWED_COMMANDS: set[str] = {"resize", "convert", "optimize"}

#: Per-command flag allow-list. The mapping is a plain ``dict`` of
#: ``str -> set[str]`` so it's easy to merge / extend at startup.
ALLOWED_FLAGS: dict[str, set[str]] = {
    "resize":   {"--width", "--height", "--in", "--out"},
    "convert":  {"--format", "--in", "--out"},
    "optimize": {"--quality", "--in", "--out"},
}


def validate(cmd: str, argv: list[str], sandbox_root: Path) -> None:
    """
    Reject a request whose ``cmd`` / ``argv`` falls outside the allow-list.

    Parameters
    ----------
    cmd : str
        Sub-command name received from the GUI payload.
    argv : list of str
        Already-split argv that will be passed to ``subprocess.Popen``.
    sandbox_root : Path
        Resolved directory that every file-path argument must live under.

    Raises
    ------
    ValueError
        If the sub-command is unknown, a flag is not in the per-command
        allow-list, or a file-path argument resolves outside
        ``sandbox_root``.
    """
    if cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"unknown cmd: {cmd}")
    # Set difference makes the "unknown flag" error message friendly.
    flags: set[str] = {a for a in argv if a.startswith("--")}
    unknown: set[str] = flags - ALLOWED_FLAGS[cmd]
    if unknown:
        raise ValueError(f"unknown flag(s) for {cmd}: {sorted(unknown)}")
    for arg in argv:
        if arg.startswith("-"):
            continue
        # File-path arguments — confine to the project sandbox.
        # ``relative_to`` raises ``ValueError`` on path-traversal attempts.
        Path(arg).resolve().relative_to(sandbox_root)
```

Allow-list, don't deny-list. If the user can introduce a new flag,
they can introduce `--exec` or whatever undocumented backdoor the
underlying CLI ships.

## 4. Subprocess sandbox

Pass arguments, not strings. Cap time and memory. Run with a clean
environment. Run from a controlled cwd.

```python
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

#: Wall-clock budget per request. Hard ceiling — kill the whole tree past it.
MAX_SECONDS: float = 30.0


def run_sandboxed(
    cli: Path,
    cmd: str,
    argv: list[str],
    sandbox_root: Path,
    on_line: "callable[[str], None]",
) -> int:
    """
    Spawn ``cli`` with the given sub-command and stream its output.

    Parameters
    ----------
    cli : Path
        Absolute path to the wrapped CLI script.
    cmd : str
        Sub-command name (already validated by :func:`validate`).
    argv : list of str
        Sub-command arguments (already validated).
    sandbox_root : Path
        Working directory for the child process; also the filesystem
        boundary used by :func:`validate`.
    on_line : callable
        Called once per stdout line so the caller can ship it as SSE.

    Returns
    -------
    int
        Child process exit code.

    Raises
    ------
    TimeoutError
        When the child runs past :data:`MAX_SECONDS`.
    """
    # Argv as a list — never a single string — so the shell never sees
    # user input. ``shell=False`` is the default; spelled out as a reminder.
    proc = subprocess.Popen(
        [sys.executable, str(cli), cmd, *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,                          # line-buffered
        cwd=str(sandbox_root),              # never the user's HOME
        env={                               # explicit env allow-list
            "PATH": "/usr/bin:/bin",
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        },
        start_new_session=True,             # killpg takes the whole tree
        shell=False,
    )
    started: float = time.monotonic()
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            on_line(line.rstrip("\n"))
            if time.monotonic() - started > MAX_SECONDS:
                # ``start_new_session=True`` set the child as a process-
                # group leader, so killpg reaps any grandchildren too.
                os.killpg(proc.pid, signal.SIGKILL)
                raise TimeoutError(f"exceeded {MAX_SECONDS}s")
    finally:
        # ``wait`` is bounded so a stuck child cannot hold the request.
        proc.wait(timeout=5)
    return proc.returncode
```

Two hard rules:

- **`shell=False` always** (the default: never set `shell=True`,
  never call `subprocess.run("cmd " + user_input, shell=True)`).
- **Argv as a list, never a string.** Even with `shell=False`,
  `subprocess.Popen("cmd " + user_input)` re-introduces injection
  when `Popen` splits the string on the wrong shell-quote conventions.

On Linux, additionally consider `resource.setrlimit` in a
`preexec_fn=` to cap RSS, CPU time, and open file handles per child.
On macOS, `sandbox-exec` profiles work. On Windows, Job Objects.

## 5. Per-route rate limit

Cap requests-per-token-per-window so a runaway browser tab cannot
spam `/run` and pin the CPU. A 10-line in-memory token bucket is
enough for single-host hosts:

```python
import time

#: Sliding-window size in seconds.
RATE_WINDOW_S: float = 60.0
#: Max accepted requests per token within :data:`RATE_WINDOW_S`.
RATE_LIMIT: int = 10
#: Per-token timestamps — kept as plain dict so it serialises cleanly
#: to logs / debug endpoints without a custom encoder.
_hits: dict[str, list[float]] = {}


def rate_limited(token: str) -> bool:
    """
    Return ``True`` when ``token`` has spent its window budget.

    Parameters
    ----------
    token : str
        Caller's bearer token (the rate-limit identity).

    Returns
    -------
    bool
        ``True`` if the request must be rejected with HTTP 429.

    Notes
    -----
    Drops timestamps older than :data:`RATE_WINDOW_S` on each call —
    no separate sweep thread needed. Good enough for single-process
    hosts; for multi-worker, switch to Redis-backed leaky bucket.
    """
    now: float = time.monotonic()
    # Filter then store; the assignment garbage-collects expired entries.
    bucket: list[float] = [t for t in _hits.get(token, []) if now - t < RATE_WINDOW_S]
    _hits[token] = bucket
    if len(bucket) >= RATE_LIMIT:
        return True
    bucket.append(now)
    return False


# In ``do_POST``, after the auth check:
#     if rate_limited(token):
#         return self.send_error(429, "Too Many Requests")
```

For multi-host or multi-process, switch to Redis-backed leaky bucket
(`redis-py` has the primitive); but at that scale you have already
outgrown a stdlib SSE proxy and should be on FastAPI + uvicorn behind
a real reverse proxy.

## 6. CORS posture

Default to `Access-Control-Allow-Origin: null` (i.e. don't set the
header). If the GUI and the API share an origin, you don't need
CORS. If they don't, pin the allowed origin explicitly:

```python
import os

#: Single allowed origin. Falls back to the demo's loopback URL so a
#: forgotten env var doesn't open the door wider than ``server.py``.
ALLOWED_ORIGIN: str = os.environ.get(
    "SPREZZATURE_CLI_GUI_ORIGIN", "http://localhost:8787",
)

# In ``do_POST`` / ``do_GET`` headers:
self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
self.send_header("Vary", "Origin")  # cache the right answer per origin
```

Never echo back the request's `Origin` header verbatim. Never send
`Access-Control-Allow-Origin: *` paired with credentials; browsers
will block it anyway, but the intent matters.

## 7. Logging — say what happened, redact what doesn't matter

The demo silences `log_message` for a clean console. For production:

- Log: timestamp, route, response code, command, duration, exit code.
- **Don't log**: full argv (user paths leak); auth tokens; the response
  body. Truncate stdout/stderr to the first 256 bytes for an audit
  trail, not a transcript.

```python
import logging

log: logging.Logger = logging.getLogger("sprezzature-cli-gui")

# Logged shape is a plain dict in the message — easy to grep, easy to
# feed to a JSON formatter later without rewriting the call sites.
log.info(
    "run cmd=%s exit=%d dur_ms=%d argv_count=%d",
    cmd, proc.returncode, int(elapsed * 1000), len(argv),
)
```

If you must keep full transcripts (debugging, support), write them to
a separate path with mode `0o600` and rotate weekly.

## 8. TLS

The demo speaks plain HTTP because everything is loopback. If you
need to reach across a network at all, **don't add TLS to the stdlib
HTTPServer**: terminate TLS at a reverse proxy (Caddy auto-issues
Let's Encrypt certs in three lines of config; Tailscale Funnel does
it with one CLI flag) and keep the Python process on plain HTTP
behind it.

## Checklist before promoting from demo

Apply in order; stop only when you can answer yes to every line.

- [ ] Bound to `127.0.0.1` (or behind a reverse proxy you own)
- [ ] `Authorization: Bearer <token>` required on `/run`
- [ ] `cmd` and `--flag` names checked against an explicit allow-list
- [ ] File-path args resolved and confined to a `SANDBOX_ROOT`
- [ ] `subprocess.Popen(..., shell=False, cwd=SANDBOX_ROOT, env={...},
      start_new_session=True)` and argv as a list
- [ ] Wall-clock timeout enforced with `os.killpg`
- [ ] Per-token rate limit (e.g. 10 req / 60 s)
- [ ] CORS unset or pinned to one origin; no `*` with credentials
- [ ] Logs include cmd / exit / duration; no argv, no token, no body
- [ ] TLS terminated at a reverse proxy (if the surface leaves loopback)

## When to outgrow the stdlib host

Switch to FastAPI / Starlette + uvicorn when any of the following
becomes true:

- You need more than one worker (the stdlib `ThreadingHTTPServer`
  shares state in-process; multi-worker rate-limit needs Redis).
- You want OpenAPI / pydantic schema validation instead of hand-rolled
  `validate(...)`.
- The SSE proxy needs to handle reconnects, last-event-id resumption,
  or WebSockets.
- You're packaging as a Tauri sidecar: Tauri's `invoke()` is a
  better fit than HTTP for in-process IPC.

`sprezzature-cli-gui` is parser-agnostic; the host is replaceable. Keep
the GUI as the stable surface, swap the host as the surface area
grows.
