# Security policy

The project is released under the [Berkeley Software Distribution (BSD)-3-Clause license](LICENSE.md)
(the same one as scikit-learn). That license carries no warranty
and disclaims liability, but security disclosure has its own
norms, set out below.

## What "security" means here

`sprezzature` is a collection of Claude skills, a `sprezzature-skills`
command that copies them, and maintenance scripts. The repo itself ships no
service, daemon or network listener. `pip install sprezzature` also installs
the ten brick packages, and each of those carries an HTTP API and an MCP
server (`<brick>-mcp`, and a Docker image that runs it); they listen only when
you start them. The realistic attack surface is:

- Commands that execute as the user who invokes them. They read and
  write files in the project directory and the bricks' caches under
  `~/.cache/`.
- Commands that download model weights or call a local Ollama daemon
  (`sprezzature-accessibility-install-alt`, `sprezzature-audio-install`,
  `make-alt`, `sprezzature-publish-meta`, `sprezzature-publish-plain`,
  `sprezzature-audio-captions`, …). HTTPS to the upstream registries
  (Hugging Face mirror, Ollama registry) and loopback to `127.0.0.1:11434`.
- The bricks' API and MCP servers, when started: they bind the address you
  give them, with no authentication. Keep them on loopback or behind your own
  proxy.
- Emitted HyperText Markup Language (HTML) / JavaScript (JS) that ships into the user's site.

Out of scope: model output. The skill calls a local model; the model
can hallucinate. That is a quality issue, not a security issue.

## Reporting a vulnerability

Open a GitHub issue at
<https://github.com/warith-harchaoui/sprezzature/issues> with the label
`security`. If the report is sensitive, email
<warithmetics@deraison.ai> instead and the issue can be opened publicly
once a fix or workaround lands.

There is no bounty program and no service-level agreement (SLA). The repo is maintained by one
person on best-effort time. Realistic turnaround:

- Acknowledgement: within one week.
- Fix or written rationale: within four weeks for issues that affect
  a script that touches the network or executes a subprocess; longer
  for everything else.

## Disclosure

Coordinated disclosure is preferred but not required. The
BSD-3-Clause license does not place any embargo obligation on
researchers. If you publish first, please link the issue or commit
that addresses the problem so users can act on the same information.

## Local execution caveats

A handful of scripts execute *code the user names on the command
line*. These are intended for use against trusted local code only.

- **`sprezzature-cli-gui`** loads the user's named
  parser-factory by importing the target module. If the target's
  top-level (or its factory) has side effects (opens files, prints
  to a daemon socket, mutates the environment): those run at GUI
  generation time. Treat the spec argument the same way you treat
  `python -c '...'`: only point it at code you would already run.
  The same caveat applies to the `--from-help` mode: it runs your
  command with `--help` appended via `subprocess.run` (no shell
  invocation, `shlex.split` parsed args, 10 s timeout, stderr +
  stdout captured). Only point it at binaries you trust.

- **`sprezzature-publish-meta`** and
  **`sprezzature-publish-plain`** speak to a *local* Ollama daemon on
  `localhost:11434`. They never send content over the public
  internet, but they do hand the document to a model running on the
  developer's machine. Do not run them against content you would
  not show to the local model.

Neither path opens a network port, and neither auto-updates itself.

## Supply-chain notes

- The `sprezzature` package declares floors, not pins, on the ten bricks,
  and the bricks declare floors on their own dependencies. Pin yourself if
  you need reproducibility.
- Bundled fonts ship under their own license (Roboto, Roboto Serif,
  Roboto Mono: all SIL Open Font License (OFL)). See `LICENSE.md` for the carve-out.
- **Distribution channels.** Two supported install paths:
  1. **Tagged GitHub release** (recommended). Each release ships
     per-skill tarballs, a bundle tarball of every skill, and a single
     `SHA256SUMS` file built by `scripts/release.sh` and published by
     the `release.yml` workflow on every `v*.*.*` tag push. Users
     verify with `shasum -a 256 -c SHA256SUMS` (or `sha256sum -c`)
     before extracting; README's *Install* section walks the full
     flow. The publish step is **idempotent**: if the maintainer ran
     `gh release create` locally before the workflow caught up, the
     workflow detects the existing release and skips with success
     rather than re-uploading and rewriting the already-published
     `SHA256SUMS` (which would invalidate downloads in flight).
  2. **`git clone` + `cp -r`** (developer / contributor path). No
     verification step beyond `git fsck`. Documented in
     `CONTRIBUTING.md`.
- **What we don't sign yet.** Release artifacts carry Secure Hash Algorithm (SHA) SHA-256 checksums
  but are **not GPG-signed** and are **not Sigstore-attested**.
  Treat the checksum as integrity proof against transport corruption,
  not as authenticity proof of the maintainer. If you need
  authenticity, build from a tagged commit you've reviewed yourself
  (the `release.yml` workflow is in-tree and reproducible).
- **What lives in the supply chain.** Direct upstream registries:
  PyPI (`pip install -r requirements-dev.txt`), the Ollama registry
  (model pulls), Hugging Face mirrors (whisper.cpp model files), the
  jsDelivr `gh` proxy (Tailwind Play content-delivery network (CDN) in prototype mode). No
  vendored binaries, no auto-updaters.
- **Trust model, short version.** This repo ships text and Python
  scripts you can read top-to-bottom in under an hour. Read what you
  install. The validators (`scripts/validate_all.py`,
  `scripts/validate_content.py`) and the deterministic test suite
  (`pytest`) run with stdlib + PyYAML only and never touch the
  network; running them locally is a cheap way to confirm an install
  is what it claims to be.
