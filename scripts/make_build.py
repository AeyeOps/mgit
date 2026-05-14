#!/usr/bin/env python3
"""Build mgit executable. Wraps existing shell scripts."""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent


def main():
    parser = argparse.ArgumentParser(description="Build mgit executable")
    parser.add_argument(
        "--target",
        choices=["linux", "macos", "windows", "all"],
        default="linux",
        help="Build target platform",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install after build (Linux: /usr/local/bin, macOS: ~/.local/bin)",
    )
    args = parser.parse_args()

    if args.target in ("linux", "macos", "all"):
        is_macos = args.target == "macos"
        label = "macOS" if is_macos else "Linux"
        print(f"Building {label} executable...")
        env = {}
        if args.install:
            env["INSTALL_TO_OPT_BIN"] = "1"
            if is_macos:
                env["INSTALL_DIR"] = str(Path.home() / ".local" / "bin")
        result = subprocess.run(
            ["bash", str(SCRIPT_DIR / "build_mac_and_linux.sh")],
            cwd=REPO_ROOT,
            env={**subprocess.os.environ, **env},
        )
        if result.returncode != 0:
            print(f"{label} build failed")
            sys.exit(result.returncode)

    if args.target in ("windows", "all"):
        print("Building Windows executable...")
        result = subprocess.run(
            ["bash", str(SCRIPT_DIR / "build_windows_from_wsl.sh")],
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print("Windows build failed")
            sys.exit(result.returncode)

    print("Build complete!")


if __name__ == "__main__":
    main()
