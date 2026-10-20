"""One API over every platform, used by both the CLI and the MCP server."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from . import adb, roku, webos
from .config import Device


class TVError(RuntimeError):
    pass


def _unsupported(device: Device, what: str) -> TVError:
    return TVError(f"'{what}' is not supported on {device.platform} yet - PRs welcome!")


def _serial(device: Device) -> str:
    serial = device.adb_serial
    adb.ensure_connected(serial)
    return serial


def _roku_password(device: Device) -> str:
    pw = device.extra.get("dev_password")
    if not pw:
        raise TVError(f"No Roku dev password saved. Run: vibetv add {device.host} --platform roku --password <pw>")
    return pw


def _webos_name(device: Device) -> str:
    return device.extra.get("ares_device", device.name)


def keypress(device: Device, key: str, times: int = 1) -> None:
    for _ in range(max(1, times)):
        if device.platform == "android":
            adb.keypress(_serial(device), key)
        elif device.platform == "roku":
            roku.keypress(device.host, key)
        else:
            raise _unsupported(device, "keypress")


def type_text(device: Device, text: str) -> None:
    if device.platform == "android":
        adb.type_text(_serial(device), text)
    elif device.platform == "roku":
        roku.type_text(device.host, text)
    else:
        raise _unsupported(device, "type")


def screenshot(device: Device) -> tuple[bytes, str]:
    """Return (image bytes, mime type)."""
    if device.platform == "android":
        return adb.screenshot(_serial(device)), "image/png"
    if device.platform == "roku":
        return roku.screenshot(device.host, _roku_password(device))
    if device.platform == "webos":
        return webos.screenshot(_webos_name(device)), "image/png"
    raise _unsupported(device, "screenshot")


def info(device: Device) -> dict:
    if device.platform == "android":
        return adb.device_info(_serial(device))
    if device.platform == "roku":
        return roku.device_info(device.host)
    return {"platform": device.platform, "host": device.host}


def apps(device: Device, third_party: bool = True) -> list[str]:
    if device.platform == "android":
        return adb.packages(_serial(device), third_party=third_party)
    if device.platform == "roku":
        return [f"{a['id']}  {a['name']}" for a in roku.apps(device.host)]
    if device.platform == "webos":
        return webos.apps(_webos_name(device))
    raise _unsupported(device, "apps")


def launch(device: Device, app: str) -> None:
    if device.platform == "android":
        adb.launch(_serial(device), app)
    elif device.platform == "roku":
        roku.launch(device.host, app)
    else:
        raise _unsupported(device, "launch")


def open_url(device: Device, url: str, package: str | None = None) -> None:
    """Open a URL on the TV - in our dev wrapper app if installed, else the system browser."""
    if device.platform == "android":
        serial = _serial(device)
        if package:
            adb.shell(serial, f"am start -n {package}/.MainActivity --es url '{url}' --activity-clear-top")
        else:
            adb.shell(serial, f"am start -a android.intent.action.VIEW -d '{url}'")
    elif device.platform == "webos":
        webos.open_url(_webos_name(device), url)
    else:
        raise _unsupported(device, "open-url")


# ---------------------------------------------------------------- project deploys


def load_project(path: Path) -> tuple[Path, dict]:
    """Walk up from ``path`` to find vibetv.json (written by `vibetv new`)."""
    for folder in [path, *path.parents]:
        cfg = folder / "vibetv.json"
        if cfg.exists():
            return folder, json.loads(cfg.read_text(encoding="utf-8"))
    raise TVError("No vibetv.json found here or in parent folders. Create a project with `vibetv new`.")


def gradle_cmd(root: Path) -> list[str]:
    wrapper = root / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if wrapper.exists():
        return [str(wrapper)]
    if gradle := shutil.which("gradle"):
        return [gradle]
    raise TVError(
        "Gradle not found. Either install Android Studio / Gradle 8.x locally, or push the project to "
        "GitHub: the included workflow builds the APK for you (Actions tab > artifacts), then run "
        "`vibetv install path/to/app.apk`."
    )


def deploy(device: Device, project_dir: Path, log=None) -> str:
    """Build (if needed) and install a project. ``log`` receives build output (default: inherit stdout)."""
    root, project = load_project(project_dir)
    kind = project["template"]
    if kind == "android-tv":
        if device.platform != "android":
            raise TVError(f"This is an Android TV project but '{device.name}' is a {device.platform} device.")
        subprocess.run([*gradle_cmd(root), "assembleDebug"], cwd=root, check=True, stdout=log, stderr=log)
        apk = next((root / "app/build/outputs/apk/debug").glob("*.apk"))
        serial = _serial(device)
        adb.install(serial, apk)
        adb.launch(serial, project["app_id"])
        return f"Installed and launched {project['app_id']}"
    if kind == "roku":
        result = roku.sideload(device.host, _roku_password(device), root)
        return f"Roku: {result}"
    if kind == "webos":
        return f"Installed and launched {webos.deploy(root, _webos_name(device))}"
    raise TVError(f"Template '{kind}' has no deploy step - use `vibetv serve` to preview it.")
