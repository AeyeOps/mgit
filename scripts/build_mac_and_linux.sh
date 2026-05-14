#!/usr/bin/env bash
# Build mgit standalone binary for Linux or macOS using uv and PyInstaller.
# PyInstaller produces a host-platform binary (ELF on Linux, Mach-O on macOS)
# from the cross-platform mgit.spec.
#
# Usage:
#   bash scripts/build_mac_and_linux.sh
#   INSTALL_TO_OPT_BIN=1 bash scripts/build_mac_and_linux.sh                # build and install (Linux default: /usr/local/bin)
#   INSTALL_TO_OPT_BIN=1 SKIP_BUILD=1 bash scripts/build_mac_and_linux.sh   # install existing dist/mgit
#   INSTALL_DIR="$HOME/.local/bin" INSTALL_TO_OPT_BIN=1 bash ...            # override install location (used by macOS targets)

set -euo pipefail

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "[build] Using uv to build standalone binary…"
  uv --version >/dev/null || { echo "uv is required. Install from https://astral.sh/uv"; exit 1; }

  echo "[build] Syncing environment (dev extras)…"
  uv sync --all-extras --dev

  echo "[build] Building with PyInstaller (using mgit.spec)…"
  uv run -- pyinstaller mgit.spec --clean

  echo "[build] Build complete: dist/mgit"
else
  echo "[build] Skipping build; using existing dist/mgit"
fi

if [[ "${INSTALL_TO_OPT_BIN:-0}" == "1" ]]; then
  INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
  BINARY_PATH="${INSTALL_DIR}/mgit"

  if [[ ! -f "dist/mgit" ]]; then
    echo "[build] dist/mgit does not exist; run the build target first"
    exit 1
  fi

  echo "[build] Creating ${INSTALL_DIR} if needed…"
  mkdir -p "${INSTALL_DIR}"

  echo "[build] Installing to ${BINARY_PATH}…"
  cp -f dist/mgit "${BINARY_PATH}"
  chmod +x "${BINARY_PATH}"
  echo "[build] Installed ${BINARY_PATH}"

  # Detect shell and set appropriate rc file
  SHELL_NAME="$(basename "${SHELL:-/bin/bash}")"
  case "${SHELL_NAME}" in
    zsh)  RC_FILE="${HOME}/.zshrc" ;;
    bash) RC_FILE="${HOME}/.bashrc" ;;
    *)    RC_FILE="${HOME}/.bashrc" ;;  # Default to bashrc for unknown shells
  esac

  PATH_EXPORT="export PATH=\"${INSTALL_DIR}:\$PATH\""

  echo "[build] Detected shell: ${SHELL_NAME}, rc file: ${RC_FILE}"

  if [[ ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
    echo "[build] ${INSTALL_DIR} not in current PATH, checking ${RC_FILE}…"

    if [[ -f "${RC_FILE}" ]]; then
      if grep -qF "${INSTALL_DIR}" "${RC_FILE}" 2>/dev/null; then
        echo "[build] ${INSTALL_DIR} already referenced in ${RC_FILE}"
      else
        echo "[build] Adding ${INSTALL_DIR} to PATH in ${RC_FILE}…"
        echo "" >> "${RC_FILE}"
        echo "# Added by mgit installer" >> "${RC_FILE}"
        echo "${PATH_EXPORT}" >> "${RC_FILE}"
        echo "[build] Added to ${RC_FILE}. Run 'source ${RC_FILE}' or restart shell."
      fi
    else
      echo "[build] Creating ${RC_FILE} with PATH…"
      echo "# Added by mgit installer" > "${RC_FILE}"
      echo "${PATH_EXPORT}" >> "${RC_FILE}"
      echo "[build] Created ${RC_FILE}. Run 'source ${RC_FILE}' or restart shell."
    fi
  else
    echo "[build] ${INSTALL_DIR} already in PATH"
  fi
fi
