#!/usr/bin/env python3
"""Check a rendered video. Exits 1 if any check fails.

Example: qa.py final.mp4 --width 1080 --height 1920 --fps 30 --max-mb 60 --ass graphics.ass
         qa.py loop.mp4 --width 1920 --height 1080 --qr-at 3,9 --qr-expect https://example.com
"""
import argparse
import json
import os
import re
import subprocess
import sys
from fractions import Fraction


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def stream_duration(st):
    if st.get("duration"):
        return float(st["duration"])
    return None


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    return (float(i.group(1)) if i else None, float(tp.group(1)) if tp else None)


def lint_ass(path, width, height, min_text):
    """Return problems found in an ASS file: wrong canvas, small text, off-screen positions."""
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    issues = []
    res = {k: re.search(rf"^{k}:\s*(\d+)", text, re.M) for k in ("PlayResX", "PlayResY")}
    if not all(res.values()):
        issues.append("PlayResX or PlayResY is missing, so coordinates will not equal pixels")
    else:
        rx, ry = int(res["PlayResX"].group(1)), int(res["PlayResY"].group(1))
        if width and height and (rx, ry) != (width, height):
            issues.append(f"PlayRes is {rx}x{ry} but the video is {width}x{height}")
    sizes = {}
    for m in re.finditer(r"^Style:\s*([^,]+),[^,]*,(\d+(?:\.\d+)?)", text, re.M):
        sizes[m.group(1).strip()] = float(m.group(2))
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        if len(fields) < 10:
            issues.append(f"line {line_no}: malformed Dialogue")
            continue
        style, body = fields[3].strip(), fields[9]
        visible = re.sub(r"\{[^}]*\}", "", body).strip()
        if style not in sizes and style != "Default":
            issues.append(f"line {line_no}: unknown style {style!r}")
        drawing = re.search(r"\\p[1-9]", body)
        if visible and not drawing:
            fs = re.findall(r"\\fs(\d+(?:\.\d+)?)", body)
            size = float(fs[-1]) if fs else sizes.get(style, 0)
            if size and size < min_text:
                issues.append(f"line {line_no}: text size {size:g} under {min_text:g}: {visible[:40]!r}")
        if width and height:
            for m in re.finditer(r"\\pos\((-?[\d.]+),(-?[\d.]+)\)", body):
                x, y = float(m.group(1)), float(m.group(2))
                if not (0 <= x <= width and 0 <= y <= height):
                    issues.append(f"line {line_no}: \\pos({x:g},{y:g}) is off-screen")
    return issues


def check_qr(path, times, expect):
    import cv2
    cap = cv2.VideoCapture(path)
    det = cv2.QRCodeDetector()
    results = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        data = ""
        if ok:
            data, _, _ = det.detectAndDecode(frame)
        results.append((t, data, bool(data) and (expect is None or data == expect)))
    cap.release()
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("video")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--fps", type=float)
    p.add_argument("--max-mb", type=float)
    p.add_argument("--max-seconds", type=float)
    p.add_argument("--no-audio", action="store_true", help="the video is meant to be silent")
    p.add_argument("--ass")
    p.add_argument("--min-text", type=float, help="smallest ASS text size; default 40 at 1080 wide")
    p.add_argument("--qr-at", help="comma-separated seconds where a QR code must decode")
    p.add_argument("--qr-expect", help="exact text the QR must contain")
    a = p.parse_args()

    failures = []

    def check(ok, label):
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            failures.append(label)

    info = probe(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    w, h = v["width"], v["height"]
    fps = float(Fraction(v["avg_frame_rate"])) if v["avg_frame_rate"] != "0/0" else 0.0
    vd = stream_duration(v) or float(info["format"]["duration"])
    mb = os.path.getsize(a.video) / 1e6

    if a.width and a.height:
        check((w, h) == (a.width, a.height), f"resolution {w}x{h}")
    else:
        print(f"INFO  resolution {w}x{h}")
    if a.fps:
        check(abs(fps - a.fps) < 0.01, f"frame rate {fps:.3f}")
    else:
        print(f"INFO  frame rate {fps:.3f}")
    check(v["pix_fmt"] == "yuv420p", f"pixel format {v['pix_fmt']}")
    if a.max_mb:
        check(mb <= a.max_mb, f"size {mb:.1f} MB (limit {a.max_mb:g})")
    else:
        print(f"INFO  size {mb:.1f} MB")
    if a.max_seconds:
        check(vd <= a.max_seconds, f"duration {vd:.3f}s (limit {a.max_seconds:g})")

    if a.no_audio:
        check(au is None, "no audio stream")
    else:
        check(au is not None, "audio stream present")
    if au is not None:
        ad = stream_duration(au) or vd
        # AAC framing rounds up to 1024 samples, on top of one video frame of tolerance.
        tol = (1 / fps if fps else 0.034) + 1024 / 48000
        check(abs(vd - ad) <= tol, f"video {vd:.3f}s, audio {ad:.3f}s, tolerance {tol:.3f}s")
        lufs, peak = loudness(a.video)
        if lufs is not None:
            check(lufs < -6 and lufs > -30, f"loudness {lufs:.1f} LUFS")
        if peak is not None:
            check(peak <= 0.0, f"true peak {peak:.1f} dBFS")

    if a.ass:
        min_text = a.min_text or 40 * (w / 1080 if h > w else 1)
        issues = lint_ass(a.ass, w, h, min_text)
        check(not issues, f"ASS checks: {len(issues)} problem(s)")
        for i in issues[:30]:
            print(f"      {i}")

    if a.qr_at:
        for t, data, ok in check_qr(a.video, [float(x) for x in a.qr_at.split(",")], a.qr_expect):
            check(ok, f"QR at {t:g}s: {data or 'not decoded'}")

    print(f"\n{'ALL AUTOMATIC CHECKS PASSED' if not failures else str(len(failures)) + ' CHECK(S) FAILED'}")
    print("These checks do not replace looking at frames, and nobody has heard the audio yet.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
