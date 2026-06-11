# Hugging Face Model Setup for digg-transcriber

## Prerequisites

Install the Hugging Face CLI:

```bash
pip install huggingface-hub
```

## Authentication

Accept terms at https://huggingface.co and generate a token:

```bash
hf auth login
```

## Download Models

### mlx-whisper (macOS Apple Silicon)

```bash
# Medium model (recommended balance of speed/accuracy)
hf download mlx-community/whisper-medium-mlx \
  --include "config.json" \
  --include "weights.npz"

# Large-v3 model (best accuracy, slower)
hf download mlx-community/whisper-large-v3-mlx \
  --include "config.json" \
  --include "weights.npz"

# Small model (faster, less accurate)
hf download mlx-community/whisper-small-mlx \
  --include "config.json" \
  --include "weights.npz"
```

### faster-whisper (Linux/other platforms)

faster-whisper downloads models automatically on first use, but you can pre-cache them:

```bash
# Using huggingface-cli
huggingface-cli download Systran/faster-whisper-medium
```

## Verify Installation

```bash
digg-transcriber check --model medium
```