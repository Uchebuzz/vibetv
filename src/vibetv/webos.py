"""LG webOS support via the official ``ares`` CLI (npm i -g @webos-tools/cli).

One-time setup on the TV: install the "Developer Mode" app from the LG Content Store,
sign in, enable Dev Mode + Key Server, then run ``ares-setup-device`` and
``ares-novacom --device <name> --getkey`` with the passphrase shown on screen.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class WebOSError(RuntimeError):
    pass


def _ares(tool: str, *args: str, timeout: int = 180) -> str:
    exe = shutil.which(tool)
    if not exe:
        raise WebOSError(f"{tool} not found. Install the webOS CLI: npm install -g @webos-tools/cli")
    proc = subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise WebOSError(f"{tool} failed: {(proc.stderr or proc.stdout).strip()}")
    return proc.stdout.strip()


def app_id(src: Path) -> str:
    info = src / "appinfo.json"
    if not info.exists():
        raise WebOSError(f"{src} has no appinfo.json - is this a webOS app folder?")
    return json.loads(info.read_text(encoding="utf-8"))["id"]


def deploy(src: Path, device: str, launch: bool = True) -> str:
    with tempfile.TemporaryDirectory() as out:
        _ares("ares-package", str(src), "--outdir", out, "--no-minify")
        ipk = next(Path(out).glob("*.ipk"))
        _ares("ares-install", "--device", device, str(ipk))
    if launch:
        _ares("ares-launch", "--device", device, app_id(src))
    return app_id(src)


def open_url(device: str, url: str) -> None:
    _ares("ares-launch", "--device", device, "com.webos.app.browser", "--params", json.dumps({"target": url}))


def screenshot(device: str) -> bytes:
    with tempfile.TemporaryDirectory() as out:
        path = Path(out) / "screen.png"
        _ares("ares-device", "--device", device, "--capture-screen", str(path))
        return path.read_bytes()


def apps(device: str) -> list[str]:
    return [line.strip() for line in _ares("ares-install", "--device", device, "--list").splitlines() if line.strip()]
