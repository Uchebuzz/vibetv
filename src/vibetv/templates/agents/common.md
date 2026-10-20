# AGENTS.md: {{APP_NAME}}

This is a TV app scaffolded by [vibetv](https://github.com/Uchebuzz/vibetv). These notes are
for AI coding agents (Claude Code, Codex, Cursor, Copilot, Gemini CLI, ...) and humans alike.

## The loop: edit, see it on the TV, check

You can **see and drive the real TV** from the terminal. Use these after every change:

| Goal | Command |
| --- | --- |
| Look at the TV screen | `vibetv screenshot shot.png`, then open/read `shot.png` |
| Press remote buttons | `vibetv key down down ok` (keys: up down left right ok back home play menu volup voldown) |
| Type text | `vibetv type "hello"` |
| See console.log / JS errors from the TV | `vibetv logs` (while `vibetv serve` is running) |
| Deploy a real build | `vibetv deploy` |

If the vibetv MCP server is configured (`vibetv mcp`), prefer its `tv_screenshot`, `tv_key`,
`tv_logs` and `tv_deploy` tools: they do the same thing without a shell.

**Always verify visually.** After a UI change, take a screenshot and check it before saying
you're done. Navigate with `vibetv key` to check that focus moves the way the user expects.

## 10-foot UI rules (do not break these)

1. **Everything works with a D-pad.** No hover-only UI, no mouse, no touch gestures. Every
   interactive element must be reachable with up/down/left/right and activated with OK.
2. **Focus is always visible and obvious** from across a room: scale, glow or outline. Never
   remove the focus style. Exactly one element is focused at any time.
3. **Back always does something sensible:** close the overlay, go up a level, or exit the app at
   the root. Never trap the user.
4. **Overscan-safe area:** keep text and controls 5% inside each edge (96px left/right, 54px
   top/bottom on a 1920x1080 canvas).
5. **Big and high-contrast:** body text ≥ 24px at 1080p, headings ≥ 40px. No thin grey-on-grey.
6. **Design for 1920x1080** and let it scale. Many TVs render web content at 1280x720 or
   960x540 CSS pixels.
7. **TV hardware is slow.** Avoid heavy blur/backdrop-filter, giant images and layout thrash.
   Animate `transform`/`opacity` only. Keep animations short (≤ 200ms).
8. **No text entry if you can avoid it.** Typing with a remote is painful; offer choices.

## Safety

- Don't run `pm uninstall` on system packages. Use `vibetv tweak` (reversible) instead.
- Don't ask for or store the user's account passwords. Developer-mode passwords live in
  `~/.vibetv/config.json`. Never commit them.
