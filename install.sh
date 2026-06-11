#!/bin/bash
# install.sh - Standalone installer for digg-transcriber
# Usage: curl -fsSL https://raw.githubusercontent.com/digg-consulting/digg-transcriber/main/install.sh | bash
#   or: bash install.sh  (from a cloned checkout)

set -euo pipefail

REPO="digg-consulting/digg-transcriber"
BRANCH="main"
INSTALL_DIR="${HOME}/.local/share/digg/digg-transcriber"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/digg/digg-transcriber"

# XDG directories
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
XDG_DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"

CONFIG_DIR="${XDG_CONFIG_HOME}/digg/digg-transcriber"
HF_HOME="${XDG_CACHE_HOME}/digg/digg-transcriber/huggingface"
HF_HUB_CACHE="${HF_HOME}/hub"

echo "==> Installing digg-transcriber..."
echo "    Install dir: ${INSTALL_DIR}"
echo "    Config dir:  ${CONFIG_DIR}"

# Check for required tools
for cmd in git pip python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not found in PATH." >&2
        exit 1
    fi
done

# Clone or update the repository
if [ -d "${INSTALL_DIR}/.git" ]; then
    echo "==> Updating existing installation..."
    git -C "${INSTALL_DIR}" fetch origin
    git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
else
    echo "==> Cloning repository..."
    mkdir -p "$(dirname "${INSTALL_DIR}")"
    git clone --branch "${BRANCH}" --depth 1 "https://github.com/${REPO}.git" "${INSTALL_DIR}"
fi

# Install the package
echo "==> Installing Python package..."
pip install --user --upgrade "${INSTALL_DIR}"

# Create XDG directories
mkdir -p "${CONFIG_DIR}"
mkdir -p "${HF_HOME}"
mkdir -p "${BIN_DIR}"

# Create wrapper script
WRAPPER="${BIN_DIR}/digg-transcriber"
if [ ! -f "${WRAPPER}" ] || [ "$(head -n1 "${WRAPPER}")" != "#!/usr/bin/env bash" ]; then
    echo "==> Creating wrapper script at ${WRAPPER}"
    cat > "${WRAPPER}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export HF_HOME="${XDG_CACHE_HOME:-$HOME/.cache}/digg/digg-transcriber/huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export PATH="${HOME}/.local/bin:${PATH}"

exec python3 -m digg_transcriber.cli "$@"
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
echo "  1. Run 'digg-transcriber init' to create your config"
echo "  2. Download a Whisper model (see docs/HUGGINGFACE.md)"
echo "  3. Run 'digg-transcriber check --model medium' to verify"
echo ""
echo "Documentation: https://github.com/${REPO}"