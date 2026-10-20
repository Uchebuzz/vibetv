
## This project: LG webOS TV app

- It's a regular web app (`index.html`, `styles.css`, `tv.js`, `app.js`) plus `appinfo.json` (id, title, icons).
- Back key is keyCode 461 (handled by `tv.js`). With `disableBackHistoryAPI: true` the app gets every Back press.
- Preview fast: `vibetv serve --open` opens your laptop's dev server in the TV browser with live reload.
- Deploy a real install: `vibetv deploy` (needs `npm i -g @webos-tools/cli` and a device registered with
  `ares-setup-device`; the vibetv device's `ares_device` name must match).
- Inspect: `ares-inspect --device <name> --app {{APP_ID}} --open`.
