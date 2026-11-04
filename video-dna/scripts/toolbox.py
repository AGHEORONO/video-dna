#!/usr/bin/env python3
"""Small helpers around optional tools. See references/tools.md.

Examples:
  toolbox.py scenes clip.mp4 --out scenes.json
  toolbox.py cutout photo.jpg person.png
  toolbox.py faces clip.mp4 --out faces.json
  toolbox.py blur-faces clip.mp4 blurred.mp4
  toolbox.py upscale old.mp4 sharp.mp4 --width 1080 --height 1920
  toolbox.py qr https://example.com qr.png
  toolbox.py check-font font.ttf
  toolbox.py html scene.html scene.png --width 1080 --height 1920 --transparent
  toolbox.py html-seq scene.html frames --width 1080 --height 1920 --duration 3
  toolbox.py stems song.mp3 --out stems
  toolbox.py tts "Hello there" voice.wav --model voice.onnx
  toolbox.py loudness final.mp4
  toolbox.py otio timeline.json timeline.otio
"""
import argparse
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


def need(module, package, profile):
    try:
        return importlib.import_module(module)
    except ImportError:
        sys.exit(f"{package} is missing. Run: python scripts/setup_tools.py --profile {profile}")


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def scenes(a):
    sd = need("scenedetect", "scenedetect", "vision")
    found = sd.detect(a.video, sd.ContentDetector(threshold=a.threshold))
    out = [{"start": round(s.get_seconds(), 3), "end": round(e.get_seconds(), 3)} for s, e in found]
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{a.out}: {len(out)} scenes")


def cutout(a):
    rembg = need("rembg", "rembg", "vision")
    src, dst = pathlib.Path(a.input), pathlib.Path(a.output)
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        pairs = [(f, dst / (f.stem + ".png")) for f in src.iterdir()
                 if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    else:
        pairs = [(src, dst)]
    for f, t in pairs:
        t.write_bytes(rembg.remove(f.read_bytes()))
        print(t)


def face_detector(cv2):
    """YuNet, bundled in assets/ so that face checks also work offline."""
    model = pathlib.Path(__file__).resolve().parent.parent / "assets" / "face_detection_yunet_2023mar.onnx"
    # OpenCV can't open some non-ASCII paths on Windows, so it loads the model from memory.
    np = need("numpy", "numpy", "core")
    data = np.frombuffer(model.read_bytes(), np.uint8)
    config = np.empty(0, np.uint8)
    return cv2.FaceDetectorYN.create("onnx", data, config, (320, 320), 0.7)


def detect(det, cv2, frame):
    h, w = frame.shape[:2]
    det.setInputSize((w, h))
    found = det.detect(frame)[1]
    return [] if found is None else [[int(v) for v in f[:4]] for f in found]


def faces(a):
    cv2 = need("cv2", "opencv-python", "core")
    det, cap, out = face_detector(cv2), cv2.VideoCapture(a.video), []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step, i = max(1, round(fps * a.every)), 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            out.append({"t": round(i / fps, 3), "boxes": detect(det, cv2, frame)})
        i += 1
    cap.release()
    pathlib.Path(a.out).write_text(json.dumps(out), encoding="utf-8")
    print(f"{a.out}: faces on {sum(bool(x['boxes']) for x in out)} of {len(out)} sampled frames")


def blur_faces(a):
    cv2 = need("cv2", "opencv-python", "core")
    det, cap = face_detector(cv2), cv2.VideoCapture(a.input)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step, k = max(1, round(fps * a.every)), a.strength | 1
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                            "-r", str(fps), "-i", "-", "-i", a.input, "-map", "0:v", "-map", "1:a?", "-c:v",
                            "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", a.output],
                           stdin=subprocess.PIPE)
    boxes, i = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            boxes = detect(det, cv2, frame)
        for x, y, bw, bh in boxes:
            m = bh // 4
            x0, y0, x1, y1 = max(x - m, 0), max(y - m, 0), min(x + bw + m, w), min(y + bh + m, h)
            frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1], (k, k), 0)
        enc.stdin.write(frame.tobytes())
        i += 1
    cap.release()
    enc.stdin.close()
    if enc.wait():
        sys.exit("ffmpeg failed")
    print(f"{a.output}: done. Detection can miss faces, so check the frames.")


def upscale(a):
    run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-map", "0:v", "-map", "0:a?", "-vf",
         f"scale={a.width}:{a.height}:flags=lanczos,hqdn3d=1.5:1.5:6:6,unsharp=5:5:0.6",
         "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy", a.output])
    print(a.output)


def qr(a):
    qrcode = need("qrcode", "qrcode[pil]", "graphics")
    cv2 = need("cv2", "opencv-python", "core")
    np = need("numpy", "numpy", "core")
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=20)
    q.add_data(a.text)
    q.make(fit=True)
    q.make_image(fill_color=a.fg, back_color=a.bg).convert("RGB").resize((a.size, a.size), 0).save(a.output)
    img = cv2.imdecode(np.fromfile(a.output, np.uint8), cv2.IMREAD_COLOR)
    got = cv2.QRCodeDetector().detectAndDecode(img)[0]
    if got != a.text:
        sys.exit(f"{a.output}: decoding check failed, read {got!r}")
    print(f"{a.output}: decodes correctly")


def check_font(a):
    tt = need("fontTools.ttLib", "fonttools", "graphics")
    cmap = tt.TTFont(a.font).getBestCmap()
    missing = [c for c in a.text if ord(c) not in cmap and not c.isspace()]
    if missing:
        sys.exit("Missing characters: " + " ".join(missing))
    print("All characters are present.")


def page_for(a, pw):
    browser = None
    # Fall back to an installed browser when Playwright's own could not be downloaded.
    for channel in (None, "chrome", "msedge"):
        try:
            browser = pw.chromium.launch(channel=channel)
            break
        except Exception:
            continue
    if browser is None:
        sys.exit("No browser found. Run: python -m playwright install chromium")
    page = browser.new_page(viewport={"width": a.width, "height": a.height},
                            device_scale_factor=getattr(a, "scale", 1))
    page.goto(pathlib.Path(a.input).resolve().as_uri(), wait_until="networkidle")
    page.evaluate("document.fonts.ready.then(() => true)")
    return browser, page


def html(a):
    sync = need("playwright.sync_api", "playwright", "graphics")
    with sync.sync_playwright() as pw:
        browser, page = page_for(a, pw)
        page.screenshot(path=a.output, omit_background=a.transparent)
        browser.close()
    print(a.output)


def html_seq(a):
    sync = need("playwright.sync_api", "playwright", "graphics")
    os.makedirs(a.outdir, exist_ok=True)
    n = round(a.duration * a.fps)
    with sync.sync_playwright() as pw:
        browser, page = page_for(a, pw)
        if not page.evaluate("typeof window.seek === 'function'"):
            browser.close()
            sys.exit("The page must define window.seek(seconds).")
        for i in range(n):
            page.evaluate("t => window.seek(t)", i / a.fps)
            page.screenshot(path=os.path.join(a.outdir, f"frame_{i:05d}.png"), omit_background=a.transparent)
        browser.close()
    print(f"{a.outdir}: {n} frames. Make a clip with: ffmpeg -framerate {a.fps} -i frame_%05d.png "
          "-c:v qtrle scene.mov, then add it with the overlay filter.")


def stems(a):
    need("demucs", "demucs", "audio")
    run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-o", a.out, a.audio])
    print(f"Voice and music are in {a.out}")


def tts(a):
    exe = shutil.which("piper")
    cmd = [exe] if exe else [sys.executable, "-m", "piper"]
    subprocess.run(cmd + ["--model", a.model, "--output_file", a.output], input=a.text.encode("utf-8"), check=True)
    print(a.output)


def loudness(a):
    pyln = need("pyloudnorm", "pyloudnorm", "audio")
    sf = need("soundfile", "soundfile", "audio")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        run(["ffmpeg", "-y", "-v", "error", "-i", a.file, "-vn", "-ac", "2", "-ar", "48000", wav])
        data, rate = sf.read(wav)
    lufs = pyln.Meter(rate).integrated_loudness(data)
    print(f"{lufs:.1f} LUFS, change by {a.target - lufs:+.1f} dB to reach {a.target:g}")


def otio(a):
    ot = need("opentimelineio", "opentimelineio", "graphics")
    with open(a.timeline, encoding="utf-8") as f:
        tl = json.load(f)
    fps = tl.get("fps", 30)
    rt = lambda sec: ot.opentime.RationalTime(round(sec * fps), fps)
    base = os.path.dirname(os.path.abspath(a.timeline))
    track = ot.schema.Track(name="Video", kind=ot.schema.TrackKind.Video)
    for s in tl["segments"]:
        if "src" in s:
            clip = ot.schema.Clip(name=os.path.basename(s["src"]),
                                  media_reference=ot.schema.ExternalReference(
                                      target_url=pathlib.Path(base, s["src"]).as_uri()),
                                  source_range=ot.opentime.TimeRange(rt(s["start"]), rt(s["end"] - s["start"])))
            if s.get("speed", 1.0) != 1.0:
                clip.metadata["video_dna_speed"] = s["speed"]
            track.append(clip)
        else:
            track.append(ot.schema.Gap(source_range=ot.opentime.TimeRange(rt(0), rt(s["dur"]))))
    timeline = ot.schema.Timeline(name=os.path.basename(a.timeline))
    timeline.tracks.append(track)
    ot.adapters.write_to_file(timeline, a.output)
    print(f"{a.output}: {len(track)} items. Graphics and audio mixes are not included.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def cmd(name, fn, *args):
        s = sub.add_parser(name)
        s.set_defaults(fn=fn)
        for names, kw in args:
            s.add_argument(*names, **kw)

    def o(*names, **kw):
        return names, kw

    size = [o("--width", type=int, required=True), o("--height", type=int, required=True)]
    cmd("scenes", scenes, o("video"), o("--out", required=True), o("--threshold", type=float, default=27.0))
    cmd("cutout", cutout, o("input"), o("output"))
    cmd("faces", faces, o("video"), o("--out", required=True), o("--every", type=float, default=0.5))
    cmd("blur-faces", blur_faces, o("input"), o("output"), o("--every", type=float, default=0.2),
        o("--strength", type=int, default=51))
    cmd("upscale", upscale, o("input"), o("output"), *size)
    cmd("qr", qr, o("text"), o("output"), o("--size", type=int, default=1000), o("--fg", default="#000000"),
        o("--bg", default="#FFFFFF"))
    cmd("check-font", check_font, o("font"), o("--text", default="ăâîșțĂÂÎȘȚ"))
    cmd("html", html, o("input"), o("output"), *size, o("--transparent", action="store_true"),
        o("--scale", type=float, default=1))
    cmd("html-seq", html_seq, o("input"), o("outdir"), *size, o("--fps", type=int, default=30),
        o("--duration", type=float, required=True), o("--transparent", action="store_true"))
    cmd("stems", stems, o("audio"), o("--out", required=True))
    cmd("tts", tts, o("text"), o("output"), o("--model", required=True))
    cmd("loudness", loudness, o("file"), o("--target", type=float, default=-14.0))
    cmd("otio", otio, o("timeline"), o("output"))
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    a.fn(a)


if __name__ == "__main__":
    main()
