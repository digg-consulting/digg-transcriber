#!/bin/bash
# install.sh - Standalone installer for digg-transcriber
# Usage: curl -fsSL https://raw.githubusercontent.com/digg-consulting/digg-transcriber/main/install.sh | bash

set -euo pipefail

REPO="digg-consulting/digg-transcriber"
BRANCH="main"
INSTALL_PARENT="${HOME}/.local/share/digg"
INSTALL_DIR="${INSTALL_PARENT}/digg-transcriber"
BIN_DIR="${HOME}/.local/bin"

# XDG directories
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
XDG_DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"

CONFIG_DIR="${XDG_CONFIG_HOME}/digg/digg-transcriber"
HF_HOME="${HF_HOME:-${XDG_CACHE_HOME}/huggingface}"
HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
UV_TOOL_DIR="${XDG_DATA_HOME}/digg/digg-transcriber/tool"

export XDG_CONFIG_HOME
export XDG_CACHE_HOME
export XDG_DATA_HOME
export HF_HOME
export HF_HUB_CACHE
export UV_TOOL_DIR
export PATH="${HOME}/.local/bin:${PATH}"

CLI_NAME="digg-transcriber"
CLI_BIN="${BIN_DIR}/${CLI_NAME}"

echo "==> Installing digg-transcriber..."
echo "    Install dir: ${INSTALL_DIR}"
echo "    Config dir:  ${CONFIG_DIR}"

# Check for required tools
for cmd in curl tar python3 uv; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not found in PATH." >&2
        exit 1
    fi
done

# Check for existing installation
if [ -d "${INSTALL_DIR}" ] && [ -f "${INSTALL_DIR}/src/digg_transcriber/cli.py" ]; then
    echo "==> Existing installation found at ${INSTALL_DIR}"
    if [ "${FORCE_INSTALL:-0}" != "1" ]; then
        if [ -t 0 ]; then
            read -p "Overwrite existing installation? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Installation cancelled. Existing installation left intact."
                exit 0
            fi
        else
            echo "Non-interactive mode detected. Proceeding with reinstall (remove ${INSTALL_DIR})."
        fi
    fi
    echo "==> Removing old installation..."
    rm -rf "${INSTALL_DIR}"
fi

# Download and extract the source tarball
mkdir -p "${INSTALL_PARENT}"

TMP_TARBALL="$(mktemp /tmp/digg-transcriber-XXXXXX.tar.gz)"
echo "==> Downloading source tarball..."
curl -fsSL "https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz" -o "${TMP_TARBALL}"

echo "==> Extracting..."
tar -xzf "${TMP_TARBALL}" -C "${INSTALL_PARENT}"
rm -f "${TMP_TARBALL}"

EXTRACTED_DIR="$(find "${INSTALL_PARENT}" -maxdepth 1 -type d -name "${REPO##*/}-*" | head -n 1)"
if [ -z "$EXTRACTED_DIR" ] || [ ! -d "$EXTRACTED_DIR" ]; then
    echo "Error: could not find extracted directory." >&2
    exit 1
fi

mv "${EXTRACTED_DIR}" "${INSTALL_DIR}"

# Create XDG directories
mkdir -p "${CONFIG_DIR}"
mkdir -p "${HF_HOME}"
mkdir -p "${BIN_DIR}"
mkdir -p "${UV_TOOL_DIR}"

cd "${INSTALL_DIR}"

echo "==> Installing Python dependencies (uv sync)..."
uv sync

echo "==> Installing CLI on PATH (uv tool install)..."
uv tool uninstall "${CLI_NAME}" 2>/dev/null || true
uv tool install --force -e .
if [[ ! -x "${CLI_BIN}" ]]; then
    echo "Expected executable at ${CLI_BIN} after uv tool install" >&2
    exit 1
fi

echo "    ${CLI_BIN}"

echo "==> Checking HuggingFace model cache..."
"${CLI_BIN}" check --model medium || true

echo ""
echo "==> Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Restart your shell or run: source ~/.zshrc (or ~/.bashrc)"
echo "  2. Run '${CLI_NAME} init' to create your config"
echo "  3. See docs/HUGGINGFACE.md for model setup"
echo ""
echo "Documentation: https://github.com/${REPO}"