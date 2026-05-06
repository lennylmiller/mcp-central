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

## Architecture

- **`servers.json`** — Canonical server list. Each entry has `transport`, `command`, `args`, and optional `env` with `${VAR}` placeholders. This is the only file to edit when adding/removing servers.
- **`scripts/render.py`** — Core logic. Contains per-CLI render functions (`render_claude`, `render_gemini`, `render_codex`) that transform `servers.json` into each format. Handles `${VAR}` substitution, JSON merge into existing config files, and TOML section replacement for Codex. Supports `stdio`, `url`, and `http` transports.
- **`scripts/apply-*.sh`** — Thin wrappers that back up existing config, then call `render.py` with the right paths. `apply-all.sh` runs all three sequentially.
- **`scripts/discover.sh`** — Read-only audit of MCP servers across all CLIs and per-project `.mcp.json` files under `~/code`.

## Important Design Decisions

- **All values are inlined** — Even though only Codex requires literal values (no `${VAR}` expansion in TOML), render.py inlines secrets for all CLIs for consistency.
- **Merge, don't clobber** — `render.py` merges the `mcpServers` key into existing Claude/Gemini JSON configs and replaces only `[mcp_servers.*]` sections in Codex TOML, preserving unrelated keys/sections.
- **No absolute paths in `servers.json`** — Keeps configs portable across macOS and WSL.
- **This repo only manages cross-CLI servers** — CLI-specific or project-local servers belong in their respective configs (e.g., `~/.claude.json` directly, or a project's `.mcp.json`).

## Requirements

Python 3.11+, `jq`, `npx`/Node, `uvx`/uv.
