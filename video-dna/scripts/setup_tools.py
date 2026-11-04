#!/usr/bin/env python3
"""Check and install the skill's optional tools, by profile.

Examples:
  setup_tools.py --list
  setup_tools.py --profile transcribe
  setup_tools.py --profile all
  setup_tools.py --download-model small --model-dir models/small
"""
import argparse
import importlib.util
import shutil
import subprocess
import sys

# profile: [(module to look for, pip package, what it is for)]
PROFILES = {
    "core": [("numpy", "numpy", "audio mixing, beats, sound effects"),
             ("cv2", "opencv-python", "contact sheets, QR checks, face detection"),
             ("PIL", "pillow", "measuring text, drawing graphics")],
    "transcribe": [("faster_whisper", "faster-whisper", "Whisper transcription, recommended")],
    "whisper-alt": [("whisper", "openai-whisper", "original Whisper; large PyTorch download")],
    "vision": [("scenedetect", "scenedetect", "finding cuts in long footage"),
               ("rembg", "rembg[cpu]", "cutting people and objects out of photos")],
    "graphics": [("qrcode", "qrcode[pil]", "making QR codes"),
                 ("fontTools", "fonttools", "checking fonts for diacritics"),
                 ("playwright", "playwright", "rendering HTML, CSS and SVG scenes"),
                 ("opentimelineio", "opentimelineio", "timelines for other editors")],
    "audio": [("librosa", "librosa", "more accurate beat analysis"),
              ("pyloudnorm", "pyloudnorm", "measuring loudness"),
              ("soundfile", "soundfile", "reading audio files"),
              ("demucs", "demucs", "separating voice from music; large PyTorch download"),
              ("piper", "piper-tts", "offline voiceover; voice models are separate")],
}
SYSTEM = [("ffmpeg", "required for everything", "https://ffmpeg.org"),
          ("ffprobe", "required for everything", "comes with ffmpeg"),
          ("node", "Remotion scenes", "https://nodejs.org"),
          ("whisper-cli", "whisper.cpp transcription", "https://github.com/ggml-org/whisper.cpp")]


def present(module):
    return importlib.util.find_spec(module) is not None


def show():
    print("System programs:")
    for name, use, source in SYSTEM:
        print(f"  {'ok' if shutil.which(name) else 'MISSING':8}{name}: {use} ({source})")
    for profile, items in PROFILES.items():
        print(f"Profile {profile}:")
        for module, package, use in items:
            print(f"  {'ok' if present(module) else 'MISSING':8}{package}: {use}")


def install(profile):
    names = list(PROFILES) if profile == "all" else [profile]
    packages = [pkg for n in names for mod, pkg, _ in PROFILES[n] if not present(mod)]
    if not packages:
        print("Everything in this profile is already installed.")
    else:
        print("Installing:", ", ".join(packages))
        code = subprocess.run([sys.executable, "-m", "pip", "install", *packages]).returncode
        if code:
            sys.exit("pip failed. If network access is restricted, see references/environments.md")
    if "graphics" in names:
        code = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"]).returncode
        if code:
            print("The Playwright browser could not be installed, so HTML scenes will not work.")


def download_model(name, target):
    """Save an official faster-whisper model to a folder, for offline use or upload."""
    try:
        from faster_whisper import download_model as fetch
    except ImportError:
        sys.exit("Install the transcribe profile first.")
    print(f"Model {name} saved in {fetch(name, output_dir=target)}")
    print("Use it with: transcribe.py clip.mp4 --model", target, "--out clip.json")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true", help="show what is installed")
    p.add_argument("--profile", choices=[*PROFILES, "all"])
    p.add_argument("--download-model", help="official faster-whisper model: tiny, base, small, medium...")
    p.add_argument("--model-dir", default="models/whisper")
    a = p.parse_args()
    if a.profile:
        install(a.profile)
    if a.download_model:
        download_model(a.download_model, a.model_dir)
    if a.list or not (a.profile or a.download_model):
        show()


if __name__ == "__main__":
    main()
