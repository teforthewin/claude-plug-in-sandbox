# claude-flow-logger

Real-time observability plugin for [Claude Code](https://claude.ai/code). Hooks into agent spawns, skill invocations, slash commands, and tool calls, then streams a live dashboard to your browser.

## How it works

```
Claude Code
    │  hook events (JSON on stdin)
    ▼
flow-logger pre|post|prompt        ← called by Claude Code hooks
    │  appends one JSONL line per event
    ▼
~/.claude/flow-logs/<project>/
    <session-id>.jsonl             ← append-only event log
    │
    └── flow-server  (FastAPI + SSE + watchdog)
            │  watches directory, pushes new entries via SSE
            └── http://localhost:7842  ← browser dashboard
```

1. Claude Code fires **PreToolUse**, **PostToolUse**, and **UserPromptSubmit** hooks on every action.
2. The `flow-logger` script receives each hook payload, filters it, and appends a JSONL line to a session log file.
3. The dashboard server watches the log directory with `watchdog` and pushes new entries to connected browsers via Server-Sent Events (SSE).
4. The server auto-starts on the first hook event of a session (no manual launch needed).

## What it captures

| Event | Pre | Post | Details logged |
|-------|:---:|:----:|----------------|
| **User prompts** | ✓ | — | All user messages (displayed in rose/pink in the flow tree) |
| `/slash-commands` | ✓ | — | Via `UserPromptSubmit` — messages starting with `/` |
| `Agent` | ✓ | ✓ | Agent type, description, name, prompt (truncated) |
| `Skill` | ✓ | ✓ | Skill name, args |
| `Bash` | ✓ | ✓ | Description or command (truncated), stdout/stderr |
| `SendMessage` | ✓ | ✓ | Recipient, message (truncated) |
| `TaskCreate` | ✓ | ✓ | Task title |
| `TaskUpdate` | ✓ | ✓ | Task id, new status |
| `Read` / `Glob` / `Grep` | ✓ | — | Only when path is inside `.claude/` config dirs |

System-injected messages (command caveats, tool results) are automatically filtered out. Everything else (file edits, web fetches, regular reads) is filtered out to keep logs focused.

## Dashboard

The dashboard has two themes — **Classic** (Alpine.js + Tailwind, light) and **Cyber** (Vue 3, dark/neon). Switch between them via the link in the top bar.

### Tabs (Classic theme)

| Tab | Description |
|-----|-------------|
| **Flow Tree** | Hierarchical view of agent/tool calls as a nested tree. Nodes are expandable, colored by tool type, and show inline token counts when stats are available. |
| **Events** | Flat table of all captured events — timestamp, direction (pre/post), tool name, summary, and token count. Click a row to expand the full response. |

### Session sidebar

The left sidebar lists all sessions grouped by project. Each entry shows the date, time range, event count, and a **LIVE** badge for active sessions.

### Stats panel

When a session is selected, a stats panel appears above the flow tree showing:

- **Token breakdown** — input, output, cache read, cache create (read from Claude's native session JSONL)
- **Tool usage** — bar chart of the most-used tools
- **Spawned agents** — list of child agent sessions

### Initial prompt

A collapsible box at the top of each session shows the first user message that started the session. Collapsed by default — click to expand.

## Installation

### As a Claude Code plugin

If this package is registered as a Claude Code plugin (via the `.claude-plugin/` directory), installation is automatic. The plugin's `SessionStart` hook:

1. Creates a Python venv in the plugin data directory
2. Installs dependencies from `requirements.txt`
3. Starts the dashboard server as a background process

No manual setup required.

### As a standalone package

```bash
bash install.sh
```

This installs the package (via `uv` or `pip`) and registers hooks globally in `~/.claude/settings.json`. To uninstall:

```bash
bash install.sh --uninstall
```

Or install the package and wire hooks manually:

```bash
pip install .              # or: uv tool install .
flow-install               # project-local hooks (in .claude/settings.json)
flow-install --global      # global hooks (in ~/.claude/settings.json)
flow-install --uninstall   # remove hooks
```

**Requires Python 3.11+.**

## CLI commands

| Command | Description |
|---------|-------------|
| `flow-logger pre\|post\|prompt` | Hook handler — called by Claude Code, reads JSON from stdin. Not invoked manually. |
| `flow-server` | Start the web dashboard. Auto-started by the plugin; use manually for standalone installs. |
| `flow-install` | Register/remove hooks in `settings.json`. |
| `flow-diagram` | Generate a Mermaid sequence diagram from a log file (offline, no server needed). |

### flow-server

```bash
flow-server                          # default port 7842
FLOW_SERVER_PORT=9000 flow-server    # custom port
```

### flow-diagram

```bash
flow-diagram                  # latest session
flow-diagram <session-id>     # specific session
flow-diagram --list           # list all sessions
flow-diagram --stdout         # print to stdout instead of file
```

## Log format

Each session produces one JSONL file at `~/.claude/flow-logs/<project>/<session-id>.jsonl`.

**Pre event:**

```json
{
  "ts": "2025-04-09T10:23:45.123456+00:00",
  "action_id": "a3f8c1d2e4b6",
  "event": "pre",
  "tool": "Agent",
  "cmd": "agent:scenario-designer convert story to scenarios",
  "input": {
    "agent": "scenario-designer",
    "description": "convert story to scenarios",
    "name": "designer-1",
    "prompt": "You are scenario-designer…[truncated]"
  }
}
```

**Post event** (adds `response` and optional `tokens`):

```json
{
  "ts": "2025-04-09T10:23:47.456789+00:00",
  "action_id": "a3f8c1d2e4b6",
  "event": "post",
  "tool": "Agent",
  "cmd": "agent:scenario-designer convert story to scenarios",
  "input": { "...": "same as pre" },
  "response": "Scenarios written to docs/test-cases/payments/",
  "tokens": { "total": 4821, "input": 3200, "output": 1621 }
}
```

**User prompt event:**

```json
{
  "ts": "2025-04-09T10:23:38.000000+00:00",
  "action_id": "d4e5f6a7b8c9",
  "event": "prompt",
  "tool": "User",
  "cmd": "convert the payment story to test scenarios",
  "input": { "message": "convert the payment story to test scenarios" }
}
```

**Command event** (slash commands):

```json
{
  "ts": "2025-04-09T10:23:40.000000+00:00",
  "action_id": "f1e2d3c4b5a6",
  "event": "command",
  "tool": "Command",
  "cmd": "/generate-pipeline FULL",
  "input": { "command": "/generate-pipeline", "args": "FULL" }
}
```

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/sessions` | List all sessions with metadata (id, project, event count, timestamps, active status) |
| `GET /api/sessions/{id}` | All entries for a session |
| `GET /api/sessions/{id}/stream` | SSE stream — pushes new entries in real time |
| `GET /api/sessions/{id}/stats` | Token usage, tool breakdown, spawned agents, initial prompt (from Claude's native session JSONL) |
| `GET /api/sessions/{id}/diagram` | Mermaid sequence diagram source |
| `GET /` | Classic dashboard (Alpine.js + Tailwind) |
| `GET /cyber` | Cyber dashboard (Vue 3, dark theme) |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOW_LOG_DIR` | `~/.claude/flow-logs/<project>/` | Where JSONL logs are written |
| `FLOW_SERVER_PORT` | `7842` | Dashboard HTTP port |

When installed as a plugin, these can also be set via `plugin.json` user config (`log_directory`, `dashboard_port`).

## Project structure

```
claude-flow-logger/
├── .claude-plugin/
│   ├── plugin.json          # Claude Code plugin manifest
│   └── marketplace.json     # Plugin marketplace metadata
├── claude_flow_logger/
│   ├── logger.py            # Hook handler — filters + writes JSONL
│   ├── server.py            # FastAPI server + embedded dashboard HTML
│   ├── diagram.py           # Mermaid diagram generator
│   └── cli.py               # CLI entry points
├── hooks/
│   └── hooks.json           # Plugin hook definitions
├── scripts/
│   └── setup.sh             # Plugin SessionStart setup script
├── install.sh               # Standalone installer
├── requirements.txt         # Python dependencies
└── pyproject.toml           # Package metadata
```

## License

MIT
