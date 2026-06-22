#!/usr/bin/env bash
# Render the canonical MCP server list into Gemini CLI's config.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.gemini/settings.json"

# Pick a working python interpreter. On Windows the bare names `python` /
# `python3` are often Microsoft Store stubs that resolve via PATH but exit
# non-zero when invoked, so validate each candidate by actually running it.
if command -v py >/dev/null 2>&1 && py -3 --version >/dev/null 2>&1; then
  PY=(py -3)
elif command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
  PY=(python3)
elif command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
  PY=(python)
else
  echo "no working python interpreter on PATH" >&2
  exit 1
fi

if [[ -f "$TARGET" ]]; then
  backup="${TARGET}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$TARGET" "$backup"
  echo "backed up existing config to $backup"
fi

"${PY[@]}" "${REPO_ROOT}/scripts/render.py" gemini \
  --in "${REPO_ROOT}/servers.json" \
  --env "${REPO_ROOT}/.env" \
  --out "$TARGET"
