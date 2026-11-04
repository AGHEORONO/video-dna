# Format recipes

Default delivery: 1080x1920, 30 fps, MP4 under about 60 MB, under 3 minutes per part so it fits Reels, TikTok and Shorts. Confirm the platform, because it decides the safe zones.

## Vlog series (hours of footage, 2+ parts)

- Split where the story naturally splits, around 2:30-3:00 per part.
- Open with the wildest moment, then jump back with a theme-native device such as a loading screen or "7 hours earlier", using the real time from file metadata.
- Introduce the cast using true traits. Ask the user for the traits they want; they know the jokes.
- End part 1 with stats for the day and a teaser for part 2. Plant items in part 1 that pay off in part 2.
- Speed up long stretches and keep the lines whole. Use freeze-frames for strong photos, with graphics anchored to the frozen object.
- Finish on an emotional beat: original audio first, then the track, then a fast photo collage on the beat where images fly in from all sides and overlap.
- Offer alternate versions when the user is unsure about a moment. A post-credits gag works well for leftovers.

## Progress update reel (35-50 s)

- For silent, short or low-resolution clips, keep it short. Past about 45 s the quality starts to show.
- Structure as phases with a persistent progress element. Each phase is labeled from what is visible in frame.
- Read real values off the footage: machine names, display readings, dates on screenshots, file timestamps.
- Exclude other projects. Ask before labeling any object you are unsure about.
- Credit the crew with confirmed roles only.
- Compute countdown numbers from the posting date, and say which date you used.
- End on status, not victory, unless the footage proves victory.

## Sponsor or funder thank-you card (about 6 s, end of video)

- Use the official text verbatim, revealed line by line.
- Put logos on a clean strip with enough contrast. A white strip works over dark themes.
- Ask about any logo not named in the text.
- Add the same thank-you line to the post caption.
- Do not skip this once the user asks for it. Carry it over to later videos for the same organisation.

## Animated poster or story (10-35 s, no footage)

- Rebuild the poster in layers rather than animating a flat image. Cut out elements and re-set the text so it stays sharp.
- Give viewers time to read: hold the final layout for several seconds with only small looping motion.
- If people need the rules explained, give each rule its own scene: what can enter, how voting works, dress code, entry price, prizes.
- Ask for the original font. If you lack it, say so and name the substitute.
- Say when supplied logos are small and may look soft.

## Reminder series (countdown to an event)

Change the angle each time so it never feels repeated:

| Moment | Angle |
|---|---|
| Several days out | Explain everything for someone seeing it for the first time |
| 2 days out | Call to action: countdown clock, ideas, checklist |
| Day before | Participation: ask for comments or requests, leave an empty slot on screen |
| Same day | Energy: new background, huge "today", where, when, how much |

Every reminder must answer what, where, when and how much on its own. Suggest cheap extras when useful: a countdown sticker, a collab post with partners, a poll, a pinned first comment.

## Music-driven reel (music videos or tracks, no speech)

- Use a player interface or another music-native theme. Give each genre its own color world.
- Use about 3 seconds per track, from a recognisable chorus, cut on the beat, with a different transition each time.
- Add a short non-lyric sticker joke per track. Do not reproduce lyrics on screen.
- Warn about muting risks. Offer a silent version for the platform's licensed music sticker.

## Screen loop: QR or projector (landscape, 1920x1080)

- Make the loop seamless: last frame flows into first, and all motion is periodic.
- Projector backgrounds go silent so they do not fight the room. QR screens may have a gentle loop.
- Nothing animated may cross the QR code. Keep a quiet zone around it and keep any frame around it centered.
- Decode the QR from rendered frames with `qa.py --qr-at`.
- Show the QR for at least 15 s in every minute of a longer cycle. Also provide a long version for players without repeat.

## Event aftermovie (60-120 s)

- Order: arrival, main showcase, atmosphere, the result, thank-you, exit.
- Photos enter dynamically, with character cards for people in costume or in a showcase.
- Let original music in the room come through when it adds to the moment.
- Take results from real vote data, and show only names the user approved.
- Ask for the lengths they want, and make a long and a short cut if asked.

## Pure motion graphics (no material)

- Build everything from code: text, shapes, charts, icons, particles, generated sound and music. See "No material" in `references/brief.md`.
- Base the pacing on the music's beats, generating the music first.
- Use one idea per scene, and animate every element in and out.
- Say that it was fully generated, and what real material would improve.

## Comedy reel

- Contrast is the engine: an epic setup against an unglamorous reality, with a hard cut between them.
- Use a persistent gag element that degrades over time, such as a draining meter, and end on its punchline.
- Written jokes are fine. Tell the user you did not use real spoken lines, if so, and ask whether there are any worth adding.
