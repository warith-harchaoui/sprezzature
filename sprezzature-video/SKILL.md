---
name: sprezzature-video
description: >-
  Check what a project video SAYS against the project itself. A film burns its
  claims into pixels where nothing re-reads them, so a count stays on screen
  long after the catalogue behind it has grown. verify checks declared claims
  against the code; scan catches numbers on screen that no claim accounts for;
  the asset ledger says whether a film can be rendered again from a clone
  (tracked, derived, or exists-nowhere-else); captions come from the narration
  script and the measured audio, not a transcript. Use it when a video
  states a fact about a project, when the project changed under a film already
  shipped, and before any re-render. Trigger phrases: "make a launch video",
  "the demo video is out of date", "verify the claims in this video", "re-cut
  the film", "is this number still right", "can we rebuild this video",
  "poster frame". Not this one when: the ask is motion
  design, which belongs to the renderer. The exhaustive trigger catalogue is in
  `references/triggers.md`.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.1
---

# sprezzature-video

> The tools below ship as the standalone package [`sprezzature-video`](https://github.com/warith-harchaoui/sprezzature-video) (`pip install sprezzature-video`, every surface included). It is invoked as `make-film …` or `sprezzature-video …`, two names for one Click group, with the agent surface `sprezzature-video-mcp …`. There is no `scripts/` folder in this monorepo; the SKILL.md here is the agentic contract.

You built a video about a project. The project moved. Nothing told the video.

## What this is for

A README gets re-read. A number burned into a keyframe does not. That asymmetry
is the whole subject: the five films on sprezzature.ai said **"127 chart kinds"**
for weeks after the catalogue reached 167, baked into ten compositions and five
rendered MP4s, with nothing anywhere watching.

This skill is the thing that watches.

## When to reach for it

Three triggers, and the second is the one people miss:

1. **A video states a fact about a project.** Counts, sizes, speeds, quoted
   claims. The moment one appears, it has acquired something that will rot.
2. **The project changed.** A catalogue grew, a package shipped, a module
   merged. The film is now wrong and will stay wrong silently.
3. **You are about to re-render.** Audit the assets first: a render that dies
   halfway because a licensed track exists on exactly one disk is a worse
   discovery than the audit that said so.

## How to use it

Eight commands. The checks (`verify`, `scan`, `assets`, `pitch`, `calque`, and
`prose` under `--strict`) exit 1 when the film fails; every command exits 2 on
a wrong call, and `poster` exits 2 when `ffmpeg` is missing.

```bash
make-film verify film.yaml --root .                      # declared claims vs the code; exit 1 = lying
make-film scan composition/index.html --spec film.yaml   # numbers nothing accounts for
make-film assets film.yaml --tree _assets --repo .       # can this be rebuilt? --restore copies back absent tracked files
make-film captions film.yaml --lang en --out film.en.vtt # --translated omits voice tags
make-film poster film.mp4 --out film.jpg --at 7.6        # one JPEG frame, through ffmpeg
make-film pitch film.yaml --duration 60                  # problem, solution, secret sauce; --voice fr reads the narration
make-film calque film.yaml --from en --to fr             # was the second language written or translated?
make-film prose script.txt --lang en --strict            # the mechanical half of the writing charter
```

Both directions matter. `verify` protects the claims somebody remembered to
declare; `scan` catches the one typed into a keyframe at midnight. Running only
the first is how "127" survived.

A film spec is YAML: `claims`, `assets`, `narration`, `scenes` and `pitch`. The
things that go stale live in a file a reviewer can diff rather than inside a
generator nobody opens.

## The surfaces

Library, the command line (`sprezzature-video` or `make-film`, Click only), a
FastAPI HTTP API, and MCP tools mounted on that same app at `/mcp`. One
implementation underneath, so the terminal answer and the HTTP answer cannot
disagree.

The five MCP tools are the routes' `operation_id`s:

| MCP tool | Route | What it answers |
|---|---|---|
| `verify_claims` | `POST /v1/verify` | Declared claims against files under a root on the server. |
| `scan_composition` | `POST /v1/scan` | Numbers on screen that no claim accounts for. |
| `build_captions` | `POST /v1/captions` | WebVTT from narration lines. |
| `list_methods` | `GET /v1/methods` | The five ways a claim's truth is read from the code. |
| `health` | `GET /health` | Liveness probe. |

The asset audit, the poster, `pitch`, `calque` and `prose` are command line and
library only.

## What it does not do

**It does not render.** Rendering is done outside the package, by Hyperframes
by default, because frame-grabbing is the most commoditised step in the chain
and the least opinionated. If the request is "add a transition" or "animate
this", it belongs to the renderer.

**It synthesizes nothing.** The narration audio is made by `sprezzature-audio`;
this package measures each file's length. The caption file is written by
`video_helper.subtitles` in `video-helper`, the suite's shared WebVTT writer;
SubRip output is `video_helper.vtt2srt`. See `references/boundaries.md`.

## Neighbours

| The question | Where it goes |
|---|---|
| What appears in the frame? | `sprezzature-figures`, `sprezzature-maps` |
| How does it sound? | `sprezzature-audio` |
| Does the page around it pass? | `sprezzature-accessibility`, `sprezzature-ux-laws` |

## Two modes: make and audit

| Mode | Tool | Purpose |
|---|---|---|
| **Make**: captions | `make-film captions <spec> --lang en` | WebVTT from the narration script and the **measured** length of each audio file. Exact where a transcriber is only close. |
| **Make**: a poster | `make-film poster <film.mp4> --out <file.jpg> --at 7.6` | The idle frame. Not 0.0 on a film that fades in. `post.bake_poster` in the library makes it frame 0, for feeds that regenerate their own thumbnail. |
| **Audit**: the claims | `make-film verify <spec> --root .` | Every declared claim against the code that decides it. Exit 1 means the film is lying. |
| **Audit**: the screen | `make-film scan <composition> --spec <spec>` | Every number visible on screen that no claim accounts for. Without this half only the numbers somebody remembered to declare are protected, never the one that drifted. |
| **Audit**: the asset tree | `make-film assets <spec> --tree _assets` | Can this be rendered again from a clone? Tracked, derived, or nowhere else at all. A divergence is reported, never silently repaired. |
| **Audit**: the pitch | `make-film pitch <spec> --duration 60` | Guy KAWASAKI's order: problem, solution, secret sauce, on screen or in the voice. |
| **Audit**: the second language | `make-film calque <spec> --from en --to fr` | A suspicion, line by line, that one cut is a translation of the other. |
| **Audit**: the writing | `make-film prose <file> --lang en --strict` | Dashes, comma-and, negative openings, banned phrases. Modals are counted, never failed on. |

The gap in this table is rendering, and it is deliberate. A second renderer
here would be a worse one, and the judgement this package holds is in the
storyboard and the claims, not in the frame grabber.
