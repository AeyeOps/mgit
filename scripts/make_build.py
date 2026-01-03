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
        choices=["linux", "windows", "all"],
        default="linux",
        help="Build target platform",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install to /opt/bin/mgit after Linux build",
    )
    args = parser.parse_args()

    if args.target in ("linux", "all"):
        print("Building Linux executable...")
        env = {"INSTALL_TO_OPT_BIN": "1"} if args.install else {}
        result = subprocess.run(
            ["bash", str(SCRIPT_DIR / "build_ubuntu.sh")],
            cwd=REPO_ROOT,
            env={**subprocess.os.environ, **env},
        )
        if result.returncode != 0:
            print("Linux build failed")
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
