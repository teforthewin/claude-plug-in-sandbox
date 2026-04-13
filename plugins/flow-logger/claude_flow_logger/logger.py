"""
Hook handler — called by Claude Code PreToolUse / PostToolUse / UserPromptSubmit hooks.
Reads the hook payload JSON from stdin and appends a JSONL entry to the session log file.

Every log entry carries:
  action_id : unique ID for this event
  cmd       : human-readable one-liner describing the call
  event     : pre | post | command
  tool      : Claude Code tool name
  input     : summarised input (tool-specific)
  response  : summarised output (post events only)
  tokens    : token usage if available (post events only)

Container tools (Agent, Skill, Bash) are captured in full.
Read / Glob / Grep are captured only when the path touches .claude/ config files.
All other tools are skipped.
"""

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Always captured in full (both pre and post)
CONTAINER_TOOLS = {"Agent", "Skill", "Bash", "SendMessage", "TaskCreate", "TaskUpdate"}

# Only captured when path touches AI config files
PATH_TOOLS = {"Read", "Glob", "Grep"}
PATH_KEYWORDS = [".claude/skills", ".claude/prompts", ".claude/agents", ".claude/instructions"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _truncate(value, max_len: int = 600):
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + f"…[+{len(value) - max_len} chars]"
    if isinstance(value, dict):
        return {k: _truncate(v, max_len) for k, v in value.items()}
    return value


def _should_capture(tool_name: str, tool_input: dict) -> bool:
    if tool_name in CONTAINER_TOOLS:
        return True
    if tool_name in PATH_TOOLS:
        path = (
            tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("pattern")
            or ""
        )
        return any(kw in path for kw in PATH_KEYWORDS)
    return False


def _cmd(tool_name: str, tool_input: dict) -> str:
    """Return a single human-readable command string for any tool."""
    if tool_name == "Agent":
        agent = tool_input.get("subagent_type", "general-purpose")
        desc  = tool_input.get("description", "")
        return f"agent:{agent} {desc}".strip()
    if tool_name == "Skill":
        skill = tool_input.get("skill", "")
        args  = tool_input.get("args", "")
        return f"skill:{skill} {args}".strip()
    if tool_name == "Bash":
        desc    = tool_input.get("description", "").strip()
        command = tool_input.get("command", "").strip()
        return f"$ {desc or command[:120]}"
    if tool_name == "Read":
        return f"read {tool_input.get('file_path', '')}"
    if tool_name == "Write":
        return f"write {tool_input.get('file_path', '')}"
    if tool_name == "Edit":
        return f"edit {tool_input.get('file_path', '')}"
    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path    = tool_input.get("path", "")
        return f"glob {pattern}" + (f" in {path}" if path else "")
    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path    = tool_input.get("path", "") or tool_input.get("file_path", "")
        return f"grep /{pattern}/" + (f" in {path}" if path else "")
    if tool_name == "SendMessage":
        return f"sendmsg to:{tool_input.get('to', '')}"
    if tool_name == "TaskCreate":
        return f"task:create {tool_input.get('title', '')}"
    if tool_name == "TaskUpdate":
        return f"task:update {tool_input.get('id', '')} → {tool_input.get('status', '')}"
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        method = parts[2] if len(parts) > 2 else tool_name
        first_val = next(iter(tool_input.values()), "") if tool_input else ""
        return f"{method} {str(first_val)[:80]}".strip()
    first_val = next(iter(tool_input.values()), "") if tool_input else ""
    return f"{tool_name} {str(first_val)[:80]}".strip()


def _summarise_input(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "Agent":
        return {
            "agent": tool_input.get("subagent_type", "general-purpose"),
            "description": tool_input.get("description", ""),
            "name": tool_input.get("name", ""),
            "prompt": _truncate(tool_input.get("prompt", ""), 2000),
        }
    if tool_name == "Skill":
        return {
            "skill": tool_input.get("skill", ""),
            "args": _truncate(tool_input.get("args", ""), 1000),
        }
    if tool_name == "Bash":
        return {
            "command": _truncate(tool_input.get("command", ""), 500),
            "description": tool_input.get("description", ""),
        }
    if tool_name == "SendMessage":
        return {
            "to": tool_input.get("to", ""),
            "message": _truncate(tool_input.get("message", ""), 200),
        }
    if tool_name == "TaskCreate":
        return {"title": tool_input.get("title", "")}
    if tool_name == "TaskUpdate":
        return {
            "id": tool_input.get("id", ""),
            "status": tool_input.get("status", ""),
        }
    if tool_name in PATH_TOOLS:
        return {
            "path": (
                tool_input.get("file_path")
                or tool_input.get("path")
                or tool_input.get("pattern")
                or ""
            ),
        }
    return _truncate(tool_input, 300)


def _summarise_response(tool_name: str, raw: object) -> object:
    if tool_name == "Bash" and isinstance(raw, dict):
        return {
            "stdout": _truncate(raw.get("stdout", ""), 1000),
            "stderr": _truncate(raw.get("stderr", ""), 400),
            "exit_code": raw.get("exit_code"),
        }
    if tool_name in {"Agent", "Skill"}:
        return _truncate(raw, 4000)
    return _truncate(raw, 400)


def _extract_tokens(source: dict) -> dict | None:
    if not isinstance(source, dict):
        return None
    usage = source.get("usage") or {}
    total = source.get("totalTokens") or (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("output_tokens", 0)
    ) or None
    if not total and not usage:
        return None
    tokens: dict = {}
    if total:                                       tokens["total"]       = total
    if usage.get("input_tokens") is not None:       tokens["input"]       = usage["input_tokens"]
    if usage.get("output_tokens") is not None:      tokens["output"]      = usage["output_tokens"]
    if usage.get("cache_read_input_tokens"):        tokens["cache_read"]  = usage["cache_read_input_tokens"]
    if usage.get("cache_creation_input_tokens"):    tokens["cache_write"] = usage["cache_creation_input_tokens"]
    if source.get("totalDurationMs") is not None:   tokens["duration_ms"] = source["totalDurationMs"]
    return tokens or None


# ---------------------------------------------------------------------------
# Log directory resolution
# ---------------------------------------------------------------------------

def _resolve_log_dir() -> Path:
    """
    Resolution order:
    1. FLOW_LOG_DIR env var  (set by flow-install into the hook command)
    2. ~/.claude/flow-logs/<project-slug>/  (central, derived from CWD)
    """
    if env := os.environ.get("FLOW_LOG_DIR"):
        return Path(env)
    project_slug = Path.cwd().name
    return Path.home() / ".claude" / "flow-logs" / project_slug


# ---------------------------------------------------------------------------
# Auto-start dashboard server
# ---------------------------------------------------------------------------

_SERVER_CHECK_COOLDOWN = 30  # seconds between port checks

def _ensure_server_running() -> None:
    """
    Check if the dashboard server is reachable on its port.
    If not, spawn it as a detached daemon process.
    Uses a cooldown file to avoid checking on every hook invocation.
    """
    port = int(os.environ.get("FLOW_SERVER_PORT", "7842"))
    check_file = Path.home() / ".claude" / ".flow-server-check"

    # Cooldown: skip if we checked recently
    try:
        if check_file.exists():
            last_check = check_file.stat().st_mtime
            if time.time() - last_check < _SERVER_CHECK_COOLDOWN:
                return
    except OSError:
        pass

    # Touch the check file (even before the socket check, to avoid re-checking
    # on rapid successive hook calls)
    try:
        check_file.parent.mkdir(parents=True, exist_ok=True)
        check_file.touch()
    except OSError:
        pass

    # Probe the port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        if result == 0:
            return  # server already running
    finally:
        sock.close()

    # Server not running — launch it as a detached daemon
    try:
        kwargs: dict = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin":  subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )
        else:
            kwargs["start_new_session"] = True

        # When running inside a Claude Code plugin, ${CLAUDE_PLUGIN_DATA}/venv
        # may hold the correct Python; fall back to python -m for pip installs.
        plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
        if plugin_data:
            venv_python = Path(plugin_data) / "venv" / "bin" / "python"
            if venv_python.exists():
                plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
                proc = subprocess.Popen(
                    [str(venv_python), "-c",
                     "import sys,os;"
                     f"sys.path.insert(0,{plugin_root!r});"
                     "from claude_flow_logger.server import run;"
                     "from pathlib import Path;"
                     f"run(Path({str(_resolve_log_dir())!r}))"],
                    env={**os.environ, "FLOW_SERVER_PORT": str(port)},
                    **kwargs,
                )
            else:
                return  # plugin not yet set up — setup.sh will handle it
        else:
            proc = subprocess.Popen(
                [sys.executable, "-m", "claude_flow_logger", "server"],
                **kwargs,
            )

        # Write PID file for clean shutdown
        pid_file = Path.home() / ".claude" / ".flow-server.pid"
        pid_file.write_text(str(proc.pid))
    except Exception:
        pass  # non-fatal — dashboard is optional


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_prompt(data: dict, log_dir: Path) -> None:
    """UserPromptSubmit — log all user messages."""
    # Claude Code sends the user's text in the "prompt" field
    message = (data.get("prompt") or data.get("message") or "").strip()
    if not message:
        return

    session_id = data.get("session_id", "unknown")
    log_dir.mkdir(parents=True, exist_ok=True)

    if message.startswith("/"):
        # Slash command
        parts = message.split(None, 1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "action_id": _new_id(),
            "event": "command",
            "tool": "Command",
            "cmd": f"{command} {args}".strip(),
            "input": {"command": command, "args": _truncate(args, 500)},
        }
    elif message.startswith("<"):
        # System-injected entry (command caveat, tool result, etc.) — skip
        return
    else:
        # Regular user prompt
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "action_id": _new_id(),
            "event": "prompt",
            "tool": "User",
            "cmd": _truncate(message, 120),
            "input": {"message": _truncate(message, 2000)},
        }

    with open(log_dir / f"{session_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_tool(event_type: str, data: dict, log_dir: Path) -> None:
    """PreToolUse / PostToolUse — log matching tool invocations."""
    tool_name  = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if not _should_capture(tool_name, tool_input):
        return

    session_id = data.get("session_id", "unknown")
    log_dir.mkdir(parents=True, exist_ok=True)

    entry: dict = {
        "ts": datetime.now(UTC).isoformat(),
        "action_id": data.get("tool_use_id") or _new_id(),
        "event": event_type,
        "tool": tool_name,
        "cmd": _cmd(tool_name, tool_input),
        "input": _summarise_input(tool_name, tool_input),
    }

    if event_type == "post":
        raw = data.get("tool_response", "")
        entry["response"] = _summarise_response(tool_name, raw)
        tokens = _extract_tokens(raw) if isinstance(raw, dict) else None
        if tokens is None:
            tokens = _extract_tokens(data)
        if tokens:
            entry["tokens"] = tokens

    with open(log_dir / f"{session_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] not in ("pre", "post", "prompt"):
        sys.exit(0)

    event_type = args[0]

    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    log_dir = _resolve_log_dir()

    # Auto-start the dashboard server on pre events and prompts
    if event_type in ("pre", "prompt"):
        _ensure_server_running()

    if event_type == "prompt":
        handle_prompt(data, log_dir)
    else:
        handle_tool(event_type, data, log_dir)

    sys.exit(0)
