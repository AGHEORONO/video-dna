#!/usr/bin/env python3
"""Estimate a track's tempo, beats and strongest hits, using only numpy and ffmpeg.

Example: beats.py track.mp3 --out beats.json
"""
import argparse
import json
import subprocess

import numpy as np

SR, HOP, WIN = 22050, 512, 2048


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def onset_envelope(y):
    n = 1 + max(len(y) - WIN, 0) // HOP
    window = np.hanning(WIN)
    prev, env = None, np.zeros(n)
    for i in range(n):
        frame = y[i * HOP:i * HOP + WIN]
        if len(frame) < WIN:
            frame = np.pad(frame, (0, WIN - len(frame)))
        mag = np.log1p(np.abs(np.fft.rfft(frame * window)) * 10)
        if prev is not None:
            env[i] = np.maximum(mag - prev, 0).sum()
        prev = mag
    return env - np.convolve(env, np.ones(16) / 16, "same")


def tempo(env, lo=70, hi=180):
    x = env - env.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(x, 2 * len(x))) ** 2)[:len(x)]
    frame_rate = SR / HOP
    lags = np.arange(int(frame_rate * 60 / hi), min(int(frame_rate * 60 / lo) + 1, len(ac)))
    if len(lags) == 0:
        return 120.0, int(frame_rate / 2)
    # Mild preference around 120 BPM to reduce octave errors.
    bpm = 60 * frame_rate / lags
    weight = np.exp(-0.5 * (np.log2(bpm / 120) / 0.9) ** 2)
    lag = lags[np.argmax(ac[lags] * weight)]
    return 60 * frame_rate / lag, int(lag)


def track(env, lag):
    """Dynamic-programming beat tracker: favour strong onsets at regular spacing."""
    env = np.maximum(env, 0)
    score, back = env.copy(), np.full(len(env), -1)
    span = np.arange(-2 * lag, -lag // 2)
    penalty = -100.0 * env.std() / max(env.std(), 1e-9) * 0.01 * (np.log(-span / lag) ** 2)
    for i in range(len(env)):
        j = i + span
        ok = j >= 0
        if ok.any():
            cand = score[j[ok]] + penalty[ok] * max(env.max(), 1e-9)
            k = np.argmax(cand)
            if cand[k] > 0:
                score[i] += cand[k]
                back[i] = j[ok][k]
    i = int(np.argmax(score[-2 * lag:])) + max(len(env) - 2 * lag, 0)
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    return np.array(beats[::-1])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("audio")
    p.add_argument("--out")
    p.add_argument("--hits", type=int, default=12, help="how many strongest hits to list")
    a = p.parse_args()

    y = load(a.audio)
    env = onset_envelope(y)
    bpm, lag = tempo(env)
    frames = track(env, lag)
    to_sec = HOP / SR
    # The envelope's frame centre sits half a window later than its index.
    offset = WIN / 2 / SR
    beats = [round(float(f) * to_sec + offset, 3) for f in frames]

    order = np.argsort(env)[::-1]
    hits = []
    for f in order:
        t = float(f) * to_sec + offset
        if all(abs(t - h) > 1.0 for h in hits):
            hits.append(t)
        if len(hits) >= a.hits:
            break

    result = {"duration": round(len(y) / SR, 3), "bpm": round(bpm, 1), "beats": beats,
              "hits": sorted(round(h, 3) for h in hits)}
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
    print(f"bpm {result['bpm']}, {len(beats)} beats, duration {result['duration']}s")
    print("strongest hits:", result["hits"])


if __name__ == "__main__":
    main()
