#!/usr/bin/env python3
"""Run ruff linter with optional arguments."""

import subprocess
import sys

if __name__ == "__main__":
    cmd = ["ruff", "check", ".", *sys.argv[1:]]
    sys.exit(subprocess.run(cmd).returncode)
