// app.js - the part you (and your AI agent) vibecode. tv.js handles keys and focus.

const DEMO_TILES = [
  { label: 'YouTube', color: '#ef4444' },
  { label: 'Netflix', color: '#b91c1c' },
  { label: 'Music', color: '#8b5cf6' },
  { label: 'Photos', color: '#0ea5e9' },
  { label: 'Live TV', color: '#10b981' },
];

function pad(n) { return String(n).padStart(2, '0'); }

function tickClock() {
  const now = new Date();
  const time = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
  const date = now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  const h = now.getHours();
  document.getElementById('time').textContent = time;
  document.getElementById('date').textContent = date;
  document.getElementById('ss-time').textContent = time;
  document.getElementById('ss-date').textContent = date;
  document.getElementById('greeting').textContent =
    h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}

function renderTiles() {
  const row = document.getElementById('tiles');
  row.innerHTML = '';
  // Inside the Android wrapper we can list and launch real installed apps -> instant custom launcher.
  const apps = TV.native ? TV.native.apps() : null;
  if (apps && apps.length) {
    document.getElementById('row-title').textContent = 'Installed apps';
    for (const app of apps) {
      const tile = document.createElement('button');
      tile.className = 'tile focusable';
      tile.textContent = app.label;
      if (app.banner) {
        tile.style.backgroundImage = `url(${app.banner})`;
        tile.classList.add('has-banner');
      }
      tile.onclick = () => TV.native.launch(app.package);
      row.appendChild(tile);
    }
    return;
  }
  for (const t of DEMO_TILES) {
    const tile = document.createElement('button');
    tile.className = 'tile focusable';
    tile.style.background = `linear-gradient(135deg, ${t.color}, #111827)`;
    tile.textContent = t.label;
    tile.onclick = () => console.log('Selected', t.label);
    row.appendChild(tile);
  }
}

function showScreensaver(on) {
  document.getElementById('screensaver').hidden = !on;
  document.getElementById('stage').hidden = on;
}

document.addEventListener('click', e => {
  const el = e.target.closest('[data-action]');
  const action = el ? el.dataset.action : null;
  if (action === 'screensaver') showScreensaver(true);
  if (action === 'theme') {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === 'sunset' ? '' : 'sunset';
  }
  if (action === 'settings') TV.native ? TV.native.openSettings() : console.log('Settings needs the Android wrapper');
});

// Any key wakes the screensaver preview.
TV.onKey(() => {
  if (!document.getElementById('screensaver').hidden && !TV.params.has('screensaver')) {
    showScreensaver(false);
    return true;
  }
});
TV.onBack(() => {
  if (!document.getElementById('screensaver').hidden && !TV.params.has('screensaver')) {
    showScreensaver(false);
    return true;
  }
});

tickClock();
setInterval(tickClock, 1000);
renderTiles();
if (TV.params.has('screensaver')) showScreensaver(true);
else TV.focusFirst();
console.log('{{APP_NAME}} ready', `${window.innerWidth}x${window.innerHeight}`);
