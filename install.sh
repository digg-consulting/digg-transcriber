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

CONFIG_DIR="${XDG_CONFIG_HOME}/digg/digg-transcriber"
HF_HOME="${XDG_CACHE_HOME}/digg/digg-transcriber/huggingface"
HF_HUB_CACHE="${HF_HOME}/hub"

echo "==> Installing digg-transcriber..."
echo "    Install dir: ${INSTALL_DIR}"
echo "    Config dir:  ${CONFIG_DIR}"

# Check for required tools
for cmd in curl tar python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not found in PATH." >&2
        exit 1
    fi
done

# Download and extract the source tarball
mkdir -p "${INSTALL_PARENT}"

TMP_TARBALL="$(mktemp /tmp/digg-transcriber-XXXXXX.tar.gz)"
echo "==> Downloading source tarball..."
curl -fsSL "https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz" -o "${TMP_TARBALL}"

echo "==> Extracting..."
tar -xzf "${TMP_TARBALL}" -C "${INSTALL_PARENT}"
rm -f "${TMP_TARBALL}"

# GitHub tarballs extract to REPO-BRANCH (e.g. digg-transcriber-main)
EXTRACTED_DIR="$(find "${INSTALL_PARENT}" -maxdepth 1 -type d -name "${REPO##*/}-*" | head -n 1)"
if [ -z "$EXTRACTED_DIR" ] || [ ! -d "$EXTRACTED_DIR" ]; then
    echo "Error: could not find extracted directory." >&2
    exit 1
fi

# Move into place (idempotent)
if [ -d "${INSTALL_DIR}" ]; then
    rm -rf "${INSTALL_DIR}"
fi
mv "${EXTRACTED_DIR}" "${INSTALL_DIR}"

# Create XDG directories
mkdir -p "${CONFIG_DIR}"
mkdir -p "${HF_HOME}"
mkdir -p "${BIN_DIR}"

# Create wrapper script
WRAPPER="${BIN_DIR}/digg-transcriber"
if [ ! -f "${WRAPPER}" ] || ! grep -q "digg-transcriber wrapper" "${WRAPPER}" 2>/dev/null; then
    echo "==> Creating wrapper script at ${WRAPPER}"
    cat > "${WRAPPER}" <<EOF
#!/usr/bin/env bash
# digg-transcriber wrapper
set -euo pipefail

export HF_HOME="\${XDG_CACHE_HOME:-\$HOME/.cache}/digg/digg-transcriber/huggingface"
export HF_HUB_CACHE="\${HF_HOME}/hub"
export PYTHONPATH="${INSTALL_DIR}/src"

exec python3 -m digg_transcriber.cli "\$@"
EOF
    chmod +x "${WRAPPER}"
fi

# Ensure PATH includes local bin
if ! echo "${PATH}" | grep -q "${BIN_DIR}"; then
    echo ""
    echo "Add this line to your shell config (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"${BIN_DIR}:\${PATH}\""
fi

echo ""
echo "==> Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Restart your shell or run: source ~/.zshrc (or ~/.bashrc)"
echo "  2. Run 'digg-transcriber init' to create your config"
echo "  3. See docs/HUGGINGFACE.md for model setup"
echo ""
echo "Documentation: https://github.com/${REPO}"