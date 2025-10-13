#!/usr/bin/env bash
# Build Linux (Ubuntu/WSL) and then trigger Windows build from WSL wrapper
# Usage:
#   bash scripts/build_all.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[build_all] Step 1/2: Linux build via uv"
bash "$SCRIPT_DIR/build_ubuntu.sh"

echo "[build_all] Step 2/2: Windows build (from WSL wrapper if available)"
if grep -qi microsoft /proc/version 2>/dev/null; then
  if [[ -x "$SCRIPT_DIR/build_windows_from_wsl.sh" || -f "$SCRIPT_DIR/build_windows_from_wsl.sh" ]]; then
    bash "$SCRIPT_DIR/build_windows_from_wsl.sh"
  else
    echo "[build_all] scripts/build_windows_from_wsl.sh not found; skipping Windows build"
  fi
else
  echo "[build_all] Not running under WSL; skipping Windows build"
fi

echo "[build_all] Done"

