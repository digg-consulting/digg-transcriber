# digg-transcriber

Universal transcription tool for video, audio, and podcast sources.

## Features

- **Multi-platform**: Uses mlx-whisper on macOS (Apple Silicon), faster-whisper elsewhere
- **Multiple sources**: Video files, local audio files, podcast RSS feeds
- **Output formats**: vtt, txt, srt, json (configurable)
- **Watch mode**: Monitor folders for new files with debounce queue
- **Podcast library tracking**: Keep a local SQLite catalog of podcasts, episodes, and transcript paths
- **pod-transcriber import**: Import existing transcripts from a pod-transcriber project
- **Source deletion**: Audio/video/podcast audio deleted after transcription (archive mode) or optionally retained
- **XDG-compliant**: Follows XDG Base Directory specification for config/cache

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/digg-consulting/digg-transcriber/main/install.sh | bash
```

The installer will:
1. Download the source to `~/.local/share/digg/digg-transcriber`
2. Create a `digg-transcriber` wrapper in `~/.local/bin`
3. Set up XDG config directory
4. Verify your HuggingFace model cache at `~/.cache/huggingface`

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

# 6. Track a podcast library and fetch episodes
digg-transcriber podcasts add --name "Example Podcast" --rss-url https://feeds.buzzsprout.com/example.rss --fetch
digg-transcriber episodes list --untranscribed
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
| `podcasts add --name NAME --rss-url URL [--fetch]` | Add a podcast to the local library |
| `podcasts fetch [--rss-url URL]` | Fetch episodes for configured podcasts |
| `podcasts list` | List configured podcasts |
| `episodes list [--podcast-id ID] [--untranscribed]` | List tracked episodes |
| `episodes import-pod-transcriber PATH [--dry-run]` | Import transcripts from a pod-transcriber project |
| `search QUERY` | Search Podcast Index for feeds |

## Podcast Sources

Transcribe episodes directly from RSS feeds:

```bash
# Transcribe latest episode
digg-transcriber podcast --rss-url https://feeds.buzzsprout.com/example.rss

# Transcribe specific episode by GUID
digg-transcriber podcast --rss-url https://feeds.buzzsprout.com/example.rss --guid abc123
```

## Podcast Library

`digg-transcriber` can maintain a local podcast library, similar to pod-transcriber. The library is stored in SQLite under the digg-transcriber cache directory and tracks:

- podcasts and RSS URLs
- episodes and GUIDs
- transcript file paths
- whether an episode still needs transcription

Add and fetch episodes:

```bash
digg-transcriber podcasts add --name "Example Podcast" --rss-url https://feeds.buzzsprout.com/example.rss --fetch
digg-transcriber podcasts fetch
digg-transcriber podcasts list
```

List episodes:

```bash
# All tracked episodes
digg-transcriber episodes list

# Only episodes without a recorded transcript path
digg-transcriber episodes list --untranscribed

# Episodes from one podcast
digg-transcriber episodes list --podcast-id 1
```

When `digg-transcriber podcast --rss-url URL` finishes an episode, it records the episode and transcript path in the library. Future runs skip episodes whose transcript path already exists unless `--force` is used.

Podcast transcripts are saved under:

```text
~/Transcripts/<podcast-title>/<episode-title>/<episode-title>.<format>
```

For example:

```text
~/Transcripts/Example Podcast/Episode One/Episode One.txt
```

## Importing pod-transcriber Transcripts

To import transcripts from an existing pod-transcriber project, point digg-transcriber at the pod-transcriber project root or its `transcripts/` folder:

```bash
digg-transcriber episodes import-pod-transcriber /Users/gadoury/github/gadouryd/pod-transcriber
```

Preview first:

```bash
digg-transcriber episodes import-pod-transcriber /Users/gadoury/github/gadouryd/pod-transcriber --dry-run
```

Import only one podcast:

```bash
digg-transcriber episodes import-pod-transcriber /Users/gadoury/github/gadouryd/pod-transcriber --podcast-title "Example Podcast"
```

Imported `.txt` transcripts are copied into digg-transcriber's transcript layout and recorded in the local library.

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

- **archive**: Each local file source gets a folder under output_dir with transcripts; source is moved into the archive folder
- **beside**: Outputs next to the source (source stays in place)
- **mirror**: Under output_dir, mirroring input directory tree
- **flat**: Local file transcript files directly in output_dir (no per-source folders)
- Podcast transcripts always use `output_dir/<podcast-title>/<episode-title>/<episode-title>.<format>`

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
