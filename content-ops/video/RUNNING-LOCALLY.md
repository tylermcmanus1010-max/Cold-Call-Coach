# Running the pipeline on your own machine

The point of running locally is network access. This container can only reach
Google's APIs — ElevenLabs, ZSky, Replicate and the rest are blocked by policy.
Your own machine has none of those restrictions.

Everything else is identical. Same code, same output.

## One-time setup (~5 minutes)

**1. Install Python 3.11 or newer.** Check with `python3 --version`.
macOS: `brew install python@3.11`. Windows: python.org installer, tick "Add to PATH".

**2. Clone the repo and check out the working branch:**

```
git clone https://github.com/tylermcmanus1010-max/Cold-Call-Coach.git
cd Cold-Call-Coach
git checkout claude/unlazy-skill-capabilities-r5gf15
```

**3. Install the dependencies:**

```
pip install pillow imageio-ffmpeg espeakng-loader
```

That's the whole list for video. `imageio-ffmpeg` bundles its own ffmpeg
binary, so there is nothing else to install. `espeakng-loader` is only the
offline fallback voice — skip it if you always have an API available.

*(The Objection Pack PDF additionally needs `pip install playwright markdown`
and `playwright install chromium`. Not needed for video.)*

**4. Set your API key:**

macOS / Linux:
```
export GEMINI_API_KEY=your_key_here
export GEMINI_VOICE=Charon
```

Windows PowerShell:
```
$env:GEMINI_API_KEY="your_key_here"
$env:GEMINI_VOICE="Charon"
```

To make it permanent, add the export lines to `~/.zshrc` (macOS) or
`~/.bashrc` (Linux) instead of typing them each session.

## Building a video

```
python3 content-ops/video/build.py content-ops/video/scenes/short-04.json
```

Output lands in `content-ops/video/out/short-04-talk-less.mp4`, ready to upload.

Useful flags:

| Flag | Effect |
|---|---|
| `--degrade` | Fill quota-blocked scenes with the offline voice instead of stopping |
| `--force` | Regenerate cached clips (use after editing a `vo` line) |
| `--silent` | Skip voice entirely, keep existing durations |
| `--backend gemini\|elevenlabs\|espeak` | Force one backend |

Build everything pending:

```
for f in content-ops/video/scenes/*.json; do python3 content-ops/video/build.py "$f"; done
```

## Using a provider other than Google

Locally you can reach anything. Two are already wired:

**ElevenLabs** — works with no code changes:
```
export ELEVENLABS_API_KEY=your_key
export ELEVENLABS_VOICE_ID=onwK4e9ZLuTAKqWW03F9
python3 content-ops/video/build.py <spec> --backend elevenlabs
```

**Anything else (ZSky, Replicate, …)** — needs an adapter. It's about thirty
lines: a function that takes text and a path, writes a 24kHz mono WAV, and gets
registered in `synth()` in `voice.py`. Send me the provider's API docs and I'll
write it; you pull and run.

## Pushing work back

Renders are yours to keep locally, but scene specs and any code changes should
come back so we stay in sync:

```
git add content-ops/video/scenes content-ops/video/*.py
git commit -m "describe what changed"
git push
```

Then tell me and I'll pull. Don't commit the `out/` directory — video files
bloat the repo, and I can always re-render from the spec.

## If something breaks

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: PIL` | `pip install pillow` — on some systems use `pip3` |
| `Set GEMINI_API_KEY` | The env var isn't set in *this* shell. Re-run the export. |
| `429` | Quota. Wait, or enable billing on the project. |
| Video renders but is silent | No `vo` lines in the spec, or `--silent` was passed |
| Render is slow | Expected: ~2.5 min of wall clock per finished minute of video |
