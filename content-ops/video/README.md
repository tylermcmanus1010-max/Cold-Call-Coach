# Video Production Pipeline

One command turns a scene file into a finished, branded, voiced MP4.

```
python3 content-ops/video/build.py content-ops/video/scenes/short-01.json
```

Output: `content-ops/video/out/<name>.mp4` — 1080×1920, 30fps, H.264 + AAC.
Ready to upload.

## What it does

```
scene JSON (script + vo lines)
   └── voice.py    synthesises one VO clip per scene
   └──             writes each clip's real duration back into the scene file
   └── render.py   draws every frame to match that timing
   └── ffmpeg      encodes and muxes
```

The important part is step two: **scene timing is derived from the voiceover,
not guessed.** Change the voice and the whole video re-times itself. No manual
sync, ever.

## Voice backends

| Backend | When it runs | Quality |
|---|---|---|
| `elevenlabs` | `ELEVENLABS_API_KEY` set *and* the API reachable | Ship quality |
| `espeak` | Always. Local, offline, no weights | Robotic placeholder |

Selection is automatic — ElevenLabs if available, espeak otherwise. Force it
with `--backend`.

**In this container espeak is the only option.** Every hosted TTS endpoint
(ElevenLabs, OpenAI, Deepgram, Replicate, fal, HuggingFace) is refused by the
environment's egress policy, and no PyPI package ships usable neural weights.
The ElevenLabs adapter is written and correct; it starts working the moment it
runs somewhere with network access, or the policy allows it. Nothing else in
the pipeline changes.

`--silent` skips voice entirely and keeps whatever durations are in the spec.
Caption-led silent video is genuinely viable on TikTok and Reels, where most
first views are sound-off. It is weak on YouTube.

## Scene types

| Type | Use | Key fields |
|---|---|---|
| `title` | Hooks. Word-by-word reveal. | `text`, `highlight`, `reveal` |
| `line` | A single statement. Fade and rise. | `text`, `highlight` |
| `script` | The exact words. Red rule, staggered reveal. | `text`, `label` |
| `counter` | Animated number for data reveals. | `value`, `label` |
| `waveform` | Stands in for call-audio moments. | `caption` |

Every scene takes `vo` (the narration line), `duration` (overwritten by the VO
pass), and `pad` (silence after the line, default 0.45s).

`highlight` recolours matching words brand red. Punctuation and case are
normalised, so `"reflex."` matches `reflex`.

## Layout constraints baked in

- 110px side margins, 300px top / 480px bottom kept clear of platform UI
- Text auto-fits: font size steps down until the wrapped block fits its box, so
  a long line never overflows or clips
- Brand mark top-left on every frame

## Staying monetisable

YouTube tightened its **inauthentic content** policy in July 2026. It does not
ban AI-assisted video — it targets *generic, repetitive, template-based* output
with little original value. Enforcement is a three-strike ladder: warning, then
90-day suspension, then permanent removal from the Partner Program.

This pipeline is a production tool, not a content mill, and the difference has
to stay real:

- **The substance is original.** Real call analysis, real numbers, specific
  scripts. That is what "original value" means, and it is the part no renderer
  provides.
- **Vary the format.** Rotate scene types and structures. Five hundred videos
  from one template is the exact pattern the policy targets.
- **Never mass-produce near-identical videos.** Volume without variation is the
  trigger.
- Long-form carries commentary and analysis, not narrated listicles.

Treat the renderer the way an editor treats After Effects: it executes the
production. It does not supply the originality.

## Render cost

About 2.5 minutes of wall clock per minute of finished video, single-threaded.
A 40-second short takes roughly 100 seconds end to end.
