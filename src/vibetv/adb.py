"""Thin wrapper over the ``adb`` binary for Android TV, Google TV and Fire TV."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Friendly key names -> Android KEYCODE_* values.
KEYS = {
    "home": "KEYCODE_HOME",
    "back": "KEYCODE_BACK",
    "up": "KEYCODE_DPAD_UP",
    "down": "KEYCODE_DPAD_DOWN",
    "left": "KEYCODE_DPAD_LEFT",
    "right": "KEYCODE_DPAD_RIGHT",
    "ok": "KEYCODE_DPAD_CENTER",
    "select": "KEYCODE_DPAD_CENTER",
    "enter": "KEYCODE_ENTER",
    "menu": "KEYCODE_MENU",
    "play": "KEYCODE_MEDIA_PLAY_PAUSE",
    "pause": "KEYCODE_MEDIA_PLAY_PAUSE",
    "rewind": "KEYCODE_MEDIA_REWIND",
    "forward": "KEYCODE_MEDIA_FAST_FORWARD",
    "volup": "KEYCODE_VOLUME_UP",
    "voldown": "KEYCODE_VOLUME_DOWN",
    "mute": "KEYCODE_VOLUME_MUTE",
    "power": "KEYCODE_POWER",
    "sleep": "KEYCODE_SLEEP",
    "wake": "KEYCODE_WAKEUP",
    "search": "KEYCODE_SEARCH",
    "settings": "KEYCODE_SETTINGS",
    "input": "KEYCODE_TV_INPUT",
}

# Stock launchers we know how to step aside from when a custom launcher is set.
STOCK_LAUNCHERS = (
    "com.google.android.apps.tv.launcherx",  # Google TV
    "com.google.android.tvlauncher",  # Android TV
    "com.amazon.tv.launcher",  # Fire TV
)


class AdbError(RuntimeError):
    pass


def adb_path() -> str:
    path = shutil.which("adb")
    if not path:
        raise AdbError(
            "adb not found. Install Android platform-tools: "
            "https://developer.android.com/tools/releases/platform-tools "
            "(winget install Google.PlatformTools | brew install android-platform-tools | apt install adb)"
        )
    return path


def run(serial: str | None, *args: str, binary: bool = False, check: bool = True, timeout: int = 60):
    cmd = [adb_path()]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        err = proc.stderr.decode(errors="replace").strip() or proc.stdout.decode(errors="replace").strip()
        raise AdbError(f"{' '.join(cmd[1:])} failed: {err}")
    return proc.stdout if binary else proc.stdout.decode(errors="replace")


def shell(serial: str, command: str, check: bool = True) -> str:
    return run(serial, "shell", command, check=check).strip()


def connect(serial: str) -> str:
    out = run(None, "connect", serial, check=False, timeout=15).strip()
    if "connected" not in out or "cannot" in out or "failed" in out:
        raise AdbError(
            f"{out or 'adb connect failed'}\n"
            "Enable Developer options > Network/ADB debugging on the TV, then accept the "
            "'Allow USB debugging?' prompt that appears on screen."
        )
    return out


def ensure_connected(serial: str) -> None:
    devices = run(None, "devices", check=False)
    for line in devices.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == serial:
            if parts[1] == "device":
                return
            if parts[1] == "unauthorized":
                raise AdbError("TV has not authorised this computer yet - accept the prompt on the TV.")
    connect(serial)


def keypress(serial: str, key: str) -> None:
    code = KEYS.get(key.lower(), key if key.upper().startswith("KEYCODE_") else None)
    if code is None:
        raise AdbError(f"Unknown key '{key}'. Known keys: {', '.join(sorted(KEYS))}")
    shell(serial, f"input keyevent {code}")


def type_text(serial: str, text: str) -> None:
    # `input text` treats spaces as separators; %s is its escape for a space.
    escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace(" ", "%s")
    shell(serial, f"input text '{escaped}'")


def screenshot(serial: str) -> bytes:
    data = run(serial, "exec-out", "screencap", "-p", binary=True)
    if not data.startswith(b"\x89PNG"):
        raise AdbError("Screenshot failed (DRM-protected video shows up black or blocks capture).")
    return data


def install(serial: str, apk: Path) -> str:
    return run(serial, "install", "-r", str(apk), timeout=300).strip()


def packages(serial: str, third_party: bool = False) -> list[str]:
    out = shell(serial, "pm list packages" + (" -3" if third_party else ""))
    return sorted(line.removeprefix("package:").strip() for line in out.splitlines() if line.strip())


def launch(serial: str, package: str, url: str | None = None) -> None:
    if url:
        shell(serial, f"am start -a android.intent.action.VIEW -d '{url}' -p {package}")
        return
    # Try the TV (leanback) launcher category first, then the regular one.
    out = shell(serial, f"monkey -p {package} -c android.intent.category.LEANBACK_LAUNCHER 1", check=False)
    if "No activities found" in out or "aborted" in out.lower():
        shell(serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1")


def get_setting(serial: str, namespace: str, key: str) -> str | None:
    value = shell(serial, f"settings get {namespace} {key}", check=False)
    return None if value in ("", "null") else value


def put_setting(serial: str, namespace: str, key: str, value: str | None) -> None:
    if value is None:
        shell(serial, f"settings delete {namespace} {key}")
    else:
        shell(serial, f"settings put {namespace} {key} '{value}'")


def is_package_enabled(serial: str, package: str) -> bool | None:
    """True/False if installed, None if the package doesn't exist on the device."""
    if package not in packages(serial):
        return None
    disabled = shell(serial, "pm list packages -d", check=False)
    return f"package:{package}" not in disabled.split()


def set_package_enabled(serial: str, package: str, enabled: bool) -> None:
    # disable-user is fully reversible and never removes data - we never uninstall system apps.
    shell(serial, f"pm {'enable' if enabled else 'disable-user --user 0'} {package}")


def device_info(serial: str) -> dict:
    props = {
        "model": "ro.product.model",
        "manufacturer": "ro.product.manufacturer",
        "android": "ro.build.version.release",
        "sdk": "ro.build.version.sdk",
    }
    info = {name: shell(serial, f"getprop {prop}", check=False) for name, prop in props.items()}
    info["resolution"] = shell(serial, "wm size", check=False).split(":")[-1].strip()
    return info
