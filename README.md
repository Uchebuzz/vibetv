<div align="center">

# 📺 vibetv

**Vibecode your TV.**

Use your AI coding agent to build a custom home screen, screensaver, dashboard or app for your
TV, and watch it update on the big screen every time you save.

Android TV · Google TV · Fire TV · Roku · LG webOS

[![CI](https://github.com/Uchebuzz/vibetv/actions/workflows/ci.yml/badge.svg)](https://github.com/Uchebuzz/vibetv/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

Everyone is vibecoding. But point an AI agent at a TV and it's blind: it can't see the
screen, can't press the remote, and doesn't know a D-pad from a mouse. **vibetv closes that loop.**

```
 you: "make my home screen show my apps as big cards, with the weather and a clock"
  │
  ▼
 AI agent edits web/app.js ──► vibetv serve live-reloads it on the TV
  ▲                                         │
  └── vibetv screenshot / tv_screenshot ◄───┘   (the agent *sees* the result)
```

## What you get

| | |
|---|---|
| 🔎 **Find your TV** | `vibetv discover` finds Android/Google/Fire TV, Roku, LG and Samsung TVs on your Wi-Fi |
| 🧱 **Scaffold** | `vibetv new android-tv "My Home"` gives you a TV-ready project with D-pad navigation, overscan-safe layout, and an `AGENTS.md` that teaches your AI the 10-foot UI rules |
| ⚡ **Live reload on the TV** | `vibetv serve --open`: save a file and the TV updates in about a second |
| 👀 **Eyes + hands for your agent** | `vibetv screenshot`, `vibetv key down down ok`, `vibetv logs` (the TV's `console.log` and JS errors in your terminal) |
| 🤖 **MCP server** | `vibetv mcp` gives Claude Code, Cursor, Codex and friends `tv_screenshot`, `tv_key`, `tv_logs`, `tv_deploy` and more |
| 🏠 **Custom launcher** | Turn your app into the TV's Home screen. The bridge lists and launches every installed app |
| 🌙 **Custom screensaver** | The same web app runs as an Android TV screensaver (Daydream) |
| 🎛️ **Reversible tweaks** | `vibetv tweak apply snappy-animations`. Every change is recorded and `vibetv tweak revert` restores the original |
| 🚀 **One-command deploy** | `vibetv deploy` builds and installs the APK (Android), sideloads the channel (Roku), or packages and installs it (webOS) |
| 🪶 **Zero dependencies** | Pure Python standard library. Nothing to break |

## Quick start (5 minutes)

**1. Install**

```bash
# with uv (recommended)
uv tool install git+https://github.com/Uchebuzz/vibetv
# or pipx
pipx install git+https://github.com/Uchebuzz/vibetv
```

For Android TV / Google TV / Fire TV you also need `adb`:
`winget install Google.PlatformTools` · `brew install android-platform-tools` · `sudo apt install adb`

**2. Put your TV in developer mode** ([full guide](docs/platforms.md))

- **Android TV / Google TV:** Settings → System → About → click *Build* 7 times → Developer options → turn on *USB debugging* / *Network debugging*
- **Fire TV:** Settings → My Fire TV → About → click the device name 7 times → Developer options → *ADB debugging* on
- **Roku:** on the remote press `Home ×3, Up ×2, Right, Left, Right, Left, Right` and set a password

**3. Connect**

```bash
vibetv doctor                 # checks your setup
vibetv discover               # finds TVs on your network
vibetv add 192.168.1.42       # Android: accept the prompt on the TV
vibetv add 192.168.1.50 --password <roku-dev-password>   # Roku
vibetv screenshot             # 🎉 saved tv-screenshot.png
```

**4. Vibecode**

```bash
vibetv new android-tv "Living Room"
cd living-room
vibetv deploy                 # installs the app once (or grab the APK GitHub Actions builds for you)
vibetv serve --open           # live-reload from now on
```

Now open your AI agent in that folder and ask for what you want:

> *"Turn this into my home screen: big cards for my installed apps sorted by most used, a
> weather widget for Lagos, and a dark theme. Check it on the TV when you're done."*

The project's `AGENTS.md` / `CLAUDE.md` tells the agent how to screenshot the TV, press keys,
read logs and follow TV UI rules, so it can check its own work.

## Give your agent superpowers (MCP)

```bash
# Claude Code
claude mcp add vibetv -- vibetv mcp
```

```jsonc
// Cursor, Windsurf, Claude Desktop, ... (mcpServers config)
{ "mcpServers": { "vibetv": { "command": "vibetv", "args": ["mcp"] } } }
```

| Tool | What it does |
|---|---|
| `tv_screenshot` | Returns the TV screen as an image the model can see |
| `tv_key` / `tv_type` | Press remote buttons / type text |
| `tv_logs` | Console output and JS errors from the app on the TV |
| `tv_deploy` | Build and install a project |
| `tv_open_url` | Open a URL in the TV browser or your app |
| `tv_apps` / `tv_launch` / `tv_info` | Inspect the TV and launch apps |
| `tv_discover` / `tv_devices` | Find and list TVs |
| `tv_tweak_list` / `tv_tweak_apply` / `tv_tweak_revert` | Reversible system tweaks |

## Templates

```bash
vibetv templates
```

| Template | Runs on | What it is |
|---|---|---|
| `android-tv` | Android TV, Google TV, Fire TV, NVIDIA Shield, most smart TVs/projectors running Android | Web UI (`web/`) in a native Kotlin shell, plus a JS bridge (installed apps, launch, settings), a custom launcher, a screensaver, and a GitHub Actions workflow that builds the APK |
| `roku` | Roku TV, Roku sticks | SceneGraph + BrightScript channel with a RowList home screen, sideloaded over Wi-Fi |
| `webos` | LG TVs | Web app with `appinfo.json`, deployed with LG's `ares` CLI |
| `web` | Any TV browser | The bare 10-foot web app: D-pad spatial navigation, overscan-safe 1080p stage, live reload |

No Android SDK? You don't need one. Push your project to GitHub and the included workflow builds
the APK. Download it from the run's artifacts, then run `vibetv install app-debug.apk`.

## Recipes

```bash
# Make your vibecoded app the Home screen (reversible)
#   1. uncomment the HOME intent-filter in app/src/main/AndroidManifest.xml, redeploy
vibetv launcher set com.vibetv.livingroom
vibetv tweak revert custom-launcher        # back to stock

# Use your app as the screensaver
vibetv screensaver set com.vibetv.livingroom/.WebDreamService --preview

# Speed up a sluggish TV box
vibetv tweak apply snappy-animations

# Drive the TV from a script
vibetv key home right right ok
vibetv type "lofi beats"
vibetv launch com.google.android.youtube.tv
```

More prompts to paste into your agent: [prompts/](prompts/README.md).

## All commands

```
vibetv doctor | discover [--scan] | add <ip> | devices | use <name> | remove <name> | info
vibetv key <keys...> | type <text> | screenshot [file] | apps | launch <app> | install <apk> | open <url>
vibetv templates | new <template> <name> | serve [--open] | logs [-f] | deploy
vibetv tweak list|show|apply|revert <preset> | launcher set <pkg> | screensaver show|set <component>
vibetv mcp
```

Every device command takes `-d <name-or-ip>` to target a specific TV.

## Safety

- vibetv **never uninstalls** system apps. It uses `pm disable-user`, which is fully reversible.
- Every tweak records the previous value in `~/.vibetv/undo.json`, and `vibetv tweak revert` puts it back.
- Presets are labelled `safe`, `moderate` or `advanced`, and non-safe ones ask before applying.
- Developer-mode passwords are stored locally in `~/.vibetv/config.json`, never in your project.
- Turn developer/network debugging **off** when you're done if your network isn't trusted.

## Platform support

| | Discover | Screenshot | Keys | Live reload | Deploy | Tweaks |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Android TV / Google TV | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fire TV | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Roku | ✅ | ✅ (dev channel) | ✅ | n/a | ✅ | n/a |
| LG webOS | ✅ | ✅ | 🚧 | ✅ (browser) | ✅ | 🚧 |
| Samsung Tizen | ✅ | 🚧 | 🚧 | ✅ (browser) | 🚧 | 🚧 |

🚧 = help wanted! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

PRs are very welcome, especially new **tweak presets** (just a JSON file), **templates**, **prompts**, and
**Tizen/webOS** support. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
