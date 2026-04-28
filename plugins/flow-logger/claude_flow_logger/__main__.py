"""
Enables: python -m claude_flow_logger install
"""
import sys


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "install":
        print("Usage: python -m claude_flow_logger install [--global] [--uninstall]")
        sys.exit(1)

    sys.argv.pop(1)
    from claude_flow_logger.cli import install_main
    install_main()


if __name__ == "__main__":
    main()
