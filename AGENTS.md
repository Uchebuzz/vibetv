# AGENTS.md

Guidance for AI coding agents working on the **vibetv** repo itself (not on projects it generates;
those get their own AGENTS.md from `src/vibetv/templates/agents/`).

- Pure standard-library Python 3.10+. **Do not add runtime dependencies.**
- Run tests with `uv run pytest` (or `python -m pytest`). Tests must never need a real TV or touch `~/.vibetv`
  (the `isolated_home` fixture handles that).
- `tv.py` is the single cross-platform API; the CLI (`cli.py`) and MCP server (`mcp.py`) both call into it.
  New device features go in the platform module (`adb.py`, `roku.py`, `webos.py`) and are exposed via `tv.py`.
- The MCP server writes JSON-RPC to stdout. Never `print()` to stdout from code reachable by `mcp.py`; use stderr.
- Every change to a TV must be reversible (see `tweaks.py`). Never add `pm uninstall` of system packages.
- Template files use `{{APP_NAME}}`, `{{APP_ID}}`, `{{APP_SLUG}}` placeholders, `__APP_PATH__` for the Kotlin
  package directory, and `_github` / `_gitignore` for dotfiles (renamed on scaffold).
- Keep files LF-only (`.gitattributes` enforces it).
