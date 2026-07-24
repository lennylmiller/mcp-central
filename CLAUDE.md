# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Does

mcp-central is a single source of truth for MCP server configuration across Claude Code, Gemini CLI, and Codex CLI. One canonical list (`servers.json`) is rendered into each CLI's native config format by `scripts/render.py`. Secrets use `${VAR}` placeholders resolved from `.env` at apply time.

## Key Commands

```sh
# Apply MCP config to all three CLIs (requires .env to exist)
./scripts/apply-all.sh

# Preview rendered output without writing files
python3 scripts/render.py preview claude
python3 scripts/render.py preview gemini
python3 scripts/render.py preview codex

# Render to a specific CLI config
python3 scripts/render.py claude --in servers.json --env .env --out ~/.claude.json
python3 scripts/render.py gemini --in servers.json --env .env --out ~/.gemini/settings.json
python3 scripts/render.py codex  --in servers.json --env .env --out ~/.codex/config.toml

# Audit what MCP servers are configured locally vs. what servers.json declares
./scripts/discover.sh
```

There are no tests or linters in this repo; verify changes with `render.py preview <cli>` before applying.

## Adding a Server

1. Add the entry to `servers.json`.
2. If it needs a secret, use a `${VAR}` placeholder in its `env` block, add `VAR=` to `.env.example`, and add the real value to `.env`.
3. Run `./scripts/apply-all.sh`.
4. Restart running CLI sessions — CLIs read MCP config at startup only.

## Architecture

- **`servers.json`** — Canonical server list. Each entry has `transport`, `command`, `args`, and optional `env` with `${VAR}` placeholders. This is the only file to edit when adding/removing servers.
- **`scripts/render.py`** — Core logic. Contains per-CLI render functions (`render_claude`, `render_gemini`, `render_codex`) that transform `servers.json` into each format. Handles `${VAR}` substitution, JSON merge into existing config files, and TOML section replacement for Codex. Supports `stdio`, `url`, and `http` transports.
- **`scripts/apply-*.sh`** — Thin wrappers that back up the existing config (timestamped `.bak` next to the target), then call `render.py` with the right paths. `apply-all.sh` runs all three sequentially. Written to work on macOS, WSL, and Git Bash (they probe `py -3`/`python3`/`python` for a working interpreter).
- **`scripts/discover.sh`** — Read-only audit of MCP servers across all CLIs and per-project `.mcp.json` files under `~/code`.

## Important Design Decisions

- **All values are inlined** — Even though only Codex requires literal values (no `${VAR}` expansion in TOML), render.py inlines secrets for all CLIs for consistency.
- **Merge, don't clobber** — `render.py` merges per server entry: servers declared in `servers.json` are replaced in the target config; servers that exist only in the target (e.g. Claude-only ones like `backlog`) are preserved, as are unrelated keys/sections. Consequence: removing a server from `servers.json` does not remove it from the CLI configs — delete it there by hand.
- **Missing env vars are a warning, not an error** — `render.py` still writes the config, leaving literal `${VAR}` placeholders that will fail at runtime. Check stderr after applying.
- **No absolute paths in `servers.json`** — Keeps configs portable across macOS and WSL.
- **Env var names can be remapped per server** — e.g. the `magic` server's upstream env key is the generic `API_KEY`; `servers.json` maps the friendlier `TWENTYFIRST_API_KEY` from `.env` into it. Prefer descriptive names in `.env` and remap in the server's `env` block.
- **Transport support differs by CLI** — `render_gemini` distinguishes `url` vs `http` (rendered as `httpUrl`); `render_claude` handles only `url` and `stdio`; `render_codex` treats `url`/`http` the same and supports optional `bearer_token_env_var` for HTTP servers.
- **This repo only manages cross-CLI servers** — CLI-specific or project-local servers belong in their respective configs (e.g., `~/.claude.json` directly, or a project's `.mcp.json`).

## Requirements

Python 3.11+, `jq`, `npx`/Node, `uvx`/uv.
