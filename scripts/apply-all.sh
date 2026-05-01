#!/usr/bin/env bash
# Apply the canonical MCP server list to all three CLIs.
# Pre-flight: warns if .env is missing or has empty required vars.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVFILE="${REPO_ROOT}/.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "error: ${ENVFILE} not found" >&2
  echo "       cp .env.example .env  &&  edit values  &&  re-run this script" >&2
  exit 1
fi

echo "==> applying to Claude Code"
"${REPO_ROOT}/scripts/apply-claude.sh"
echo
echo "==> applying to Gemini CLI"
"${REPO_ROOT}/scripts/apply-gemini.sh"
echo
echo "==> applying to Codex CLI"
"${REPO_ROOT}/scripts/apply-codex.sh"
echo
echo "done. restart any running CLI sessions to pick up the new MCP servers."
