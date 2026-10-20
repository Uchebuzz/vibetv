# Contributing to vibetv

Thanks for helping make TVs hackable! Contributions of every size are welcome.

## Easy first contributions

- **Tweak presets**: one JSON file in `src/vibetv/presets/`. See [docs/tweaks.md](docs/tweaks.md).
- **Prompts**: add a prompt that worked well to [prompts/README.md](prompts/README.md).
- **Device reports**: open an issue saying what worked or didn't on your TV (brand, model, OS version).
- **Docs**: setup steps for a TV brand we don't cover yet.

## Bigger ones (help wanted)

- Samsung Tizen: certificate + install flow, key control over the 8001/8002 websocket.
- LG webOS: key control and app launch via SSAP (port 3000/3001) without `ares`.
- New templates: e.g. a React/Preact web template, a Jetpack Compose for TV template.
- Roku: a `vibetv logs` equivalent that tails the 8085 debug console.

## Development

```bash
git clone https://github.com/Uchebuzz/vibetv && cd vibetv
uv venv && uv pip install -e . pytest     # or: python -m venv .venv && pip install -e . pytest
uv run pytest
```

Ground rules:

1. **Zero runtime dependencies.** vibetv uses only the Python standard library so it installs
   anywhere. Dev/test dependencies are fine.
2. **Reversible by default.** Anything that changes a TV must be undoable. Never uninstall
   system packages.
3. **Python 3.10+**, type hints, small functions. Match the style of the surrounding code.
4. **Tests** for anything that doesn't need a real TV (parsing, packaging, presets, scaffolding).
   Mock `adb` the way `tests/test_tweaks.py` does.
5. Templates must keep working with a D-pad only, and keep the overscan-safe layout.

## Project layout

```
src/vibetv/
  cli.py          command line
  mcp.py          MCP server (stdio JSON-RPC)
  tv.py           one API over all platforms (used by cli + mcp)
  adb.py          Android TV / Google TV / Fire TV
  roku.py         Roku ECP + dev sideloader
  webos.py        LG webOS via ares-cli
  discover.py     SSDP + port probing
  devserver.py    live reload + TV console forwarding
  scaffold.py     `vibetv new`
  tweaks.py       reversible preset engine
  presets/        built-in tweak presets (JSON)
  templates/      project templates + per-platform AGENTS.md fragments
```

## Pull requests

- Keep PRs focused; describe what you tested and on which device.
- CI runs the tests on Linux/macOS/Windows and builds the Android template APK.
