#!/usr/bin/env bash
# Read-only audit of MCP servers across all three CLIs and ~/code projects.
# Use this when adding a new machine or when configs drift, to see what's
# actually configured locally vs. what servers.json declares.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq not found in PATH" >&2
  exit 1
fi

echo "=== Claude Code (global) ==="
if [[ -f "${HOME}/.claude.json" ]]; then
  jq -r '.mcpServers // {} | keys[]' "${HOME}/.claude.json" 2>/dev/null | sort -u || echo "(none)"
else
  echo "(no ~/.claude.json)"
fi

echo
echo "=== Claude Code (per-project .mcp.json files under ~/code) ==="
while IFS= read -r f; do
  servers=$(jq -r '.mcpServers // {} | keys | join(",")' "$f" 2>/dev/null)
  [[ -n "$servers" && "$servers" != "" ]] && echo "  $f: $servers"
done < <(find "${HOME}/code" -maxdepth 4 -type f -name ".mcp.json" 2>/dev/null)

echo
echo "=== Gemini CLI ==="
if [[ -f "${HOME}/.gemini/settings.json" ]]; then
  jq -r '.mcpServers // {} | keys[]' "${HOME}/.gemini/settings.json" 2>/dev/null | sort -u || echo "(none)"
else
  echo "(no ~/.gemini/settings.json)"
fi

echo
echo "=== Codex CLI ==="
if [[ -f "${HOME}/.codex/config.toml" ]]; then
  grep -E "^\[mcp_servers\." "${HOME}/.codex/config.toml" | sed -E 's/^\[mcp_servers\.([^]]+)\].*/\1/' | sort -u
else
  echo "(no ~/.codex/config.toml)"
fi
