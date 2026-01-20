#!/usr/bin/env bash
# Build mgit Linux binary using uv and PyInstaller
# Usage:
#   bash scripts/build_ubuntu.sh
#   INSTALL_TO_OPT_BIN=1 bash scripts/build_ubuntu.sh   # optionally install to /usr/local/bin/mgit

set -euo pipefail

echo "[build_ubuntu] Using uv to build Linux binary…"
uv --version >/dev/null || { echo "uv is required. Install from https://astral.sh/uv"; exit 1; }

echo "[build_ubuntu] Syncing environment (dev extras)…"
uv sync --all-extras --dev

echo "[build_ubuntu] Building with PyInstaller (using mgit.spec)…"
uv run -- pyinstaller mgit.spec --clean

echo "[build_ubuntu] Build complete: dist/mgit"

if [[ "${INSTALL_TO_OPT_BIN:-0}" == "1" ]]; then
  INSTALL_DIR="/usr/local/bin"
  BINARY_PATH="${INSTALL_DIR}/mgit"

  echo "[build_ubuntu] Creating ${INSTALL_DIR} if needed…"
  sudo mkdir -p "${INSTALL_DIR}"

  echo "[build_ubuntu] Installing to ${BINARY_PATH}…"
  sudo cp -f dist/mgit "${BINARY_PATH}"
  sudo chmod +x "${BINARY_PATH}"
  echo "[build_ubuntu] Installed ${BINARY_PATH}"

  # Detect shell and set appropriate rc file
  SHELL_NAME="$(basename "${SHELL:-/bin/bash}")"
  case "${SHELL_NAME}" in
    zsh)  RC_FILE="${HOME}/.zshrc" ;;
    bash) RC_FILE="${HOME}/.bashrc" ;;
    *)    RC_FILE="${HOME}/.bashrc" ;;  # Default to bashrc for unknown shells
  esac

  PATH_EXPORT='export PATH="/usr/local/bin:$PATH"'

  echo "[build_ubuntu] Detected shell: ${SHELL_NAME}, rc file: ${RC_FILE}"

  if [[ ":${PATH}:" != *":/usr/local/bin:"* ]]; then
    echo "[build_ubuntu] /usr/local/bin not in current PATH, checking ${RC_FILE}…"

    if [[ -f "${RC_FILE}" ]]; then
      # Check if already present in rc file (various forms)
      if grep -qE '^[^#]*export PATH=.*(/usr/local/bin|"\$PATH").*(/usr/local/bin|"\$PATH")' "${RC_FILE}" 2>/dev/null || \
         grep -qF '/usr/local/bin' "${RC_FILE}" 2>/dev/null; then
        echo "[build_ubuntu] /usr/local/bin already referenced in ${RC_FILE}"
      else
        echo "[build_ubuntu] Adding /usr/local/bin to PATH in ${RC_FILE}…"
        echo "" >> "${RC_FILE}"
        echo "# Added by mgit installer" >> "${RC_FILE}"
        echo "${PATH_EXPORT}" >> "${RC_FILE}"
        echo "[build_ubuntu] Added to ${RC_FILE}. Run 'source ${RC_FILE}' or restart shell."
      fi
    else
      echo "[build_ubuntu] Creating ${RC_FILE} with PATH…"
      echo "# Added by mgit installer" > "${RC_FILE}"
      echo "${PATH_EXPORT}" >> "${RC_FILE}"
      echo "[build_ubuntu] Created ${RC_FILE}. Run 'source ${RC_FILE}' or restart shell."
    fi
  else
    echo "[build_ubuntu] /usr/local/bin already in PATH"
  fi
fi

