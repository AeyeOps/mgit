#!/usr/bin/env python3
"""
mgit build system - Display available make commands.

Parses the Makefile to extract targets and their descriptions.
Usage: make [target] or uv run python scripts/make.py [command]
"""
import re
import subprocess
import sys
from pathlib import Path

# Try to use Rich for colorful output, fall back to plain text
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
MAKEFILE = REPO_ROOT / "Makefile"

# Targets to hide from help (internal/alias targets)
HIDDEN_TARGETS = {"help", "install"}


def parse_makefile() -> dict[str, str]:
    """
    Parse Makefile to extract targets and their descriptions.

    Convention: A comment line immediately before a target is its description.
    Example:
        # Run pytest test suite
        test:
            @uv run ...

    Returns:
        dict mapping target name to description
    """
    if not MAKEFILE.exists():
        return {}

    content = MAKEFILE.read_text()
    lines = content.splitlines()

    targets = {}
    pending_comment = None

    for line in lines:
        # Check for comment line
        if line.startswith("#"):
            pending_comment = line[1:].strip()
            continue

        # Check for target definition (name followed by colon)
        match = re.match(r"^([a-zA-Z0-9_-]+):\s*", line)
        if match:
            target_name = match.group(1)
            # Skip hidden targets
            if target_name not in HIDDEN_TARGETS:
                # Use pending comment as description, or generate one
                if pending_comment:
                    targets[target_name] = pending_comment
                else:
                    targets[target_name] = f"Run {target_name}"
            pending_comment = None
        elif line.strip() and not line.startswith("\t") and not line.startswith("."):
            # Non-target, non-command line - reset pending comment
            pending_comment = None

    return targets


def show_help_rich(targets: dict[str, str]):
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
    table.add_column("Target", style="bold green", width=14)
    table.add_column("Description", style="white")

    for name, description in targets.items():
        table.add_row(name, description)

    console.print(table)
    console.print()

    # Usage hint
    usage = Text()
    usage.append("Usage: ", style="dim")
    usage.append("make ", style="cyan")
    usage.append("<target>", style="bold yellow")
    usage.append("  or  ", style="dim")
    usage.append("make ", style="cyan")
    usage.append("<target>", style="bold yellow")
    usage.append(" ARGS=", style="dim yellow")
    usage.append("\"...\"", style="yellow")
    console.print(usage)
    console.print()


def show_help_plain(targets: dict[str, str]):
    """Display help using plain text (no Rich)."""
    print()
    print("=" * 50)
    print("  mgit Build System")
    print("=" * 50)
    print()
    print("Targets:")
    print("-" * 50)
    for name, description in targets.items():
        print(f"  {name:<14} {description}")
    print()
    print("Usage: make <target>  or  make <target> ARGS=\"...\"")
    print()


def run_command(command: str, args: list[str], targets: dict[str, str]) -> int:
    """Run a make target by delegating to the underlying script."""
    if command not in targets and command not in HIDDEN_TARGETS:
        print(f"Error: Unknown target '{command}'")
        print(f"Available targets: {', '.join(targets.keys())}")
        return 1

    # Map commands to their scripts
    script_map = {
        "test": "make_test.py",
        "test-e2e": "make_test.py",  # Same script, different marker
        "lint": "make_lint.py",
        "format": "make_format.py",
        "build": "make_build.py",
        "build-install": "make_build.py",
        "clean": "make_clean.py",
        "version": "make_version.py",
        "test-binary": "test_binary.py",
    }

    script = script_map.get(command)
    if not script:
        # Fall back to running via make
        result = subprocess.run(["make", command], cwd=REPO_ROOT)
        return result.returncode

    script_path = SCRIPT_DIR / script

    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return 1

    # Special handling for test-e2e
    if command == "test-e2e":
        args = ["-m", "e2e", *args]

    # Special handling for build-install
    if command == "build-install":
        args = ["--target", "linux", "--install", *args]

    # Run the script with passed arguments
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
    )
    return result.returncode


def main():
    targets = parse_makefile()

    if len(sys.argv) < 2:
        # No command specified - show help
        if HAS_RICH:
            show_help_rich(targets)
        else:
            show_help_plain(targets)
        return 0

    command = sys.argv[1]

    # Handle help explicitly
    if command in ("--help", "-h", "help"):
        if HAS_RICH:
            show_help_rich(targets)
        else:
            show_help_plain(targets)
        return 0

    # Run the command
    return run_command(command, sys.argv[2:], targets)


if __name__ == "__main__":
    sys.exit(main())
