# Platform setup

One-time setup per TV. After this, `vibetv add <ip>` and everything else just works.

## Android TV / Google TV (Chromecast with Google TV, Sony, TCL, Hisense, Philips, Shield, projectors)

1. **Settings → System → About** (on some TVs: *Settings → Device Preferences → About*).
2. Scroll to **Android TV OS build** and press OK on it **7 times** until it says you're a developer.
3. Back to **Settings → System → Developer options**:
   - turn on **USB debugging**
   - turn on **Network debugging** / **ADB over network**, if your TV has it
4. Find the TV's IP: *Settings → Network & Internet → (your Wi-Fi)*.
5. `vibetv add <ip>` and pick **Allow** (tick *Always allow*) on the prompt that appears on the TV.

> **Android 11+ "Wireless debugging" (pairing code):** some newer TVs only offer this. Run
> `adb pair <ip>:<pair-port>` with the code shown on the TV, then `vibetv add <ip> --port <port>` using
> the port shown under *Wireless debugging*.

## Amazon Fire TV (Stick, Cube, Fire TV Edition TVs)

1. **Settings → My Fire TV → About** and press OK on your device name **7 times**.
2. **Settings → My Fire TV → Developer options** → **ADB debugging: ON**. Also allow
   **Apps from Unknown Sources** if you want to install your own APKs.
3. IP: *Settings → My Fire TV → About → Network*.
4. `vibetv add <ip>` and accept the prompt.

## Roku (Roku TVs, Streaming Sticks, Express, Ultra)

1. On the Roku remote press: **Home ×3, Up ×2, Right, Left, Right, Left, Right**.
2. Accept the developer agreement, set a **dev password**, and note the IP shown.
3. `vibetv add <ip> --password <dev-password>`

Notes:
- Only one sideloaded "dev" channel can be installed at a time; `vibetv deploy` replaces it.
- Screenshots only capture the dev channel, not other apps or the home screen (Roku limitation).
- Debug output: `telnet <ip> 8085`.
- Keys/launch work on any Roku with *Settings → System → Advanced → Control by mobile apps* enabled (the default).

## LG webOS

1. Install **Developer Mode** from the LG Content Store and sign in with a free
   [LG developer account](https://webostv.developer.lge.com/).
2. Turn on **Dev Mode Status** and **Key Server**, then restart when asked.
3. On your computer: `npm install -g @webos-tools/cli`
4. `ares-setup-device` and add the TV (name it e.g. `lgtv`, IP from Developer Mode app, port 9922, user `prisoner`).
5. `ares-novacom --device lgtv --getkey` and enter the passphrase shown in the Developer Mode app.
6. `vibetv add <ip> --platform webos --ares-device lgtv`

Developer Mode expires after 1000 hours; open the app and press *Extend*.

## Samsung Tizen (help wanted)

`vibetv discover` detects Samsung TVs, and `vibetv serve` works in the TV's built-in browser.
Installing apps needs Tizen Studio and a Samsung certificate. A guided flow for that is the
most-wanted contribution, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `vibetv discover` finds nothing | Same Wi-Fi? Guest networks and "AP isolation" block discovery. Try `--scan`, or `vibetv add <ip>` directly |
| `unauthorized` | Accept the prompt on the TV. If you missed it: Developer options → *Revoke USB debugging authorisations*, then `vibetv add` again |
| `connection refused` on 5555 | Network debugging is off, or the TV rebooted and turned it off. Some TVs need a USB cable once: `adb tcpip 5555` |
| Black screenshot | DRM-protected video (Netflix etc.) is blacked out by design |
| Live reload doesn't reach the TV | Firewall on your computer is blocking port 8765. Allow Python on private networks |
| Roku 401 | Wrong dev password. The username is always `rokudev` |
