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

# Remove uv tool installation
if command -v uv &>/dev/null; then
    echo "==> Removing uv tool..."
    uv tool uninstall digg-transcriber 2>/dev/null || true
else
    echo "==> uv not found, skipping tool uninstall"
fi

# Remove wrapper script
if [ -f "${WRAPPER}" ]; then
    echo "==> Removing wrapper script..."
    rm -f "${WRAPPER}"
else
    echo "==> No wrapper found at ${WRAPPER}"
fi

# Remove installed source
if [ -d "${INSTALL_DIR}" ]; then
    echo "==> Removing installed source..."
    rm -rf "${INSTALL_DIR}"
else
    echo "==> No install dir found at ${INSTALL_DIR}"
fi

# Prompt for config removal
if [ -t 0 ]; then
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
else
    echo "==> Non-interactive mode: keeping config directory."
fi

echo ""
echo "==> Uninstall complete."
echo ""
echo "Note: Python dependencies managed by uv are stored in uv's global tool cache"
echo "and may be shared with other tools. uv tool uninstall above removed the CLI entry."
echo ""
echo "To clean HuggingFace model cache:"
echo "  rm -rf ${HOME}/.cache/digg/digg-transcriber/huggingface"
echo ""
echo "To clean uv's tool cache (shared):"
echo "  uv cache clean"
