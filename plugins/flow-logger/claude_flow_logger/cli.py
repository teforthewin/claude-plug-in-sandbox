"""
CLI entry points for the claude-flow-logger package.

  flow-server                    — start web dashboard (reads native ~/.claude/ sessions)
  flow-diagram [session-id]      — generate Mermaid diagram from a native session
  flow-install                   — manage hook installation (legacy; no hooks needed)
"""

import json
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# flow-server — web dashboard
# ---------------------------------------------------------------------------

def server_main() -> None:
    from .server import run
    run(None)


# ---------------------------------------------------------------------------
# flow-diagram — CLI diagram generator (native sessions)
# ---------------------------------------------------------------------------

def diagram_main() -> None:
    from . import parser as _parser
    from .diagram import build_diagram

    args = sys.argv[1:]

    if "--list" in args:
        sessions = _parser.discover_sessions()
        if not sessions:
            print("No Claude Code sessions found.")
            return
        from datetime import datetime
        print(f"{'Session ID':<38} {'Project':<20} {'Modified':<20} {'Events':>6}")
        print("-" * 90)
        for ps in sessions:
            mtime = datetime.fromtimestamp(ps.mtime).strftime("%Y-%m-%d %H:%M")
            marker = " *LIVE*" if ps.is_active else ""
            print(f"{ps.session_id:<38} {ps.project:<20} {mtime:<20} {len(ps.events):>6}{marker}")
        return

    to_stdout  = "--stdout" in args
    positional = [a for a in args if not a.startswith("--")]

    sessions = _parser.discover_sessions()
    if not sessions:
        print("No Claude Code sessions found.")
        sys.exit(1)

    if positional:
        sid = positional[0]
        ps  = next((s for s in sessions if s.session_id.startswith(sid)), None)
        if ps is None:
            print(f"Session '{sid}' not found. Use --list to see available sessions.")
            sys.exit(1)
    else:
        ps = sessions[0]
        print(f"Using most recent session: {ps.session_id} ({ps.project})")

    diagram = build_diagram(ps.events, ps.session_id)
    if to_stdout:
        print(diagram)
    else:
        out = Path(f"flow-diagram-{ps.session_id[:8]}.md")
        out.write_text(
            f"# Flow Diagram — {ps.project} / {ps.session_id[:8]}\n\n"
            f"- **Start:** {ps.first_ts()}\n"
            f"- **End:**   {ps.last_ts()}\n"
            f"- **Events:** {len(ps.events)}\n\n"
            + diagram + "\n",
            encoding="utf-8",
        )
        print(f"Diagram written to: {out}")


# ---------------------------------------------------------------------------
# flow-install — legacy hook manager (uninstall only)
# ---------------------------------------------------------------------------

_HOOK_MARKER = "claude-flow-logger"


def _hooks_already_installed(settings: dict) -> bool:
    for hook_list in settings.get("hooks", {}).values():
        for block in hook_list:
            if block.get("_source") == _HOOK_MARKER:
                return True
    return False


def _remove_hooks(settings: dict) -> dict:
    hooks = settings.get("hooks", {})
    for event, blocks in list(hooks.items()):
        hooks[event] = [b for b in blocks if b.get("_source") != _HOOK_MARKER]
        if not hooks[event]:
            del hooks[event]
    return settings


def _find_settings_json(start: Path) -> Path | None:
    current = start
    for _ in range(5):
        candidate = current / ".claude" / "settings.json"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    global_settings = Path.home() / ".claude" / "settings.json"
    return global_settings if global_settings.exists() else None


def install_main() -> None:
    args = sys.argv[1:]

    if "--uninstall" in args:
        # Remove legacy hooks from any settings.json that has them
        settings_path = _find_settings_json(Path.cwd())
        if settings_path is None:
            print("No settings.json found with legacy hooks.")
            return
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
        if not _hooks_already_installed(settings):
            print("No claude-flow-logger hooks found — nothing to remove.")
            return
        settings = _remove_hooks(settings)
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Legacy hooks removed from {settings_path}")
        return

    # Native mode: no hooks needed
    print()
    print("claude-flow-logger v0.5+ reads native Claude Code session files directly.")
    print("No hooks need to be installed.")
    print()
    from . import parser as _parser
    sessions = _parser.discover_sessions()
    print(f"  Sessions dir : {_parser.CLAUDE_PROJECTS_DIR}")
    print(f"  Sessions found: {len(sessions)}")
    print()
    print("  Run 'flow-server' to start the dashboard.")
    print("  Run 'flow-install --uninstall' to remove any legacy hooks.")
    print()
