#!/usr/bin/env python3
"""
Voiceover generation with swappable backends.

    python3 content-ops/video/voice.py --text "Hello there" --out /tmp/vo.wav
    python3 content-ops/video/voice.py --scenes content-ops/video/scenes/short-01.json

Backends, tried in order unless --backend forces one:
  elevenlabs  ELEVENLABS_API_KEY set and api.elevenlabs.io reachable. Ship quality.
  espeak      Local formant synthesis. Always available, no network, robotic.

Both return 22.05k/24k mono WAV. The renderer uses per-line durations to drive
scene timing, so swapping backends re-times the video automatically.
"""
import argparse
import ctypes
import json
import os
import struct
import subprocess
import sys
import wave

import espeakng_loader

SR_ESPEAK = 22050


# ---------------- espeak backend ----------------
class _Espeak:
    """ctypes wrapper. espeak-ng ships no CLI here, only the shared object."""

    AUDIO_OUTPUT_SYNCHRONOUS = 0x02
    CHARS_UTF8 = 1

    def __init__(self, voice="en-us", rate=165, pitch=42):
        self.lib = ctypes.CDLL(espeakng_loader.get_library_path())
        sr = self.lib.espeak_Initialize(
            self.AUDIO_OUTPUT_SYNCHRONOUS, 0,
            espeakng_loader.get_data_path().encode(), 0)
        if sr <= 0:
            raise RuntimeError("espeak_Initialize failed")
        self.sr = sr
        self.lib.espeak_SetVoiceByName(voice.encode())
        # 1=rate 2=volume 3=pitch 4=range
        self.lib.espeak_SetParameter(1, rate, 0)
        self.lib.espeak_SetParameter(3, pitch, 0)
        self.lib.espeak_SetParameter(4, 62, 0)
        self._buf = bytearray()

        CB = ctypes.CFUNCTYPE(ctypes.c_int,
                              ctypes.POINTER(ctypes.c_short),
                              ctypes.c_int, ctypes.c_void_p)

        def _cb(wav, n, events):
            if wav and n > 0:
                self._buf.extend(ctypes.string_at(wav, n * 2))
            return 0

        self._cb = CB(_cb)                       # keep a reference alive
        self.lib.espeak_SetSynthCallback(self._cb)

    def say(self, text):
        self._buf = bytearray()
        b = text.encode("utf-8")
        self.lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, self.CHARS_UTF8, None, None)
        self.lib.espeak_Synchronize()
        return bytes(self._buf)


def espeak_wav(text, path, voice="en-us", rate=165, pitch=42):
    eng = _Espeak(voice, rate, pitch)
    pcm = eng.say(text)
    raw = path + ".raw.wav"
    with wave.open(raw, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(eng.sr)
        w.writeframes(pcm)
    # Warm it up: espeak is thin and sibilant raw. EQ down the harshness,
    # add body, compress, and pad a beat of silence at each end.
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    chain = ("highpass=f=85,"
             "equalizer=f=250:t=q:w=1.2:g=3,"
             "equalizer=f=3200:t=q:w=1.6:g=-5,"
             "equalizer=f=6500:t=q:w=2:g=-7,"
             "acompressor=threshold=-18dB:ratio=3:attack=8:release=180,"
             "aresample=24000,"
             "adelay=120|120,apad=pad_dur=0.25,"
             "loudnorm=I=-16:TP=-1.5:LRA=11")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", raw,
                    "-af", chain, "-ar", "24000", "-ac", "1", path], check=True)
    os.remove(raw)
    return path


# ---------------- elevenlabs backend ----------------
def elevenlabs_available():
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return False
    try:
        import urllib.request
        req = urllib.request.Request("https://api.elevenlabs.io/v1/models",
                                     headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]})
        urllib.request.urlopen(req, timeout=8).read(1)
        return True
    except Exception:
        return False


def elevenlabs_wav(text, path, voice_id=None, model="eleven_turbo_v2_5"):
    import urllib.request
    key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
    body = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.42, "similarity_boost": 0.75,
                           "style": 0.35, "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    mp3 = path + ".mp3"
    with urllib.request.urlopen(req, timeout=60) as r, open(mp3, "wb") as fh:
        fh.write(r.read())
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", mp3,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "24000", "-ac", "1", path], check=True)
    os.remove(mp3)
    return path


# ---------------- dispatch ----------------
def gemini_available():
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def gemini_wav(text, path, voice=None):
    """Gemini TTS. The API is reachable from this container; only a key is missing."""
    import gemini
    raw = path + ".raw.wav"
    gemini.tts(text, raw, voice=voice)
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", raw,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "24000", "-ac", "1", path], check=True)
    os.remove(raw)
    return path


def synth(text, path, backend=None):
    if backend == "gemini" or (backend is None and gemini_available()):
        return gemini_wav(text, path), "gemini"
    if backend == "elevenlabs" or (backend is None and elevenlabs_available()):
        return elevenlabs_wav(text, path), "elevenlabs"
    return espeak_wav(text, path), "espeak"


def wav_duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def batch_synth(lines, out_dir, voice=None, backend=None, gap=0.65):
    """Generate every VO line in ONE request, then split it back into clips.

    Free tier is metered per request, not per second, so a video that makes one
    call instead of eleven costs one eleventh of the quota. The lines are read
    as a single narration with deliberate pauses, then split on the silence
    between them.
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()

    # A pause instruction the model reads as timing, not as words to speak.
    joined = "\n\n".join(lines)
    style = ("Read the following lines as separate beats. Pause for a full "
             "second between each line. Steady, direct delivery.")

    whole = os.path.join(out_dir, "_whole.wav")
    if backend == "gemini" or (backend is None and gemini_available()):
        import gemini
        gemini.tts(joined, whole, voice=voice, style=style)
        used = "gemini"
    else:
        espeak_wav(joined, whole)
        used = "espeak"

    # Find the gaps the model left between beats.
    r = subprocess.run([ff, "-i", whole, "-af",
                        f"silencedetect=noise=-34dB:d={gap}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts, ends = [], []
    for ln in r.stderr.splitlines():
        if "silence_start:" in ln:
            starts.append(float(ln.split("silence_start:")[1].strip()))
        elif "silence_end:" in ln:
            ends.append(float(ln.split("silence_end:")[1].split("|")[0].strip()))

    total = wav_duration(whole)
    # Build cut points: speech runs from each silence_end to the next silence_start.
    bounds = []
    cur = 0.0
    for i, st in enumerate(starts):
        if st <= cur + 0.15:            # leading silence
            cur = ends[i] if i < len(ends) else cur
            continue
        bounds.append((cur, st))
        cur = ends[i] if i < len(ends) else st
    if cur < total - 0.15:
        bounds.append((cur, total))

    if len(bounds) != len(lines):
        print(f"  split found {len(bounds)} segments for {len(lines)} lines "
              f"— falling back to per-line requests")
        return None, used

    clips = []
    for i, (a, b) in enumerate(bounds):
        p = os.path.join(out_dir, f"{i:02d}.wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", whole,
                        "-ss", str(max(a - 0.08, 0)), "-to", str(b + 0.12),
                        "-ar", "24000", "-ac", "1", p], check=True)
        clips.append(p)
    os.remove(whole)
    print(f"  1 request -> {len(clips)} clips (saved {len(lines) - 1} requests)")
    return clips, used


def _cache_key(line, voice):
    """Fingerprint the text and voice so a changed line regenerates its clip."""
    import hashlib
    return hashlib.sha256(f"{voice}|{line}".encode()).hexdigest()[:16]


def _is_cached(d, i, line, voice):
    p = os.path.join(d, f"{i:02d}.wav")
    meta = p + ".key"
    if not (os.path.exists(p) and os.path.exists(meta) and os.path.getsize(p) > 1000):
        return False
    return open(meta).read().strip().lstrip("espeak:") == _cache_key(line, voice)


def scene_voice(spec_path, backend=None, force=False, fallback=True):
    """Render one VO clip per scene that has `vo`, and write durations back.

    Clips are cached by (text, voice) fingerprint, so a re-run only generates
    what is missing or changed. That makes a quota-limited run resumable —
    stop when the daily cap hits, run again tomorrow, and it picks up where it
    left off instead of paying for the whole video again.
    """
    spec = json.load(open(spec_path))
    name = spec.get("name", "vo")
    d = os.path.join(os.path.dirname(spec_path), "..", "out", f"_vo_{name}")
    os.makedirs(d, exist_ok=True)
    voice = os.environ.get("GEMINI_VOICE", "default")
    used, clips = None, []
    made = cached = degraded = 0

    # One request for the whole script beats one per scene: free tier meters
    # requests, not audio length. Only worth it when several scenes are stale.
    vo_idx = [i for i, sc in enumerate(spec["scenes"]) if sc.get("vo")]
    stale = [i for i in vo_idx
             if force or not _is_cached(d, i, spec["scenes"][i]["vo"], voice)]
    if len(stale) > 1 and not force:
        lines = [spec["scenes"][i]["vo"] for i in vo_idx]
        batched, bused = batch_synth(lines, d, voice=voice, backend=backend)
        if batched:
            for n, i in enumerate(vo_idx):
                open(os.path.join(d, f"{i:02d}.wav.key"), "w").write(
                    _cache_key(spec["scenes"][i]["vo"], voice))
            used = bused

    for i, sc in enumerate(spec["scenes"]):
        line = sc.get("vo")
        if not line:
            clips.append(None)
            continue
        p = os.path.join(d, f"{i:02d}.wav")
        meta = p + ".key"
        want = _cache_key(line, voice)
        have = open(meta).read().strip() if os.path.exists(meta) else None

        if not force and have == want and os.path.exists(p) and os.path.getsize(p) > 1000:
            dur = wav_duration(p)
            sc["duration"] = round(dur + sc.get("pad", 0.45), 2)
            clips.append(p)
            cached += 1
            print(f"  scene {i:02d}  {dur:5.2f}s  [cached]  {line[:44]}")
            continue

        try:
            p, used = synth(line, p, backend)
            open(meta, "w").write(want)
            made += 1
        except RuntimeError as e:
            if not fallback or "429" not in str(e):
                json.dump(spec, open(spec_path, "w"), indent=2)
                done = made + cached
                raise SystemExit(
                    f"\nQuota exhausted after {done}/{len([x for x in spec['scenes'] if x.get('vo')])} scenes.\n"
                    f"Generated clips are cached — re-run when quota resets and it resumes\n"
                    f"from scene {i:02d}. Or pass --degrade to fill the rest with espeak.") from None
            print(f"  scene {i:02d}  [quota] falling back to espeak")
            p = espeak_wav(line, p)
            open(meta, "w").write("espeak:" + want)
            degraded += 1
            used = used or "espeak"

        dur = wav_duration(p)
        sc["duration"] = round(dur + sc.get("pad", 0.45), 2)
        clips.append(p)
        print(f"  scene {i:02d}  {dur:5.2f}s  {line[:52]}")

    json.dump(spec, open(spec_path, "w"), indent=2)
    note = f"{made} generated, {cached} cached"
    if degraded:
        note += f", {degraded} DEGRADED to espeak"
    print(f"backend: {used}  |  {note}")
    return clips, used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--out", default="/tmp/vo.wav")
    ap.add_argument("--scenes")
    ap.add_argument("--backend", choices=["gemini", "espeak", "elevenlabs"])
    ap.add_argument("--force", action="store_true", help="regenerate cached clips")
    ap.add_argument("--degrade", action="store_true",
                    help="fill quota-blocked scenes with espeak instead of stopping")
    a = ap.parse_args()
    if a.scenes:
        scene_voice(a.scenes, a.backend, force=a.force, fallback=a.degrade)
    elif a.text:
        p, used = synth(a.text, a.out, a.backend)
        print(f"{p}  {wav_duration(p):.2f}s  backend={used}")
    else:
        ap.error("need --text or --scenes")


if __name__ == "__main__":
    main()
