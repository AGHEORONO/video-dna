# Pre-delivery checklist

Run automatic checks first:

```bash
python scripts/qa.py final.mp4 --width 1080 --height 1920 --fps 30 --max-mb 60 --ass graphics.ass
python scripts/contact_sheet.py final.mp4 --every 1 --out review.jpg
```

Then look at the frames. Use a dense sheet, or extract single frames around each graphic's entrance and exit.

## Graphics

- [ ] Arrows, circles and labels stay on their object for their whole duration. If the camera moves, use a freeze-frame or move the graphic with it. Positions are measured on the frame.
- [ ] No graphic overlaps another graphic, the captions or a face.
- [ ] Nothing is clipped at the edge, and no text escapes its box.
- [ ] Centered things are truly centered. Check big titles and frames around centered objects against the frame's midline.
- [ ] All text is readable on a phone: at least about 40 px at 1080 width.
- [ ] Graphics animate in and out, aligned to a beat or a line. Nothing simply appears.
- [ ] Colors and sizes are consistent, with good contrast over bright backgrounds.
- [ ] Vertical formats keep text clear of the platform interface: roughly the top 250 px, the bottom 400 px, and the right 140 px.

## Content

- [ ] Every joke is clear without context. If not, it is cut.
- [ ] Every fact is true, or is listed for confirmation.
- [ ] Spoken lines are left whole, with no word chopped at a cut.
- [ ] Uncertain transcript lines are listed.
- [ ] Hook in the first 2-3 seconds. Callbacks pay off.
- [ ] For promos: what, where, when and how much can be understood by a first-time viewer.
- [ ] Required sponsor text and logos are present, word for word.

## Audio and technical

- [ ] Video duration equals audio duration, within one frame.
- [ ] No clicks at cuts. `render.py` adds short fades; check levels around sharp transitions.
- [ ] Peaks stay under about -1 dBTP, and music sits below speech.
- [ ] 1080x1920, 30 fps, within the size limit, H.264 and AAC, unless the format differs by design.
- [ ] QR codes decode from rendered frames: `qa.py --qr-at 3,9 --qr-expect <url>`.
- [ ] Loops: compare the first and last frames.

## Report

Say plainly what you checked and what you could not. You did not hear the video.
