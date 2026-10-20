"""LAN dev server with live reload and TV console forwarding.

Serves a folder to the TV, injects a tiny script into every HTML page that
  * reloads the page when any file changes (so AI edits show up on the TV instantly), and
  * forwards console.log / errors from the TV back to your terminal (and to AI agents via
    ``vibetv logs`` / the MCP ``tv_logs`` tool).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import deque
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config

SKIP_DIRS = {".git", "node_modules", "__pycache__", "build", ".gradle"}

CLIENT_JS = r"""
(() => {
  const send = (level, args) => {
    try {
      const msg = args.map(a => {
        if (a instanceof Error) return a.stack || String(a);
        if (typeof a === 'object') { try { return JSON.stringify(a); } catch (_) { return String(a); } }
        return String(a);
      }).join(' ');
      fetch('/__vibetv/log', {method: 'POST', body: JSON.stringify({level, msg})});
    } catch (_) {}
  };
  for (const level of ['log', 'info', 'warn', 'error']) {
    const orig = console[level].bind(console);
    console[level] = (...args) => { send(level, args); orig(...args); };
  }
  window.addEventListener('error', e => send('error', [`${e.message} @ ${e.filename}:${e.lineno}`]));
  window.addEventListener('unhandledrejection', e => send('error', ['Unhandled promise rejection:', e.reason]));
  window.addEventListener('keydown', e => { if (window.__VIBETV_LOG_KEYS) send('key', [e.key, e.keyCode]); });
  let version = null;
  setInterval(async () => {
    try {
      const v = await (await fetch('/__vibetv/version', {cache: 'no-store'})).text();
      if (version && v !== version) location.reload();
      version = v;
    } catch (_) {}
  }, 1000);
})();
"""

TAG = b'<script src="/__vibetv/client.js"></script>'


def tree_version(root: Path) -> str:
    h = hashlib.sha1()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            h.update(f"{path}:{st.st_mtime_ns}:{st.st_size}".encode())
    return h.hexdigest()[:12]


def inject(html: bytes) -> bytes:
    lower = html.lower()
    idx = lower.rfind(b"</body>")
    if idx == -1:
        return html + TAG
    return html[:idx] + TAG + html[idx:]


class LogBuffer:
    def __init__(self, size: int = 500):
        self.lines: deque[str] = deque(maxlen=size)
        self.lock = threading.Lock()

    def add(self, level: str, msg: str) -> str:
        line = f"{time.strftime('%H:%M:%S')} [{level}] {msg}"
        with self.lock:
            self.lines.append(line)
        return line

    def tail(self, n: int = 100) -> list[str]:
        with self.lock:
            return list(self.lines)[-n:]


class Handler(SimpleHTTPRequestHandler):
    logs: LogBuffer
    quiet: bool = False

    def log_message(self, format, *args):  # noqa: A002 - signature from base class
        pass  # keep the terminal for TV logs, not access logs

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/__vibetv/client.js":
            return self._send(CLIENT_JS.encode(), "application/javascript")
        if path == "/__vibetv/version":
            return self._send(tree_version(Path(self.directory)).encode(), "text/plain")
        if path == "/__vibetv/logs":
            return self._send(json.dumps(self.logs.tail(500)).encode(), "application/json")
        local = Path(self.translate_path(path))
        if local.is_dir():
            local = local / "index.html"
        if local.suffix in (".html", ".htm") and local.is_file():
            return self._send(inject(local.read_bytes()), "text/html; charset=utf-8")
        return super().do_GET()

    def do_POST(self):
        if self.path != "/__vibetv/log":
            return self._send(b"not found", "text/plain", 404)
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            data = {"level": "log", "msg": "<unparseable log>"}
        line = self.logs.add(data.get("level", "log"), str(data.get("msg", "")))
        if not self.quiet:
            print(f"  tv> {line}", flush=True)
        self._send(b"ok", "text/plain")


def make_server(root: Path, host: str = "0.0.0.0", port: int = 8765, quiet: bool = False) -> ThreadingHTTPServer:
    handler = partial(type("BoundHandler", (Handler,), {"logs": LogBuffer(), "quiet": quiet}), directory=str(root))
    return ThreadingHTTPServer((host, port), handler)


def record_running(url: str) -> None:
    (config.home() / "devserver.json").write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")


def running_url() -> str | None:
    path = config.home() / "devserver.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("url")
