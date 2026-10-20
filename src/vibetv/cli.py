"""vibetv command line."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from . import __version__, adb, config, devserver, discover, roku, scaffold, tv, tweaks


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def ok(msg: str) -> None:
    print(f"[ok] {msg}")


def _device(args) -> config.Device:
    return config.get_device(getattr(args, "device", None))


def _android_serial(args) -> str:
    device = _device(args)
    if device.platform != "android":
        die(f"'{device.name}' is a {device.platform} device; this command is Android TV / Google TV / Fire TV only.")
    adb.ensure_connected(device.adb_serial)
    return device.adb_serial


# ------------------------------------------------------------------ devices


def cmd_discover(args) -> None:
    print("Searching the network for TVs (SSDP + port probe)...")
    found = discover.discover(timeout=args.timeout, scan_subnet=args.scan)
    if not found:
        print("No TVs found. Make sure the TV is on and on the same Wi-Fi, or try `vibetv discover --scan`.")
        return
    for t in found:
        label = " ".join(x for x in (t.manufacturer, t.model) if x) or "unknown device"
        ports = ", ".join(f"{p} ({discover.PORTS[p][1]})" for p in t.open_ports) or "no control ports open"
        print(f"\n  {t.host:<16} {t.name or label}")
        print(f"  {'':<16} platform: {t.platform}   {label}")
        print(f"  {'':<16} ports: {ports}")
        if t.platform == "android" and 5555 not in t.open_ports:
            print(f"  {'':<16} -> enable Developer options > Network debugging, then: vibetv add {t.host}")
        elif t.platform == "tizen":
            print(f"  {'':<16} -> Samsung Tizen: see docs/platforms.md (limited support)")
        elif t.platform != "unknown":
            print(f"  {'':<16} -> vibetv add {t.host} --platform {t.platform}")


def cmd_add(args) -> None:
    platform = args.platform
    if not platform:
        if discover.port_open(args.host, 5555):
            platform = "android"
        elif discover.port_open(args.host, 8060):
            platform = "roku"
        else:
            die("Couldn't detect the platform (no ADB on 5555, no Roku ECP on 8060). Pass --platform.")
    extra = {}
    if platform == "android":
        serial = f"{args.host}:{args.port or 5555}"
        print(f"Connecting to {serial} - accept the 'Allow debugging?' prompt on the TV if it appears...")
        adb.connect(serial)
        for _ in range(30):  # wait for the on-screen authorisation
            try:
                adb.ensure_connected(serial)
                break
            except adb.AdbError:
                time.sleep(1)
        info = adb.device_info(serial)
        name = args.name or f"{info.get('manufacturer', '')} {info.get('model', '')}".strip() or args.host
    elif platform == "roku":
        info = roku.device_info(args.host)
        name = args.name or info.get("friendly-device-name") or args.host
        if args.password:
            extra["dev_password"] = args.password
        if info.get("developer-enabled") != "true":
            print("note: developer mode is off. On the remote press Home x3, Up x2, Right, Left, Right, Left, Right.")
    elif platform == "webos":
        name = args.name or args.ares_device or args.host
        extra["ares_device"] = args.ares_device or name
    else:
        die(f"Platform must be one of {', '.join(config.PLATFORMS)}")
    name = name.replace(" ", "-").lower()
    device = config.Device(name=name, host=args.host, platform=platform, port=args.port, extra=extra)
    config.save_device(device, make_default=not args.no_default)
    ok(f"Saved '{name}' ({platform} @ {args.host}){'' if args.no_default else ' as the default device'}")


def cmd_devices(args) -> None:
    devices = config.load_devices()
    if not devices:
        print("No saved devices. Run `vibetv discover` then `vibetv add <ip>`.")
        return
    try:
        default = config.get_device().name
    except LookupError:
        default = None
    for d in devices.values():
        star = "*" if d.name == default else " "
        print(f" {star} {d.name:<24} {d.platform:<8} {d.host}")


def cmd_use(args) -> None:
    device = config.get_device(args.name)
    config.save_device(device, make_default=True)
    ok(f"Default device is now '{device.name}'")


def cmd_remove(args) -> None:
    if not config.remove_device(args.name):
        die(f"No device named '{args.name}'")
    ok(f"Removed '{args.name}'")


def cmd_info(args) -> None:
    for k, v in tv.info(_device(args)).items():
        print(f"{k:>22}: {v}")


# ------------------------------------------------------------------ control


def cmd_key(args) -> None:
    device = _device(args)
    for key in args.keys:
        tv.keypress(device, key, times=args.repeat)
        time.sleep(args.delay)


def cmd_type(args) -> None:
    tv.type_text(_device(args), args.text)


def cmd_screenshot(args) -> None:
    data, mime = tv.screenshot(_device(args))
    out = Path(args.output)
    if mime == "image/jpeg" and out.suffix.lower() == ".png":
        out = out.with_suffix(".jpg")
    out.write_bytes(data)
    ok(f"Saved {out.resolve()}")


def cmd_apps(args) -> None:
    for app in tv.apps(_device(args), third_party=not args.all):
        print(app)


def cmd_launch(args) -> None:
    tv.launch(_device(args), args.app)


def cmd_install(args) -> None:
    serial = _android_serial(args)
    print(adb.install(serial, Path(args.apk)))


def cmd_open(args) -> None:
    tv.open_url(_device(args), args.url, args.package)


# ------------------------------------------------------------------ projects


def cmd_templates(args) -> None:
    for t in scaffold.TEMPLATES.values():
        print(f"  {t.name:<12} {t.description}")


def cmd_new(args) -> None:
    dest = Path(args.dir or scaffold.slugify(args.name))
    path = scaffold.create(args.template, args.name, dest, app_id=args.app_id, force=args.force)
    ok(f"Created {args.template} project in {path.resolve()}")
    print("\nNext steps:")
    print(f"  cd {dest}")
    if args.template == "android-tv":
        print("  vibetv deploy            # build + install the app (or use the GitHub Actions APK)")
        print("  vibetv serve --open      # live-reload web/ on the TV while you vibecode")
    elif args.template == "roku":
        print("  vibetv deploy            # sideload to your Roku (developer mode)")
    elif args.template == "webos":
        print("  vibetv serve --open      # live preview in the TV browser")
        print("  vibetv deploy            # package + install with ares-cli")
    else:
        print("  vibetv serve             # open the URL in any browser, or --open to push to the TV")
    print("\nThen open your AI coding agent here - AGENTS.md / CLAUDE.md tell it how to drive the TV.")


def cmd_serve(args) -> None:
    folder = Path(args.dir).resolve()
    package = None
    try:
        root, project = tv.load_project(folder)
        folder = root / (project.get("web_root") or ".")
        if project["template"] == "android-tv":
            package = project["app_id"]
        if project["template"] == "roku":
            die("Roku channels aren't web apps - use `vibetv deploy` instead.")
    except tv.TVError:
        pass
    ip = discover.local_ip() or "127.0.0.1"
    server = devserver.make_server(folder, port=args.port, quiet=args.quiet)
    url = f"http://{ip}:{server.server_address[1]}/"
    devserver.record_running(url)
    print(f"Serving {folder}\n  on your network: {url}\n  live reload: on   TV console logs: shown below\n")
    if args.open:
        device = _device(args)
        try:
            tv.open_url(device, url, package)
            ok(f"Opened on {device.name}" + (f" in {package}" if package else ""))
        except Exception as e:  # keep serving even if the TV couldn't be reached
            print(f"warning: couldn't open on TV: {e}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def cmd_logs(args) -> None:
    url = devserver.running_url()
    if not url:
        die("No dev server found. Run `vibetv serve` first.")
    seen = 0
    while True:
        try:
            with urllib.request.urlopen(f"{url}__vibetv/logs", timeout=3) as resp:
                lines = json.loads(resp.read())
        except OSError:
            die(f"Dev server at {url} isn't responding.")
        new = lines[seen:] if args.follow and seen else lines[-args.lines:]
        for line in new:
            print(line)
        seen = len(lines)
        if not args.follow:
            return
        time.sleep(1)


def cmd_deploy(args) -> None:
    device = _device(args)
    print(f"Deploying to {device.name} ({device.platform})...")
    ok(tv.deploy(device, Path(args.dir).resolve()))


# ------------------------------------------------------------------ tweaks


def cmd_tweak(args) -> None:
    presets = tweaks.load_presets()
    if args.action == "list":
        applied = set()
        try:
            applied = set(tweaks.applied(_device(args).adb_serial))
        except LookupError:
            pass
        for p in presets.values():
            mark = "[applied]" if p.id in applied else ""
            print(f"  {p.id:<26} {p.risk:<9} {p.title} {mark}")
            print(f"  {'':<26} {'':<9} {p.description}")
        print("\nAdd your own: drop a JSON preset in ~/.vibetv/presets/ (see docs/tweaks.md)")
        return
    if not args.preset:
        die("Which preset? See `vibetv tweak list`.")
    if args.action == "revert":
        for line in tweaks.revert(_android_serial(args), args.preset):
            ok(line)
        return
    if args.preset not in presets:
        die(f"Unknown preset '{args.preset}'. See `vibetv tweak list`.")
    _apply(args, presets[args.preset])


def _apply(args, preset: tweaks.Preset) -> None:
    print(f"{preset.title} [{preset.risk}]\n{preset.description}\n")
    for line in tweaks.plan(preset):
        print(f"  - {line}")
    if args.action == "show" or getattr(args, "dry_run", False):
        return
    if preset.risk != "safe" and not args.yes:
        if input(f"\nThis preset is '{preset.risk}' risk (fully reversible). Apply? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return
    for line in tweaks.apply(_android_serial(args), preset):
        ok(line)
    print(f"\nUndo any time with: vibetv tweak revert {preset.id}")


def cmd_launcher(args) -> None:
    serial = _android_serial(args)
    args.action = "apply"
    _apply(args, tweaks.custom_launcher_preset(serial, args.package))
    adb.keypress(serial, "home")


def cmd_screensaver(args) -> None:
    serial = _android_serial(args)
    if args.action == "show":
        print(adb.get_setting(serial, "secure", "screensaver_components") or "(system default)")
        return
    if not args.component:
        die("Give a component, e.g. com.vibetv.myapp/.WebDreamService")
    args.action = "apply"
    _apply(args, tweaks.screensaver_preset(args.component))
    if args.preview:
        adb.shell(serial, "am start -n com.android.systemui/.Somnambulator", check=False)


# ------------------------------------------------------------------ misc


def cmd_doctor(args) -> None:
    checks = [
        ("adb", "Android TV / Google TV / Fire TV control", "https://developer.android.com/tools/releases/platform-tools"),
        ("java", "Building Android TV apps locally (JDK 17)", "https://adoptium.net"),
        ("gradle", "Building Android TV apps locally (or use the GitHub Actions workflow)", "https://gradle.org/install/"),
        ("ares-package", "LG webOS packaging", "npm install -g @webos-tools/cli"),
        ("node", "Optional: JS tooling", "https://nodejs.org"),
    ]
    print(f"vibetv {__version__}  python {sys.version.split()[0]}  config: {config.home()}\n")
    for exe, why, how in checks:
        path = shutil.which(exe)
        print(f"  {'[ok]' if path else '[--]'} {exe:<13} {why}" + ("" if path else f"\n{'':>20}install: {how}"))
    print(f"\n  LAN address: {discover.local_ip() or 'unknown'}")
    devices = config.load_devices()
    print(f"  Saved TVs:   {', '.join(devices) or 'none (run vibetv discover)'}")


def cmd_mcp(args) -> None:
    from . import mcp

    mcp.serve()


def build_parser() -> argparse.ArgumentParser:
    dev = argparse.ArgumentParser(add_help=False)
    dev.add_argument("-d", "--device", help="saved device name or IP (default: the default device)")

    p = argparse.ArgumentParser(prog="vibetv", description="Vibecode your TV.")
    p.add_argument("--version", action="version", version=f"vibetv {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="<command>")

    def add(name, func, help, parents=(dev,)):
        sp = sub.add_parser(name, help=help, description=help, parents=list(parents))
        sp.set_defaults(func=func)
        return sp

    s = add("doctor", cmd_doctor, "check your setup", parents=())
    s = add("discover", cmd_discover, "find TVs on your network", parents=())
    s.add_argument("--scan", action="store_true", help="also probe every address on your /24 subnet")
    s.add_argument("--timeout", type=float, default=3.0)
    s = add("add", cmd_add, "save a TV (auto-detects Android/Roku)", parents=())
    s.add_argument("host")
    s.add_argument("--name")
    s.add_argument("--platform", choices=config.PLATFORMS)
    s.add_argument("--port", type=int)
    s.add_argument("--password", help="Roku developer-mode password")
    s.add_argument("--ares-device", help="webOS device name registered with ares-setup-device")
    s.add_argument("--no-default", action="store_true", help="don't make this the default device")
    add("devices", cmd_devices, "list saved TVs", parents=())
    s = add("use", cmd_use, "set the default TV", parents=())
    s.add_argument("name")
    s = add("remove", cmd_remove, "forget a saved TV", parents=())
    s.add_argument("name")
    add("info", cmd_info, "show TV model / OS / resolution")

    s = add("key", cmd_key, "press remote keys: vibetv key down down ok")
    s.add_argument("keys", nargs="+")
    s.add_argument("--repeat", type=int, default=1, help="press each key N times")
    s.add_argument("--delay", type=float, default=0.15, help="seconds between keys")
    s = add("type", cmd_type, "type text on the TV")
    s.add_argument("text")
    s = add("screenshot", cmd_screenshot, "save a screenshot of the TV")
    s.add_argument("output", nargs="?", default="tv-screenshot.png")
    s = add("apps", cmd_apps, "list installed apps")
    s.add_argument("--all", action="store_true", help="include system apps (Android)")
    s = add("launch", cmd_launch, "launch an app (package name or Roku channel id)")
    s.add_argument("app")
    s = add("install", cmd_install, "install an APK (Android)")
    s.add_argument("apk")
    s = add("open", cmd_open, "open a URL on the TV")
    s.add_argument("url")
    s.add_argument("--package", help="open inside a vibetv Android app instead of the browser")

    add("templates", cmd_templates, "list project templates", parents=())
    s = add("new", cmd_new, "create a TV project", parents=())
    s.add_argument("template", choices=list(scaffold.TEMPLATES))
    s.add_argument("name")
    s.add_argument("--dir", help="output folder (default: slug of name)")
    s.add_argument("--app-id", help="package / app id, e.g. com.you.myapp")
    s.add_argument("--force", action="store_true")
    s = add("serve", cmd_serve, "LAN dev server with live reload + TV console logs")
    s.add_argument("dir", nargs="?", default=".")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--open", action="store_true", help="open it on the TV")
    s.add_argument("--quiet", action="store_true", help="don't print TV logs")
    s = add("logs", cmd_logs, "show console output from the TV (needs `vibetv serve`)", parents=())
    s.add_argument("-n", "--lines", type=int, default=100)
    s.add_argument("-f", "--follow", action="store_true")
    s = add("deploy", cmd_deploy, "build + install the project in this folder")
    s.add_argument("dir", nargs="?", default=".")

    s = add("tweak", cmd_tweak, "reversible Android TV tweaks: list | show | apply | revert")
    s.add_argument("action", choices=["list", "show", "apply", "revert"])
    s.add_argument("preset", nargs="?")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("-y", "--yes", action="store_true", help="don't ask before moderate/advanced presets")
    s = add("launcher", cmd_launcher, "make an installed app your Home screen (Android, reversible)")
    s.add_argument("action", choices=["set"])
    s.add_argument("package")
    s.add_argument("-y", "--yes", action="store_true")
    s = add("screensaver", cmd_screensaver, "show or set the screensaver (Android)")
    s.add_argument("action", choices=["show", "set"])
    s.add_argument("component", nargs="?")
    s.add_argument("--preview", action="store_true", help="start it right away")
    s.add_argument("-y", "--yes", action="store_true")

    add("mcp", cmd_mcp, "run the MCP server (for Claude Code, Cursor, ...)", parents=())
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (LookupError, adb.AdbError, roku.RokuError, tv.TVError, ValueError, FileExistsError) as e:
        die(str(e).strip("'\""))
    except KeyboardInterrupt:
        sys.exit(130)
