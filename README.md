# digg-transcriber

Universal transcription tool for video, audio, and podcast sources.

## Features

- **Multi-platform**: Uses mlx-whisper on macOS (Apple Silicon), faster-whisper elsewhere
- **Multiple sources**: Video files, local audio files, podcast RSS feeds
- **Output formats**: vtt, txt, srt, json (configurable)
- **Watch mode**: Monitor folders for new files with debounce queue
- **Source deletion**: Audio/video/podcast audio deleted after transcription (archive mode) or optionally retained
- **XDG-compliant**: Follows XDG Base Directory specification for config/cache

## Installation

**Option A: Clone the repository**

```bash
git clone https://github.com/digg-consulting/digg-transcriber.git
cd digg-transcriber
pip install -e .
```

**Option B: Download and install**

```bash
curl -sSL https://github.com/digg-consulting/digg-transcriber/archive/refs/heads/main.tar.gz | tar xz
cd digg-transcriber-main
pip install -e .
```

Then run the setup script:

```bash
./install.sh
```

## Quick Start

```bash
# 1. Create config
digg-transcriber init

# 2. Download a model (macOS)
hf auth login
hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"

# 3. Verify model
digg-transcriber check --model medium

# 4. Transcribe files
digg-transcriber transcribe ~/Videos/recording.mp4

# 5. Transcribe a podcast episode
digg-transcriber podcast --rss-url https://feeds.buzzsprout.com/example.rss
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Create default config file |
| `check` | Check model cache status |
| `transcribe [PATH...]` | Transcribe files or directories |
| `watch` | Watch folders for new files |
| `prereqs` | Check prerequisites (model cache) |
| `podcast --rss-url URL` | Transcribe podcast episode from RSS |
| `podcast --rss-url URL --guid GUID` | Transcribe specific episode |
| `search QUERY` | Search Podcast Index for feeds |

## Podcast Sources

Transcribe episodes directly from RSS feeds:

```bash
# Transcribe latest episode
digg-transcriber podcast --rss-url https://feeds.buzzsprout.com/example.rss

# Transcribe specific episode by GUID
digg-transcriber podcast --rss-url https://feeds.buzzsprout.com/example.rss --guid abc123
```

## Podcast Index Search

Search for podcasts via Podcast Index (requires API credentials):

```bash
digg-transcriber search "tech podcast"
```

Get free credentials at https://podcastindex.org

## Podcast Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `podcast.podcast_index_api_key` | Podcast Index API key | `""` |
| `podcast.podcast_index_api_secret` | Podcast Index API secret | `""` |

## Local File Configuration

Config file: `~/.config/digg/digg-transcriber/config.yaml`

| Option | Description | Default |
|--------|-------------|---------|
| `model` | Whisper model (medium, large-v3, etc.) | `medium` |
| `language` | Language code or 'auto' | `auto` |
| `output_mode` | archive, beside, mirror, flat | `archive` |
| `output_dir` | Where transcripts are saved | `~/Transcripts` |
| `formats` | Output formats: vtt, txt, srt, json | `["vtt", "txt"]` |
| `watch.paths` | Folders to monitor | `[]` |
| `watch.debounce_seconds` | File stability wait time | `2` |
| `watch.extensions` | File extensions to watch | Video/audio extensions |

## Output Modes

- **archive**: Each source gets a folder under output_dir with transcripts; source is moved into the archive folder
- **beside**: Outputs next to the source (source stays in place)
- **mirror**: Under output_dir, mirroring input directory tree
- **flat**: All transcript files directly in output_dir (no per-source folders)

## Source Types

| Extension | Plugin |
|-----------|--------|
| .mp4, .mov, .avi, .mkv, .webm, .m4v | Video (extracts audio via ffmpeg) |
| .mp3, .m4a, .wav, .flac, .ogg, .opus, .aac | Local audio (used directly) |

## Watch Mode

Monitor folders for new/modified files:

```bash
# Edit config to add watch.paths
digg-transcriber watch
```

Files are processed after being stable for `debounce_seconds` (default 2s).
