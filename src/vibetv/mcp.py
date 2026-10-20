"""`vibetv mcp`: a Model Context Protocol server over stdio.

Gives AI agents eyes and hands on the TV: screenshots come back as images the model can
see, and it can press keys, read console logs, deploy, and apply reversible tweaks.

Add to Claude Code:   claude mcp add vibetv -- vibetv mcp
Add to Cursor / others: {"mcpServers": {"vibetv": {"command": "vibetv", "args": ["mcp"]}}}
"""

from __future__ import annotations

import base64
import json
import sys
import traceback
import urllib.request
from dataclasses import asdict
from pathlib import Path

from . import __version__, config, discover, tv, tweaks
from .devserver import running_url

PROTOCOL_VERSION = "2025-06-18"

DEVICE_ARG = {"device": {"type": "string", "description": "Saved device name or IP. Omit for the default device."}}


def _schema(props: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": {**DEVICE_ARG, **(props or {})}, "required": required or []}


TOOLS = [
    {
        "name": "tv_screenshot",
        "description": "Capture what is on the TV screen right now. Use after every UI change to verify it visually.",
        "inputSchema": _schema(),
    },
    {
        "name": "tv_key",
        "description": "Press remote-control keys in order. Keys: up, down, left, right, ok, back, home, menu, play, "
        "pause, rewind, forward, volup, voldown, mute, power, search, settings.",
        "inputSchema": _schema({"keys": {"type": "array", "items": {"type": "string"}}}, ["keys"]),
    },
    {
        "name": "tv_type",
        "description": "Type text into the focused text field on the TV.",
        "inputSchema": _schema({"text": {"type": "string"}}, ["text"]),
    },
    {
        "name": "tv_logs",
        "description": "Recent console.log output and JavaScript errors from the web app running on the TV "
        "(requires `vibetv serve` to be running).",
        "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer", "default": 100}}},
    },
    {
        "name": "tv_deploy",
        "description": "Build and install the vibetv project in the given folder onto the TV, then launch it.",
        "inputSchema": _schema({"project_dir": {"type": "string", "description": "Folder containing vibetv.json"}}, ["project_dir"]),
    },
    {
        "name": "tv_open_url",
        "description": "Open a URL on the TV (Android: system browser or a vibetv app via `package`; webOS: browser).",
        "inputSchema": _schema({"url": {"type": "string"}, "package": {"type": "string"}}, ["url"]),
    },
    {
        "name": "tv_apps",
        "description": "List apps installed on the TV (third-party apps on Android).",
        "inputSchema": _schema(),
    },
    {
        "name": "tv_launch",
        "description": "Launch an app by package name (Android) or channel id (Roku).",
        "inputSchema": _schema({"app": {"type": "string"}}, ["app"]),
    },
    {
        "name": "tv_info",
        "description": "Model, OS version and resolution of the TV.",
        "inputSchema": _schema(),
    },
    {
        "name": "tv_devices",
        "description": "List saved TVs and which one is the default.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tv_discover",
        "description": "Search the local network for TVs.",
        "inputSchema": {"type": "object", "properties": {"scan_subnet": {"type": "boolean", "default": False}}},
    },
    {
        "name": "tv_tweak_list",
        "description": "List reversible Android TV tweak presets and which are applied.",
        "inputSchema": _schema(),
    },
    {
        "name": "tv_tweak_apply",
        "description": "Apply a tweak preset (reversible). Ask the user before applying 'moderate' or 'advanced' risk presets.",
        "inputSchema": _schema({"preset": {"type": "string"}}, ["preset"]),
    },
    {
        "name": "tv_tweak_revert",
        "description": "Undo a previously applied tweak preset, restoring the original values.",
        "inputSchema": _schema({"preset": {"type": "string"}}, ["preset"]),
    },
]


def _text(value) -> list[dict]:
    if not isinstance(value, str):
        value = json.dumps(value, indent=2, default=str)
    return [{"type": "text", "text": value}]


def _android(args: dict) -> tuple[config.Device, str]:
    device = config.get_device(args.get("device"))
    if device.platform != "android":
        raise tv.TVError("Tweaks are only available on Android TV / Google TV / Fire TV.")
    serial = device.adb_serial
    tv.adb.ensure_connected(serial)
    return device, serial


def call_tool(name: str, args: dict) -> list[dict]:
    if name == "tv_devices":
        devices = {n: asdict(d) for n, d in config.load_devices().items()}
        for d in devices.values():
            d["extra"] = {k: "***" if "password" in k else v for k, v in d["extra"].items()}
        return _text(devices or "No saved devices. Use tv_discover, then ask the user to run `vibetv add <ip>`.")
    if name == "tv_discover":
        found = discover.discover(scan_subnet=bool(args.get("scan_subnet")))
        return _text([{"host": t.host, "name": t.name, "maker": t.manufacturer, "model": t.model,
                       "platform": t.platform, "ports": t.open_ports} for t in found] or "No TVs found.")
    if name == "tv_logs":
        url = running_url()
        if not url:
            return _text("No dev server recorded. Start one with `vibetv serve` in the project folder.")
        try:
            with urllib.request.urlopen(f"{url}__vibetv/logs", timeout=3) as resp:
                lines = json.loads(resp.read())
        except OSError:
            return _text(f"Dev server at {url} isn't responding. Is `vibetv serve` still running?")
        return _text("\n".join(lines[-int(args.get("lines", 100)):]) or "(no logs yet)")

    if name.startswith("tv_tweak"):
        _, serial = _android(args)
        presets = tweaks.load_presets()
        if name == "tv_tweak_list":
            applied = set(tweaks.applied(serial))
            return _text([{"id": p.id, "title": p.title, "risk": p.risk, "applied": p.id in applied,
                           "description": p.description} for p in presets.values()])
        if name == "tv_tweak_apply":
            if args["preset"] not in presets:
                raise KeyError(f"Unknown preset {args['preset']}. Options: {', '.join(presets)}")
            return _text(tweaks.apply(serial, presets[args["preset"]]))
        return _text(tweaks.revert(serial, args["preset"]))

    device = config.get_device(args.get("device"))
    if name == "tv_screenshot":
        data, mime = tv.screenshot(device)
        return [{"type": "image", "data": base64.b64encode(data).decode(), "mimeType": mime}]
    if name == "tv_key":
        for key in args["keys"]:
            tv.keypress(device, key)
        return _text(f"Pressed: {' '.join(args['keys'])}")
    if name == "tv_type":
        tv.type_text(device, args["text"])
        return _text("Typed.")
    if name == "tv_deploy":
        return _text(tv.deploy(device, Path(args["project_dir"]).expanduser().resolve(), log=sys.stderr))
    if name == "tv_open_url":
        tv.open_url(device, args["url"], args.get("package"))
        return _text(f"Opened {args['url']}")
    if name == "tv_apps":
        return _text(tv.apps(device))
    if name == "tv_launch":
        tv.launch(device, args["app"])
        return _text(f"Launched {args['app']}")
    if name == "tv_info":
        return _text(tv.info(device))
    raise KeyError(f"Unknown tool {name}")


def handle(msg: dict) -> dict | None:
    method, msg_id = msg.get("method"), msg.get("id")
    if msg_id is None:  # notification (e.g. notifications/initialized) - no reply
        return None
    if method == "initialize":
        requested = msg.get("params", {}).get("protocolVersion")
        result = {
            "protocolVersion": requested or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "vibetv", "version": __version__},
            "instructions": "Tools to see and control the user's TV. After changing a TV app, deploy or let "
            "`vibetv serve` live-reload it, then call tv_screenshot to verify the result visually.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params", {})
        try:
            result = {"content": call_tool(params.get("name", ""), params.get("arguments") or {}), "isError": False}
        except Exception as e:  # report tool failures to the model instead of crashing the server
            traceback.print_exc(file=sys.stderr)
            result = {"content": _text(f"{type(e).__name__}: {e}"), "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
