#!/usr/bin/env python3
"""
Gemini API adapters: text-to-speech and Veo video generation.

The Gemini API is reachable from this container (verified: real API responses,
not proxy blocks). A key is all that is missing.

    export GEMINI_API_KEY=...
    python3 content-ops/video/gemini.py --check
    python3 content-ops/video/gemini.py --tts "Not interested is a reflex." --out vo.wav
    python3 content-ops/video/gemini.py --veo "a cold caller at a desk, cinematic" --out clip.mp4

Model IDs are discovered from the live models list rather than hard-coded, so a
rename upstream does not break the pipeline.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Narrator candidates, best fit for this brand first. Direct, unfussy, credible.
VOICE_PREFERENCE = ["Charon", "Orus", "Algenib", "Iapetus", "Kore"]

# Each TTS model carries its own free-tier quota — both per-minute and per-day.
# Requests round-robin across them so no single model is hammered into its
# rate limit, which roughly triples free-tier throughput. A model that reports
# a quota error is parked and skipped for the rest of the run.
TTS_MODELS = [
    "models/gemini-2.5-flash-preview-tts",
    "models/gemini-3.1-flash-tts-preview",
    "models/gemini-2.5-pro-preview-tts",
]

_rr = {"i": 0}
_exhausted = set()


def _ring():
    """Models to try this call, starting at the next in rotation."""
    live = [m for m in TTS_MODELS if m not in _exhausted]
    if not live:                       # everything parked: clear and retry once
        _exhausted.clear()
        live = list(TTS_MODELS)
    start = _rr["i"] % len(live)
    _rr["i"] += 1
    return live[start:] + live[:start]


def key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        sys.exit("Set GEMINI_API_KEY (get one at aistudio.google.com/apikey)")
    return k


def _retry_after(detail, attempt):
    """Free tier answers 429 with a suggested delay; honour it when present."""
    import re
    m = re.search(r"retry in ([0-9.]+)s", detail)
    if m:
        return min(float(m.group(1)) + 2, 90)
    return min(2 ** attempt * 5, 60)


def _req(url, body=None, method=None, timeout=180, retries=6):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        r = urllib.request.Request(url, data=data,
                                   method=method or ("POST" if data else "GET"),
                                   headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:600]
            # 429 = free-tier rate limit (3 req/min on TTS). 5xx = transient.
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                wait = _retry_after(detail, attempt)
                print(f"    {e.code}, waiting {wait:.0f}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt * 4, 45))
                continue
            raise RuntimeError(f"network: {e}") from None
    raise RuntimeError("exhausted retries")


def list_models():
    out, page = [], None
    while True:
        url = f"{BASE}/models?key={key()}&pageSize=200" + (f"&pageToken={page}" if page else "")
        d = _req(url)
        out += d.get("models", [])
        page = d.get("nextPageToken")
        if not page:
            break
    return out


def pick_model(substr, methods=None):
    """Newest model whose name contains `substr` and supports `methods`."""
    cands = []
    for m in list_models():
        n = m.get("name", "")
        if substr not in n:
            continue
        if methods and not any(x in m.get("supportedGenerationMethods", []) for x in methods):
            continue
        cands.append(n)
    if not cands:
        raise RuntimeError(f"no model matching '{substr}' available to this key")
    # prefer non-preview, then lexically highest (version numbers sort usefully)
    cands.sort(key=lambda n: ("preview" in n or "exp" in n, n), reverse=False)
    stable = [c for c in cands if "preview" not in c and "exp" not in c]
    return (stable or cands)[-1] if stable else sorted(cands)[-1]


# ---------------- TTS ----------------
def tts(text, out_wav, voice=None, model=None, style=None):
    voice = voice or os.environ.get("GEMINI_VOICE") or VOICE_PREFERENCE[0]
    prompt = f"{style}: {text}" if style else text
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }
    candidates = [model] if model else _ring()
    last = None
    for i, m in enumerate(candidates):
        try:
            # One attempt per model: with rotation the next model is almost
            # always free, so moving on beats waiting out a rate limit.
            d = _req(f"{BASE}/{m}:generateContent?key={key()}", body, retries=1)
            break
        except RuntimeError as e:
            last = e
            if "429" not in str(e):
                raise
            _exhausted.add(m)
            short = m.split("/")[-1]
            if i < len(candidates) - 1:
                print(f"    {short} rate-limited, rotating")
                continue
            # every model refused this pass: wait out the shortest window once
            wait = _retry_after(str(e), 0)
            print(f"    all models rate-limited, waiting {wait:.0f}s")
            time.sleep(wait)
            _exhausted.clear()
            d = _req(f"{BASE}/{candidates[0]}:generateContent?key={key()}", body, retries=3)
            break
    else:
        raise last
    part = d["candidates"][0]["content"]["parts"][0]
    inline = part["inlineData"]
    pcm = base64.b64decode(inline["data"])
    # mimeType looks like: audio/L16;codec=pcm;rate=24000
    rate = 24000
    for chunk in inline.get("mimeType", "").split(";"):
        if chunk.strip().startswith("rate="):
            rate = int(chunk.split("=")[1])
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out_wav


# ---------------- Veo ----------------
def veo(prompt, out_mp4, aspect="9:16", model=None, negative=None, poll=10, timeout=900):
    model = model or pick_model("veo", ["predictLongRunning", "generateVideos"])
    params = {"aspectRatio": aspect}
    if negative:
        params["negativePrompt"] = negative
    op = _req(f"{BASE}/{model}:predictLongRunning?key={key()}",
              {"instances": [{"prompt": prompt}], "parameters": params})
    name = op["name"]
    waited = 0
    while waited < timeout:
        time.sleep(poll)
        waited += poll
        st = _req(f"{BASE}/{name}?key={key()}")
        if st.get("done"):
            if "error" in st:
                raise RuntimeError(st["error"])
            resp = st.get("response", {})
            samples = (resp.get("generateVideoResponse", {}).get("generatedSamples")
                       or resp.get("generatedSamples") or [])
            if not samples:
                raise RuntimeError(f"no video in response: {json.dumps(resp)[:400]}")
            uri = samples[0]["video"]["uri"]
            sep = "&" if "?" in uri else "?"
            req = urllib.request.Request(f"{uri}{sep}key={key()}")
            with urllib.request.urlopen(req, timeout=300) as r, open(out_mp4, "wb") as fh:
                fh.write(r.read())
            return out_mp4
        print(f"  generating... {waited}s")
    raise RuntimeError("timed out")


def check():
    ms = list_models()
    print(f"{len(ms)} models available to this key\n")
    for tag in ("tts", "veo", "imagen"):
        hits = [m["name"] for m in ms if tag in m["name"]]
        print(f"  {tag:8s} {len(hits):3d}  {', '.join(h.split('/')[-1] for h in hits[:4]) or '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tts")
    ap.add_argument("--veo")
    ap.add_argument("--out", default="out.bin")
    ap.add_argument("--voice")
    ap.add_argument("--aspect", default="9:16")
    a = ap.parse_args()
    if a.check:
        check()
    elif a.tts:
        print(tts(a.tts, a.out, a.voice))
    elif a.veo:
        print(veo(a.veo, a.out, a.aspect))
    else:
        ap.error("need --check, --tts or --veo")


if __name__ == "__main__":
    main()
