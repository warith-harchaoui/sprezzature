# Boundaries

Which package owns what, between the sprezzature suite and ai-helpers.

**The principle: ai-helpers owns the primitive, sprezzature owns the opinion.**
The test for any capability — would this be identical for somebody with
entirely different taste? If yes it is a primitive. If it encodes a judgement
about what good looks like, it is sprezzature's.

## The voice is four layers, not a choice between two packages

| Layer | Owns |
|---|---|
| `speaker-engines` | Model weights, self-hosted; nothing fetched from Hugging Face at runtime. |
| `speaker-helper` | **The engines**: Kokoro, OpenVoice, Chatterbox, Voicebox. espeak-ng handling, cloning, the evaluation gate. |
| `sprezzature-audio` | "The sound modality in both directions" — drives speaker-helper, and owns the suite's single WebVTT module. |
| `sprezzature-publish`, `sprezzature-video` | Applying it: a narrated post, a film's narration track. |

`sprezzature-audio` declares `narrate = ["speaker-helper[kokoro,detect]"]`, so
Kokoro arrives through speaker-helper whichever door you knock on. **A
sprezzature package wanting a voice depends on `sprezzature-audio[narrate]`,
never on speaker-helper directly** — the espeak-ng loader can kill a process
from C with no Python traceback, and that handling lives one layer down where
it was learned.

`vocal-helper` and `audio-helper` do no synthesis. They decode, separate and
diarize.

## The moving picture

| Layer | Owns |
|---|---|
| `video-helper` | ffmpeg primitives: frames, convert, compress, concat, overlay, mux, burn subtitles. |
| `capture-helper` | Frames out of the room rather than out of a file. |
| `sprezzature-figures`, `-maps` | What appears inside the frame. |
| `sprezzature-video` | What the film **is**: storyboard, claims, asset ledger, captions, poster, series. |
| Hyperframes (Apache-2.0, third party) | Turning a composition into frames. Behind a seam. |

Audio duration is `audio_helper.get_audio_duration`; video duration is
`video_helper.video_duration`. That split is deliberate — the latter's own
docstring calls itself the mirror of the former "for the video side", and it
raises on a file with no video stream.
