#!/usr/bin/env python3
"""Test optional tools. A missing dependency is reported as SKIP, not as a failure.

Run: python tests/test_tools.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "video-dna", "scripts")
sys.path.insert(0, SCRIPTS)
results = {"ok": [], "skip": [], "fail": []}


def tool(label, script, *args, cwd, check=None):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = r.stdout + r.stderr
    if r.returncode and "is missing" in text:
        results["skip"].append(label)
        print(f"SKIP  {label}: {text.strip()[-90:]}")
        return
    good = r.returncode == 0 and (check is None or check())
    results["ok" if good else "fail"].append(label)
    print(f"{'ok' if good else 'FAIL'}    {label}" + ("" if good else f"\n{text[-900:]}"))


def ff(*args, cwd):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True, cwd=cwd)


SEEK_PAGE = """<!doctype html><html><body style="margin:0;background:transparent">
<div id="b" style="position:absolute;top:100px;left:0;width:100px;height:100px;background:#ffc531"></div>
<script>window.seek = t => { document.getElementById('b').style.left = (t * 200) + 'px'; };</script>
</body></html>"""

WHISPER_CPP = {"result": {"language": "ro"}, "transcription": [{
    "offsets": {"from": 0, "to": 1500}, "text": " Bună ziua",
    "tokens": [{"text": "[_BEG_]", "offsets": {"from": 0, "to": 0}, "p": 1.0},
               {"text": " Bu", "offsets": {"from": 0, "to": 300}, "p": 0.9},
               {"text": "nă", "offsets": {"from": 300, "to": 600}, "p": 0.7},
               {"text": " ziua", "offsets": {"from": 700, "to": 1500}, "p": 0.3}]}]}


def main():
    import transcribe
    language, segs = transcribe.parse_whisper_cpp(WHISPER_CPP)
    words = segs[0]["words"]
    good = (language == "ro" and [w["word"] for w in words] == ["Bună", "ziua"]
            and words[0]["end"] == 0.6 and words[0]["prob"] == 0.8)
    results["ok" if good else "fail"].append("whisper.cpp parser")
    print(f"{'ok' if good else 'FAIL'}    whisper.cpp parser")

    with tempfile.TemporaryDirectory() as d:
        ex = lambda *names: (lambda: all(os.path.getsize(os.path.join(d, n)) > 0 for n in names))
        ff("-f", "lavfi", "-i", "color=c=red:s=640x360:r=30:d=2", "-f", "lavfi", "-i",
           "color=c=blue:s=640x360:r=30:d=2", "-f", "lavfi", "-i", "sine=f=330:d=4", "-filter_complex",
           "[0][1]concat=n=2:v=1[v]", "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "cut.mp4", cwd=d)
        tool("scenes", "toolbox.py", "scenes", "cut.mp4", "--out", "scenes.json", cwd=d,
             check=lambda: len(json.load(open(os.path.join(d, "scenes.json")))) == 2)
        tool("faces", "toolbox.py", "faces", "cut.mp4", "--out", "faces.json", cwd=d, check=ex("faces.json"))
        tool("blur-faces", "toolbox.py", "blur-faces", "cut.mp4", "blur.mp4", cwd=d, check=ex("blur.mp4"))
        tool("upscale", "toolbox.py", "upscale", "cut.mp4", "up.mp4", "--width", 1080, "--height", 1920, cwd=d,
             check=ex("up.mp4"))
        tool("qr", "toolbox.py", "qr", "https://example.com/ă", "qr.png", cwd=d, check=ex("qr.png"))
        font = "C:/Windows/Fonts/arial.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(font):
            tool("check-font", "toolbox.py", "check-font", font, cwd=d)
        with open(os.path.join(d, "scene.html"), "w", encoding="utf-8") as f:
            f.write(SEEK_PAGE)
        tool("html", "toolbox.py", "html", "scene.html", "scene.png", "--width", 300, "--height", 300,
             "--transparent", cwd=d, check=ex("scene.png"))
        tool("html-seq", "toolbox.py", "html-seq", "scene.html", "frames", "--width", 300, "--height", 300,
             "--duration", 0.5, "--fps", 10, "--transparent", cwd=d,
             check=lambda: len(os.listdir(os.path.join(d, "frames"))) == 5)
        tool("cutout", "toolbox.py", "cutout", "scene.png", "cut.png", cwd=d, check=ex("cut.png"))
        tool("loudness", "toolbox.py", "loudness", "cut.mp4", cwd=d)
        with open(os.path.join(d, "tl.json"), "w", encoding="utf-8") as f:
            json.dump({"fps": 30, "segments": [{"src": "cut.mp4", "start": 0, "end": 2, "speed": 2.0},
                                               {"color": "#000000", "dur": 1}]}, f)
        tool("otio", "toolbox.py", "otio", "tl.json", "tl.otio", cwd=d, check=ex("tl.otio"))
        ff("-f", "lavfi", "-i", "sine=f=220:d=6", "tone.wav", cwd=d)
        if os.environ.get("VIDEO_DNA_HEAVY"):
            tool("stems", "toolbox.py", "stems", "tone.wav", "--out", "stems", cwd=d)

    print(f"\n{len(results['ok'])} ok, {len(results['skip'])} skipped, {len(results['fail'])} failed")
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
