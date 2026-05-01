#!/usr/bin/env bash
# Render the canonical MCP server list into Claude Code's config.
# Backs up the existing ~/.claude.json before writing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.claude.json"

if [[ -f "$TARGET" ]]; then
  backup="${TARGET}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$TARGET" "$backup"
  echo "backed up existing config to $backup"
fi

python3 "${REPO_ROOT}/scripts/render.py" claude \
  --in "${REPO_ROOT}/servers.json" \
  --env "${REPO_ROOT}/.env" \
  --out "$TARGET"
