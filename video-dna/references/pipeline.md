# Render pipeline

## Why it works this way

Each segment is rendered separately: video without audio, plus a WAV with an exact sample count. Durations are whole frames. This keeps audio and video equal in length and prevents drift. All text and graphics live in one ASS file burned in at the end, so a text fix does not re-render footage. Loudness normalisation can change the sample rate, so `aresample=48000` always follows `loudnorm`.

`scripts/render.py` does all of this. Keep the timeline as JSON so corrections stay small.

## Timeline JSON

Paths are relative to the JSON file.

```json
{
  "width": 1080, "height": 1920, "fps": 30,
  "segments": [
    {"src": "clip1.mp4", "start": 12.0, "end": 15.5, "captions": true},
    {"src": "clip2.mp4", "start": 3.0, "end": 13.0, "speed": 3.0, "voice": false},
    {"image": "photo.jpg", "dur": 2.0, "vf": "zoompan=z='min(zoom+0.0015,1.2)':d=60:s=1080x1920:fps=30"}
  ],
  "music": [
    {"src": "music/1_city.mp3", "at": 0.0, "from": 42.0, "dur": 20.0, "gain_db": -12, "fade_in": 0.3, "fade_out": 1.0}
  ],
  "sfx": [{"src": "sfx/impact.wav", "at": 2.0, "gain_db": -6}],
  "duck_db": -10,
  "ass": "graphics.ass",
  "fontsdir": "fonts",
  "out": "final.mp4",
  "no_music_out": "final_no_music.mp4",
  "loudness": -14
}
```

Segment fields:

- `src` with `start` and `end`, `image` with `dur`, or `color` (such as `"#101820"`) with `dur` for a plain background under graphics. Footage is scaled and center-cropped to fill the frame. Use `"fit": "pad"` to letterbox instead.
- `speed`: speed-up factor. Speech pitch is preserved.
- `voice`: `false` drops the clip's sound.
- `gain_db`: voice gain for this segment.
- `vf`: extra ffmpeg filters, applied after scaling. The output must stay at the timeline's size and frame rate.

Run it with `python scripts/render.py timeline.json`. Options: `--jobs N`, `--only 3,7` to rebuild specific segments, `--clean` to discard the cache. Unchanged segments are reused from `_work/` next to the timeline.

## Graphics in ASS

Set `PlayResX` and `PlayResY` to the output size so ASS coordinates equal pixels. Use `\an5` for center-anchored elements, and measure positions on an extracted frame.

Useful animation recipes:

```text
Pop in with overshoot:
{\an5\pos(540,960)\fscx0\fscy0\t(0,120,\fscx115\fscy115)\t(120,200,\fscx100\fscy100)}

Slide in from the left, out to the right:
{\an5\move(-400,300,540,300,0,180)}
{\an5\move(540,300,1500,300,0,180)}   (second event, on exit)

Fade in and out:
{\fad(120,120)}

Impact flash:
{\t(0,60,\c&HFFFFFF&)\t(60,200,\c&H00D7FF&)}

Tilt:
{\frz-4}

Vector box:
{\an7\pos(80,1200)\p1\c&H201810&\1a&H20&}m 0 0 l 920 0 920 180 0 180{\p0}
```

ASS colors are `&HBBGGRR&`, and alpha `00` is opaque. Draw boxes on a lower `Layer` than their text. Size each box from the real text width: measure it with Pillow using the same font, because boxes guessed by eye are how text ends up escaping borders.

For anything ASS cannot do well (photo collages, cut-outs, 3D tilts, particles), render a transparent PNG sequence or short clip with Pillow and numpy, then overlay it through the segment's `vf` or pre-render it as its own clip. Remotion is a good option in Claude Code when a scene needs complex layout.

## Motion on footage

- **Punch zoom:** `crop` with a time-based expression, or `zoompan` on a freeze-frame.
- **Shake:** `crop=iw-40:ih-40:20+15*sin(t*50):20+15*cos(t*43),scale=1080:1920`
- **Freeze-frame:** extract one frame to PNG and use it as an `image` segment. Prefer this whenever a label must stay on a moving object, since positions no longer drift.
- **Speed ramp:** split into segments with different `speed` values.

## Captions

1. `python scripts/transcribe.py clip.mp4 --lang ro --out transcripts/clip.json`
2. Mark timeline segments with `"captions": true`.
3. `python scripts/captions.py timeline.json --transcripts transcripts --merge graphics.ass`

Options include `--censor word1,word2`, `--font`, `--size`, `--color`, `--active-color` and `--margin-v`. Re-run after timing changes. Correct mistakes in the transcript JSON, not in the ASS, so a re-run keeps them.

## Beat sync

`python scripts/beats.py track.mp3 --out beats.json` gives the estimated BPM, beat times and strongest hits. Snap cuts and impacts to these times, adding the music entry's `at` and subtracting its `from`. Beat data is an estimate, so tell the user they should judge sync by ear.

## Long renders

- Run in the background and report an honest estimate.
- Split very long renders by segment, which `render.py` does with `--jobs`.
- Do not pipe commands that write results into `head`: a closed pipe can stop them before the file is written. Send output to a log, then read the log.
