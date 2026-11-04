# Environments

The same skill runs in both places. Decide by what `scripts/doctor.py` reports rather than by assumptions.

## Claude Code

- Runs on the user's computer with direct access to their folders.
- Install missing tools when the user agrees: ffmpeg with libass, then `python scripts/setup_tools.py --profile core` and `--profile transcribe`. See `references/tools.md` for the rest.
- The first transcription downloads a Whisper model. `small` is a good default for Romanian and most other languages; use `medium` when accuracy matters and speed does not.
- Write finished videos directly into the user's folder, in `output/` unless they name another place. Keep intermediates in a clearly named `_work` folder, and say at the end what can be deleted.

## Claude app

- Runs in a cloud sandbox. Files must be uploaded or come through a connected folder.
- Deliver finished videos directly in the chat, as downloadable files. Also copy to a connected folder only when the user asks.
- Network access may be limited, and sandbox sessions can time out, so render in small resumable pieces. `render.py` caches finished segments.
- Long waits: start renders in the background and check on them. Give honest estimates when asked.
- If a file is too large to deliver or copy (a 20 MB limit was seen on connected folders), options in order:
  1. Keep the full-quality file in the chat for download.
  2. `scripts/fit_size.py in.mp4 out.mp4 --target-mb 18` for a smaller copy, saying that quality dropped.
  3. `scripts/fit_size.py in.mp4 --split-mb 18`, then reassemble the parts on the user's side and verify the hash it prints.
- If you cannot delete files on the user's computer, tell them which working folder they can remove.
- A folder may be connected from a different device. If paths disappear, say what you see and ask the user to reconnect it.

## If transcription is not available

Do not fetch model weights from unverified mirrors or unofficial packages, and do not work around the sandbox's network rules. Instead:

1. Try the normal install and model download: `setup_tools.py --profile transcribe`, then `transcribe.py`.
2. If the download fails, ask the user to save an official model on their computer with `setup_tools.py --download-model small --model-dir models/small`, upload that folder if the app allows its size, and pass it with `--model`.
3. Otherwise, ask them to run `transcribe.py` on their computer, for instance through Claude Code, and upload the resulting JSON files.
4. As a last resort, work from what they give you, and mark every caption as unverified.

## If images or sites cannot be reached

Some sites block automated access. Do not pretend you saw the content. Say so, then cut elements from the user's own material or draw them in code, or ask the user to add files to the folder.

## Fonts

Check that the chosen font has every character needed, such as `ă â î ș ț` for Romanian. Use `fontsdir` in the timeline for bundled fonts, and prefer open licenses such as the SIL Open Font License. If a font lacks glyphs or is unavailable, tell the user which substitute you used.
