#!/usr/bin/env python3
"""
ZSky AI adapter — generated video and image footage.

Ported from the official Go SDK (github.com/zsky-ai/zsky-sdk-go), so the
endpoints, request bodies and job model match the real /v1 API rather than
being guessed.

    export ZSKY_API_KEY=zsky_live_...
    python3 content-ops/video/zsky.py --check
    python3 content-ops/video/zsky.py --video "slow push over an empty office at night" \
        --aspect 9:16 --seconds 8 --out broll.mp4

WHAT THIS DOES AND DOES NOT SOLVE
  ZSky generates *footage*. It is a Veo alternative, not an ElevenLabs one —
  there is no text-to-speech endpoint, so it does not fix the voiceover
  bottleneck. Our shorts are kinetic typography with narration; ZSky supplies
  b-roll to cut behind them.

NETWORK
  zsky.ai is refused by this container's egress proxy. This module is written
  to run on a machine with open network access — see RUNNING-LOCALLY.md.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("ZSKY_BASE_URL", "https://zsky.ai")

# From the SDK's aspectDimensions table.
ASPECT = {
    "1:1":  (1024, 1024),
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "4:3":  (1152, 864),
    "3:4":  (864, 1152),
    "21:9": (1344, 576),
    "3:2":  (1248, 832),
    "2:3":  (832, 1248),
}

FPS = 24
MIN_FRAMES, MAX_FRAMES = 25, 241          # ~1.04s to ~10.04s
TERMINAL = {"completed", "failed", "blocked"}


class ZskyError(RuntimeError):
    def __init__(self, message, code=None, status=None, retry_after=None):
        super().__init__(message)
        self.code, self.status, self.retry_after = code, status, retry_after


def key():
    k = os.environ.get("ZSKY_API_KEY")
    if not k:
        sys.exit("Set ZSKY_API_KEY (Max-tier key, format zsky_live_...)")
    return k


def seconds_to_frames(seconds):
    """Mirrors the SDK: 24fps, clamped. Max clip is ~10 seconds."""
    return max(MIN_FRAMES, min(int(seconds * FPS), MAX_FRAMES))


def _req(path, body=None, method=None, timeout=60):
    url = BASE.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method or ("POST" if data else "GET"),
        headers={"X-API-Key": key(), "Accept": "application/json",
                 **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        ra = e.headers.get("Retry-After")
        msg = {401: "invalid or missing API key",
               429: "rate limited",
               451: "prompt blocked by content policy",
               408: "request timeout", 504: "gateway timeout"}.get(e.code, detail)
        raise ZskyError(f"{e.code}: {msg}", status=e.code,
                        retry_after=float(ra) if ra and ra.isdigit() else None) from None
    except urllib.error.URLError as e:
        raise ZskyError(f"network error contacting ZSky: {e}") from None


def generate_video(prompt, aspect="9:16", seconds=None, seed=None):
    prompt = prompt.strip()[:2000]
    if not prompt:
        raise ZskyError("prompt must be non-empty", code="invalid_prompt")
    w, h = ASPECT.get(aspect, ASPECT["16:9"])
    body = {"prompt": prompt, "width": w, "height": h}
    if seconds:
        body["length"] = seconds_to_frames(seconds)
    if seed:
        body["seed"] = seed
    return _req("/v1/videos/generate", body)


def generate_image(prompt, aspect="1:1", count=None, seed=None):
    prompt = prompt.strip()[:2000]
    w, h = ASPECT.get(aspect, ASPECT["1:1"])
    body = {"prompt": prompt, "width": w, "height": h}
    if count:
        body["count"] = min(count, 4)
    if seed:
        body["seed"] = seed
    return _req("/v1/images/generate", body)


def poll_until_done(job_id, interval=3, timeout=600, verbose=True):
    waited = 0
    while waited < timeout:
        st = _req(f"/v1/jobs/{urllib.parse.quote(job_id)}")
        status = st.get("status")
        if status in TERMINAL:
            if status != "completed":
                raise ZskyError(f"job {status}: {st.get('error') or 'no detail'}")
            return st
        if verbose:
            pos = st.get("queue_position")
            extra = f" queue {pos}" if pos else ""
            print(f"  {status} {st.get('progress', 0)}%{extra}  ({waited}s)")
        time.sleep(interval)
        waited += interval
    raise ZskyError("poll timeout", code="poll_timeout")


def download(url, out_path):
    with urllib.request.urlopen(url, timeout=300) as r, open(out_path, "wb") as fh:
        fh.write(r.read())
    return out_path


def make_video(prompt, out_path, aspect="9:16", seconds=8, seed=None):
    """Submit, wait, download. Returns the local path."""
    job = generate_video(prompt, aspect=aspect, seconds=seconds, seed=seed)
    jid = job.get("job_id")
    print(f"  job {jid} ({job.get('status')})")
    done = poll_until_done(jid)
    results = done.get("results") or []
    if not results:
        raise ZskyError("job completed with no results")
    return download(results[0]["url"], out_path)


def check():
    """Cheapest possible liveness probe: submit nothing, just hit a bad job id."""
    try:
        _req("/v1/jobs/_probe_")
        print("API reachable and key accepted")
    except ZskyError as e:
        if e.status == 401:
            print("Reachable, but the key was rejected (401)")
        elif e.status in (400, 404):
            print("API reachable and key accepted (probe id rejected, as expected)")
        else:
            print(f"{e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--image")
    ap.add_argument("--aspect", default="9:16", choices=sorted(ASPECT))
    ap.add_argument("--seconds", type=float, default=8)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", default="zsky-out.mp4")
    a = ap.parse_args()
    if a.check:
        check()
    elif a.video:
        if a.seconds > MAX_FRAMES / FPS:
            print(f"  note: clamped to {MAX_FRAMES / FPS:.1f}s (API maximum)")
        print(make_video(a.video, a.out, a.aspect, a.seconds, a.seed))
    elif a.image:
        job = generate_image(a.image, a.aspect, seed=a.seed)
        done = poll_until_done(job["job_id"])
        print(download(done["results"][0]["url"], a.out))
    else:
        ap.error("need --check, --video or --image")


if __name__ == "__main__":
    main()
