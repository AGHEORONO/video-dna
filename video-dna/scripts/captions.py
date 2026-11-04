#!/usr/bin/env python3
"""Build word-by-word ASS captions, mapping source transcripts onto the timeline.

Each segment with "captions": true uses <transcripts>/<source stem>.json.

Example: captions.py timeline.json --transcripts transcripts --merge graphics.ass
"""
import argparse
import json
import os
import re


def ts(t):
    t = max(t, 0)
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_color(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def censor(word, banned):
    core = re.sub(r"\W", "", word).lower()
    if core in banned:
        return re.sub(r"(?<=\w)\w(?=\w)", "*", word)
    return word


def seg_duration(s):
    if "src" in s:
        return (s["end"] - s["start"]) / s.get("speed", 1.0)
    return s["dur"]


def timeline_words(tl, base, transcripts, banned):
    """Return caption words in output time, split at timeline cuts."""
    fps = tl.get("fps", 30)
    words, cursor = [], 0.0
    for s in tl["segments"]:
        n_frames = round(seg_duration(s) * fps)
        dur = n_frames / fps
        if s.get("captions") and "src" in s:
            stem = os.path.splitext(os.path.basename(s["src"]))[0]
            path = os.path.join(transcripts, stem + ".json")
            if not os.path.exists(path):
                raise SystemExit(f"missing transcript: {path}")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            speed = s.get("speed", 1.0)
            for seg in data["segments"]:
                for w in seg["words"]:
                    mid = (w["start"] + w["end"]) / 2
                    if s["start"] <= mid < s["end"]:
                        a = cursor + (max(w["start"], s["start"]) - s["start"]) / speed
                        b = cursor + (min(w["end"], s["end"]) - s["start"]) / speed
                        words.append({"text": censor(w["word"], banned),
                                      "start": a, "end": max(b, a + 0.08)})
            if words:
                words[-1]["cut"] = True
        cursor += dur
    return words


def group_lines(words, max_words, max_chars, gap):
    lines, cur = [], []
    for w in words:
        too_long = len(" ".join(x["text"] for x in cur + [w])) > max_chars
        paused = cur and w["start"] - cur[-1]["end"] > gap
        if cur and (len(cur) >= max_words or too_long or paused):
            lines.append(cur)
            cur = []
        cur.append(w)
        ends_sentence = w["text"][-1:] in ".?!"
        if ends_sentence or w.get("cut"):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def events(lines, active, hold):
    out = []
    for i, line in enumerate(lines):
        next_start = lines[i + 1][0]["start"] if i + 1 < len(lines) else float("inf")
        for j, w in enumerate(line):
            start = w["start"]
            if j + 1 < len(line):
                end = line[j + 1]["start"]
            else:
                end = min(w["end"] + hold, next_start)
            parts = []
            for k, x in enumerate(line):
                t = x["text"].replace("{", "(").replace("}", ")")
                parts.append(f"{{\\c{active}&}}{t}{{\\r}}" if k == j else t)
            pop = "{\\fscx108\\fscy108\\t(0,80,\\fscx100\\fscy100)}" if j == 0 else ""
            out.append(f"Dialogue: 50,{ts(start)},{ts(end)},Caption,,0,0,0,,{pop}{' '.join(parts)}")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("timeline")
    p.add_argument("--transcripts", required=True)
    p.add_argument("--merge", help="insert captions into this existing ASS file")
    p.add_argument("--out", help="write a standalone ASS file")
    p.add_argument("--font", default="Arial")
    p.add_argument("--size", type=int, default=64)
    p.add_argument("--color", default="#FFFFFF")
    p.add_argument("--active-color", default="#FFD400")
    p.add_argument("--outline", type=int, default=5)
    p.add_argument("--margin-v", type=int, default=480)
    p.add_argument("--max-words", type=int, default=4)
    p.add_argument("--max-chars", type=int, default=26)
    p.add_argument("--gap", type=float, default=0.5)
    p.add_argument("--hold", type=float, default=0.25)
    p.add_argument("--censor", default="", help="comma-separated words to star out on screen")
    a = p.parse_args()
    if bool(a.merge) == bool(a.out):
        raise SystemExit("use exactly one of --merge or --out")

    with open(a.timeline, encoding="utf-8") as f:
        tl = json.load(f)
    banned = {w.strip().lower() for w in a.censor.split(",") if w.strip()}
    words = timeline_words(tl, os.path.dirname(a.timeline), a.transcripts, banned)
    lines = group_lines(words, a.max_words, a.max_chars, a.gap)
    active = ass_color(a.active_color)[:2] + ass_color(a.active_color)[4:]
    evts = events(lines, active, a.hold)
    style = (f"Style: Caption,{a.font},{a.size},{ass_color(a.color)},{ass_color(a.color)},"
             f"&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{a.outline},2,2,90,90,{a.margin_v},1")

    if a.out:
        w, h = tl.get("width", 1080), tl.get("height", 1920)
        text = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\n"
                "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
                "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"{style}\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
                "MarginV, Effect, Text\n" + "\n".join(evts) + "\n")
        target = a.out
    else:
        with open(a.merge, encoding="utf-8") as f:
            src = f.read().splitlines()
        # Re-runs replace earlier captions rather than stacking them.
        kept = [l for l in src if not l.startswith("Style: Caption,")
                and not re.match(r"Dialogue: [^,]*,[^,]*,[^,]*,Caption,", l)]
        idx = next((i for i, l in enumerate(kept) if l.startswith("Format:")
                    and "Fontname" in l), None)
        if idx is None:
            raise SystemExit(f"no [V4+ Styles] format line in {a.merge}")
        kept.insert(idx + 1, style)
        while kept and not kept[-1].strip():
            kept.pop()
        text = "\n".join(kept + evts) + "\n"
        target = a.merge

    with open(target, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{target}: {len(lines)} caption lines, {len(words)} words")


if __name__ == "__main__":
    main()
