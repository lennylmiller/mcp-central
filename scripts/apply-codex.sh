#!/usr/bin/env bash
# Render the canonical MCP server list into Codex CLI's config.toml.
# Preserves [projects.*] and other top-level sections; only the
# [mcp_servers.*] blocks are replaced.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.codex/config.toml"

if [[ -f "$TARGET" ]]; then
  backup="${TARGET}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$TARGET" "$backup"
  echo "backed up existing config to $backup"
fi

python3 "${REPO_ROOT}/scripts/render.py" codex \
  --in "${REPO_ROOT}/servers.json" \
  --env "${REPO_ROOT}/.env" \
  --out "$TARGET"
