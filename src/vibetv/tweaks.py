"""Reversible Android TV tweaks driven by JSON presets.

A preset is a list of steps. Each step either changes a ``settings`` value or
enables/disables a package (``pm disable-user`` - never uninstall). Before a step
runs we record the current value, so ``vibetv tweak revert <id>`` restores exactly
what was there. Built-in presets ship in ``vibetv/presets``; drop your own JSON
files in ``~/.vibetv/presets`` to extend them.

Preset format::

    {
      "id": "snappy-animations",
      "title": "Snappier UI",
      "description": "...",
      "platforms": ["android"],
      "risk": "safe",               # safe | moderate | advanced
      "steps": [
        {"setting": "global", "key": "window_animation_scale", "value": "0.5"},
        {"package": "com.example.bloat", "enabled": false}
      ]
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from . import adb, config

RISKS = ("safe", "moderate", "advanced")


@dataclass
class Preset:
    id: str
    title: str
    description: str
    steps: list[dict]
    platforms: tuple[str, ...] = ("android",)
    risk: str = "safe"
    source: str = "built-in"


def validate(data: dict) -> list[str]:
    errors = []
    for key in ("id", "title", "description", "steps"):
        if key not in data:
            errors.append(f"missing '{key}'")
    if data.get("risk", "safe") not in RISKS:
        errors.append(f"risk must be one of {RISKS}")
    for i, step in enumerate(data.get("steps", [])):
        if "setting" in step:
            if step["setting"] not in ("global", "secure", "system"):
                errors.append(f"step {i}: setting namespace must be global|secure|system")
            if "key" not in step or "value" not in step:
                errors.append(f"step {i}: setting steps need 'key' and 'value'")
        elif "package" in step:
            if not isinstance(step.get("enabled"), bool):
                errors.append(f"step {i}: package steps need boolean 'enabled'")
        else:
            errors.append(f"step {i}: must have 'setting' or 'package'")
    return errors


def _from_json(text: str, source: str) -> Preset:
    data = json.loads(text)
    if errors := validate(data):
        raise ValueError(f"Invalid preset {source}: {'; '.join(errors)}")
    return Preset(
        id=data["id"], title=data["title"], description=data["description"], steps=data["steps"],
        platforms=tuple(data.get("platforms", ["android"])), risk=data.get("risk", "safe"), source=source,
    )


def load_presets() -> dict[str, Preset]:
    presets: dict[str, Preset] = {}
    for entry in resources.files("vibetv").joinpath("presets").iterdir():
        if entry.name.endswith(".json"):
            p = _from_json(entry.read_text(encoding="utf-8"), entry.name)
            presets[p.id] = p
    user_dir = config.home() / "presets"
    if user_dir.is_dir():
        for path in sorted(user_dir.glob("*.json")):
            p = _from_json(path.read_text(encoding="utf-8"), str(path))
            presets[p.id] = p  # user presets override built-ins with the same id
    return presets


def plan(preset: Preset) -> list[str]:
    """Human-readable description of what a preset will do (for --dry-run)."""
    lines = []
    for step in preset.steps:
        if "setting" in step:
            lines.append(f"settings put {step['setting']} {step['key']} {step['value']}")
        else:
            verb = "enable" if step["enabled"] else "disable (reversible)"
            lines.append(f"{verb} package {step['package']}")
    return lines


def apply(serial: str, preset: Preset) -> list[str]:
    undo = config.load_undo()
    device_undo = undo.setdefault(serial, {})
    first_apply = preset.id not in device_undo
    inverse: list[dict] = []
    done: list[str] = []
    for step in preset.steps:
        if "setting" in step:
            ns, key = step["setting"], step["key"]
            inverse.append({"setting": ns, "key": key, "value": adb.get_setting(serial, ns, key)})
            adb.put_setting(serial, ns, key, str(step["value"]))
            done.append(f"{ns}/{key} = {step['value']}")
        else:
            pkg = step["package"]
            state = adb.is_package_enabled(serial, pkg)
            if state is None:
                done.append(f"skip {pkg} (not installed)")
                continue
            inverse.append({"package": pkg, "enabled": state})
            adb.set_package_enabled(serial, pkg, step["enabled"])
            done.append(f"{'enabled' if step['enabled'] else 'disabled'} {pkg}")
    # Re-applying must not overwrite the original values with our own.
    if first_apply:
        device_undo[preset.id] = inverse
        config.save_undo(undo)
    return done


def revert(serial: str, preset_id: str) -> list[str]:
    undo = config.load_undo()
    steps = undo.get(serial, {}).pop(preset_id, None)
    if steps is None:
        raise KeyError(f"No record of '{preset_id}' being applied on {serial}.")
    done = []
    for step in reversed(steps):
        if "setting" in step:
            adb.put_setting(serial, step["setting"], step["key"], step["value"])
            done.append(f"{step['setting']}/{step['key']} restored to {step['value']}")
        else:
            adb.set_package_enabled(serial, step["package"], step["enabled"])
            done.append(f"{'re-enabled' if step['enabled'] else 'disabled'} {step['package']}")
    config.save_undo(undo)
    return done


def applied(serial: str) -> list[str]:
    return sorted(config.load_undo().get(serial, {}))


def custom_launcher_preset(serial: str, package: str) -> Preset:
    """Build a preset that disables the stock launcher(s) so ``package`` becomes Home."""
    installed = set(adb.packages(serial))
    if package not in installed:
        raise ValueError(f"{package} is not installed on the TV.")
    stock = [p for p in adb.STOCK_LAUNCHERS if p in installed]
    if not stock:
        raise ValueError("No known stock launcher found - set the default Home app from TV Settings instead.")
    return Preset(
        id="custom-launcher",
        title=f"Use {package} as Home",
        description="Disables the stock launcher (reversible). Revert with `vibetv tweak revert custom-launcher`.",
        steps=[{"package": p, "enabled": False} for p in stock],
        risk="moderate",
        source="generated",
    )


def screensaver_preset(component: str) -> Preset:
    return Preset(
        id="custom-screensaver",
        title=f"Screensaver: {component}",
        description="Sets the active screensaver (Daydream) component.",
        steps=[
            {"setting": "secure", "key": "screensaver_enabled", "value": "1"},
            {"setting": "secure", "key": "screensaver_components", "value": component},
        ],
        source="generated",
    )
