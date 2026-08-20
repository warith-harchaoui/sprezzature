# Contributing to `sprezzature`

The project is released under the [Berkeley Software Distribution (BSD)-3-Clause
license](LICENSE.md), the same one used by scikit-learn. Permissive:
use, modify, redistribute, sell, ship in commercial products, with
three short conditions (copyright notice in source + in binary
distribution docs; no endorsement-without-permission). Contributions
are welcome on the same terms.

## Before you start

Pick the skill your change belongs to:

| Change touches… | Skill |
|---|---|
| user-interface (UI) generation, components, design tokens, color, dataviz, design system, anti-patterns, ergonomic criteria, ux psychology, Apple Human Interface Guidelines (HIG) references | `sprezzature-ui/` |
| command-line-interface (CLI) → graphical-user-interface (GUI) workflow, the runnable demo, host adapters (Tauri / FastAPI / Express / stdlib server-sent events (SSE)) | `sprezzature-cli-gui/` |
| Markdown → website workflow, meta tags, favicons, site indexes, plain-language rewriter, i18n | `sprezzature-publish/` |
| `lint_a11y.py` (static HyperText Markup Language (HTML) accessibility (a11y) lint) | `sprezzature-accessibility/` |
| Web Content Accessibility Guidelines (WCAG) contrast audit, color-vision-deficiency (CVD) simulation, curated palette, perceptual lighten / darken | `sprezzature-colors/` |
| World Wide Web Consortium (W3C) alt text via local Ollama vision (`qwen3-vl:8b`) | `sprezzature-vision/` |
| Local WebVTT / SubRip subtitle format (SRT) captions via whisper.cpp | `sprezzature-audio/` |

Cross-skill changes (e.g. a stack rule that affects every skill) start in
`sprezzature-ui/` since it is the source of truth for the shared rules, then
the companion skills reference it.

## Local setup

```bash
git clone https://github.com/warith-harchaoui/sprezzature.git
cd sprezzature
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

The deterministic gates (`validate.py`, `lint_a11y.py`,
`audit_contrast.py`, `site_indexes.py`) are stdlib only. The
Ollama-backed scripts need a running Ollama daemon and the relevant
model; see each skill's `SKILL.md` for the install path.

## Running tests

```bash
pytest                  # default: fast, deterministic
pytest -m eval          # opt-in deepeval LLM-quality tests (need Ollama)
```

The default invocation skips the `eval` marker. Tests must pass before a
pull request (PR) is merged.

## Linting & types

The continuous-integration (CI) `lint` job runs two blocking static gates: the audit half of the suite's
make/audit pattern. Before opening a PR:

```bash
ruff check .            # lint audit: must be clean (CI blocks otherwise)
ruff check --fix .      # lint make: apply the auto-fixable subset
./scripts/run_mypy.sh   # type audit: per-skill-dir mypy (config in mypy.ini)
```

Config lives in `ruff.toml` and `mypy.ini`. Three conventions the config
already encodes: `E741` (`l`) is allowed because it is the OKLab *lightness*
channel in the colour math; helper functions a script re-exports for its tests
use the `name as name` form so `ruff --fix` never deletes a live re-export
(keep that form when adding one); and the type gate uses `ignore_missing_imports`
so the heavy optional backends (torch / nemo / dowhy / ollama) need not be
installed to type-check the code's own annotations.

## Conventions

- **No emojis in shipped files** (SKILL.md, references, scripts). The
  README header may use flag emojis for the language switcher only.
- **No marketing-voice phrases** in SKILL.md or references. The
  validator (`sprezzature-ui/scripts/validate.py`) catches the worst
  offenders.
- **Hard rules are hard.** If a change weakens rule 1–9 in any
  SKILL.md, document the reason in the PR description and update
  `CHANGELOG.md`.
- **BSD-3-Clause.** New files inherit the repo's BSD-3-Clause
  license. Do not include code copied from a license-incompatible
  source (GPL, AGPL) without documenting a clean-room carve-out;
  permissively-licensed (Massachusetts Institute of Technology (MIT) / BSD / Apache / Unlicense) snippets
  are fine to vendor as long as the upstream copyright notice is
  preserved. The Roboto / Roboto Serif / Roboto Mono SIL Open Font License (OFL) bundle is
  the template for how to ship a carve-out.

## What we ship

- Reproducible: stdlib-only validators run in any CI container.
- Honest: scope and limitations are stated, not hidden.
- Composable: each skill works on its own; companions are additive.
- Bilingual-ready: text content is written so a future translator can
  add a second language without touching markup.

## What we will not ship

- React / Vue / Svelte / Solid / Angular code. The skill refuses to
  emit framework code by design.
- Marketing voice ("seamlessly", "production-grade", "non-negotiable",
  "boost your productivity"). The validator gates on this.
- Auto-fix suggestions presented as final decisions for things that
  need a designer's eye (palette choices, typography pairings).

## Artificial-intelligence (AI) tool attribution

AI tools may be used during development, but **authorship and responsibility
remain with the human maintainers**. Commit authorship, release notes, and the
contributor list name only human contributors. Do **not** add
`Co-Authored-By: …` AI trailers or list an AI assistant as an author or
co-author. This is enforced in CI by `.github/workflows/no-claude-trailers.yml`,
which fails a push whose commits carry an AI-attribution trailer.

## Release process (maintainer)

Two equivalent paths; pick one per release and don't mix them.

- **Tag-only** (recommended). Bump the version in the four
  `SKILL.md` frontmatters + `README.md` / `LISEZMOI.md` install
  snippets + a new `CHANGELOG.md` section, commit, then
  `git tag -a v<version> -m "release v<version>" && git push origin
  main v<version>`. The `release.yml` workflow runs
  `scripts/release.sh` on the runner, publishes the GitHub release,
  attaches the five tarballs + `SHA256SUMS`, and generates notes
  from commits since the previous tag.

- **Local-build, then tag-push**. Run `scripts/release.sh <version>`
  to build into `dist/`, verify locally, then optionally publish
  manually with `gh release create v<version> dist/*.tar.gz
  dist/SHA256SUMS …`. The workflow still triggers on the tag push;
  since v0.6.1 the publish step is idempotent: it detects the
  existing release and skips with success rather than re-uploading
  and rewriting `SHA256SUMS`. (Before v0.6.1, the workflow exited 1
  with `a release with the same tag name already exists` whenever
  the maintainer published locally first.)

The artifacts the workflow uploads and the artifacts a local
`scripts/release.sh` produces are **not byte-identical** (gzip /
tar versions differ between macOS and the ubuntu-latest runner), so
the SHA256SUMS the user fetches depends on which path produced the
release. Either path is fine; pick one consciously.

## Reporting issues

GitHub issues at <https://github.com/warith-harchaoui/sprezzature/issues>.
For things that involve the Anthropic skill spec itself, also see
<https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf>.

## Maintainer

[Warith Harchaoui](https://www.linkedin.com/in/warith-harchaoui/).
