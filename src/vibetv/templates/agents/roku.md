
## This project: Roku channel (BrightScript + SceneGraph)

- Roku does **not** run HTML/JS. UI is SceneGraph XML in `components/`, logic is BrightScript (`.brs`).
- Layout: `manifest` (name, icons, resolution), `source/main.brs` (entry), `components/MainScene.{xml,brs}`
  (the screen), `components/Tile.xml` (a row item).
- Deploy: `vibetv deploy` zips this folder and sideloads it over Wi-Fi to the Roku in developer mode.
- Debug console (print output, crashes, stack traces): `telnet <roku-ip> 8085`. Check it after every deploy;
  a crash shows up there, not on screen.
- Screenshots only work while the sideloaded dev channel is in the foreground.
- BrightScript gotchas: case-insensitive; `m` is component-scoped state; arrays/assocarrays are reference
  types; use `observeField` for async; UI nodes can only be touched on the render thread. Use `Task` nodes
  for network calls (`roUrlTransfer`), never in `init()`.
- Key handling: implement `onKeyEvent(key, press)` in the focused component. Return `true` to consume.
- Docs: https://developer.roku.com/docs/developer-program/getting-started/roku-dev-prog.md
