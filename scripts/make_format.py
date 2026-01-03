#!/usr/bin/env python3
"""Run ruff formatter. Use --check to verify without modifying."""
import subprocess
import sys

if __name__ == "__main__":
    cmd = ["ruff", "format", ".", *sys.argv[1:]]
    sys.exit(subprocess.run(cmd).returncode)
