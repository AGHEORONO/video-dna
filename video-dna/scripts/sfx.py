#!/usr/bin/env python3
"""Generate a palette of copyright-free sound effects as 48 kHz mono WAV files.

Example: sfx.py --out sfx
         sfx.py --out sfx --only coin,impact --pitch 1.2
"""
import argparse
import os
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(SR * d)) / SR


def square(f, d):
    x = t(d)
    freq = np.broadcast_to(f, x.shape)
    return np.sign(np.sin(2 * np.pi * np.cumsum(freq) / SR))


def env(x, a=0.002, r=0.05):
    n = len(x)
    e = np.ones(n)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e


def seq(notes, dur, gap=0.0):
    return np.concatenate([np.concatenate([env(square(f, dur) * 0.5), np.zeros(int(gap * SR))])
                           for f in notes])


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def blip():
    return env(square(880, 0.04) * 0.4, r=0.015)


def coin():
    return np.concatenate([env(square(988, 0.07) * 0.5), env(square(1319, 0.28) * 0.5, r=0.25)])


def level_up():
    return seq([523, 659, 784, 1047, 1319], 0.09, 0.01)


def quest():
    return seq([659, 880, 1109], 0.12, 0.02)


def damage():
    x = t(0.3)
    return env(square(np.linspace(420, 90, len(x)), 0.3) * 0.5 + rng.normal(0, 0.15, len(x)), r=0.1)


def fail():
    return seq([392, 370, 349, 311], 0.2, 0.02)


def whoosh():
    x = t(0.45)
    n = rng.normal(0, 1, len(x))
    k = np.linspace(40, 4, len(x)).astype(int)
    c = np.cumsum(n)
    y = np.array([(c[min(i + q, len(c) - 1)] - c[max(i - q, 0)]) / (2 * q) for i, q in enumerate(k)])
    y /= np.abs(y).max()
    return y * np.sin(np.pi * x / x[-1]) ** 2 * 0.8


def impact():
    x = t(0.8)
    sub = np.sin(2 * np.pi * (45 * x + 60 * (1 - np.exp(-x * 20)) / 20 * 3)) * np.exp(-x * 5)
    hit = lowpass(rng.normal(0, 1, len(x)), 6) * np.exp(-x * 30)
    return np.clip(sub * 0.9 + hit * 0.7, -1, 1)


def stinger():
    x = t(1.2)
    y = sum(np.sign(np.sin(2 * np.pi * f * x)) for f in (110, 165, 220)) / 3
    return env(lowpass(y, 12) * np.exp(-x * 1.5) * 0.8, r=0.1)


def tick():
    x = t(0.03)
    return rng.normal(0, 1, len(x)) * np.exp(-x * 250) * 0.6


def ding():
    x = t(0.7)
    return (np.sin(2 * np.pi * 1320 * x) + 0.4 * np.sin(2 * np.pi * 2640 * x)) * np.exp(-x * 6) * 0.5


def scratch():
    x = t(0.5)
    f = 500 + 400 * np.sin(2 * np.pi * 7 * x)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) + rng.normal(0, 0.5, len(x))
    return env(lowpass(y, 4) * 0.5, r=0.08)


def glitch():
    parts = [env(square(float(rng.uniform(200, 3000)), float(rng.uniform(0.012, 0.04))) * 0.4, r=0.003)
             for _ in range(10)]
    return np.concatenate(parts)


def sad_brass():
    out = []
    for f, d in [(233, 0.3), (220, 0.3), (208, 0.3), (196, 0.9)]:
        x = t(d)
        vib = 1 + 0.015 * np.sin(2 * np.pi * 5.5 * x)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        y = sum(np.sin(k * ph) / k for k in range(1, 7))
        out.append(env(y * 0.35, a=0.02, r=0.05))
    return np.concatenate(out)


SOUNDS = {"blip": blip, "coin": coin, "level_up": level_up, "quest": quest, "damage": damage,
          "fail": fail, "whoosh": whoosh, "impact": impact, "stinger": stinger, "tick": tick,
          "ding": ding, "scratch": scratch, "glitch": glitch, "sad_brass": sad_brass}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--only", help="comma-separated names")
    p.add_argument("--pitch", type=float, default=1.0, help="pitch and speed factor")
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    if a.list:
        print(", ".join(SOUNDS))
        return
    names = a.only.split(",") if a.only else list(SOUNDS)
    unknown = [n for n in names if n not in SOUNDS]
    if unknown:
        raise SystemExit(f"unknown: {unknown}. Available: {', '.join(SOUNDS)}")
    os.makedirs(a.out, exist_ok=True)
    for name in names:
        y = SOUNDS[name]().astype(np.float64)
        if a.pitch != 1.0:
            idx = np.arange(0, len(y), a.pitch)
            y = np.interp(idx, np.arange(len(y)), y)
        y = y / max(np.abs(y).max(), 1e-9) * 0.89
        # A tiny fade prevents clicks at both ends.
        k = min(96, len(y) // 2)
        y[:k] *= np.linspace(0, 1, k)
        y[-k:] *= np.linspace(1, 0, k)
        path = os.path.join(a.out, name + ".wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((y * 32767).astype(np.int16).tobytes())
    print(f"{a.out}: {len(names)} sounds: {', '.join(names)}")


if __name__ == "__main__":
    main()
