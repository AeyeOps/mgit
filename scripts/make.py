#!/usr/bin/env python3
"""
mgit build system - Display available make commands.

Usage: uv run python scripts/make.py [command] [args...]
"""
import subprocess
import sys
from pathlib import Path

# Try to use Rich for colorful output, fall back to plain text
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

SCRIPT_DIR = Path(__file__).parent

# Command registry: name -> (script, description, examples)
COMMANDS = {
    "test": (
        "make_test.py",
        "Run pytest test suite",
        [
            "uv run python scripts/make.py test",
            "uv run python scripts/make.py test -v",
            "uv run python scripts/make.py test tests/unit/",
            "uv run python scripts/make.py test -m unit",
        ],
    ),
    "lint": (
        "make_lint.py",
        "Run ruff linter to check code quality",
        [
            "uv run python scripts/make.py lint",
            "uv run python scripts/make.py lint --fix",
        ],
    ),
    "format": (
        "make_format.py",
        "Run ruff formatter on codebase",
        [
            "uv run python scripts/make.py format",
            "uv run python scripts/make.py format --check",
        ],
    ),
    "build": (
        "make_build.py",
        "Build standalone executables",
        [
            "uv run python scripts/make.py build",
            "uv run python scripts/make.py build --target linux",
            "uv run python scripts/make.py build --target windows",
            "uv run python scripts/make.py build --target linux --install",
        ],
    ),
    "clean": (
        "make_clean.py",
        "Remove build artifacts and caches",
        [
            "uv run python scripts/make.py clean",
        ],
    ),
    "version": (
        "make_version.py",
        "Bump project version (patch/minor/major)",
        [
            "uv run python scripts/make.py version --bump patch",
            "uv run python scripts/make.py version --bump minor",
            "uv run python scripts/make.py version --bump major",
        ],
    ),
    "test-binary": (
        "test_binary.py",
        "Test the standalone binary at /opt/bin/mgit",
        [
            "uv run python scripts/make.py test-binary",
            "uv run python scripts/make.py test-binary --verbose",
        ],
    ),
}


def show_help_rich():
    """Display help using Rich formatting."""
    console = Console()

    # Header
    title = Text()
    title.append("🔧 ", style="bold")
    title.append("mgit", style="bold cyan")
    title.append(" Build System", style="bold")

    console.print()
    console.print(Panel(title, border_style="cyan", padding=(0, 2)))
    console.print()

    # Commands table
    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("Command", style="bold green", width=14)
    table.add_column("Description", style="white")
    table.add_column("Example", style="dim cyan")

    for name, (script, description, examples) in COMMANDS.items():
        table.add_row(name, description, examples[0].replace("uv run python scripts/make.py ", ""))

    console.print(table)
    console.print()

    # Usage hint
    usage = Text()
    usage.append("Usage: ", style="dim")
    usage.append("uv run python scripts/make.py ", style="cyan")
    usage.append("<command>", style="bold yellow")
    usage.append(" [args...]", style="dim yellow")
    console.print(usage)
    console.print()

    # Quick aliases hint
    hint = Text()
    hint.append("Tip: ", style="bold blue")
    hint.append("You can also run commands directly: ", style="dim")
    hint.append("uv run python scripts/make_test.py -v", style="cyan dim")
    console.print(hint)
    console.print()


def show_help_plain():
    """Display help using plain text (no Rich)."""
    print()
    print("=" * 50)
    print("  mgit Build System")
    print("=" * 50)
    print()
    print("Commands:")
    print("-" * 50)
    for name, (script, description, examples) in COMMANDS.items():
        print(f"  {name:<14} {description}")
    print()
    print("Usage: uv run python scripts/make.py <command> [args...]")
    print()


def run_command(command: str, args: list[str]) -> int:
    """Run a make command with arguments."""
    if command not in COMMANDS:
        print(f"Error: Unknown command '{command}'")
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        return 1

    script = COMMANDS[command][0]
    script_path = SCRIPT_DIR / script

    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return 1

    # Run the script with passed arguments
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=SCRIPT_DIR.parent,
    )
    return result.returncode


def main():
    if len(sys.argv) < 2:
        # No command specified - show help
        if HAS_RICH:
            show_help_rich()
        else:
            show_help_plain()
        return 0

    command = sys.argv[1]

    # Handle help explicitly
    if command in ("--help", "-h", "help"):
        if HAS_RICH:
            show_help_rich()
        else:
            show_help_plain()
        return 0

    # Run the command
    return run_command(command, sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
