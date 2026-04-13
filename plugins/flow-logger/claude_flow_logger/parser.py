"""
parser.py — Read native Claude Code JSONL session files and produce normalized events.

Native files live at:
  ~/.claude/projects/{encoded-project}/{session-uuid}/{session-uuid}.jsonl
  ~/.claude/projects/{encoded-project}/{session-uuid}/subagents/agent-{id}.jsonl

Normalized event fields (one dict per tool call, prompt, or system event):

  id                  — tool_use_id (tool events) or entry uuid (prompts/system)
  ts                  — ISO 8601 timestamp
  session_id          — UUID of the owning session
  parent_session_id   — None for main session, session_id for sub-agents
  depth               — 0 = main session, 1 = sub-agent
  event               — "pre" | "post" | "prompt" | "system"
  tool                — Claude tool name (Bash, Read, Agent, …)
  cmd                 — human-readable one-liner for the events table
  input               — tool input dict (pre) / {"message": "…"} (prompt)
  response            — tool output (post events only)
  tokens              — {input, output, cache_read, cache_write, total} or None
  model               — model name string (pre events only)
  thinking            — extended thinking text (pre events only, may be None)
  stop_reason         — API stop_reason (pre events only)
  agent_type          — subagent_type string (Agent post events only)
  agent_id            — agentId from toolUseResult (Agent post events only)
  agent_duration_ms   — totalDurationMs (Agent post events only)
  agent_total_tokens  — totalTokens (Agent post events only)
  agent_tool_count    — totalToolUseCount (Agent post events only)
  cwd                 — working directory (prompt events only)
  git_branch          — git branch (prompt events only)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


# ---------------------------------------------------------------------------
# Human-readable one-liner (mirrors logger.py _cmd for UI compatibility)
# ---------------------------------------------------------------------------

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
        return f"task:create {tool_input.get('subject', tool_input.get('title', ''))}"
    if tool_name == "TaskUpdate":
        return f"task:update {tool_input.get('taskId', tool_input.get('id', ''))} → {tool_input.get('status', '')}"
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        method = parts[2] if len(parts) > 2 else tool_name
        first_val = next(iter(tool_input.values()), "") if tool_input else ""
        return f"{method} {str(first_val)[:80]}".strip()
    first_val = next(iter(tool_input.values()), "") if tool_input else ""
    return f"{tool_name} {str(first_val)[:80]}".strip()


# ---------------------------------------------------------------------------
# Token extraction from native usage dict
# ---------------------------------------------------------------------------

def _extract_tokens(usage: dict) -> dict | None:
    if not isinstance(usage, dict):
        return None
    inp  = usage.get("input_tokens", 0) or 0
    out  = usage.get("output_tokens", 0) or 0
    cr   = usage.get("cache_read_input_tokens", 0) or 0
    cc   = usage.get("cache_creation_input_tokens", 0) or 0
    total = inp + out + cr + cc
    if not total:
        return None
    result: dict = {"total": total}
    if inp: result["input"]      = inp
    if out: result["output"]     = out
    if cr:  result["cache_read"] = cr
    if cc:  result["cache_write"] = cc
    return result


# ---------------------------------------------------------------------------
# Tool response normalization
# ---------------------------------------------------------------------------

def _normalize_response(tool_name: str, content: object) -> object:
    """Flatten tool_result content blocks into something the UI can display."""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                t = block.get("type", "")
                if t == "text":
                    parts.append(block.get("text", ""))
                elif t == "image":
                    parts.append("[image]")
                else:
                    parts.append(str(block.get("content", block)))
        return "\n".join(parts) if parts else content
    return content


# ---------------------------------------------------------------------------
# Low-level JSONL loader
# ---------------------------------------------------------------------------

def load_raw(path: Path) -> list[dict]:
    """Load all valid JSON lines from a JSONL file."""
    entries: list[dict] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        entries.append(obj)
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return entries


# ---------------------------------------------------------------------------
# Core parser: raw native entries → normalized events
# ---------------------------------------------------------------------------

def parse_entries(
    raw: list[dict],
    session_id: str,
    parent_session_id: str | None = None,
    depth: int = 0,
) -> list[dict]:
    """
    Convert raw native JSONL entries to normalized events.

    Two-pass strategy:
      Pass 1 — index tool_use blocks from assistant messages
               → {tool_use_id: {name, input, ts, model, thinking, tokens, stop_reason}}
      Pass 2 — index tool_result blocks from user messages
               → {tool_use_id: {content, toolUseResult, ts}}
      Emit    — one "pre" + one "post" per tool call, in conversation order
              — one "prompt" per genuine user text message
              — one "system" per turn_duration entry
    """

    # ── Pass 1: tool_use index ─────────────────────────────────────────────
    tool_use_index: dict[str, dict] = {}

    for entry in raw:
        if entry.get("type") != "assistant":
            continue
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue

        model       = msg.get("model", "")
        stop_reason = msg.get("stop_reason", "")
        tokens      = _extract_tokens(msg.get("usage", {}))
        ts          = entry.get("timestamp", "")

        # Thinking: first non-empty thinking block
        thinking: str | None = None
        for block in content:
            if isinstance(block, dict) and block.get("type") == "thinking":
                t = block.get("thinking", "")
                if t:
                    thinking = t
                    break

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tid = block.get("id", "")
            if not tid:
                continue
            tool_use_index[tid] = {
                "name":        block.get("name", "unknown"),
                "input":       block.get("input") or {},
                "ts":          ts,
                "model":       model,
                "thinking":    thinking,
                "tokens":      tokens,
                "stop_reason": stop_reason,
            }

    # ── Pass 2: tool_result index ──────────────────────────────────────────
    tool_result_index: dict[str, dict] = {}

    for entry in raw:
        if entry.get("type") != "user":
            continue
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue

        # toolUseResult is a top-level field on the user entry (agent metadata)
        tur = entry.get("toolUseResult")
        ts  = entry.get("timestamp", "")

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tid = block.get("tool_use_id", "")
            if not tid:
                continue
            tool_result_index[tid] = {
                "content":       block.get("content", ""),
                "toolUseResult": tur,
                "ts":            ts,
            }

    # ── Emit events in conversation order ─────────────────────────────────
    events: list[dict] = []

    # Tool pre + post events (ordered by assistant message appearance)
    for entry in raw:
        if entry.get("type") != "assistant":
            continue
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tid = block.get("id", "")
            if not tid:
                continue

            meta   = tool_use_index.get(tid, {})
            result = tool_result_index.get(tid, {})
            name   = meta.get("name", block.get("name", "unknown"))
            inp    = meta.get("input", block.get("input") or {})

            # pre
            events.append({
                "id":                tid,
                "ts":                meta.get("ts", ""),
                "session_id":        session_id,
                "parent_session_id": parent_session_id,
                "depth":             depth,
                "event":             "pre",
                "tool":              name,
                "cmd":               _cmd(name, inp),
                "input":             inp,
                "model":             meta.get("model") or None,
                "thinking":          meta.get("thinking") or None,
                "stop_reason":       meta.get("stop_reason") or None,
                "tokens":            meta.get("tokens"),
            })

            # post
            tur_raw  = result.get("toolUseResult")
            tur      = tur_raw if isinstance(tur_raw, dict) else {}
            raw_resp = result.get("content", "")
            events.append({
                "id":                 tid,
                "ts":                 result.get("ts") or meta.get("ts", ""),
                "session_id":         session_id,
                "parent_session_id":  parent_session_id,
                "depth":              depth,
                "event":              "post",
                "tool":               name,
                "cmd":                _cmd(name, inp),
                "input":              inp,
                "response":           _normalize_response(name, raw_resp),
                "agent_type":         tur.get("agentType") or None,
                "agent_id":           tur.get("agentId") or None,
                "agent_duration_ms":  tur.get("totalDurationMs") or None,
                "agent_total_tokens": tur.get("totalTokens") or None,
                "agent_tool_count":   tur.get("totalToolUseCount") or None,
            })

    # Prompt events — genuine user text (no tool_results, not system-injected)
    for entry in raw:
        if entry.get("type") != "user":
            continue
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])

        text = ""
        has_tool_result = False

        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        has_tool_result = True
                    elif block.get("type") == "text":
                        parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            text = "\n".join(parts).strip()

        # Skip: no text, system-injected (<…>), or mixed with tool results
        if not text or text.startswith("<") or has_tool_result:
            continue

        events.append({
            "id":                entry.get("uuid", ""),
            "ts":                entry.get("timestamp", ""),
            "session_id":        session_id,
            "parent_session_id": parent_session_id,
            "depth":             depth,
            "event":             "prompt",
            "tool":              "User",
            "cmd":               text[:120],
            "input":             {"message": text},
            "cwd":               entry.get("cwd", ""),
            "git_branch":        entry.get("gitBranch", ""),
        })

    # System events — turn_duration only
    for entry in raw:
        if entry.get("type") != "system" or entry.get("subtype") != "turn_duration":
            continue
        events.append({
            "id":                entry.get("uuid", ""),
            "ts":                entry.get("timestamp", ""),
            "session_id":        session_id,
            "parent_session_id": parent_session_id,
            "depth":             depth,
            "event":             "system",
            "tool":              "System",
            "cmd":               f"turn {entry.get('durationMs', 0)}ms / {entry.get('messageCount', 0)} msgs",
            "input":             {
                "duration_ms":   entry.get("durationMs", 0),
                "message_count": entry.get("messageCount", 0),
            },
        })

    events.sort(key=lambda e: e.get("ts") or "")
    return events


# ---------------------------------------------------------------------------
# Session context extraction
# ---------------------------------------------------------------------------

def _session_context(raw: list[dict]) -> dict:
    """Extract cwd, git_branch, version from the first user entry."""
    for entry in raw:
        if entry.get("type") == "user":
            return {
                "cwd":        entry.get("cwd", ""),
                "git_branch": entry.get("gitBranch", ""),
                "version":    entry.get("version", ""),
            }
    return {"cwd": "", "git_branch": "", "version": ""}


def _initial_prompt(events: list[dict]) -> str:
    """Return the text of the first user prompt event."""
    for e in events:
        if e.get("event") == "prompt":
            return e.get("input", {}).get("message", "")
    return ""


# ---------------------------------------------------------------------------
# Project folder → display name
# ---------------------------------------------------------------------------

def project_display_name(folder_name: str) -> str:
    """
    Convert an encoded project folder name to a human-readable display name.

    Claude encodes the working directory as the folder name by replacing '/' with '-'.
    Example: '-Users-alice-Documents-repos-my-app' → 'my-app'
    """
    clean = folder_name.lstrip("-")
    if not clean:
        return folder_name
    # Last hyphen-separated segment is usually the project/repo name
    parts = clean.split("-")
    return parts[-1] if parts else clean


# ---------------------------------------------------------------------------
# ParsedSession dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedSession:
    session_id:  str
    session_dir: Path
    project:     str
    cwd:         str
    git_branch:  str
    version:     str
    events:      list[dict] = field(default_factory=list)
    mtime:       float      = 0.0

    @property
    def is_active(self) -> bool:
        import time
        return (time.time() - self.mtime) < 300

    def first_ts(self) -> str:
        return self.events[0]["ts"] if self.events else ""

    def last_ts(self) -> str:
        return self.events[-1]["ts"] if self.events else ""

    def initial_prompt(self) -> str:
        return _initial_prompt(self.events)


# ---------------------------------------------------------------------------
# Session directory parser
# ---------------------------------------------------------------------------

def parse_session_dir(session_dir: Path) -> "ParsedSession | None":
    """
    Parse a session given its aux directory.

    Actual on-disk layout (Claude Code native format):
      {project_dir}/{session_uuid}.jsonl            — main session file
      {project_dir}/{session_uuid}/subagents/…      — sub-agent files

    `session_dir` is `{project_dir}/{session_uuid}` (the aux dir).
    It may or may not exist; only the sibling .jsonl file is required.
    """
    session_id = session_dir.name
    main_jsonl = session_dir.parent / f"{session_id}.jsonl"

    if not main_jsonl.exists():
        return None

    project = project_display_name(session_dir.parent.name)
    raw     = load_raw(main_jsonl)
    if not raw:
        return None

    ctx    = _session_context(raw)
    events = parse_entries(raw, session_id, parent_session_id=None, depth=0)

    # Sub-agents (only when the aux directory exists)
    subagents_dir = session_dir / "subagents"
    if session_dir.exists() and subagents_dir.exists():
        for agent_jsonl in sorted(subagents_dir.glob("agent-*.jsonl")):
            if "acompact" in agent_jsonl.stem:
                continue
            sub_raw = load_raw(agent_jsonl)
            if not sub_raw:
                continue
            sub_events = parse_entries(
                sub_raw,
                session_id=f"{session_id}/{agent_jsonl.stem}",
                parent_session_id=session_id,
                depth=1,
            )
            events.extend(sub_events)

    events.sort(key=lambda e: e.get("ts") or "")

    return ParsedSession(
        session_id=session_id,
        session_dir=session_dir,
        project=project,
        cwd=ctx["cwd"],
        git_branch=ctx["git_branch"],
        version=ctx["version"],
        events=events,
        mtime=main_jsonl.stat().st_mtime,
    )


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def discover_sessions(base: Path | None = None) -> list["ParsedSession"]:
    """
    Walk ~/.claude/projects/ and return all valid sessions, newest first.

    Native on-disk layout:
      base/{encoded-project}/{session-uuid}.jsonl        — main file
      base/{encoded-project}/{session-uuid}/subagents/   — sub-agents
    """
    root = base or CLAUDE_PROJECTS_DIR
    if not root.exists():
        return []

    sessions: list[ParsedSession] = []
    for project_dir in sorted(root.iterdir()):
        if not project_dir.is_dir():
            continue
        for main_jsonl in sorted(project_dir.glob("*.jsonl")):
            session_id  = main_jsonl.stem
            session_dir = project_dir / session_id   # aux dir (may not exist)
            ps = parse_session_dir(session_dir)
            if ps is not None:
                sessions.append(ps)

    sessions.sort(key=lambda s: s.mtime, reverse=True)
    return sessions


# ---------------------------------------------------------------------------
# Stats helpers (used by the /api/sessions/{id}/stats endpoint)
# ---------------------------------------------------------------------------

def compute_stats(ps: "ParsedSession") -> dict:
    """
    Compute aggregate stats from a ParsedSession's normalized events.
    Mirrors the shape previously returned by _read_claude_session_stats().
    """
    tokens: dict[str, int] = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
    tools:  dict[str, int] = {}
    timeline: list[dict]   = []
    agents:   list[dict]   = []

    for e in ps.events:
        evt  = e.get("event", "")
        tool = e.get("tool", "")

        if evt == "pre":
            tok = e.get("tokens") or {}
            tokens["input"]        += tok.get("input", 0)
            tokens["output"]       += tok.get("output", 0)
            tokens["cache_read"]   += tok.get("cache_read", 0)
            tokens["cache_create"] += tok.get("cache_write", 0)
            tools[tool] = tools.get(tool, 0) + 1

        elif evt == "post" and tool == "Agent" and e.get("agent_id"):
            agents.append({
                "agent_id":    e["agent_id"],
                "agent_type":  e.get("agent_type", ""),
                "duration_ms": e.get("agent_duration_ms"),
                "tokens":      e.get("agent_total_tokens"),
                "tool_count":  e.get("agent_tool_count"),
            })

        elif evt == "system":
            inp_dur = e.get("input", {})
            timeline.append({
                "ts":           e.get("ts", ""),
                "duration_ms":  inp_dur.get("duration_ms", 0),
                "message_count": inp_dur.get("message_count", 0),
            })

    return {
        "tokens":         tokens,
        "tools":          tools,
        "agents":         agents,
        "timeline":       timeline,
        "initial_prompt": ps.initial_prompt(),
    }
