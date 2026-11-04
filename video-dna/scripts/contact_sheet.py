#!/usr/bin/env python3
"""Make a timestamped grid of frames from a video, for reviewing footage or renders.

Example: contact_sheet.py clip.mp4 --every 2 --out clip.jpg
"""
import argparse
import math

import cv2
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("video")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, help="seconds between frames")
    p.add_argument("--count", type=int, default=24, help="frames, if --every is not set")
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--end", type=float)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--thumb", type=int, default=320, help="longest thumbnail side in px")
    p.add_argument("--max-frames", type=int, default=120)
    a = p.parse_args()

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    end = min(a.end, total) if a.end else total
    span = max(end - a.start, 0.001)
    every = a.every or span / a.count
    n = min(int(span / every) + 1, a.max_frames)
    if n == a.max_frames:
        every = span / n

    thumbs = []
    for i in range(n):
        t = a.start + i * every
        if t >= end:
            break
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        k = a.thumb / max(h, w)
        frame = cv2.resize(frame, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
        label = f"{int(t // 60):02d}:{t % 60:05.2f}"
        cv2.rectangle(frame, (0, 0), (118, 26), (0, 0, 0), -1)
        cv2.putText(frame, label, (5, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
        thumbs.append(frame)
    cap.release()
    if not thumbs:
        raise SystemExit("no frames could be read")

    th, tw = thumbs[0].shape[:2]
    rows = math.ceil(len(thumbs) / a.cols)
    sheet = np.zeros((rows * th, a.cols * tw, 3), np.uint8)
    for i, t in enumerate(thumbs):
        y, x = divmod(i, a.cols)
        sheet[y * th:y * th + t.shape[0], x * tw:x * tw + t.shape[1]] = t
    ok, buf = cv2.imencode("." + a.out.rsplit(".", 1)[-1], sheet)
    if not ok:
        raise SystemExit(f"cannot encode {a.out}")
    buf.tofile(a.out)  # handles non-ASCII paths on Windows, unlike cv2.imwrite
    print(f"{a.out}: {len(thumbs)} frames, every {every:.2f}s, duration {total:.2f}s")


if __name__ == "__main__":
    main()
