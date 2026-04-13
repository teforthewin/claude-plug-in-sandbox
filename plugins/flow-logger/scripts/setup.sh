#!/usr/bin/env bash
# setup.sh — called on SessionStart to install deps and start the dashboard.
# Reads native Claude Code session files from ~/.claude/projects/ — no hooks needed.
set -e

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-.}"
PLUGIN_DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/flow-logger}"
VENV="$PLUGIN_DATA/venv"
REQ="$PLUGIN_ROOT/requirements.txt"
REQ_STAMP="$PLUGIN_DATA/requirements.txt"
PID_FILE="$PLUGIN_DATA/dashboard.pid"

PORT="${CLAUDE_PLUGIN_OPTION_dashboard_port:-7842}"

# ── 1. Create venv if missing ──────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
  mkdir -p "$PLUGIN_DATA"
  python3 -m venv "$VENV" 2>/dev/null || python -m venv "$VENV"
fi

# ── 2. Install/update deps if requirements.txt changed ─────────────────────────
if ! diff -q "$REQ" "$REQ_STAMP" >/dev/null 2>&1; then
  "$VENV/bin/pip" install --quiet -r "$REQ" 2>/dev/null
  cp "$REQ" "$REQ_STAMP"
fi

# ── 3. Start dashboard if not already running ──────────────────────────────────
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0  # already running
  fi
fi

FLOW_SERVER_PORT="$PORT" \
  nohup "$VENV/bin/python" -c "
import sys, os
sys.path.insert(0, os.environ.get('CLAUDE_PLUGIN_ROOT', '.'))
from claude_flow_logger.server import run
run(None)
" >"$PLUGIN_DATA/dashboard.log" 2>&1 &

echo $! > "$PID_FILE"
exit 0
