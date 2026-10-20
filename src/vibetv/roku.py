"""Roku support: External Control Protocol (keys/apps) and the developer sideloader.

Developer mode: on the Roku remote press Home x3, Up x2, Right, Left, Right, Left, Right,
then set a dev password. The default dev username is always ``rokudev``.
"""

from __future__ import annotations

import io
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree

KEYS = {
    "home": "Home", "back": "Back", "up": "Up", "down": "Down", "left": "Left",
    "right": "Right", "ok": "Select", "select": "Select", "enter": "Enter",
    "play": "Play", "pause": "Play", "rewind": "Rev", "forward": "Fwd",
    "replay": "InstantReplay", "info": "Info", "menu": "Info", "search": "Search",
    "volup": "VolumeUp", "voldown": "VolumeDown", "mute": "VolumeMute",
    "power": "Power", "sleep": "PowerOff", "wake": "PowerOn",
}

ZIP_EXCLUDE = {".git", "node_modules", "out", "dist", ".vscode", ".DS_Store", "vibetv.json", ".gitignore"}
ZIP_EXCLUDE_SUFFIXES = {".zip", ".md"}


class RokuError(RuntimeError):
    pass


def _ecp(host: str, path: str, method: str = "GET", timeout: int = 5) -> bytes:
    req = urllib.request.Request(f"http://{host}:8060/{path}", method=method, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def keypress(host: str, key: str) -> None:
    name = KEYS.get(key.lower(), key)
    _ecp(host, f"keypress/{urllib.parse.quote(name)}", "POST")


def type_text(host: str, text: str) -> None:
    for ch in text:
        _ecp(host, f"keypress/Lit_{urllib.parse.quote(ch, safe='')}", "POST")


def device_info(host: str) -> dict[str, str]:
    root = ElementTree.fromstring(_ecp(host, "query/device-info"))
    wanted = ("friendly-device-name", "model-name", "software-version", "developer-enabled", "ui-resolution")
    return {child.tag: (child.text or "") for child in root if child.tag in wanted}


def apps(host: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(_ecp(host, "query/apps"))
    return [{"id": a.get("id", ""), "name": a.text or "", "version": a.get("version", "")} for a in root]


def launch(host: str, app_id: str) -> None:
    _ecp(host, f"launch/{urllib.parse.quote(app_id)}", "POST")


def zip_channel(src: Path) -> bytes:
    """Zip a channel directory with the manifest at the archive root, as Roku requires."""
    if not (src / "manifest").exists():
        raise RokuError(f"{src} has no 'manifest' file - is this a Roku channel folder?")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            rel = path.relative_to(src)
            if path.is_file() and not (set(rel.parts) & ZIP_EXCLUDE) and path.suffix not in ZIP_EXCLUDE_SUFFIXES:
                zf.write(path, rel.as_posix())
    return buf.getvalue()


def _multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content) in files.items():
        body.write(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n".encode()
        )
        body.write(content + b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def _dev_opener(host: str, password: str) -> urllib.request.OpenerDirector:
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, f"http://{host}/", "rokudev", password)
    return urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(mgr))


def _dev_post(host: str, password: str, path: str, fields: dict, files: dict | None = None) -> str:
    body, ctype = _multipart(fields, files or {})
    req = urllib.request.Request(f"http://{host}/{path}", data=body, headers={"Content-Type": ctype})
    try:
        with _dev_opener(host, password).open(req, timeout=120) as resp:
            return resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RokuError("Roku rejected the dev password (user is always 'rokudev').") from e
        raise RokuError(f"Roku dev server returned HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RokuError(f"Can't reach Roku dev server at {host} - is Developer Mode enabled? ({e.reason})") from e


def sideload(host: str, password: str, src: Path) -> str:
    html = _dev_post(host, password, "plugin_install", {"mysubmit": "Install"}, {"archive": ("dev.zip", zip_channel(src))})
    for marker in ("Install Success", "Identical to previous version", "Application Received"):
        if marker in html:
            return marker
    raise RokuError("Roku did not confirm the install. Check the manifest and BrightScript console: telnet <tv> 8085")


def screenshot(host: str, password: str) -> tuple[bytes, str]:
    _dev_post(host, password, "plugin_inspect", {"mysubmit": "Screenshot", "passwd": ""}, {"archive": ("", b"")})
    opener = _dev_opener(host, password)
    for ext, mime in (("png", "image/png"), ("jpg", "image/jpeg")):
        try:
            with opener.open(f"http://{host}/pkgs/dev.{ext}", timeout=20) as resp:
                return resp.read(), mime
        except urllib.error.HTTPError:
            continue
    raise RokuError("Screenshot failed - a dev channel must be running (screenshots only capture sideloaded apps).")
