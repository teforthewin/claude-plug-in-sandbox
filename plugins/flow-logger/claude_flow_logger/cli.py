"""
CLI entry points for the claude-flow-logger package.

  flow-install               — register hooks in .claude/settings.json
  flow-install --global      — register hooks in ~/.claude/settings.json
  flow-install --uninstall   — remove hooks
"""

import json
import sys
from pathlib import Path


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
        settings_path = _find_settings_json(Path.cwd())
        if settings_path is None:
            print("No settings.json found with flow-logger hooks.")
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
        print(f"Hooks removed from {settings_path}")
        return

    use_global = "--global" in args
    if use_global:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = Path.cwd() / ".claude" / "settings.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        settings = {}

    if _hooks_already_installed(settings):
        print(f"Hooks already installed in {settings_path}")
        return

    python = sys.executable
    pkg    = str(Path(__file__).parent)

    hook_block = {
        "_source": _HOOK_MARKER,
        "hooks": [
            {
                "type": "command",
                "command": f"{python} {pkg}/logger.py {{event}}",
            }
        ],
    }

    hooks = settings.setdefault("hooks", {})
    for event, arg in [
        ("UserPromptSubmit", "prompt"),
        ("PreToolUse",       "pre"),
        ("PostToolUse",      "post"),
    ]:
        block = {**hook_block, "hooks": [{"type": "command", "command": f"{python} {pkg}/logger.py {arg}"}]}
        if event == "PreToolUse" or event == "PostToolUse":
            block["matcher"] = ".*"
        hooks.setdefault(event, []).append(block)

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Hooks installed in {settings_path}")
