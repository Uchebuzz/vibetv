# Prompt library

Copy-paste prompts for your AI coding agent. Run them inside a project created with
`vibetv new`. The project's `AGENTS.md` already teaches the agent how to see and drive your TV.

Tip: keep `vibetv serve --open` running in another terminal so every change shows up live.

---

### 🏠 Custom home screen

> Turn this app into my TV home screen. Show my installed apps as large 16:9 cards using their
> banners, in a single horizontal row I can scroll with the D-pad. Above it, a big clock and
> date. Dark theme, subtle gradient background, focused card scales up with a soft glow.
> Remember the last focused app between launches (localStorage). Screenshot the TV when done.

Then, to make it the real Home screen: uncomment the HOME intent-filter in
`AndroidManifest.xml`, run `vibetv deploy`, then `vibetv launcher set <your.app.id>`.

### 🌙 Ambient screensaver

> Redesign the screensaver mode (`?screensaver=1`): slowly drifting large clock (to avoid
> burn-in, move it every minute), today's date, and a gentle animated aurora gradient. It must
> be very light on CPU, using CSS transforms only, no canvas. Then activate it with
> `vibetv screensaver set <app-id>/.WebDreamService --preview` and screenshot it.

### 🌦️ Family dashboard

> Make a family dashboard for the living room TV: weather for my city from the free
> Open-Meteo API (no key needed), a clock, and a "today" list I can edit in `data/today.json`.
> Big readable type from 3 metres away. Refresh weather every 15 minutes. Handle offline
> gracefully.

### 🖼️ Photo frame

> Turn this into a photo frame: read image URLs from `photos.json`, crossfade every 20
> seconds with a slow Ken Burns zoom, and show the time in a small corner. Left/right on the
> remote skip photos, OK pauses.

### 🎮 Couch game

> Build a simple multiplayer-free couch game that's fun with just a TV remote, e.g. a
> reaction-time game or trivia with 4 answers mapped to up/down/left/right. Keep score in
> localStorage. Test it by pressing keys with `vibetv key` and checking screenshots.

### 📺 Kid-safe launcher

> Make a kid-safe launcher: only show the apps listed in `allowed.json` as huge colourful
> tiles. Hide everything else. Holding Back for 5 seconds asks for a 4-digit PIN (entered
> with the D-pad) before exiting.

### 🧹 Speed up my TV

> Using vibetv, check what tweak presets are available and which are applied. Explain what
> each does in plain English, then apply the safe ones that would make my TV feel faster.
> Don't apply anything moderate or advanced without asking me.

### 🔍 Debug it

> Something's broken on the TV. Read `vibetv logs`, take a screenshot, reproduce by pressing
> keys with `vibetv key`, find the bug, fix it, and verify on the TV.

---

Got a prompt that worked great? Add it here in a PR. Include a screenshot if you can!
