/*
 * tv.js - tiny, dependency-free TV helpers. Works on Android TV WebView, Fire TV,
 * LG webOS, Samsung Tizen and desktop browsers (arrow keys + Enter + Backspace/Esc).
 *
 *   TV.key            normalised key names: 'up' 'down' 'left' 'right' 'ok' 'back' 'play' ...
 *   TV.onKey(fn)      fn(name, event) -> return true to stop default navigation
 *   TV.focus(el)      move focus
 *   TV.focusFirst()   focus the first .focusable element
 *   TV.native         Android bridge (installed apps, launch, open settings) or null
 *   TV.onBack(fn)     fn() -> return true if you handled Back (otherwise the app exits)
 */
(function () {
  const KEYMAP = {
    ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
    Up: 'up', Down: 'down', Left: 'left', Right: 'right',
    Enter: 'ok', ' ': 'ok', Select: 'ok',
    Backspace: 'back', Escape: 'back', GoBack: 'back', BrowserBack: 'back',
    MediaPlayPause: 'play', MediaPlay: 'play', MediaPause: 'pause',
    MediaRewind: 'rewind', MediaFastForward: 'forward', ColorF0Red: 'red',
    ColorF1Green: 'green', ColorF2Yellow: 'yellow', ColorF3Blue: 'blue',
  };
  // keyCodes for platforms that don't fill in event.key
  const CODEMAP = {
    37: 'left', 38: 'up', 39: 'right', 40: 'down', 13: 'ok', 23: 'ok',
    8: 'back', 27: 'back', 461: 'back' /* webOS */, 10009: 'back' /* Tizen */,
    415: 'play', 19: 'pause', 412: 'rewind', 417: 'forward', 179: 'play',
  };

  const listeners = [];
  const backHandlers = [];
  let current = null;

  function nameOf(e) { return KEYMAP[e.key] || CODEMAP[e.keyCode] || null; }

  function focusables() {
    return Array.from(document.querySelectorAll('.focusable'))
      .filter(el => !el.disabled && el.offsetParent !== null);
  }

  function focus(el) {
    if (!el) return;
    if (current) current.classList.remove('focused');
    current = el;
    el.classList.add('focused');
    el.focus({ preventScroll: true });
    el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  }

  function center(r) { return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }

  // Geometric spatial navigation: pick the nearest element in the pressed direction,
  // strongly preferring elements that are aligned on the other axis.
  function move(dir) {
    const items = focusables();
    if (!current || !items.includes(current)) return focus(items[0]);
    const from = center(current.getBoundingClientRect());
    let best = null, bestScore = Infinity;
    for (const el of items) {
      if (el === current) continue;
      const to = center(el.getBoundingClientRect());
      const dx = to.x - from.x, dy = to.y - from.y;
      const main = { left: -dx, right: dx, up: -dy, down: dy }[dir];
      if (main <= 1) continue;
      const cross = dir === 'left' || dir === 'right' ? Math.abs(dy) : Math.abs(dx);
      const score = main + cross * 3;
      if (score < bestScore) { bestScore = score; best = el; }
    }
    if (best) focus(best);
  }

  document.addEventListener('keydown', e => {
    const name = nameOf(e);
    if (!name) return;
    for (const fn of listeners) if (fn(name, e) === true) { e.preventDefault(); return; }
    if (['up', 'down', 'left', 'right'].includes(name)) { e.preventDefault(); move(name); }
    else if (name === 'ok' && current) { e.preventDefault(); current.click(); }
    else if (name === 'back') { e.preventDefault(); TV.back(); }
  });

  // Desktop preview: mouse hover moves focus too.
  document.addEventListener('mouseover', e => {
    const el = e.target.closest && e.target.closest('.focusable');
    if (el) focus(el);
  });

  function fitStage() {
    const stage = document.getElementById('stage');
    if (!stage) return;
    const s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = `scale(${s})`;
  }
  window.addEventListener('resize', fitStage);
  document.addEventListener('DOMContentLoaded', fitStage);

  let nativeBridge = null;
  if (window.VibeTVNative) {
    nativeBridge = {
      apps: () => JSON.parse(window.VibeTVNative.apps()),
      launch: pkg => window.VibeTVNative.launch(pkg),
      openSettings: () => window.VibeTVNative.openSettings(),
      exit: () => window.VibeTVNative.exit(),
    };
  }

  window.TV = {
    onKey: fn => listeners.push(fn),
    onBack: fn => backHandlers.push(fn),
    // Called on Back. The Android wrapper calls this too and exits the app when it returns false.
    back() {
      for (let i = backHandlers.length - 1; i >= 0; i--) if (backHandlers[i]() === true) return true;
      return false;
    },
    focus,
    focusFirst: () => focus(focusables()[0]),
    get focused() { return current; },
    native: nativeBridge,
    params: new URLSearchParams(location.search),
  };
})();
