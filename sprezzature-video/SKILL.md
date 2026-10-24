---
name: sprezzature-video
description: >-
  Check what a project video SAYS against the project itself. A film burns its
  claims into pixels where nothing re-reads them, so a count stays on screen
  long after the catalogue behind it has grown. verify checks declared claims
  against the code; scan catches numbers on screen that no claim accounts for;
  the asset ledger says whether a film can be rendered again from a clone
  (tracked, derived, or exists-nowhere-else); captions come from the narration
  script and the measured audio, not a transcript. Use it when a video states a
  fact about a project, when the project changed under a film already shipped,
  and before any re-render. Trigger phrases: "make a launch video", "the demo
  video is out of date", "verify the claims in this video", "re-cut the film",
  "is this number still right", "can we rebuild this video", "poster frame".
  Not this one when: the ask is motion design, which belongs to the renderer.
  The exhaustive trigger catalogue is in `references/triggers.md`.
metadata:
  author: Warith HARCHAOUI
  version: 1.6.0
---

# sprezzature-video

> The tools below ship as the standalone package [`sprezzature-video`](https://github.com/warith-harchaoui/sprezzature-video) (`pip install sprezzature-video`), invoked as `make-film …`, with the Click twin `sprezzature-video …` and the agent surface `sprezzature-video-mcp …`. There is no `scripts/` folder in this monorepo; the SKILL.md here is the agentic contract.

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

```bash
make-film verify film.yaml --root .      # declared claims vs the code; exit 1 = lying
make-film scan composition/index.html --spec film.yaml   # numbers nothing accounts for
make-film assets film.yaml --tree _assets --repo .       # can this be rebuilt?
make-film captions film.yaml --lang en --out film.en.vtt
make-film poster film.mp4 --out film.jpg --at 7.6
```

Both directions matter. `verify` protects the claims somebody remembered to
declare; `scan` catches the one typed into a keyframe at midnight. Running only
the first is how "127" survived.

A film spec is YAML — claims, assets, narration — so the things that go stale
live in a file a reviewer can diff rather than inside a generator nobody opens.

## The surfaces

Library, `make-film` (argparse), `sprezzature-video` (Click), a FastAPI HTTP
API, and MCP tools mounted on that same app. One implementation underneath, so
the terminal answer and the HTTP answer cannot disagree.

## What it does not do

**It does not render.** Rendering is delegated — Hyperframes by default, with
Playwright and ffmpeg not excluded — because frame-grabbing is the most
commoditised step in the chain and the least opinionated. If the request is
"add a transition" or "animate this", it belongs to the renderer.

It does not synthesize speech or write WebVTT by hand either: narration comes
through `sprezzature-audio[narrate]`, and the VTT writer is that package's
single shared module. See `references/boundaries.md`.

## Neighbours

| The question | Where it goes |
|---|---|
| What appears in the frame? | `sprezzature-figures`, `sprezzature-maps` |
| How does it sound? | `sprezzature-audio` |
| Does the page around it pass? | `sprezzature-accessibility`, `sprezzature-ux-laws` |

## Two modes: make and audit

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — captions | `make-film captions <spec> --lang en` | WebVTT from the narration script and the **measured** length of each audio file. Exact where a transcriber is only close. |
| **Make** — a poster | `make-film poster <film.mp4> --at 7.6` | The idle frame. Not 0.0 on a film that fades in, and baked as frame 0 when a feed will regenerate its own thumbnail. |
| **Audit** — the claims | `make-film verify <spec> --root .` | Every declared claim against the code that decides it. Exit 1 means the film is lying. |
| **Audit** — the screen | `make-film scan <composition>` | Every number visible on screen that no claim accounts for. Without this half only the numbers somebody remembered to declare are protected — never the one that drifted. |
| **Audit** — the asset tree | `make-film assets <spec> --tree _assets` | Can this be rendered again from a clone? Tracked, derived, or nowhere else at all. A divergence is reported, never silently repaired. |

The gap in this table is rendering, and it is deliberate: the frames are drawn
by Hyperframes behind a seam. A second renderer here would be a worse one, and
the judgement this package holds is in the storyboard and the claims, not in
the frame grabber.
