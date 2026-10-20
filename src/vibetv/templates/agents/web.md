
## This project: plain web TV app

- Files: `index.html`, `styles.css`, `tv.js` (keys + spatial navigation, rarely needs edits), `app.js` (your app).
- Preview: `vibetv serve` → open the printed URL on a laptop (arrow keys + Enter + Backspace emulate the remote),
  or `vibetv serve --open` to push it to an Android TV / webOS TV in its browser.
- Make anything focusable by giving it the class `focusable`. React to keys with `TV.onKey((name, e) => ...)`,
  handle Back with `TV.onBack(() => true)`.
- To ship it as an installable app, scaffold `vibetv new android-tv` or `vibetv new webos` and copy these files in.
