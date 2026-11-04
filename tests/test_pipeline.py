#!/usr/bin/env python3
"""End-to-end test with synthetic media. Needs ffmpeg, numpy and opencv-python.

Run: python tests/test_pipeline.py
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "video-dna", "scripts")


def script(name, *args, cwd=None):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    print(f"--- {name}\n{r.stdout.strip()}")
    if r.returncode:
        print(r.stderr)
    return r


def ff(*args, cwd=None):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True, cwd=cwd)


def make_qr(path, text):
    """Encode a QR with OpenCV, enlarged and given a white quiet zone."""
    import cv2
    qr = cv2.QRCodeEncoder.create().encode(text)
    qr = cv2.resize(qr, None, fx=12, fy=12, interpolation=cv2.INTER_NEAREST)
    img = cv2.copyMakeBorder(qr, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
    h, w = img.shape
    canvas = np.full((1920, 1080), 255, np.uint8)
    y, x = (1920 - h) // 2, (1080 - w) // 2
    canvas[y:y + h, x:x + w] = img
    ok, buf = cv2.imencode(".png", canvas)
    assert ok
    buf.tofile(path)


ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Arial,96,&H0000D7FF,&H0000D7FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 10,0:00:00.20,0:00:02.50,Title,,0,0,0,,{\\an5\\pos(540,500)\\fscx0\\fscy0\\t(0,120,\\fscx115\\fscy115)\\t(120,200,\\fscx100\\fscy100)}TITLU ĂÂÎȘȚ
"""

TRANSCRIPT = {"source": "a.mp4", "language": "ro", "segments": [{
    "start": 0.2, "end": 2.6, "text": "Ce mai faci prietene dragă",
    "words": [{"word": w, "start": s, "end": e, "prob": 0.9} for w, s, e in [
        ("Ce", 0.2, 0.5), ("mai", 0.5, 0.8), ("faci", 0.8, 1.2),
        ("prostule", 1.3, 1.8), ("dragă.", 1.9, 2.6)]]}]}


def main():
    failures = []

    def expect(cond, label):
        print(f"{'ok' if cond else 'FAILED'}: {label}")
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as d:
        ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=25:d=6", "-f", "lavfi", "-i",
           "sine=f=330:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           "a.mp4", cwd=d)
        ff("-f", "lavfi", "-i", "testsrc=s=720x1280:r=30:d=8", "-an", "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "b.mp4", cwd=d)
        qr_url = "https://example.com/video-dna"
        make_qr(os.path.join(d, "qr.png"), qr_url)

        expect(script("doctor.py").returncode == 0, "doctor reports render support")
        expect(script("sfx.py", "--out", "sfx", cwd=d).returncode == 0, "sfx generates")
        for f in os.listdir(os.path.join(d, "sfx")):
            with wave.open(os.path.join(d, "sfx", f)) as w:
                peak = np.abs(np.frombuffer(w.readframes(w.getnframes()), np.int16)).max()
            expect(0 < peak < 32767, f"sfx {f} has signal without clipping")

        # Generated music: known tempo, loop length, and beats.py recovers the tempo.
        r = script("music.py", "--out", "m.wav", "--bpm", 120, "--bars", 8, "--seed", 2, cwd=d)
        expect(r.returncode == 0, "music generates")
        meta = json.load(open(os.path.join(d, "m.beats.json")))
        expect(abs(meta["duration"] - 16.0) < 0.01, "8 bars at 120 BPM last 16 s")
        r = script("beats.py", "m.wav", "--out", "beats.json", cwd=d)
        got = json.load(open(os.path.join(d, "beats.json")))
        expect(any(abs(got["bpm"] * k - 120) < 3 for k in (0.5, 1, 2)),
               f"beats.py finds the tempo: {got['bpm']} for 120 BPM")
        expect(len(got["beats"]) > 8, "beats.py returns beats")

        tl = {"width": 1080, "height": 1920, "fps": 30,
              "segments": [
                  {"src": "a.mp4", "start": 0.0, "end": 3.0, "captions": True},
                  {"src": "b.mp4", "start": 1.0, "end": 7.0, "speed": 3.0},
                  {"image": "qr.png", "dur": 2.0},
                  {"color": "#101820", "dur": 1.0}],
              "music": [{"src": "m.wav", "at": 0.0, "dur": 8.0, "gain_db": -10, "fade_out": 0.5}],
              "sfx": [{"src": "sfx/impact.wav", "at": 0.2, "gain_db": -6}],
              "ass": "g.ass", "out": "out/final.mp4", "no_music_out": "out/final_nm.mp4"}
        json.dump(tl, open(os.path.join(d, "tl.json"), "w"))
        open(os.path.join(d, "g.ass"), "w", encoding="utf-8").write(ASS)
        os.makedirs(os.path.join(d, "tr"))
        json.dump(TRANSCRIPT, open(os.path.join(d, "tr", "a.json"), "w", encoding="utf-8"))

        expect(script("captions.py", "tl.json", "--transcripts", "tr", "--merge", "g.ass",
                      "--censor", "prostule", cwd=d).returncode == 0, "captions merge")
        first = open(os.path.join(d, "g.ass"), encoding="utf-8").read()
        expect("p******e" in first and "prostule" not in first, "censoring stars the word")
        script("captions.py", "tl.json", "--transcripts", "tr", "--merge", "g.ass",
               "--censor", "prostule", cwd=d)
        expect(open(os.path.join(d, "g.ass"), encoding="utf-8").read() == first,
               "re-running captions does not stack them")

        expect(script("render.py", "tl.json", cwd=d).returncode == 0, "render succeeds")
        qa = ["--width", 1080, "--height", 1920, "--fps", 30, "--ass", "g.ass"]
        expect(script("qa.py", "out/final.mp4", *qa, "--qr-at", 6.0, "--qr-expect", qr_url,
                      cwd=d).returncode == 0, "QA passes, including the QR")
        expect(script("qa.py", "out/final_nm.mp4", *qa, cwd=d).returncode == 0, "no-music QA passes")

        # Total: 3 s + 2 s + 2 s + 1 s = 8 s at 30 fps.
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0",
                            "out/final.mp4"], capture_output=True, text=True, cwd=d).stdout.strip()
        expect(n == "240", f"exactly 240 frames, got {n}")

        # QA must catch real faults, not just pass everything.
        open(os.path.join(d, "bad.ass"), "w", encoding="utf-8").write(
            ASS.replace("Title,Arial,96", "Title,Arial,20").replace("pos(540,500)", "pos(1500,500)"))
        bad = script("qa.py", "out/final.mp4", *qa[:-1], "bad.ass", cwd=d)
        expect(bad.returncode == 1 and "off-screen" in bad.stdout and "under" in bad.stdout,
               "QA catches small and off-screen text")
        expect(script("qa.py", "out/final.mp4", "--qr-at", 0.5, cwd=d).returncode == 1,
               "QA fails when no QR is present")

        # Cached segments make a re-render fast, and the result stays the same length.
        expect(script("render.py", "tl.json", cwd=d).returncode == 0, "re-render from cache")

        r = script("contact_sheet.py", "out/final.mp4", "--every", 1, "--out", "sheet.jpg", cwd=d)
        expect(r.returncode == 0 and os.path.getsize(os.path.join(d, "sheet.jpg")) > 1000,
               "contact sheet is written")

        r = script("fit_size.py", "out/final.mp4", "small.mp4", "--target-mb", 0.5, cwd=d)
        expect(r.returncode == 0 and os.path.getsize(os.path.join(d, "small.mp4")) <= 0.5e6,
               "fit_size reaches the target")
        r = script("fit_size.py", "out/final.mp4", "--split-mb", 0.2, cwd=d)
        parts = sorted(f for f in os.listdir(os.path.join(d, "out")) if ".part" in f)
        joined = b"".join(open(os.path.join(d, "out", f), "rb").read() for f in parts)
        expect(joined == open(os.path.join(d, "out", "final.mp4"), "rb").read(),
               "split parts rejoin into the original")

        # Keep review material outside the temp folder if asked.
        keep = os.environ.get("VIDEO_DNA_KEEP")
        if keep:
            import shutil
            os.makedirs(keep, exist_ok=True)
            for f in ("out/final.mp4", "sheet.jpg", "g.ass"):
                shutil.copy(os.path.join(d, f), keep)

    print(f"\n{'ALL PASSED' if not failures else 'FAILED: ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
