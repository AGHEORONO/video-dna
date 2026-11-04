#!/usr/bin/env python3
"""Transcribe speech to word-level JSON with Whisper and flag uncertain words.

Backends: faster-whisper, openai-whisper and whisper.cpp run locally. --backend auto
uses the first one available. openai-api uploads the audio to OpenAI, so it only runs
when asked for by name.

Examples:
  transcribe.py clip.mp4 --lang ro --out transcripts/clip.json
  transcribe.py clip.mp4 --lang ro --model models/small --out transcripts/clip.json
  transcribe.py clip.mp4 --backend whisper-cpp --model ggml-small.bin --out clip.json
  transcribe.py clip.mp4 --lang ro --initial-prompt "Name One, Place Two" --out clip.json
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

SETUP_HINT = "Run: python scripts/setup_tools.py --profile transcribe. See references/environments.md"


def load_audio(path):
    """Decode to mono 16 kHz float32 through ffmpeg."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def word(text, start, end, prob):
    return {"word": text.strip(), "start": round(float(start), 3), "end": round(float(end), 3),
            "prob": round(float(prob), 3)}


def segment(start, end, text, words):
    return {"start": round(float(start), 3), "end": round(float(end), 3), "text": text.strip(),
            "words": words}


def run_faster_whisper(a):
    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device=a.device, compute_type=a.compute_type)
    segs, info = model.transcribe(load_audio(a.media), language=a.lang, word_timestamps=True,
                                  vad_filter=a.vad, initial_prompt=a.initial_prompt)
    out = [segment(s.start, s.end, s.text, [word(w.word, w.start, w.end, w.probability)
                                            for w in (s.words or [])]) for s in segs]
    return info.language, out


def run_openai_whisper(a):
    import whisper
    model = whisper.load_model(a.model)
    r = model.transcribe(load_audio(a.media), language=a.lang, word_timestamps=True, fp16=False,
                         initial_prompt=a.initial_prompt)
    out = [segment(s["start"], s["end"], s["text"],
                   [word(w["word"], w["start"], w["end"], w.get("probability", 1.0))
                    for w in s.get("words", [])]) for s in r["segments"]]
    return r.get("language"), out


def find_whisper_cpp(explicit=None):
    if explicit:
        return explicit
    for name in ("whisper-cli", "whisper-cpp"):
        found = shutil.which(name)
        if found:
            return found
    return None


def parse_whisper_cpp(data):
    """Turn whisper.cpp -ojf output into segments. A token with a leading space starts a word."""
    out = []
    for s in data.get("transcription", []):
        words, cur = [], None
        for t in s.get("tokens", []):
            text = t.get("text", "")
            if not text or text.startswith("[_") or "offsets" not in t:
                continue
            if cur is None or text.startswith(" "):
                if cur:
                    words.append(cur)
                cur = {"text": "", "start": t["offsets"]["from"], "end": t["offsets"]["to"], "p": []}
            cur["text"] += text
            cur["end"] = t["offsets"]["to"]
            cur["p"].append(t.get("p", 1.0))
        if cur:
            words.append(cur)
        out.append(segment(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s.get("text", ""),
                           [word(w["text"], w["start"] / 1000, w["end"] / 1000,
                                 sum(w["p"]) / len(w["p"])) for w in words]))
    return data.get("result", {}).get("language"), out


def run_whisper_cpp(a):
    binary = find_whisper_cpp(a.whisper_cpp_bin)
    if not binary:
        sys.exit("whisper.cpp was not found. Use --whisper-cpp-bin. " + SETUP_HINT)
    if not os.path.isfile(a.model):
        sys.exit("whisper.cpp needs --model set to a ggml .bin file")
    with tempfile.TemporaryDirectory() as tmp:
        wav, base = os.path.join(tmp, "audio.wav"), os.path.join(tmp, "out")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.media, "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", wav], check=True)
        cmd = [binary, "-m", a.model, "-f", wav, "-l", a.lang or "auto", "-ojf", "-of", base]
        if a.initial_prompt:
            cmd += ["--prompt", a.initial_prompt]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(base + ".json", encoding="utf-8") as f:
            return parse_whisper_cpp(json.load(f))


def run_openai_api(a):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("--backend openai-api needs the OPENAI_API_KEY environment variable")
    print("Sending this audio to OpenAI for transcription.")
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = os.path.join(tmp, "audio.mp3")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.media, "-vn", "-ac", "1", "-ar", "16000",
                        "-b:a", "64k", mp3], check=True)
        with open(mp3, "rb") as f:
            audio = f.read()
    fields = [("model", "whisper-1"), ("response_format", "verbose_json"),
              ("timestamp_granularities[]", "word"), ("timestamp_granularities[]", "segment")]
    if a.lang:
        fields.append(("language", a.lang))
    if a.initial_prompt:
        fields.append(("prompt", a.initial_prompt))
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields:
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.mp3"\r\n'
             "Content-Type: audio/mpeg\r\n\r\n").encode() + audio + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    words = data.get("words", [])
    out = [segment(s["start"], s["end"], s["text"],
                   [word(w["word"], w["start"], w["end"], 1.0) for w in words
                    if s["start"] <= (w["start"] + w["end"]) / 2 < s["end"]])
           for s in data.get("segments", [])]
    return data.get("language"), out


BACKENDS = {"faster-whisper": run_faster_whisper, "openai-whisper": run_openai_whisper,
            "whisper-cpp": run_whisper_cpp, "openai-api": run_openai_api}


def choose_backend(a):
    if a.backend != "auto":
        return a.backend
    if importlib.util.find_spec("faster_whisper"):
        return "faster-whisper"
    if importlib.util.find_spec("whisper"):
        return "openai-whisper"
    if find_whisper_cpp(a.whisper_cpp_bin):
        return "whisper-cpp"
    sys.exit("No local Whisper backend was found. " + SETUP_HINT)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("media")
    p.add_argument("--out", required=True)
    p.add_argument("--backend", default="auto", choices=["auto", *BACKENDS])
    p.add_argument("--lang", default=None, help="language code such as ro or en; detected if omitted")
    p.add_argument("--model", default="small", help="size name, local model folder, or ggml .bin file")
    p.add_argument("--device", default="auto")
    p.add_argument("--compute-type", default="int8")
    p.add_argument("--vad", default=True, action=argparse.BooleanOptionalAction)
    p.add_argument("--initial-prompt", help="names and jargon that help recognition")
    p.add_argument("--whisper-cpp-bin")
    p.add_argument("--min-confidence", type=float, default=0.5,
                   help="words below this are listed as uncertain")
    a = p.parse_args()

    backend = choose_backend(a)
    try:
        language, segments = BACKENDS[backend](a)
    except ImportError:
        sys.exit(f"{backend} is not installed. " + SETUP_HINT)

    uncertain = []
    for s in segments:
        low = [w["word"] for w in s["words"] if w["prob"] < a.min_confidence]
        if low:
            uncertain.append({"start": round(s["start"], 2), "text": s["text"], "low": low})
    out = {"source": os.path.basename(a.media), "language": language, "backend": backend,
           "segments": segments, "uncertain": uncertain}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{a.out}: {len(segments)} segments, language {language}, backend {backend}, "
          f"{len(uncertain)} uncertain")
    for u in uncertain:
        print(f"  ? {u['start']:.2f}s: {u['text']}  [{', '.join(u['low'])}]")


if __name__ == "__main__":
    main()
