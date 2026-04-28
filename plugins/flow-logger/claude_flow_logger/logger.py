"""
Hook handler — called by Claude Code PreToolUse / PostToolUse / UserPromptSubmit.

Writes a sidecar .flow.jsonl file alongside Claude's native session JSONL:
  ~/.claude/projects/{encoded-cwd}/{session-id}.flow.jsonl

Captures every tool call (no filtering) so the caller always knows:
  - which tool was invoked
  - which session/agent context invoked it
  - with what input and response
"""

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _truncate(value, max_len: int = 2000):
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + f"…[+{len(value) - max_len} chars]"
    if isinstance(value, dict):
        return {k: _truncate(v, max_len) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v, max_len) for v in value[:30]]
    return value


def _encode_cwd(cwd: str) -> str:
    """Encode a filesystem path the same way Claude Code does for project folder names."""
    return cwd.replace("/", "-").replace(".", "-")


def _resolve_project_dir() -> Path:
    """
    Return the ~/.claude/projects/{encoded-cwd}/ directory for the current working directory.
    Falls back to scanning by session_id if the encoded path doesn't exist yet.
    """
    cwd = str(Path.cwd())
    return CLAUDE_PROJECTS_DIR / _encode_cwd(cwd)


def _find_project_dir_for_session(session_id: str) -> Path | None:
    """
    Scan ~/.claude/projects/ to find the project directory that owns this session.
    Only matches on the presence of the exact session .jsonl file.
    """
    if not CLAUDE_PROJECTS_DIR.exists():
        return None
    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        if (project_dir / f"{session_id}.jsonl").exists():
            return project_dir
    return None


def _project_dir(session_id: str) -> Path:
    """Resolve the project dir by finding where the session .jsonl lives, falling back to CWD."""
    found = _find_project_dir_for_session(session_id)
    if found:
        return found
    # Session not found yet (new session or unknown id) — fall back to CWD encoding
    return _resolve_project_dir()


def _cmd(tool_name: str, tool_input: dict) -> str:
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
    if tool_name == "SendMessage":
        return f"sendmsg to:{tool_input.get('to', '')}"
    if tool_name == "TaskCreate":
        return f"task:create {tool_input.get('title', '')}"
    if tool_name == "TaskUpdate":
        return f"task:update {tool_input.get('id', '')} → {tool_input.get('status', '')}"
    if tool_name == "Read":
        return f"read {tool_input.get('file_path', '')}"
    if tool_name == "Write":
        return f"write {tool_input.get('file_path', '')}"
    if tool_name == "Edit":
        return f"edit {tool_input.get('file_path', '')}"
    if tool_name == "Glob":
        return f"glob {tool_input.get('pattern', '')}"
    if tool_name == "Grep":
        return f"grep /{tool_input.get('pattern', '')}/"
    if tool_name == "ToolSearch":
        return f"tool-search {tool_input.get('query', '')}"
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        method = parts[2] if len(parts) > 2 else tool_name
        first_val = next(iter(tool_input.values()), "") if tool_input else ""
        return f"{method} {str(first_val)[:80]}".strip()
    first_val = next(iter(tool_input.values()), "") if tool_input else ""
    return f"{tool_name} {str(first_val)[:80]}".strip()


def handle_prompt(data: dict) -> None:
    message = (data.get("prompt") or data.get("message") or "").strip()
    if not message or message.startswith("<"):
        return

    session_id  = data.get("session_id", "unknown")
    project_dir = _project_dir(session_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts":         datetime.now(UTC).isoformat(),
        "id":         _new_id(),
        "event":      "prompt",
        "session_id": session_id,
        "tool":       "User",
        "cmd":        message[:120],
        "input":      {"message": _truncate(message, 2000)},
    }

    sidecar = project_dir / f"{session_id}.flow.jsonl"
    with open(sidecar, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_tool(event_type: str, data: dict) -> None:
    tool_name   = data.get("tool_name", "")
    tool_input  = data.get("tool_input", {})
    session_id  = data.get("session_id", "unknown")
    project_dir = _project_dir(session_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    entry: dict = {
        "ts":         datetime.now(UTC).isoformat(),
        "id":         data.get("tool_use_id") or _new_id(),
        "event":      event_type,
        "session_id": session_id,
        "tool":       tool_name,
        "cmd":        _cmd(tool_name, tool_input),
        "input":      _truncate(tool_input, 2000),
    }

    if event_type == "post":
        entry["response"] = _truncate(data.get("tool_response", ""), 2000)

    sidecar = project_dir / f"{session_id}.flow.jsonl"
    with open(sidecar, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] not in ("pre", "post", "prompt"):
        sys.exit(0)

    event_type = args[0]

    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if event_type == "prompt":
        handle_prompt(data)
    else:
        handle_tool(event_type, data)

    sys.exit(0)


if __name__ == "__main__":
    main()
