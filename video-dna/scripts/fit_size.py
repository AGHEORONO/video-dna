#!/usr/bin/env python3
"""Shrink a video to a target size, or split a file into parts for size-limited transfers.

Example: fit_size.py in.mp4 out.mp4 --target-mb 18
         fit_size.py in.mp4 --split-mb 18
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def two_pass(src, dst, kbps, audio_kbps):
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "pass")
        common = ["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-preset", "medium",
                  "-b:v", f"{kbps}k", "-pix_fmt", "yuv420p", "-passlogfile", log]
        subprocess.run(common + ["-pass", "1", "-an", "-f", "null", os.devnull], check=True)
        subprocess.run(common + ["-pass", "2", "-c:a", "aac", "-b:a", f"{audio_kbps}k",
                                 "-movflags", "+faststart", dst], check=True)


def shrink(a):
    if os.path.getsize(a.input) <= a.target_mb * 1e6:
        shutil.copy(a.input, a.output)
        print(f"{a.output}: already under target, copied unchanged")
        return
    secs = duration(a.input)
    budget_kbps = a.target_mb * 8000 * 0.97 / secs
    kbps = int(budget_kbps - a.audio_kbps)
    if kbps < 200:
        raise SystemExit(f"a {a.target_mb} MB target leaves only {kbps} kbps of video. "
                         "Use a bigger target, or --split-mb.")
    for _ in range(3):
        two_pass(a.input, a.output, kbps, a.audio_kbps)
        mb = os.path.getsize(a.output) / 1e6
        if mb <= a.target_mb:
            print(f"{a.output}: {mb:.1f} MB at {kbps} kbps. Quality is lower than the original.")
            return
        kbps = int(kbps * a.target_mb / mb * 0.97)
    raise SystemExit(f"could not get under {a.target_mb} MB, last attempt was {mb:.1f} MB")


def split(a):
    size = int(a.split_mb * 1e6)
    sha = hashlib.sha256()
    names = []
    with open(a.input, "rb") as f:
        while chunk := f.read(size):
            sha.update(chunk)
            name = f"{a.input}.part{len(names):02d}"
            with open(name, "wb") as out:
                out.write(chunk)
            names.append(name)
    base = os.path.basename(a.input)
    parts = [os.path.basename(n) for n in names]
    print(f"{len(names)} parts, sha256 {sha.hexdigest()}")
    print(f"Windows: copy /b {'+'.join(parts)} {base}")
    print(f"macOS or Linux: cat {' '.join(parts)} > {base}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output", nargs="?")
    p.add_argument("--target-mb", type=float)
    p.add_argument("--audio-kbps", type=int, default=128)
    p.add_argument("--split-mb", type=float)
    a = p.parse_args()
    if a.split_mb:
        split(a)
    elif a.target_mb and a.output:
        shrink(a)
    else:
        p.error("use: input output --target-mb N, or: input --split-mb N")


if __name__ == "__main__":
    main()
