#!/usr/bin/env python3
"""Run ruff linter matching CI configuration.

By default runs on mgit/ directory to match CI behavior.
Use --all to lint entire repository including tests and scripts.
"""

import subprocess
import sys

TARGET = "mgit/"

if __name__ == "__main__":
    args = sys.argv[1:]

    # Allow --all flag to lint everything (original behavior)
    if "--all" in args:
        args.remove("--all")
        target = "."
    else:
        target = TARGET

    cmd = ["ruff", "check", target, *args]
    sys.exit(subprocess.run(cmd).returncode)
