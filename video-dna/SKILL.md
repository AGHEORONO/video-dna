---
name: video-dna
description: Make story-driven videos with heavy motion graphics from real footage, photos and music, or from nothing but a brief, with a new theme chosen for each one. Asks for what it needs first: format, orientation, rhythm, motion intensity, visual identity. Use when the user wants to edit or make a reel, TikTok, Short, vlog series, aftermovie, event promo or reminder, progress update, animated poster or story, QR or projector loop, or says "make a video", "editează", "montează", "fă un reel", "fă un video", "motion graphics", "aftermovie". Works in Claude Code and the Claude app. Handles transcription, word-by-word captions, cutting on the beat, generated sound effects, rendering with ffmpeg, frame-level checks and post captions.
---

# Video DNA

Turn a folder of footage into a video that feels edited by someone who was there. Keep the DNA, never reuse a template: every video gets its own theme, drawn from what really happened in the footage.

Reply in the user's language. Captions and on-screen text use the language of the footage unless told otherwise.

## Start here

1. Run `python scripts/doctor.py` to see what this environment can do. Read `references/environments.md` if anything is missing, or if you are in a cloud sandbox.
2. Look at the working folder, then read `references/brief.md` and collect the brief. Ask only what the request and the material do not already answer.
3. Read `references/formats.md` and use the recipe closest to the request. If there is no material, follow "No material" in `references/brief.md`.
4. Read `references/pipeline.md` before building the timeline.

## Workflow

Do these in order. Do not render anything before step 5.

0. **Brief.** Settle format, orientation, length, rhythm, motion intensity, visual identity and audio. See `references/brief.md`. Use its choices for the whole video.
1. **Inventory.** List clips, photos, music and logos, if there are any. Make contact sheets with `scripts/contact_sheet.py` and look at them. Transcribe speech with `scripts/transcribe.py`, shortest and densest clips first. Real lines are usually the funniest material.
2. **Story.** Write down what actually happened, in order, with the best real lines and who said them. Ask who the people are if you were not told.
3. **Theme.** Propose 2-3 new themes, each with 2 concrete gags built from real moments. Recommend one, preferring a theme the footage already suggests. Then stop and let the user choose. See `references/themes.md`.
4. **Music.** Propose one track per section with a target filename, and ask the user to put the files in the folder. A name such as `2_chorus_0m45s.mp3` means "start at 0:45". Never download commercial music, even if asked. Offer generated sound and a no-music version instead.
5. **Sample first.** For anything over about 45 seconds, render one short chapter so the user can judge direction. Then build the rest.
6. **Check.** Run `scripts/qa.py`, look at extracted frames and go through `references/qa-checklist.md`. Fix what you find before delivering.
7. **Deliver.** Hand over the files, a no-music version when useful, and ready-to-paste text from `references/copy.md`. Include the honest report below.

## The DNA

- **One theme, fully committed.** Same fonts, colors, animation and sound from first frame to last. Every graphic belongs to the theme's world.
- **Every graphic carries a true joke or a true fact from this footage.** Nothing decorative, nothing generic. A label reading a real value on a real display beats any stock caption.
- **Callbacks.** Plant something early and pay it off late. A line from the start returns at the end.
- **Hook in the first 2-3 seconds** with the strongest moment, then return to the beginning in a way that belongs to the theme.
- **Rhythm.** Cut on the beat, punch-zoom on punchlines, use moving transitions, shake on impacts, speed up the dull stretches. Leave spoken lines whole.
- **Captions** on all speech, word by word, styled for the theme. Censor swearing on screen only.
- **Sound design.** Each graphic has its own sound. Music changes by section, the track's big hit lands on the key moment, and music ducks under speech.
- **Clarity beats density.** If a joke needs context the viewer lacks, cut it. For a first-time viewer, what, where, when and how much must be clear.

## Truth rules

- Never invent a fact. Anything deduced, approximate or illustrative must be listed for confirmation: dates, roles, numbers, prizes, heights, who said what.
- List uncertain transcript lines for the user to confirm. `transcribe.py` flags low-confidence words.
- Illustrative numbers that could be read as real results must be flagged, or removed.
- Do not put words in real people's mouths as quotes. Written jokes are fine when they read as captions.
- Ask before including embarrassing moments of people, and before showing strangers' faces unblurred.
- Keep official text from sponsors and funders word for word. If it does not match their logos, ask instead of editing it.
- Check a QR code's destination and warn the user if it is an openly editable document.

## Handling corrections

Apply feedback exactly and leave everything else untouched. Keep the timeline as data, so one change re-renders only the affected segments. When something must be removed to stay under a length limit, say what you removed.

## Honest report

You cannot hear audio or watch in real time. State this every time, in plain words:

- what you verified (extracted frames, durations, levels, QR decoding);
- what the user must judge by ear and eye (beat sync, caption timing, mix balance);
- what you removed, and what you could not do as asked;
- whether platforms may mute the video because of commercial music.

## Bundled files

| File | Use |
|---|---|
| `scripts/doctor.py` | Check tools and dependencies |
| `scripts/contact_sheet.py` | Timestamped frame grids for reviewing footage and renders |
| `scripts/transcribe.py` | Word-level transcript with low-confidence flags |
| `scripts/captions.py` | Word-by-word ASS captions, mapped onto the timeline |
| `scripts/beats.py` | Tempo, beat times and strongest hits of a track |
| `scripts/sfx.py` | Generate copyright-free sound effects |
| `scripts/music.py` | Generate a simple original chiptune or pulse music bed that loops |
| `scripts/render.py` | Timeline JSON to final MP4, with an optional no-music version |
| `scripts/qa.py` | Duration, format, size, loudness, ASS and QR checks |
| `scripts/fit_size.py` | Compress to a target size, or split for transfer |
| `references/brief.md` | Questions to ask at the start, and what to do with an empty folder |
| `references/formats.md` | Recipes per type of video |
| `references/themes.md` | How to find a theme, with worked examples |
| `references/pipeline.md` | Timeline format, render rules, ASS animation recipes |
| `references/environments.md` | Claude Code and Claude app differences |
| `references/qa-checklist.md` | Pre-delivery checks |
| `references/copy.md` | Post captions and shareable messages |
