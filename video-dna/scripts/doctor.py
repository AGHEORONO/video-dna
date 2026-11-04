#!/usr/bin/env python3
"""Report what this environment can do. Exits 1 if rendering is impossible."""
import importlib.util
import os
import shutil
import subprocess
import sys


def main():
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    filters = ""
    if ffmpeg:
        filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"],
                                 capture_output=True, text=True).stdout
    needed_filters = ["ass", "loudnorm", "aresample", "atempo"]
    missing_filters = [f for f in needed_filters if f" {f} " not in filters]
    mods = {m: importlib.util.find_spec(m) is not None
            for m in ["numpy", "cv2", "PIL", "faster_whisper"]}

    app = os.path.isdir("/mnt/user-data/outputs")
    print(f"environment: {'Claude app sandbox' if app else 'local computer, such as Claude Code'}")
    print(f"deliver finished videos: {'in the chat, from /mnt/user-data/outputs' if app else 'directly in the output folder'}")
    print(f"python: {sys.version.split()[0]}")
    print(f"ffmpeg: {ffmpeg or 'MISSING'}")
    print(f"ffprobe: {ffprobe or 'MISSING'}")
    print(f"ffmpeg filters missing: {', '.join(missing_filters) or 'none'}")
    for m, ok in mods.items():
        print(f"{m}: {'ok' if ok else 'MISSING'}")

    can_render = bool(ffmpeg and ffprobe and not missing_filters and mods["numpy"])
    print(f"render: {'yes' if can_render else 'NO'}")
    print(f"contact sheets and QR checks: {'yes' if mods['cv2'] else 'NO (needs opencv-python)'}")
    whisper = mods["faster_whisper"] or importlib.util.find_spec("whisper") or shutil.which("whisper-cli")
    print(f"transcription: {'yes' if whisper else 'NO (run setup_tools.py --profile transcribe)'}")
    print("optional tools: run setup_tools.py --list")
    return 0 if can_render else 1


if __name__ == "__main__":
    sys.exit(main())
