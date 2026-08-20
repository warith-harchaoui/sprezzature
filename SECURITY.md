# Security policy

The project is released under the [Berkeley Software Distribution (BSD)-3-Clause license](LICENSE.md)
(the same one as scikit-learn). That license carries no warranty
and disclaims liability, but security disclosure has its own
norms, set out below.

## What "security" means here

`sprezzature` is a collection of Claude skills plus stdlib-and-Pillow
Python scripts. There is no service, no daemon, no network listener
shipped by the repo itself. The realistic attack surface is:

- Scripts that execute as the user who invokes them. They read and
  write files in the project directory and `~/.cache/sprezzature-skill/`.
- Scripts that download model weights or call a local Ollama daemon
  (`install_alt_ai.py`, `install_captions.py`,
  `alt_from_ollama.py`, `meta_from_ollama.py`,
  `plain_language.py`, `captions_from_whisper.py`). HTTPS to the
  upstream registries (Hugging Face mirror, Ollama registry) and
  loopback to `127.0.0.1:11434`.
- Emitted HyperText Markup Language (HTML) / JavaScript (JS) that ships into the user's site. The skill bans
  inline `<script>` and inline `<style>` for production output and
  the `validate.py` gate refuses to pass with them present.

Out of scope: model output. The skill calls a local model; the model
can hallucinate. That is a quality issue, not a security issue.

## Reporting a vulnerability

Open a GitHub issue at
<https://github.com/warith-harchaoui/sprezzature/issues> with the label
`security`. If the report is sensitive, email
<warith@deraison.ai> instead and the issue can be opened publicly
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

- **`sprezzature-cli-gui/scripts/cli_to_gui.py`** loads the user's named
  parser-factory by importing the target module. If the target's
  top-level (or its factory) has side effects (opens files, prints
  to a daemon socket, mutates the environment): those run at GUI
  generation time. Treat the spec argument the same way you treat
  `python -c '...'`: only point it at code you would already run.
  The same caveat applies to the `--from-help` mode: it runs your
  command with `--help` appended via `subprocess.run` (no shell
  invocation, `shlex.split` parsed args, 10 s timeout, stderr +
  stdout captured). Only point it at binaries you trust.

- **`sprezzature-publish/scripts/meta_from_ollama.py`** and
  **`…/plain_language.py`** speak to a *local* Ollama daemon on
  `localhost:11434`. They never send content over the public
  internet, but they do hand the document to a model running on the
  developer's machine. Do not run them against content you would
  not show to the local model.

Neither path opens a network port; neither auto-updates itself; both
are stdlib + a single optional dependency (the SDK or the daemon).

## Supply-chain notes

- The skill pins no minor versions for the Python dependencies it
  declares (`requests`, `click`, `Pillow`, `numpy`). Pin yourself if
  you need reproducibility.
- Bundled fonts ship under their own license (Roboto, Roboto Serif,
  Roboto Mono: all SIL Open Font License (OFL)). See `LICENSE.md` for the carve-out.
- **Distribution channels.** Two supported install paths:
  1. **Tagged GitHub release** (recommended). Each release ships
     per-skill tarballs, a four-skill bundle tarball, and a single
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
  `sprezzature-ui/scripts/validate.py`) and the deterministic test suite
  (`pytest`) run with stdlib + PyYAML only and never touch the
  network; running them locally is a cheap way to confirm an install
  is what it claims to be.
