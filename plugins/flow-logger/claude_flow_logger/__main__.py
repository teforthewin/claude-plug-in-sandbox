"""
Enables: python -m claude_flow_logger {install|server}
"""
import sys


def main() -> None:
    commands = {
        "install": "claude_flow_logger.cli:install_main",
        "server":  "claude_flow_logger.cli:server_main",
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Usage: python -m claude_flow_logger [{' | '.join(commands)}]")
        sys.exit(1)

    cmd = sys.argv.pop(1)
    module_path, func_name = commands[cmd].rsplit(":", 1)

    from importlib import import_module
    mod = import_module(module_path)
    getattr(mod, func_name)()


if __name__ == "__main__":
    main()
