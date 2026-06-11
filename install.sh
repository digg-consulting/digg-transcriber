#!/bin/bash
# install.sh - XDG-compliant installation for digg-transcriber

set -e

# Set XDG directories
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

# Create directories
mkdir -p "$XDG_CONFIG_HOME/digg/digg-transcriber"
mkdir -p "$XDG_CACHE_HOME/digg/digg-transcriber/huggingface"
mkdir -p "$XDG_DATA_HOME/digg/digg-transcriber"
mkdir -p "$HOME/.local/bin"

echo "Created XDG directories:"
echo "  Config: $XDG_CONFIG_HOME/digg/digg-transcriber"
echo "  Cache:  $XDG_CACHE_HOME/digg/digg-transcriber"
echo "  Data:   $XDG_DATA_HOME/digg/digg-transcriber"

# Install the package
echo ""
echo "Installing digg-transcriber..."
pip install -e .

# Set up environment
export HF_HOME="$XDG_CACHE_HOME/digg/digg-transcriber/huggingface"
export HF_HUB_CACHE="$XDG_CACHE_HOME/digg/digg-transcriber/huggingface/hub"
export PATH="$HOME/.local/bin:$PATH"

echo ""
echo "Environment variables to set in your shell config:"
echo "  export HF_HOME=\"$XDG_CACHE_HOME/digg/digg-transcriber/huggingface\""
echo "  export HF_HUB_CACHE=\"$XDG_CACHE_HOME/digg/digg-transcriber/huggingface/hub\""

# Create default config
digg-transcriber init

echo ""
echo "Installation complete. Download a Whisper model to get started:"
echo "  hf auth login"
echo "  hf download mlx-community/whisper-medium-mlx --include \"config.json\" --include \"weights.npz\""
echo "  digg-transcriber check --model medium"