#!/usr/bin/env python3
"""Transcribe speech to word-level JSON with faster-whisper and flag uncertain words.

Example: transcribe.py clip.mp4 --lang ro --out transcripts/clip.json
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np


def load_audio(path):
    """Decode to mono 16 kHz float32 through ffmpeg."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
         "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("media")
    p.add_argument("--out", required=True)
    p.add_argument("--lang", default=None, help="language code such as ro or en; detected if omitted")
    p.add_argument("--model", default="small")
    p.add_argument("--device", default="auto")
    p.add_argument("--compute-type", default="int8")
    p.add_argument("--min-confidence", type=float, default=0.5,
                   help="words below this are listed as uncertain")
    a = p.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. See references/environments.md")

    model = WhisperModel(a.model, device=a.device, compute_type=a.compute_type)
    segs, info = model.transcribe(load_audio(a.media), language=a.lang,
                                  word_timestamps=True, vad_filter=True)
    out = {"source": os.path.basename(a.media), "language": info.language, "segments": []}
    uncertain = []
    for s in segs:
        words = [{"word": w.word.strip(), "start": round(w.start, 3),
                  "end": round(w.end, 3), "prob": round(w.probability, 3)}
                 for w in (s.words or [])]
        out["segments"].append({"start": round(s.start, 3), "end": round(s.end, 3),
                                "text": s.text.strip(), "words": words})
        low = [w["word"] for w in words if w["prob"] < a.min_confidence]
        if low:
            uncertain.append({"start": round(s.start, 2), "text": s.text.strip(), "low": low})
    out["uncertain"] = uncertain

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{a.out}: {len(out['segments'])} segments, language {info.language}, "
          f"{len(uncertain)} uncertain")
    for u in uncertain:
        print(f"  ? {u['start']:.2f}s: {u['text']}  [{', '.join(u['low'])}]")


if __name__ == "__main__":
    main()
