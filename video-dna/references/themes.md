# Choosing a theme

These are examples, not templates. Never reuse one unchanged for a new video. Look for a theme the footage already suggests: a person narrating like a reporter suggests news; a folder named after a game suggests a game.

## How to find it

1. List what people do repeatedly in the footage, and how they talk about it.
2. Ask which world would make those real moments funnier or bigger.
3. Test it: write two gags using real moments. If they could fit any video, the theme is too generic. Discard it.
4. Mixing is fine when it comes from the user or the story, for example news delivered by a herald inside a game.

Directions to start from: video game, wildlife documentary, breaking news, heist film, phone or chat interface, scientific report, mission control, reality show, expedition map, ironic horror, sports broadcast, retro radio, vintage paper collage, museum exhibit, instruction manual.

## Defining the theme

Before building, fix these and keep them for the whole video:

- 1-2 fonts, tested for every diacritic the language needs;
- 3-5 colors, with contrast over bright footage;
- 3-4 animation behaviours for entrances, exits and impacts;
- a sound palette, where each graphic type has its own sound;
- the theme's device for going back in time, chapter changes and the ending.

## Worked examples (fictional)

**Role-playing game, for a mountain trip**
- Cast select screen with true stats. Inventory items that return later. Quest cards that really fail: `× Summit: postponed`, `+ Plan B: soup`.
- Gag: a wrong turn triggers `DEBUFF: wet socks, HP −50` on a freeze-frame.
- Gag: an item bought on day one returns on day two with `Source: that shop`.

**Mission control, for a robotics build**
- Thin HUD, monospace type, timecode, LIVE tag, progress bar with phases.
- Gag: a multimeter in frame becomes `VOLTAGE: 4.99 V · NOMINAL`, using the value on its display.
- Ending: status readout rather than a victory screen, because the work is ongoing.

**Vintage paper collage, for an update post**
- Cut-out people with sticker outlines, stamps, tape, torn paper, sepia, to match the team's existing posts.
- Gag: the track's line about stopping cuts to a stamp reading `STOP? NO.`
- Draw props in code when images cannot be downloaded, and say so.

**Sports broadcast, for an amateur fun run**
- Live graphics with a real speed multiplier and a `TEAM BATTERY` bar that drains.
- Gag: an epic slow-motion intro breaks with a record scratch on a freeze-frame selfie.
- Ending: a teammate flat on the ground at `BATTERY 1%`.

**Music player, for a party's playlist**
- A station-style player with track number, equaliser and a next button pressed exactly on the transition.
- Each genre gets its own color world. Stickers joke about the venue instead of quoting lyrics.

## Sound without files

`scripts/sfx.py` generates a palette: text blips, coin, level-up, damage, quest, whoosh, impact, stinger, tick, ding, scratch, glitch, sad brass. Pitch or layer them to fit the theme. Say when you substitute generated sound for a track that was missing.
