#!/usr/bin/env python3
"""
One command: script -> voiceover -> timed scenes -> rendered, muxed MP4.

    python3 content-ops/video/build.py content-ops/video/scenes/short-01.json
    python3 content-ops/video/build.py <spec> --backend elevenlabs
    python3 content-ops/video/build.py <spec> --silent      # captions only

Scene durations are derived from the voiceover, so the visuals always match the
read. Swap the voice backend and the whole video re-times itself.
"""
import argparse
import json
import os
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice as V
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def build_audio_track(spec_path, clips, out_wav):
    """Pad each VO clip out to its scene duration and concatenate."""
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    spec = json.load(open(spec_path))
    parts = []
    tmp = os.path.join(OUT, "_audio_parts")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))

    for i, (sc, clip) in enumerate(zip(spec["scenes"], clips)):
        dur = sc.get("duration", 3.0)
        p = os.path.join(tmp, f"{i:03d}.wav")
        if clip:
            subprocess.run([ff, "-y", "-loglevel", "error", "-i", clip,
                            "-af", f"apad=whole_dur={dur}", "-t", str(dur),
                            "-ar", "24000", "-ac", "1", p], check=True)
        else:
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", f"anullsrc=r=24000:cl=mono", "-t", str(dur),
                            p], check=True)
        parts.append(p)

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out_wav], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return out_wav


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--backend", choices=["gemini", "espeak", "elevenlabs"])
    ap.add_argument("--silent", action="store_true",
                    help="skip voiceover; keep the durations already in the spec")
    a = ap.parse_args()

    spec = json.load(open(a.spec))
    name = spec.get("name", "video")
    has_vo = any(s.get("vo") for s in spec["scenes"])

    if not a.silent and has_vo:
        print("VOICEOVER")
        clips, backend = V.scene_voice(a.spec, a.backend)
        track = build_audio_track(a.spec, clips, os.path.join(OUT, f"{name}.wav"))
        spec = json.load(open(a.spec))
        spec["audio"] = track
        json.dump(spec, open(a.spec, "w"), indent=2)
        print(f"  track: {track}  {V.wav_duration(track):.1f}s\n")
    elif a.silent:
        spec.pop("audio", None)
        json.dump(spec, open(a.spec, "w"), indent=2)

    print("RENDER")
    path = R.render(a.spec)

    total = sum(s.get("duration", 3) for s in json.load(open(a.spec))["scenes"])
    print(f"\nDONE  {name}  {total:.1f}s")
    return path


if __name__ == "__main__":
    main()
