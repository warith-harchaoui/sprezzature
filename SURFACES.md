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
| 2 | **Command line** | an argparse command **and** its click twin, both on `PATH` | a human at a terminal |
| 3 | **HTTP API** | FastAPI app, shipped in a container | a service, a colleague's stack |
| 4 | **MCP** | the same routes republished as agent tools | an agent |
| 5 | **Skill** | `SKILL.md` in this monorepo | Claude |

`python scripts/audit_surfaces.py` reports which brick holds which, right now,
from what is on disk. This file is the contract; that script is the state.

It runs in CI too, as `--require-checkouts`, after `scripts/fetch_siblings.sh`
brings the nine siblings in metadata-only. Without the flag a brick with no
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

Both parsers, both installed. `argparse` because it is in the standard library
and therefore always available; `click` because its sub-commands, types and
`Choice` validation carry the richer shapes without hand-rolling them.

The measurement that matters is `[project.scripts]`, not the source tree. A
parser living in a module that no console script names is reachable from a
clone and from nowhere else. `sprezzature-ux-laws` shipped exactly that: its
own `--help` advertised `sprezzature-ux-laws-audit`, the README told people to
run `python scripts/audit_laws_of_ux.py` — a path that exists in a clone and
not in a wheel — and `pip install sprezzature-ux-laws` put nothing on `PATH`
but the MCP server.

**Carried by** `sprezzature_<brick>/cli.py` (argparse) and
`sprezzature_<brick>/cli_click.py` (click), both named in `[project.scripts]`.

## 3. HTTP API — and the container it ships in

A FastAPI app in `api.py`, with its dependencies behind an `api` extra so that
nobody installing the library pays for `uvicorn`.

Then **a `Dockerfile` and a `docker-compose.yml`, always together.** This is
not a style preference. A Dockerfile alone is a recipe, not a way in: it leaves
the next person to reconstruct the port mapping, the volume, the environment
and the command by reading it — and to get one of them wrong, in silence, with
a container that starts and does the wrong thing. The compose file is where
those four live as declared facts, so that `docker compose up` is the whole
onboarding. One container is reason enough; a second only makes it worse.

**Carried by** `sprezzature_<brick>/api.py`, the `api` extra, `Dockerfile`,
`docker-compose.yml`.

## 4. MCP

`fastapi-mcp` mounts the FastAPI app that already exists as MCP tools, so the
agent surface is not a second implementation — it is the same routes, named.
This is the surface that lets someone describe the problem in their own words
and have the engine answer.

Two things make it real rather than nominal: an `mcp` extra that declares
`fastapi-mcp` (pinned below `mcp 2.0`, which broke `FastApiMCP(...)`
construction), and a `sprezzature-<brick>-mcp` console script, because an MCP
server a host cannot spawn is not a server.

**Carried by** `sprezzature_<brick>/mcp.py`, the `mcp` extra, a `-mcp` console
script.

## 5. Skill

`SKILL.md` in this monorepo, with its `references/triggers.md` catalogue and a
`description` that says both when to fire and — since the TRIGGERS pass — when
**not** to, naming the sibling brick that should answer instead.

The skill is not documentation for the other four surfaces. It is the surface
where the vocabulary is the problem's ("make this chart readable") rather than
the tool's (`--palette`, `--contrast-ratio`).

**Carried by** `<brick>/SKILL.md` here, listed in `SKILLS.txt`.

---

## Publication

A surface nobody can install is a surface in a drawer. Every brick owes both
halves:

- **its own name on PyPI**, so `pip install sprezzature-maps` works for someone
  who wants one brick;
- **a floor in this repo's `all` extra**, so `pip install sprezzature[all]`
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
│   ├── cli.py             # 2. command line, argparse  → make-map
│   ├── cli_click.py       # 2. command line, click     → sprezzature-maps
│   ├── api.py             # 3. FastAPI app
│   └── mcp.py             # 4. fastapi-mcp over that app → sprezzature-maps-mcp
├── scripts/               #    packaged as sprezzature_maps_scripts
├── Dockerfile             # 3. runs the API without a Python install
├── docker-compose.yml     # 3. port, volume, environment, command — declared
├── pyproject.toml         #    extras: cli, api, mcp, dev
└── tests/
```

with `SKILL.md` for the same brick living here, in the monorepo.

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
