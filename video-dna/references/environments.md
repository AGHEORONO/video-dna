# Environments

The same skill runs in both places. Decide by what `scripts/doctor.py` reports rather than by assumptions.

## Claude Code

- Runs on the user's computer with direct access to their folders.
- Install missing tools when the user agrees: ffmpeg with libass, and `pip install faster-whisper numpy opencv-python pillow`.
- The first transcription downloads a Whisper model. `small` is a good default for Romanian and most other languages; use `medium` when accuracy matters and speed does not.
- Write outputs into the user's project folder, and keep intermediates in a clearly named `_work` folder. Say at the end what can be deleted.

## Claude app

- Runs in a cloud sandbox. Files must be uploaded or come through a connected folder.
- Network access may be limited, and sandbox sessions can time out, so render in small resumable pieces. `render.py` caches finished segments.
- Long waits: start renders in the background and check on them. Give honest estimates when asked.
- Copying back to a connected folder can have a file-size limit (20 MB was seen). Options, in order:
  1. Let the user download the file from the conversation.
  2. `scripts/fit_size.py in.mp4 out.mp4 --target-mb 18` for a smaller copy, saying that quality dropped.
  3. `scripts/fit_size.py in.mp4 --split-mb 18`, then reassemble the parts on the user's side and verify the hash it prints.
- If you cannot delete files on the user's computer, tell them which working folder they can remove.
- A folder may be connected from a different device. If paths disappear, say what you see and ask the user to reconnect it.

## If transcription is not available

Do not fetch model weights from unverified mirrors or unofficial packages, and do not work around the sandbox's network rules. Instead:

1. Try the normal model download.
2. If it fails, ask the user to run `transcribe.py` on their computer, for instance through Claude Code, and to upload the resulting JSON files.
3. Otherwise, work from what they give you, and mark every caption as unverified.

## If images or sites cannot be reached

Some sites block automated access. Do not pretend you saw the content. Say so, then cut elements from the user's own material or draw them in code, or ask the user to add files to the folder.

## Fonts

Check that the chosen font has every character needed, such as `ă â î ș ț` for Romanian. Use `fontsdir` in the timeline for bundled fonts, and prefer open licenses such as the SIL Open Font License. If a font lacks glyphs or is unavailable, tell the user which substitute you used.
