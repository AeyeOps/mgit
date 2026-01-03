#!/usr/bin/env python3
"""Run e2e tests against real provider APIs."""

import subprocess
import sys

if __name__ == "__main__":
    cmd = ["pytest", "-m", "e2e", "tests/e2e/", *sys.argv[1:]]
    sys.exit(subprocess.run(cmd).returncode)
