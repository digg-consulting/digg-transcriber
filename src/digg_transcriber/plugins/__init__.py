"""Source plugins for digg-transcriber."""

from .video import VideoSource
from .local_audio import LocalAudioSource
from .podcast import PodcastSource

SOURCE_PLUGINS: dict[str, type] = {
    "video": VideoSource,
    "local_audio": LocalAudioSource,
    "podcast": PodcastSource,
}

__all__ = ["SOURCE_PLUGINS", "VideoSource", "LocalAudioSource", "PodcastSource"]