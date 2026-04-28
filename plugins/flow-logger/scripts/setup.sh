#!/usr/bin/env bash
# setup.sh — called on SessionStart to create the venv and install the package.
set -e

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-.}"
PLUGIN_DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/flow-logger}"
VENV="$PLUGIN_DATA/venv"
STAMP="$PLUGIN_DATA/.installed"

# Create venv if missing
if [ ! -d "$VENV" ]; then
  mkdir -p "$PLUGIN_DATA"
  python3 -m venv "$VENV"
fi

# Install/reinstall package if not yet stamped or plugin root changed
if [ ! -f "$STAMP" ] || [ "$PLUGIN_ROOT" != "$(cat "$STAMP" 2>/dev/null)" ]; then
  "$VENV/bin/pip" install --quiet --no-deps -e "$PLUGIN_ROOT"
  echo "$PLUGIN_ROOT" > "$STAMP"
fi
