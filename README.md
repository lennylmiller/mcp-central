# mcp-central

Single source of truth for the MCP servers used across **Claude Code**, **Gemini CLI**, and **Codex CLI**, on macOS and Windows-WSL.

## Why

Three CLIs, three config formats, two machines. Without something like this, MCP servers drift, secrets get hand-copied, and adding a new server means editing three files in three formats.

This repo holds one canonical list (`servers.json`) and three small projector scripts that render it into the right shape for each CLI. Secrets live in a gitignored `.env` and are inlined at apply time.

## Layout

```
servers.json        Canonical MCP server list. Use ${VAR} for secrets.
.env.example        Template for required env vars (no values).
.env                Real values. Gitignored. Created by you.
scripts/
  render.py         YAML/JSON → CLI-specific format. The brain.
  apply-claude.sh   Renders to ~/.claude.json
  apply-gemini.sh   Renders to ~/.gemini/settings.json
  apply-codex.sh    Renders to ~/.codex/config.toml
  apply-all.sh      Runs all three.
  discover.sh       Read-only audit: what MCP servers does this machine have?
```

## First-time setup

### macOS

```sh
git clone <this-repo> ~/code/mcp-central
cd ~/code/mcp-central
cp .env.example .env
$EDITOR .env                       # fill in TWENTYFIRST_API_KEY, MORPH_API_KEY
./scripts/apply-all.sh
```

The Claude/Gemini/Codex CLIs need to be installed already; this repo only manages their MCP server config, not the CLIs themselves. Required system tools: `python3` (3.11+), `jq`, `npx`/Node, `uvx`/uv.

### Windows-WSL (Ubuntu/Debian)

Inside your WSL distro:

```sh
# one-time tooling, if not already present
sudo apt update && sudo apt install -y python3 jq curl
# install uv (gets you uvx)
curl -LsSf https://astral.sh/uv/install.sh | sh
# install Node + npx via nvm (recommended) or nodesource
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash
exec $SHELL && nvm install --lts

# the actual setup
git clone <this-repo> ~/code/mcp-central
cd ~/code/mcp-central
cp .env.example .env
nano .env                          # fill in real values
./scripts/apply-all.sh
```

WSL caveat: the apply scripts write to `$HOME/.claude.json`, `$HOME/.gemini/settings.json`, `$HOME/.codex/config.toml` — that's the **WSL** home, not Windows `C:\Users\<you>`. If you also run Claude/Gemini/Codex CLIs from PowerShell/cmd on the Windows side, you'll need a separate apply pass there (see "Cross-environment" below).

## Daily workflow

**Add a new MCP server:**
1. Edit `servers.json`, add the new entry.
2. If it needs a secret, add `${VAR_NAME}` to its `env` block, append `VAR_NAME=` to `.env.example`, and append the real value to `.env`.
3. Run `./scripts/apply-all.sh`.
4. Restart any running CLI sessions.

**Rotate a secret:**
1. Update the value in `.env`.
2. Run `./scripts/apply-all.sh`.

**Verify what's installed locally:**
```sh
./scripts/discover.sh
```

**Preview without writing:**
```sh
python3 scripts/render.py preview claude     # what would land in ~/.claude.json's mcpServers
python3 scripts/render.py preview gemini
python3 scripts/render.py preview codex
```

## Required env vars

See `.env.example` for the live list. As of the initial check-in:

| Variable | Used by | Where to get it |
|---|---|---|
| `TWENTYFIRST_API_KEY` | `magic` | https://21st.dev |
| `MORPH_API_KEY` | `morphllm-fast-apply` | https://morphllm.com |

The `magic` server's MCP env-var key is literally `API_KEY` (a generic, easy-to-collide name); the canonical config maps the friendlier `TWENTYFIRST_API_KEY` from your `.env` into `API_KEY` for that one server only.

## What this does NOT manage

- **Project-local MCP servers.** If a server only makes sense inside a specific repo (e.g. a `makerkit` server that points to that project's source tree, or a `supabase` server bound to one project's `project_ref`), keep it in that repo's `.mcp.json`. Centralizing those would just create paths that don't exist on other machines.
- **Claude-specific servers.** This repo's `servers.json` only holds servers that work in all three CLIs. If you add something Claude-only (e.g. `claude-in-chrome`), put it directly in `~/.claude.json` and add a comment so you remember not to add it here.
- **The CLIs themselves.** Install Claude Code, Gemini CLI, and Codex CLI per their own docs.
- **Per-CLI auth.** Things like `~/.codex/auth.json` (OpenAI login state) and Gemini's Google account state are not managed here — only MCP-server config is.

## Cross-environment notes

- **Path differences:** No absolute paths in `servers.json`. `serena` runs via `uvx --from git+https://...` so the same line works on mac and WSL with no changes.
- **Codex TOML quirk:** Codex doesn't expand `${VAR}` inside `config.toml` values, so the renderer **inlines** literal secrets there. That's fine — the file lives on your machine, not in this repo. (Same approach used for Claude/Gemini for consistency.) If you'd rather use Codex's `bearer_token_env_var` indirection for HTTP servers, add `"bearer_token_env_var": "VAR_NAME"` to that server's entry in `servers.json`.
- **If you also use Claude/Gemini/Codex from native Windows (PowerShell):** clone this repo on the Windows side too and run the equivalent commands in PowerShell/Git Bash. The Python script is portable; the `.sh` wrappers aren't. A `.ps1` equivalent is a small follow-up — open an issue if you want it.

## Troubleshooting

- `apply-all.sh` says "env vars not set" → check `.env` against `.env.example`.
- A CLI doesn't pick up the new servers → restart the CLI session. They read MCP config at startup, not on every prompt.
- `uvx` not found → `curl -LsSf https://astral.sh/uv/install.sh | sh`, then restart your shell.
- The render preview looks right but the CLI errors → run `./scripts/discover.sh` and compare against `servers.json`.
