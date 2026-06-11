#!/bin/bash
# uninstall.sh - Remove digg-transcriber
# Usage: curl -fsSL https://raw.githubusercontent.com/digg-consulting/digg-transcriber/main/uninstall.sh | bash

set -euo pipefail

REPO="digg-consulting/digg-transcriber"
BRANCH="main"
INSTALL_DIR="${HOME}/.local/share/digg/digg-transcriber"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/digg/digg-transcriber"

WRAPPER="${BIN_DIR}/digg-transcriber"

echo "==> Uninstalling digg-transcriber..."
echo "    Install dir: ${INSTALL_DIR}"
echo "    Config dir:  ${CONFIG_DIR}"

if [ -f "${WRAPPER}" ]; then
    echo "==> Removing wrapper script..."
    rm -f "${WRAPPER}"
else
    echo "==> No wrapper found at ${WRAPPER}"
fi

if [ -d "${INSTALL_DIR}" ]; then
    echo "==> Removing installed source..."
    rm -rf "${INSTALL_DIR}"
else
    echo "==> No install dir found at ${INSTALL_DIR}"
fi

read -p "Remove config directory ${CONFIG_DIR}? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "${CONFIG_DIR}" ]; then
        rm -rf "${CONFIG_DIR}"
        echo "==> Removed config directory."
    else
        echo "==> No config dir found at ${CONFIG_DIR}"
    fi
else
    echo "==> Keeping config directory."
fi

echo ""
echo "==> Uninstall complete."
echo ""
echo "Note: Python dependencies installed by the installer (requests, feedparser, etc.)"
echo "were installed with '--user' and are shared with other tools. They were NOT removed."
echo "To remove them manually:"
echo "  pip3 uninstall requests feedparser pyyaml watchdog"
echo ""
echo "To clean HuggingFace model cache:"
echo "  rm -rf ${HOME}/.cache/digg/digg-transcriber/huggingface"
