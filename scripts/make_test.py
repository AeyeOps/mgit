#!/usr/bin/env python3
"""Run pytest with optional arguments."""

import subprocess
import sys

if __name__ == "__main__":
    cmd = ["pytest", *sys.argv[1:]]
    sys.exit(subprocess.run(cmd).returncode)
