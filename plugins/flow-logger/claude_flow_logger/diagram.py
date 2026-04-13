"""
Mermaid sequence diagram builder.
Reads JSONL session logs and produces diagram markup + markdown reports.
"""

import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path

# Display-name overrides for well-known agent types.
# Unknown types are handled automatically via _AliasRegistry → "Agent:<type>".
AGENT_LABELS: dict[str, str] = {
    "general-purpose":          "Agent:General",
    "Explore":                  "Agent:Explore",
    "Plan":                     "Agent:Plan",
    "claude-code-guide":        "Agent:Guide",
    "statusline-setup":         "Agent:StatusLine",
}


class _AliasRegistry:
    """
    Generates unique, compact Mermaid-safe participant IDs for any label.

    A few well-known labels have fixed short aliases; everything else gets
    a CamelCase-initials abbreviation that is guaranteed to be unique within
    a single diagram build.
    """

    _FIXED: dict[str, str] = {
        "Claude":  "C",
        "Skill":   "SK",
        "Read":    "FS",
        "Command": "CMD",
    }

    def __init__(self) -> None:
        self._map: dict[str, str] = dict(self._FIXED)
        self._used: set[str] = set(self._FIXED.values())

    def get(self, label: str) -> str:
        if label not in self._map:
            alias = self._generate(label)
            self._map[label] = alias
            self._used.add(alias)
        return self._map[label]

    def _generate(self, label: str) -> str:
        # Strip instance suffix (" #2") and bracketed name ("[myname]") before abbreviating
        clean = re.sub(r"\s*#\d+$", "", label)
        clean = re.sub(r"\[.*?\]", "", clean)
        parts = re.split(r"[:\s_\-]+", clean)
        base = "".join(p[0].upper() for p in parts if p) or "X"
        candidate = base
        n = 2
        while candidate in self._used:
            candidate = f"{base}{n}"
            n += 1
        return candidate


def _safe(text: str, max_len: int = 60) -> str:
    text = str(text).replace('"', "'").replace("\n", " ").strip()
    return text[:max_len] + "…" if len(text) > max_len else text


def _agent_label(entry: dict) -> str:
    """Return a display label for an Agent tool entry."""
    inp = entry.get("input", {})
    # Native JSONL uses "subagent_type"; hook-based logs used "agent"
    agent_type = inp.get("subagent_type") or inp.get("agent", "general-purpose")
    label = AGENT_LABELS.get(agent_type, f"Agent:{agent_type}")
    return label


def load_entries(log_file: Path) -> list[dict]:
    entries = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def build_diagram(entries: list[dict], session_id: str = "") -> str:
    """
    Build a Mermaid sequence diagram from a list of log entries.

    Handles:
    - Unknown/custom agent types (dynamic alias generation)
    - Parallel agents of the same type (unique participant names: "Agent:X #2")
    - Nested agents (parent attribution via caller stack)
    - SendMessage with exact-then-substring target matching
    """
    aliases = _AliasRegistry()
    participant_lines: list[str] = []
    event_lines: list[str] = []
    declared: set[str] = set()

    def ensure(label: str, display: str | None = None) -> str:
        """Declare a Mermaid participant on first use; return its alias."""
        if label not in declared:
            declared.add(label)
            a = aliases.get(label)
            participant_lines.append(f"    participant {a} as {display or label}")
        return aliases.get(label)

    ensure("Claude")
    c = aliases.get("Claude")

    # Per-label FIFO queue of currently active unique instance labels.
    # FIFO is used so that parallel agents of the same type are matched
    # in spawn order (first spawned = first to complete).
    active_queues: dict[str, deque[str]] = {}

    # Per-label count of currently active instances (reset to 0 when queue empties).
    active_counts: dict[str, int] = {}

    # Caller stack for parent attribution.
    # Works correctly for sequential and nested agents.
    # For parallel agents the heuristic is: if the same label already has an
    # active instance, assume the new one is a sibling (spawned by Claude),
    # not a child of the running instance.
    caller_stack: list[str] = ["Claude"]

    # Map sub-agent session IDs → participant label for depth-based attribution
    # Populated when Agent pre events are encountered.
    subagent_session_labels: dict[str, str] = {}

    for e in entries:
        tool  = e.get("tool", "")
        event = e.get("event", "")
        depth = e.get("depth", 0)
        inp   = e.get("input") or {}

        # Depth-aware caller: for sub-agent events (depth > 0) prefer the
        # top non-Claude agent from caller_stack; fall back to Claude.
        if depth > 0:
            agent_callers = [p for p in caller_stack if p != "Claude"]
            parent = agent_callers[-1] if agent_callers else "Claude"
        else:
            parent = caller_stack[-1]
        pa = aliases.get(parent)

        if tool == "Command":
            cmd_alias = ensure("Command")
            cmd  = _safe(inp.get("command", "/?"), 40)
            args = _safe(inp.get("args", ""), 40)
            label = f"{cmd} {args}".strip() if args else cmd
            event_lines.append(f"    Note over {c},{cmd_alias}: {label}")

        elif tool == "Agent":
            base_label = _agent_label(e)

            if event == "pre":
                n = active_counts.get(base_label, 0) + 1
                active_counts[base_label] = n
                # Use a numbered suffix only when a sibling is already active,
                # so that serial reuse of the same type shares one participant.
                unique_label = base_label if n == 1 else f"{base_label} #{n}"
                a = ensure(unique_label, display=base_label)

                # Parallel sibling heuristic: if n > 1 the spawner is Claude,
                # not the currently running instance of the same type.
                effective_parent = c if n > 1 else pa
                desc = _safe(inp.get("description", "spawn"))
                event_lines.append(f"    {effective_parent}->>{a}: {desc}")
                event_lines.append(f"    activate {a}")

                active_queues.setdefault(base_label, deque()).append(unique_label)
                caller_stack.append(unique_label)

            elif event == "post":
                q = active_queues.get(base_label)
                if q:
                    unique_label = q.popleft()  # FIFO
                    active_counts[base_label] = max(0, active_counts.get(base_label, 1) - 1)
                    a = aliases.get(unique_label)

                    # Remove from caller stack wherever it sits (may not be at top
                    # if parallel agents interleave).
                    if unique_label in caller_stack:
                        caller_stack.remove(unique_label)

                    parent_after = caller_stack[-1] if caller_stack else "Claude"
                    pa_after = aliases.get(parent_after)

                    resp = e.get("response", "")
                    summary = _safe(resp, 80) if isinstance(resp, str) else "done"
                    event_lines.append(f"    {a}-->>{pa_after}: {summary}")
                    event_lines.append(f"    deactivate {a}")

        elif tool == "Skill":
            sk = ensure("Skill")
            skill_name = inp.get("skill", "")
            args = inp.get("args", "")
            label = _safe(f"{skill_name} {args}".strip(), 50)
            if event == "pre":
                event_lines.append(f"    {pa}->>{sk}: invoke {label}")
            elif event == "post":
                event_lines.append(f"    {sk}-->>{pa}: content loaded")

        elif tool in ("Read", "Glob", "Grep"):
            fs = ensure("Read")
            # Native fields differ by tool; fall back gracefully
            path = (
                inp.get("file_path")
                or inp.get("pattern")
                or inp.get("path")
                or ""
            )
            if event == "pre":
                event_lines.append(f"    Note over {c},{fs}: {_safe(path, 50)}")

        elif tool == "Bash":
            if event == "pre":
                bash_alias = ensure("Bash")
                label = _safe(inp.get("description") or inp.get("command", ""), 55)
                event_lines.append(f"    {pa}->>{bash_alias}: {label}")
                event_lines.append(f"    activate {bash_alias}")
            elif event == "post":
                bash_alias = ensure("Bash")
                event_lines.append(f"    {bash_alias}-->>{pa}: done")
                event_lines.append(f"    deactivate {bash_alias}")

        elif tool in ("Write", "Edit"):
            if event == "pre":
                path = _safe(inp.get("file_path", ""), 50)
                verb = "write" if tool == "Write" else "edit"
                event_lines.append(f"    Note over {pa}: {verb} {path}")

        elif tool == "SendMessage":
            target = inp.get("to", "target")
            msg = _safe(inp.get("message", ""), 60)
            # Exact match first, then case-insensitive substring to avoid
            # false matches between similarly named agents.
            target_label = next(
                (p for p in declared if p.lower() == target.lower()), None
            ) or next(
                (p for p in declared if target.lower() in p.lower()), None
            )
            if target_label is None:
                target_label = f"Agent:{target}"
                ensure(target_label)
            ta = aliases.get(target_label)
            if event == "pre":
                event_lines.append(f"    {pa}->>{ta}: msg: {msg}")

        elif tool == "TaskCreate":
            if event == "pre":
                # Native input has "subject"; hook-based had "title"
                task_title = _safe(inp.get("subject") or inp.get("title", "task"), 50)
                event_lines.append(f"    Note over {c}: task: {task_title}")

    lines = (
        ["```mermaid", "sequenceDiagram", "    autonumber"]
        + participant_lines
        + [""]
        + event_lines
        + ["```"]
    )
    return "\n".join(lines)


def build_diagram_mermaid_only(
    entries: list[dict],
    session_id: str = "",
    max_entries: int = 200,
) -> tuple[str, bool]:
    """
    Returns (mermaid_syntax, was_truncated).
    Strips the fenced code block markers — returns only the inner mermaid content.
    """
    truncated = len(entries) > max_entries
    display = entries[-max_entries:] if truncated else entries
    full_markdown = build_diagram(display, session_id)

    inner: list[str] = []
    inside = False
    for line in full_markdown.split("\n"):
        if line.strip() == "```mermaid":
            inside = True
            continue
        if inside and line.strip() == "```":
            inside = False
            continue
        if inside:
            inner.append(line)

    return "\n".join(inner), truncated


def generate_report(log_file: Path, to_stdout: bool = False) -> None:
    session_id = log_file.stem
    entries = load_entries(log_file)

    if not entries:
        print(f"No entries found in {log_file}")
        return

    diagram = build_diagram(entries, session_id)

    report_lines = [
        f"# Flow Diagram — Session `{session_id}`",
        "",
        f"- **Start:** {entries[0].get('ts', '')}",
        f"- **End:** {entries[-1].get('ts', '')}",
        f"- **Events captured:** {len(entries)}",
        "",
        "## Sequence Diagram",
        "",
        diagram,
        "",
        "## Raw Event Log",
        "",
        "| # | Time | Event | Tool | Summary |",
        "|---|------|-------|------|---------|",
    ]

    for i, e in enumerate(entries, 1):
        ts   = e.get("ts", "")[-15:]
        inp  = e.get("input") or {}
        tool = e.get("tool", "")
        # Use pre-computed cmd field when available; fall back to input summary
        summary = e.get("cmd") or str(inp)[:60]
        report_lines.append(f"| {i} | {ts} | {e.get('event', '')} | {tool} | {_safe(summary, 80)} |")

    report = "\n".join(report_lines)

    if to_stdout:
        print(report)
    else:
        out = log_file.with_suffix(".md")
        out.write_text(report, encoding="utf-8")
        print(f"Diagram written to: {out}")


def list_sessions(log_dir: Path) -> None:
    if not log_dir.exists():
        print(f"No log directory found at {log_dir}")
        return
    logs = sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        print("No sessions found.")
        return
    print(f"{'Session ID':<50} {'Modified':<25} {'Events':>8}")
    print("-" * 85)
    for log in logs:
        mtime = datetime.fromtimestamp(log.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        lines = sum(1 for _ in open(log, encoding="utf-8"))
        print(f"{log.stem:<50} {mtime:<25} {lines:>8}")
