"""`vibetv new`: create a TV project from a bundled template."""

from __future__ import annotations

import json
import re
import struct
import zlib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.abc import Traversable

RENAMES = {"_github": ".github", "_gitignore": ".gitignore"}
APP_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


@dataclass
class Template:
    name: str
    platform: str | None  # which device type `vibetv deploy` targets
    description: str
    parts: list[tuple[str, str]]  # (template folder, destination subfolder)
    web_root: str | None = None  # folder `vibetv serve` should serve
    images: dict[str, tuple[int, int]] = field(default_factory=dict)


TEMPLATES = {
    "android-tv": Template(
        "android-tv", "android",
        "Android TV / Google TV / Fire TV app: web UI in a native shell, plus custom launcher and screensaver support",
        [("android-tv", ""), ("web", "web")], web_root="web",
    ),
    "roku": Template(
        "roku", "roku", "Roku channel (BrightScript + SceneGraph), sideloaded over Wi-Fi",
        [("roku", "")], images={"images/icon_hd.png": (336, 210), "images/splash_fhd.png": (1920, 1080)},
    ),
    "webos": Template(
        "webos", "webos", "LG webOS TV web app",
        [("webos", ""), ("web", "")], web_root=".", images={"icon.png": (80, 80), "largeIcon.png": (130, 130)},
    ),
    "web": Template(
        "web", None, "Plain 10-foot web app (D-pad navigation, live reload). Runs in any TV browser",
        [("web", "")], web_root=".",
    ),
}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "tv-app"


def default_app_id(name: str) -> str:
    ident = re.sub(r"[^a-z0-9]", "", name.lower()) or "app"
    if ident[0].isdigit():
        ident = "app" + ident
    return f"com.vibetv.{ident}"


def png(width: int, height: int, bg=(11, 13, 18), fg=(110, 231, 183)) -> bytes:
    """A dependency-free PNG: dark background with a simple TV glyph in the middle."""
    s = min(width, height)
    x0, x1 = int((width - s * 0.8) / 2), int((width + s * 0.8) / 2)
    y0, y1 = int((height - s * 0.5) / 2), int((height + s * 0.5) / 2)
    border = max(2, s // 20)
    sx0, sx1 = int(width / 2 - s * 0.15), int(width / 2 + s * 0.15)
    bg_px, fg_px = bytes(bg), bytes(fg)

    def row(spans: list[tuple[int, int]]) -> bytes:
        out, pos = bytearray(b"\x00"), 0  # leading 0 = PNG filter type "none"
        for a, b in spans:
            out += bg_px * (a - pos) + fg_px * (b - a)
            pos = b
        return bytes(out + bg_px * (width - pos))

    blank = row([])
    frame_edge = row([(x0, x1)])
    frame_sides = row([(x0, x0 + border), (x1 - border, x1)])
    stand = row([(sx0, sx1)])
    rows = []
    for y in range(height):
        if y0 <= y < y0 + border or y1 - border <= y < y1:
            rows.append(frame_edge)
        elif y0 <= y < y1:
            rows.append(frame_sides)
        elif y1 + border <= y < y1 + border * 2:
            rows.append(stand)
        else:
            rows.append(blank)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
    )


def _copy_tree(src: Traversable, dest: Path, subs: dict[str, str], app_path: str) -> list[Path]:
    written = []
    for entry in src.iterdir():
        name = RENAMES.get(entry.name, entry.name)
        if name == "__APP_PATH__":
            target = dest.joinpath(*app_path.split("/"))
        else:
            target = dest / name
        if entry.is_dir():
            written += _copy_tree(entry, target, subs, app_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        data = entry.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            target.write_bytes(data)
        else:
            for key, value in subs.items():
                text = text.replace(key, value)
            target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    return written


def create(template: str, name: str, dest: Path, app_id: str | None = None, force: bool = False) -> Path:
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Choose from: {', '.join(TEMPLATES)}")
    tpl = TEMPLATES[template]
    app_id = app_id or default_app_id(name)
    if not APP_ID_RE.match(app_id):
        raise ValueError(f"App id '{app_id}' must look like com.example.myapp (lowercase, dot separated).")
    if dest.exists() and any(dest.iterdir()) and not force:
        raise FileExistsError(f"{dest} already exists and is not empty (use --force to write into it).")
    dest.mkdir(parents=True, exist_ok=True)

    subs = {"{{APP_NAME}}": name, "{{APP_ID}}": app_id, "{{APP_SLUG}}": slugify(name)}
    root = resources.files("vibetv").joinpath("templates")
    for folder, sub in tpl.parts:
        _copy_tree(root.joinpath(folder), dest / sub if sub else dest, subs, app_id.replace(".", "/"))

    for rel, (w, h) in tpl.images.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png(w, h))

    agents = root.joinpath("agents")
    text = agents.joinpath("common.md").read_text(encoding="utf-8") + agents.joinpath(f"{template}.md").read_text(encoding="utf-8")
    for key, value in subs.items():
        text = text.replace(key, value)
    (dest / "AGENTS.md").write_text(text, encoding="utf-8", newline="\n")
    # Claude Code reads CLAUDE.md; the @ import keeps a single source of truth.
    (dest / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8", newline="\n")

    project = {"template": template, "name": name, "app_id": app_id, "platform": tpl.platform, "web_root": tpl.web_root}
    (dest / "vibetv.json").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8", newline="\n")
    return dest
