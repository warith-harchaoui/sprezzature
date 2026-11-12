# Surfaces: the five ways into a brick

Every brick of this suite is an **engine** — a piece of code that does one
thing and gets it right. An engine nobody can reach is a private script. So
each engine is published through five surfaces, and the rule is that **the
engine is written once** and the five surfaces are thin wrappers over it. The
moment a surface starts holding logic of its own, the engine has two versions
of the truth and one of them is wrong.

The five, in the order a project usually grows them:

| # | Surface | What it is | Who it is for |
|---|---|---|---|
| 1 | **Library** | `import sprezzature_<brick>` | another program |
| 2 | **Command line** | one click command, on `PATH` under two names | a human at a terminal |
| 3 | **HTTP API** | FastAPI app, shipped in a container | a service, a colleague's stack |
| 4 | **MCP** | the same routes republished as agent tools | an agent |
| 5 | **Skill** | `SKILL.md` inside the package, installed by `sprezzature-<brick>-skill --install` | Claude, OpenCode |

`python scripts/audit_surfaces.py` reports which brick holds which, right now,
from what is on disk. This file is the contract; that script is the state.

It runs in CI too, as `--require-checkouts`, after `scripts/fetch_siblings.sh`
brings the ten siblings in metadata-only. Without the flag a brick with no
checkout is reported as undecidable and does not fail the run — right on a
machine holding one clone, wrong in the one place that knows every clone
should be there.

---

## 1. Library

`import sprezzature_colors` must hand back something you can call. The package's
`__init__.py` exports the engine — not a version string.

This is the surface most easily faked. Four bricks of this suite shipped an
`__init__.py` holding `__version__`, `__author__`, `__email__` and a docstring,
and nothing else: the engine lived in `sprezzature_<brick>_scripts.<tool>`, a
package named for how it was built rather than for what it does. `pip install`
worked, `import` worked, and the caller still had nothing to call. A library
surface that exports no callable is not a library surface.

**Carried by** `sprezzature_<brick>/__init__.py`, with an `__all__`.

## 2. Command line

One parser, installed under two names. `click`, because its sub-commands,
types and `Choice` validation carry the richer shapes without hand-rolling
them; one of it, because two doors drift.

The measurement that matters is `[project.scripts]`, not the source tree. A
parser living in a module that no console script names is reachable from a
clone and from nowhere else. `sprezzature-ux-laws` shipped exactly that: its
own `--help` advertised `sprezzature-ux-laws-audit`, the README told people to
run `python scripts/audit_laws_of_ux.py` — a path that exists in a clone and
not in a wheel — and `pip install sprezzature-ux-laws` put nothing on `PATH`
but the MCP server.

**Carried by** `sprezzature_<brick>/cli.py`, in click, named twice in
`[project.scripts]`: the historical `make-<thing>` spelling and the suite-wide
`sprezzature-<brick>` one, both pointing at the same callable.

There were two parsers until 2026-10-25 — an argparse front door and a click
twin that imported the argparse module's table. The pair cost every
sub-command twice, forced a conditional `main` whose two definitions had to
agree by hand (and a mypy suppression in every brick to tolerate it), and let
a command go missing from one door with nothing to notice: `make-map density`
existed in argparse and not in click. One door cannot drift from itself.

click is a **base dependency**, not an extra. With argparse gone no parser
ships with Python, so an optional click would mean an install whose own
commands do not run.

The rule reached the per-tool commands on 2026-11-04. The groups had been
click since 2026-10-25, but `sprezzature-<brick>-<tool>` and every
`*-mcp` server still pointed at argparse `main`s in `scripts/`, which a grep
of the package never saw. Every brick now carries a guard that runs each
console script with `--help` and expects click's `Usage:`, and fails on an
`argparse` import in its own modules. Two uses stay on purpose:
sprezzature-cli-gui reads argparse parsers as its job, and the standalone
per-chart generators of sprezzature-figures are scripts, not commands.

## 3. HTTP API — and the container it ships in

A FastAPI app in `api.py`. FastAPI and uvicorn are in the base install since
2026-11-01, like every other dependency: no brick has a feature extra.

Then **a `Dockerfile` and a `docker-compose.yml`, always together.** This is
not a style preference. A Dockerfile alone is a recipe, not a way in: it leaves
the next person to reconstruct the port mapping, the volume, the environment
and the command by reading it — and to get one of them wrong, in silence, with
a container that starts and does the wrong thing. The compose file is where
those four live as declared facts, so that `docker compose up` is the whole
onboarding. One container is reason enough; a second only makes it worse.

The image runs the brick's `-mcp` server, not `uvicorn <brick>.api:app`. The
MCP endpoint is mounted when `mcp.py` is imported, so an image that served the
API module alone answered every `/v1/...` route and had no `/mcp`: that was
the case in all ten bricks until 2026-11-04. One process on port 8000 now
serves both.

**Carried by** `sprezzature_<brick>/api.py`, `Dockerfile`, `docker-compose.yml`.

## 4. MCP

`fastapi-mcp` mounts the FastAPI app that already exists as MCP tools, so the
agent surface is not a second implementation — it is the same routes, named.
This is the surface that lets someone describe the problem in their own words
and have the engine answer.

Two things make it real rather than nominal: `fastapi-mcp` in the base
install (with `mcp` pinned below 2.0, which broke `FastApiMCP(...)`
construction), and a `sprezzature-<brick>-mcp` console script, because an MCP
server a host cannot spawn is not a server. The `description` passed to
`FastApiMCP` is what a host reads first: two bricks served another brick's
description until 2026-11-04.

**Carried by** `sprezzature_<brick>/mcp.py`, a `-mcp` console script, the
image's `CMD`.

## 5. Skill

`SKILL.md` inside the brick's own package, with its `references/` and the
`references/triggers.md` catalogue, and a `description` that says both when to
fire and — since the TRIGGERS pass — when **not** to, naming the sibling brick
that should answer instead. The format is Anthropic's, from *The Complete Guide
to Building Skills for Claude*.

Until 2026-11-12 the ten skills lived in this repository only, so `pip install
sprezzature-maps` brought a library, a command line, an API and an MCP server,
and nothing an agent could route on: the one surface written for an agent did
not travel with the package. Each brick now ships its skill in its wheel.
`sprezzature-<brick>-skill` (also `sprezzature-<brick> skill` where the command
is a group) says whether the copy under `~/.claude/skills/` is in step, and
`--install` puts it there (`--agent opencode` for `~/.opencode/skills/`).
`sprezzature-skills --install`, from this repository's package, does the ten at
once. This repository keeps no copy: it reads the skills from the brick
checkouts beside it, through `skill_dir()` in `scripts/skills_manifest.py`, to
validate them and to generate their trigger catalogues.

The skill is not documentation for the other four surfaces. It is the surface
where the vocabulary is the problem's ("make this chart readable") rather than
the tool's (`--palette`, `--contrast-ratio`).

**Carried by** `sprezzature_<brick>/skill/SKILL.md` in the brick, declared as
`package-data` so the wheel carries it, installed by `sprezzature_<brick>/_skill.py`
(shared verbatim across the ten by `scripts/sync_helpers.py`), and listed in
this repository's `SKILLS.txt`.

---

## Publication

A surface nobody can install is a surface in a drawer. Every brick owes both
halves:

- **its own name on PyPI**, so `pip install sprezzature-maps` works for someone
  who wants one brick;
- **a floor in this repo's base install**, so `pip install sprezzature`
  pulls the suite.

Check the first with `python scripts/audit_surfaces.py --pypi`, which reads the
**simple index** rather than `/pypi/<name>/json` — the two are cached
independently and the legacy JSON endpoint lags by minutes after an upload,
long enough to report NOT PUBLISHED for something `pip` already resolves.
Before tagging the umbrella, `python scripts/check_all_extra_resolves.py`
checks the other direction: that no floor names a version which exists only on
a laptop.

## The reference layout

`sprezzature-maps` is the one to copy:

```
sprezzature-maps/
├── sprezzature_maps/
│   ├── __init__.py        # 1. library — exports the engine
│   ├── cli.py             # 2. command line, click → make-map AND sprezzature-maps
│   ├── api.py             # 3. FastAPI app
│   ├── mcp.py             # 4. fastapi-mcp over that app → sprezzature-maps-mcp
│   ├── skill/             # 5. SKILL.md + references/, shipped in the wheel
│   ├── _skill.py          # 5. sprezzature-maps-skill: report, or --install
│   └── editor/            #    the model-backed Editor, sprezzature-maps
├── scripts/               #    packaged as sprezzature_maps_scripts
├── Dockerfile             # 3. runs sprezzature-maps-mcp: the API and /mcp on port 8000
├── docker-compose.yml     # 3. port, volume, environment, command — declared
├── .dockerignore          #    keeps .git and .private/ out of the image
├── pyproject.toml         #    one install, no feature extras; `dev` only
└── tests/
```

The skill lives in the brick; this repository holds none.

**After extracting a brick, run `python scripts/sync_helpers.py`.** The
shared helpers (`_argparse.py`, `_click.py`, `_lang.py`, `_vocab.py`,
`_vtt.py`) are copied into every repository on purpose, and an extraction
takes a snapshot of them at whatever moment the copy happens. `_vtt.py` drifted
exactly that way: the new repo was seeded before a sync reached the monorepo's
copy, and the source folder emptied immediately after — so the drift was born
at the one moment nothing could see it. Everything stayed internally
consistent and the suite stayed green; it surfaced hours later, as a missing
attribute, in something unrelated.

## Declaring an exemption

Not every brick owes every surface, and forcing one is its own kind of damage.

`sprezzature-ui` was the live case, and it is worth recording how it
resolved. Its API was declared exempt because *writing a component* is the
model's work guided by `SKILL.md` and no HTTP route can carry it. That
reasoning was right about the generation half and wrong about the rest: the
i18n audit **is** engine-able — source in, findings out — so the brick now
ships one route rather than none. The exemption became a lie in the useful
direction and was removed.

The lesson is not "exemptions are bad". It is that an exemption covers a
*surface*, and a brick is rarely all generation or all engine. Ask which
half is which before writing one down.

So exemptions are allowed, and they are **declared with their reason** in
`EXEMPTIONS` in `scripts/audit_surfaces.py`. The reason is required —
`tests/test_surfaces_contract.py` refuses an exemption without one. The point
is to force the thought, not to provide an escape hatch: the table is where
"we did not get to it" and "it would be wrong to do it" stop looking alike.
