#!/usr/bin/env python3
"""Run ruff formatter matching CI configuration.

By default runs on mgit/ directory to match CI behavior.
Use --check to verify without modifying (like CI does).
Use --all to format entire repository including tests and scripts.
"""

import subprocess
import sys

TARGET = "mgit/"

if __name__ == "__main__":
    args = sys.argv[1:]

    # Allow --all flag to format everything (original behavior)
    if "--all" in args:
        args.remove("--all")
        target = "."
    else:
        target = TARGET

    cmd = ["ruff", "format", target, *args]
    sys.exit(subprocess.run(cmd).returncode)
