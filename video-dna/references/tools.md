# Tools

`python scripts/setup_tools.py --list` shows what is installed. Install a group with `--profile <name>`, after telling the user what it will download. The core pipeline never needs more than ffmpeg and numpy.

## Use the right tool

| Need | Tool | How | Profile |
|---|---|---|---|
| Cut, mix, render | ffmpeg with libass | `render.py` | core |
| Transcribe | Whisper | `transcribe.py` | transcribe |
| Find cuts in long footage | PySceneDetect | `toolbox.py scenes` | vision |
| Cut out people or objects | rembg | `toolbox.py cutout` | vision |
| Keep graphics off faces | OpenCV with YuNet, bundled | `toolbox.py faces` | core |
| Blur strangers' faces | YuNet + ffmpeg | `toolbox.py blur-faces` | core |
| Improve low-resolution clips | ffmpeg | `toolbox.py upscale` | core |
| Text and shapes on video | ASS | `references/pipeline.md` | core |
| Complex layouts, SVG, CSS animation | HTML in Chromium | `toolbox.py html`, `html-seq` | graphics |
| Scenes written in React | Remotion | Needs Node. Check the Remotion license for company use | none |
| QR codes | qrcode | `toolbox.py qr` | graphics |
| Check a font's diacritics | fontTools | `toolbox.py check-font` | graphics |
| Beats | numpy, or librosa | `beats.py`; use librosa if results look wrong | audio |
| Separate voice from music | Demucs | `toolbox.py stems` | audio |
| Loudness | ffmpeg, pyloudnorm | `qa.py`, `toolbox.py loudness` | audio |
| Voiceover | Piper | `toolbox.py tts`, with consent and a voice model | audio |
| Hand off to another editor | OpenTimelineIO | `toolbox.py otio` | graphics |
| Sound effects and simple music | numpy | `sfx.py`, `music.py` | core |
| Generated images or video | Connected tools, if any | Ask first, and label them as generated | none |
| Designs from Canva or similar | Connected tools, if any | Ask first | none |

Prefer the smallest tool that does the job. ASS handles most text graphics and re-renders fastest.

## Whisper

Choose a backend with `--backend`. The default, `auto`, uses the first local one available.

| Backend | Best for | Notes |
|---|---|---|
| `faster-whisper` | Most cases | Fast on CPU, with confidence per word and voice detection |
| `openai-whisper` | When PyTorch is already installed | Large download |
| `whisper-cpp` | Machines where Python packages are a problem | Needs its program and a ggml model file |
| `openai-api` | Only when the user asks | Uploads the audio to OpenAI and needs their API key |

- **Model size:** `small` is the default. Use `medium` or `large-v3` when accuracy matters more than time, and `tiny` only for quick tests.
- **Names:** pass them with `--initial-prompt "Name One, Place Two"`.
- **Language:** always pass `--lang` when known. Detection on short clips can be wrong.
- **Noisy clips:** if speech goes missing, try `--no-vad`, or separate the voice first with `toolbox.py stems`.
- **Offline or restricted network:** save an official model with `setup_tools.py --download-model small --model-dir models/small`, then use `--model models/small`.

## Left out on purpose

- **Downloaders for commercial music or videos.** The user supplies the files.
- **Unofficial mirrors of model weights.** See `references/environments.md`.
- **AI upscalers and frame interpolation.** They can invent detail on real people and text. If a user wants one, name the option and let them run it.
