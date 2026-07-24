#!/usr/bin/env python3
"""
Render the canonical MCP server list (servers.json) into the CLI-specific
config formats: Claude Code (JSON), Gemini CLI (JSON), Codex CLI (TOML).

Resolves ${VAR} placeholders from a .env file at apply time. Codex doesn't
support ${VAR} expansion in TOML so we always inline literal values; for
consistency we do the same for Claude and Gemini.

Usage:
    render.py claude --in servers.json --env .env --out ~/.claude.json
    render.py gemini --in servers.json --env .env --out ~/.gemini/settings.json
    render.py codex  --in servers.json --env .env --out ~/.codex/config.toml
    render.py preview <claude|gemini|codex>   # print to stdout, no writes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_env(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Empty values and comments allowed."""
    if not path.exists():
        return {}
    out = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def substitute(value, env: dict[str, str], missing: list[str]):
    """Recursively replace ${VAR} placeholders with env values. Records misses."""
    if isinstance(value, str):
        def repl(m):
            name = m.group(1)
            if name in env and env[name]:
                return env[name]
            missing.append(name)
            return m.group(0)
        return VAR_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: substitute(v, env, missing) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, env, missing) for v in value]
    return value


def render_claude(servers: dict, env: dict) -> tuple[dict, list[str]]:
    """
    Claude Code stores MCPs at top-level `mcpServers` in ~/.claude.json. We
    merge into the existing file (don't clobber unrelated keys).
    """
    missing: list[str] = []
    mcp = {}
    for name, cfg in servers.items():
        s = substitute(cfg, env, missing)
        if s.get("transport") == "url":
            entry = {"url": s["url"]}
            if "headers" in s:
                entry["headers"] = s["headers"]
        else:
            entry = {"command": s["command"], "args": s.get("args", [])}
            if "env" in s:
                entry["env"] = s["env"]
        mcp[name] = entry
    return mcp, missing


def render_gemini(servers: dict, env: dict) -> tuple[dict, list[str]]:
    """Gemini CLI: ~/.gemini/settings.json, top-level `mcpServers` (camelCase)."""
    missing: list[str] = []
    mcp = {}
    for name, cfg in servers.items():
        s = substitute(cfg, env, missing)
        if s.get("transport") == "url":
            entry = {"url": s["url"]}
            if "headers" in s:
                entry["headers"] = s["headers"]
        elif s.get("transport") == "http":
            entry = {"httpUrl": s["url"]}
            if "headers" in s:
                entry["headers"] = s["headers"]
        else:
            entry = {"command": s["command"], "args": s.get("args", [])}
            if "env" in s:
                entry["env"] = s["env"]
        mcp[name] = entry
    return mcp, missing


def toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_codex(servers: dict, env: dict) -> tuple[str, list[str]]:
    """
    Codex CLI: ~/.codex/config.toml, sections `[mcp_servers.NAME]` (snake_case).
    No ${VAR} expansion in TOML — values are literal. We emit only the
    [mcp_servers.*] sections; the apply script merges them into config.toml
    without touching unrelated sections like [projects.*].
    """
    missing: list[str] = []
    lines: list[str] = []
    for name, cfg in servers.items():
        s = substitute(cfg, env, missing)
        section_name = name if name.replace("-", "").replace("_", "").isalnum() else f'"{name}"'
        lines.append(f"[mcp_servers.{section_name}]")
        if s.get("transport") in ("url", "http"):
            lines.append(f'url = "{toml_escape(s["url"])}"')
            if "bearer_token_env_var" in s:
                lines.append(f'bearer_token_env_var = "{s["bearer_token_env_var"]}"')
        else:
            lines.append(f'command = "{toml_escape(s["command"])}"')
            args = s.get("args", [])
            args_repr = ", ".join(f'"{toml_escape(a)}"' for a in args)
            lines.append(f"args = [{args_repr}]")
            if "env" in s and s["env"]:
                env_pairs = ", ".join(
                    f'{k} = "{toml_escape(v)}"' for k, v in s["env"].items()
                )
                lines.append(f"env = {{ {env_pairs} }}")
        lines.append("")
    return "\n".join(lines), missing


def merge_into_json(target_path: Path, key: str, value: dict) -> dict:
    """
    Read target JSON file (if any) and merge `value` into its top-level `key`
    map, entry by entry. Servers declared in servers.json are replaced; servers
    that exist only in the target (e.g. CLI-specific ones like `backlog`) are
    preserved. A server removed from servers.json must be removed from the
    target config by hand.
    """
    if target_path.exists():
        try:
            data = json.loads(target_path.read_text())
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    existing = data.get(key)
    if isinstance(existing, dict):
        data[key] = {**existing, **value}
    else:
        data[key] = value
    return data


def codex_section_server_name(header: str) -> str | None:
    """Extract NAME from a `[mcp_servers.NAME]` or `[mcp_servers.NAME.sub]`
    section header (bare or quoted). Returns None for non-mcp sections."""
    m = re.match(r'\[mcp_servers\.(?:"([^"]+)"|([A-Za-z0-9_-]+))', header)
    if not m:
        return None
    return m.group(1) or m.group(2)


def merge_codex_toml(target_path: Path, new_mcp_section: str, managed: set[str]) -> str:
    """
    Replace the [mcp_servers.NAME] blocks for servers declared in servers.json
    with the newly rendered ones. Blocks for servers not in servers.json (e.g.
    CLI-specific ones) and all other top-level sections ([projects.*],
    [profiles.*], ...) are preserved. A server removed from servers.json must
    be removed from config.toml by hand.
    """
    if not target_path.exists():
        return new_mcp_section.rstrip() + "\n"
    existing = target_path.read_text()
    out_lines = []
    skip = False
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            name = codex_section_server_name(stripped)
            skip = name is not None and name in managed
        if not skip:
            out_lines.append(line)
    cleaned = "\n".join(out_lines).rstrip() + "\n\n"
    return cleaned + new_mcp_section.rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["claude", "gemini", "codex", "preview"])
    ap.add_argument("preview_target", nargs="?", choices=["claude", "gemini", "codex"])
    ap.add_argument("--in", dest="src", default=None)
    ap.add_argument("--env", dest="envfile", default=None)
    ap.add_argument("--out", dest="dest", default=None)
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    src = Path(args.src) if args.src else repo_root / "servers.json"
    envfile = Path(args.envfile) if args.envfile else repo_root / ".env"

    if not src.exists():
        sys.exit(f"error: canonical config not found at {src}")

    canonical = json.loads(src.read_text())
    servers = canonical.get("servers", {})
    env = load_env(envfile)

    target = args.preview_target if args.target == "preview" else args.target
    if target == "claude":
        rendered, missing = render_claude(servers, env)
        body_kind = "json"
    elif target == "gemini":
        rendered, missing = render_gemini(servers, env)
        body_kind = "json"
    elif target == "codex":
        rendered, missing = render_codex(servers, env)
        body_kind = "toml"
    else:
        sys.exit(f"unknown target: {target}")

    if missing:
        unique = sorted(set(missing))
        print(
            f"warning: {len(unique)} env var(s) referenced but not set in {envfile}: "
            f"{', '.join(unique)}",
            file=sys.stderr,
        )
        print(
            "  servers depending on those vars will be rendered with literal "
            "${VAR} placeholders and likely fail at runtime.",
            file=sys.stderr,
        )

    if args.target == "preview":
        if body_kind == "json":
            print(json.dumps(rendered, indent=2))
        else:
            print(rendered)
        return

    dest = Path(args.dest).expanduser() if args.dest else None
    if dest is None:
        sys.exit("error: --out required for non-preview targets")
    dest.parent.mkdir(parents=True, exist_ok=True)

    if target == "claude":
        merged = merge_into_json(dest, "mcpServers", rendered)
        dest.write_text(json.dumps(merged, indent=2) + "\n")
    elif target == "gemini":
        merged = merge_into_json(dest, "mcpServers", rendered)
        dest.write_text(json.dumps(merged, indent=2) + "\n")
    elif target == "codex":
        dest.write_text(merge_codex_toml(dest, rendered, set(servers)))

    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
