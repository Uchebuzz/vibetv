# Tweak presets

A tweak preset is a small JSON file describing reversible changes to an Android-based TV.
vibetv records the original value before every change, so `vibetv tweak revert <id>` puts
things back exactly as they were.

```bash
vibetv tweak list                       # what's available and what's applied
vibetv tweak show snappy-animations     # what it will do
vibetv tweak apply snappy-animations    # do it
vibetv tweak revert snappy-animations   # undo it
```

## Writing a preset

Put the file in `~/.vibetv/presets/` for personal use, or in
[`src/vibetv/presets/`](../src/vibetv/presets) to contribute it.

```json
{
  "id": "my-preset",
  "title": "Short name",
  "description": "What it does and what the user will notice. Mention side effects.",
  "platforms": ["android"],
  "risk": "safe",
  "steps": [
    {"setting": "global", "key": "window_animation_scale", "value": "0.5"},
    {"package": "com.example.preinstalled.bloat", "enabled": false}
  ]
}
```

### Step types

| Step | Effect | Undo |
|---|---|---|
| `{"setting": "global" \| "secure" \| "system", "key": "...", "value": "..."}` | `settings put` | restores the old value, or deletes the key if it didn't exist |
| `{"package": "...", "enabled": false}` | `pm disable-user --user 0` | `pm enable` |
| `{"package": "...", "enabled": true}` | `pm enable` | restores the previous state |

Packages that aren't installed are skipped, so one preset can cover several brands.

### Risk levels

- **safe**: cosmetic or performance changes, nothing disappears.
- **moderate**: hides or disables a feature (e.g. recommendations, a stock launcher). vibetv asks before applying.
- **advanced**: could break something the user relies on (e.g. disabling an updater). Explain why in the description.

### Rules for contributed presets

1. **Never uninstall**: only `enabled: false`. That's what keeps everything reversible.
2. Test on a real device and say which one in your PR (brand, model, OS version).
3. Don't disable anything required to boot, reach Settings, or connect to the network.
4. No telemetry or ad-blocking claims you can't back up. Describe what you observed.
