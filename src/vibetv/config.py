"""Persistent config: known devices, the default device, and tweak undo state.

Everything lives in ``~/.vibetv`` (override with ``VIBETV_HOME``) as plain JSON so
users can read and edit it by hand.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

PLATFORMS = ("android", "roku", "webos")


def home() -> Path:
    path = Path(os.environ.get("VIBETV_HOME", Path.home() / ".vibetv"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load(name: str) -> dict:
    path = home() / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(name: str, data: dict) -> None:
    (home() / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class Device:
    name: str
    host: str
    platform: str  # one of PLATFORMS
    port: int | None = None
    extra: dict = field(default_factory=dict)  # e.g. roku dev password, webOS device name

    @property
    def adb_serial(self) -> str:
        return f"{self.host}:{self.port or 5555}"


def load_devices() -> dict[str, Device]:
    raw = _load("config.json").get("devices", {})
    return {name: Device(**d) for name, d in raw.items()}


def save_device(device: Device, make_default: bool = True) -> None:
    cfg = _load("config.json")
    cfg.setdefault("devices", {})[device.name] = asdict(device)
    if make_default or "default" not in cfg:
        cfg["default"] = device.name
    _save("config.json", cfg)


def remove_device(name: str) -> bool:
    cfg = _load("config.json")
    if name not in cfg.get("devices", {}):
        return False
    del cfg["devices"][name]
    if cfg.get("default") == name:
        cfg["default"] = next(iter(cfg["devices"]), None)
    _save("config.json", cfg)
    return True


def get_device(name: str | None = None) -> Device:
    """Resolve a device by name, host, or fall back to the default device."""
    cfg = _load("config.json")
    devices = load_devices()
    if name:
        if name in devices:
            return devices[name]
        for dev in devices.values():
            if dev.host == name:
                return dev
        raise LookupError(f"Unknown device '{name}'. Run `vibetv devices` or `vibetv add`.")
    default = cfg.get("default")
    if default and default in devices:
        return devices[default]
    raise LookupError("No default device. Run `vibetv discover` then `vibetv add <host>`.")


def load_undo() -> dict:
    return _load("undo.json")


def save_undo(data: dict) -> None:
    _save("undo.json", data)
