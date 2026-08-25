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
| `gemini` | `GEMINI_API_KEY` set. **Reachable from this container.** | Ship quality |
| `elevenlabs` | `ELEVENLABS_API_KEY` set *and* API reachable | Ship quality |
| `espeak` | Always. Local, offline, no weights | Robotic placeholder |

Selection is automatic in that order. Force one with `--backend`.

### Reachability, tested

| Host | Result |
|---|---|
| `generativelanguage.googleapis.com` | **Reachable** — real API errors, not proxy blocks |
| `aiplatform.googleapis.com` | **Reachable** |
| ElevenLabs, OpenAI, Deepgram | 403 at proxy |
| Replicate, fal.run, Together, Kling, MiniMax, Volces | Blocked |
| HuggingFace | 403 at proxy |

**The Gemini API is the open door.** One key unlocks both ship-quality
voiceover and Veo video generation from inside this container — no local
running, no second machine. Get one at `aistudio.google.com/apikey` and set
`GEMINI_API_KEY`.

Until then espeak is the working backend: fine for reviewing pacing and
timing, not for publishing.

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

## Veo video generation

`gemini.py` also drives Veo for generated footage — the same API family, the
same key.

```
python3 content-ops/video/gemini.py --veo "prompt here" --aspect 9:16 --out clip.mp4
```

It submits a long-running operation, polls to completion, and downloads the
result. Model IDs are discovered from the live models list rather than
hard-coded, so an upstream rename does not break it.

Veo clips are short (single-shot, seconds long) and generated with native
audio. They are b-roll and cutaways inside a structured video, not a substitute
for one. Cost is per-generation and adds up fast — budget it against the RPM
model in `tools/revenue.mjs` before generating at volume.

## Render cost

About 2.5 minutes of wall clock per minute of finished video, single-threaded.
A 40-second short takes roughly 100 seconds end to end.
