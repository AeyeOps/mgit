#!/usr/bin/env bash
# Build mgit Linux binary using uv and PyInstaller
# Usage:
#   bash scripts/build_ubuntu.sh
#   INSTALL_TO_OPT_BIN=1 bash scripts/build_ubuntu.sh   # optionally copy to /opt/bin/mgit

set -euo pipefail

echo "[build_ubuntu] Using uv to build Linux binary…"
uv --version >/dev/null || { echo "uv is required. Install from https://astral.sh/uv"; exit 1; }

echo "[build_ubuntu] Syncing environment (dev extras)…"
uv sync --all-extras --dev

echo "[build_ubuntu] Building with PyInstaller (using mgit.spec)…"
uv run -- pyinstaller mgit.spec --clean

echo "[build_ubuntu] Build complete: dist/mgit"

if [[ "${INSTALL_TO_OPT_BIN:-0}" == "1" ]]; then
  echo "[build_ubuntu] Installing to /opt/bin/mgit (requires permissions)…"
  cp -f dist/mgit /opt/bin/mgit
  echo "[build_ubuntu] Installed /opt/bin/mgit"
fi

