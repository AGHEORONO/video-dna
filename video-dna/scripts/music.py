#!/usr/bin/env python3
"""Generate a simple original music bed as a 48 kHz stereo WAV that loops without a gap.

Example: music.py --out bed.wav --bpm 128 --bars 16 --mood upbeat --seed 3

It also writes bed.beats.json with the beat times, for cutting on the beat.
"""
import argparse
import json
import wave

import numpy as np

SR = 48000
# Chord roots as semitones from the key, with a scale for the melody.
MOODS = {
    "upbeat": {"chords": [0, 7, 9, 5], "scale": [0, 2, 4, 7, 9], "minor": [0, 0, 1, 0]},
    "epic": {"chords": [0, 8, 3, 10], "scale": [0, 3, 5, 7, 10], "minor": [1, 0, 0, 0]},
    "spooky": {"chords": [0, 1, 0, 6], "scale": [0, 3, 6, 7, 10], "minor": [1, 1, 1, 1]},
    "calm": {"chords": [0, 5, 9, 7], "scale": [0, 2, 4, 7, 9], "minor": [0, 0, 1, 0]},
}


def freq(semi, base=220.0):
    return base * 2 ** (semi / 12)


def add(buf, start, x):
    """Mix x into buf at a sample index, wrapping so tails carry over the loop point."""
    idx = (start + np.arange(len(x))) % len(buf)
    np.add.at(buf, idx, x)


def pulse(f, n, duty=0.5, decay=6.0):
    t = np.arange(n) / SR
    y = np.where((t * f) % 1 < duty, 1.0, -1.0) * np.exp(-t * decay)
    k = min(48, n // 2)
    y[:k] *= np.linspace(0, 1, k)
    y[-k:] *= np.linspace(1, 0, k)
    return y


def kick():
    t = np.arange(int(0.18 * SR)) / SR
    return np.sin(2 * np.pi * (50 * t + 8 * (1 - np.exp(-t * 35)))) * np.exp(-t * 18)


def noise_hit(rng, dur, decay):
    t = np.arange(int(dur * SR)) / SR
    return rng.normal(0, 1, len(t)) * np.exp(-t * decay)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--bpm", type=float, default=128)
    p.add_argument("--bars", type=int, default=16, help="4/4 bars; the loop length")
    p.add_argument("--mood", choices=MOODS, default="upbeat")
    p.add_argument("--key", type=int, default=0, help="semitones up from A")
    p.add_argument("--seed", type=int, default=1, help="change for a different melody")
    p.add_argument("--no-drums", action="store_true")
    a = p.parse_args()

    rng = np.random.default_rng(a.seed)
    mood = MOODS[a.mood]
    # Whole samples per sixteenth note, so beats stay exact over the whole loop.
    six = round(SR * 60 / a.bpm / 4)
    total = six * 16 * a.bars
    left, right = np.zeros(total), np.zeros(total)
    # A short motif repeats through the piece, which makes it sound composed.
    motif = [(rng.integers(0, 16), rng.choice(mood["scale"]) + 12 * rng.integers(0, 2))
             for _ in range(7)]

    for bar in range(a.bars):
        cidx = bar % 4
        root = mood["chords"][cidx] + a.key
        third = 3 if mood["minor"][cidx] else 4
        start = bar * 16 * six
        for s in range(16):
            at = start + s * six
            if s % 2 == 0:
                bass = pulse(freq(root, 55.0) * (2 if s % 8 == 6 else 1), six * 2, 0.5, 4) * 0.30
                add(left, at, bass)
                add(right, at, bass)
            arp = [0, third, 7, 12][s % 4]
            note = pulse(freq(root + arp, 220.0), six, 0.25, 9) * 0.10
            add(left, at, note * 1.2)
            add(right, at, note * 0.7)
            if not a.no_drums and a.mood != "calm":
                if s % 4 == 0:
                    k = kick() * 0.55
                    add(left, at, k)
                    add(right, at, k)
                if s % 8 == 4:
                    sn = noise_hit(rng, 0.12, 22) * 0.20
                    add(left, at, sn)
                    add(right, at, sn)
                if s % 2 == 1:
                    h = np.diff(noise_hit(rng, 0.03, 120), prepend=0) * 0.10
                    add(left, at, h)
                    add(right, at, h)
        if bar % 8 >= 4:  # the melody enters for the second half of each 8 bars
            for pos, semi in motif:
                n = pulse(freq(root + int(semi), 440.0), six * 2, 0.5, 5) * 0.14
                add(left, start + int(pos) * six, n * 0.8)
                add(right, start + int(pos) * six, n * 1.1)

    stereo = np.stack([left, right], 1)
    stereo *= 0.89 / max(np.abs(stereo).max(), 1e-9)
    with wave.open(a.out, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((stereo * 32767).astype(np.int16).tobytes())
    beats = [round(i * 4 * six / SR, 4) for i in range(4 * a.bars)]
    side = a.out.rsplit(".", 1)[0] + ".beats.json"
    with open(side, "w", encoding="utf-8") as f:
        json.dump({"bpm": round(SR * 60 / (4 * six), 3), "duration": total / SR, "beats": beats,
                   "bars": [beats[i] for i in range(0, len(beats), 4)]}, f, indent=1)
    print(f"{a.out}: {total / SR:.2f}s loop, {a.mood}, {a.bpm:g} BPM; beats in {side}")


if __name__ == "__main__":
    main()
