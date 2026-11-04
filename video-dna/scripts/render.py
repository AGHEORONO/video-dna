#!/usr/bin/env python3
"""Render a timeline JSON to a final MP4. See references/pipeline.md for the format.

Each segment becomes a silent video and a WAV with an exact sample count, so audio
and video always have equal length. Finished segments are cached in _work/ and reused.

Example: render.py timeline.json --jobs 4
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

SR = 48000


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", **kw)
    if r.returncode:
        sys.exit(f"command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def has_audio(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
               "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def atempo_chain(speed):
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.6f}")
    return parts


def frames_of(seg, fps):
    if "src" in seg:
        dur = (seg["end"] - seg["start"]) / seg.get("speed", 1.0)
    else:
        dur = seg["dur"]
    return max(1, round(dur * fps))


def seg_key(seg, tl, base):
    """Cache key: settings plus the source file's size and modification time."""
    stamp = None
    if "color" not in seg:
        st = os.stat(os.path.join(base, seg.get("src") or seg["image"]))
        stamp = [st.st_size, st.st_mtime]
    payload = json.dumps([seg, tl["width"], tl["height"], tl["fps"], stamp], sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def render_segment(i, seg, tl, base, work, force):
    w, h, fps = tl["width"], tl["height"], tl["fps"]
    n = frames_of(seg, fps)
    samples = round(n * SR / fps)
    key = seg_key(seg, tl, base)
    vid, wav = os.path.join(work, f"{key}.mp4"), os.path.join(work, f"{key}.wav")
    if not force and os.path.exists(vid) and os.path.exists(wav):
        return vid, wav

    if seg.get("fit") == "pad":
        fit = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black")
    else:
        fit = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    speed = seg.get("speed", 1.0)
    vf = [fit, "setsar=1"]
    if speed != 1.0:
        vf.insert(0, f"setpts=PTS/{speed}")
    if seg.get("vf"):
        vf.append(seg["vf"])
    vf += [f"fps={fps}", "format=yuv420p"]

    if "color" in seg:
        color = seg["color"].replace("#", "0x")
        inp = ["-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r={fps}"]
    elif "image" in seg:
        inp = ["-loop", "1", "-framerate", str(fps), "-i", os.path.join(base, seg["image"])]
    else:
        src = os.path.join(base, seg["src"])
        inp = ["-ss", str(seg["start"]), "-t", str(seg["end"] - seg["start"]), "-i", src]

    tmp_v = vid + ".tmp.mp4"
    run(["ffmpeg", "-y", "-v", "error", *inp, "-an", "-vf", ",".join(vf),
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-pix_fmt", "yuv420p", tmp_v])
    if "src" in seg and seg.get("voice", True) and has_audio(os.path.join(base, seg["src"])):
        fade = min(0.008, n / fps / 4)
        af = [f"aresample={SR}", *([] if speed == 1.0 else atempo_chain(speed)),
              f"volume={seg.get('gain_db', 0)}dB", "aformat=channel_layouts=stereo",
              "apad", f"atrim=end_sample={samples}",
              f"afade=t=in:d={fade}", f"afade=t=out:st={n / fps - fade}:d={fade}"]
        tmp_a = wav + ".tmp.wav"
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(seg["start"]),
             "-t", str(seg["end"] - seg["start"]), "-i", os.path.join(base, seg["src"]),
             "-vn", "-af", ",".join(af), "-ar", str(SR), "-c:a", "pcm_s16le", tmp_a])
    else:
        tmp_a = wav + ".tmp.wav"
        with wave.open(tmp_a, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(SR)
            f.writeframes(b"\0" * (samples * 4))
    os.replace(tmp_v, vid)
    os.replace(tmp_a, wav)
    return vid, wav


def read_wav(path):
    with wave.open(path, "rb") as f:
        return np.frombuffer(f.readframes(f.getnframes()), np.int16).reshape(-1, 2) / 32768.0


def decode(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def place(buf, clip, at, gain_db=0.0, fade_in=0.0, fade_out=0.0):
    i = round(at * SR)
    if i >= len(buf):
        return
    clip = clip[:len(buf) - i].copy()
    if not len(clip):
        return
    if fade_in:
        k = min(round(fade_in * SR), len(clip))
        clip[:k] *= np.linspace(0, 1, k)[:, None]
    if fade_out:
        k = min(round(fade_out * SR), len(clip))
        clip[-k:] *= np.linspace(1, 0, k)[:, None]
    buf[i:i + len(clip)] += clip * 10 ** (gain_db / 20)


def duck_curve(voice, duck_db):
    """Gain curve for music: lower while voice is present, with smooth attack and release."""
    hop = 480
    mono = np.abs(voice).max(axis=1)
    n = len(mono) // hop + 1
    present = np.array([mono[i * hop:(i + 1) * hop].max(initial=0) > 0.02 for i in range(n)], float)
    atk, rel = 1 - np.exp(-1 / 5), 1 - np.exp(-1 / 30)
    # Look ahead so the music dips just before speech starts.
    env, cur = np.zeros(n), 0.0
    for i in range(n - 1, -1, -1):
        cur += ((present[i] - cur) * (atk if present[i] > cur else rel))
        env[i] = cur
    fwd, cur = np.zeros(n), 0.0
    for i in range(n):
        cur += ((env[i] - cur) * (atk if env[i] > cur else rel))
        fwd[i] = cur
    gain = 10 ** (duck_db * fwd / 20)
    return np.interp(np.arange(len(mono)), np.arange(n) * hop, gain)[:, None]


def write_wav(path, x):
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def master(in_wav, out_wav, samples, loudness):
    run(["ffmpeg", "-y", "-v", "error", "-i", in_wav, "-af",
         f"loudnorm=I={loudness}:TP=-1.5:LRA=11,aresample={SR},apad,atrim=end_sample={samples}",
         "-ar", str(SR), "-c:a", "pcm_s16le", out_wav])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("timeline")
    p.add_argument("--jobs", type=int, default=max((os.cpu_count() or 4) // 2, 1))
    p.add_argument("--only", help="comma-separated segment numbers to force-rebuild, from 0")
    p.add_argument("--clean", action="store_true", help="discard the segment cache first")
    p.add_argument("--crf", type=int, default=20)
    a = p.parse_args()

    tl_path = os.path.abspath(a.timeline)
    base = os.path.dirname(tl_path)
    with open(tl_path, encoding="utf-8") as f:
        tl = json.load(f)
    tl.setdefault("width", 1080)
    tl.setdefault("height", 1920)
    tl.setdefault("fps", 30)
    work = os.path.join(base, "_work")
    if a.clean:
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)

    force = {int(x) for x in a.only.split(",")} if a.only else set()
    segs = tl["segments"]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futures = [ex.submit(render_segment, i, s, tl, base, work, i in force)
                   for i, s in enumerate(segs)]
        parts = [f.result() for f in futures]
    print(f"segments ready: {len(parts)}")

    list_file = os.path.join(work, "concat.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for v, _ in parts:
            f.write(f"file '{os.path.basename(v)}'\n")
    video = os.path.join(work, "video.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c", "copy", video])

    voice = np.concatenate([read_wav(w) for _, w in parts])
    samples = len(voice)
    duration = samples / SR
    fx = np.zeros_like(voice)
    for s in tl.get("sfx", []):
        place(fx, decode(os.path.join(base, s["src"])), s["at"], s.get("gain_db", 0))
    music = np.zeros_like(voice)
    for m in tl.get("music", []):
        clip = decode(os.path.join(base, m["src"]), m.get("from", 0.0), m.get("dur"))
        place(music, clip, m.get("at", 0.0), m.get("gain_db", -12),
              m.get("fade_in", 0.0), m.get("fade_out", 0.0))
    if tl.get("music"):
        music *= duck_curve(voice, tl.get("duck_db", -10))

    loud = tl.get("loudness", -14)
    mixes = {"main": voice + fx + music}
    if tl.get("no_music_out"):
        mixes["no_music"] = voice + fx
    for name, x in mixes.items():
        peak = np.abs(x).max()
        if peak > 0.98:
            x = x * 0.98 / peak  # avoid clipping before the master stage
        write_wav(os.path.join(work, f"{name}_raw.wav"), x)
        if peak > 0:
            master(os.path.join(work, f"{name}_raw.wav"), os.path.join(work, f"{name}.wav"),
                   samples, loud)
        else:
            shutil.copy(os.path.join(work, f"{name}_raw.wav"), os.path.join(work, f"{name}.wav"))

    # The ass filter is run from the file's own folder, to avoid escaping Windows paths.
    burned = os.path.join(work, "burned.mp4")
    if tl.get("ass"):
        ass_path = os.path.join(base, tl["ass"])
        vf = f"ass={os.path.basename(ass_path)}"
        if tl.get("fontsdir"):
            fonts = os.path.relpath(os.path.join(base, tl["fontsdir"]), os.path.dirname(ass_path))
            vf += f":fontsdir={fonts.replace(os.sep, '/')}"
        run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
             burned], cwd=os.path.dirname(ass_path))
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", video, "-c:v", "libx264", "-preset", "medium",
             "-crf", str(a.crf), "-pix_fmt", "yuv420p", burned])

    outputs = {"main": tl.get("out", "final.mp4")}
    if tl.get("no_music_out"):
        outputs["no_music"] = tl["no_music_out"]
    for name, out in outputs.items():
        target = os.path.join(base, out)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        run(["ffmpeg", "-y", "-v", "error", "-i", burned, "-i", os.path.join(work, f"{name}.wav"),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-ar", str(SR), "-movflags", "+faststart", target])
        mb = os.path.getsize(target) / 1e6
        print(f"{out}: {duration:.3f}s, {mb:.1f} MB")


if __name__ == "__main__":
    main()
