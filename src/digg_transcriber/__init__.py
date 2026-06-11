"""digg-transcriber - Universal transcription tool for video and audio."""

__version__ = "0.1.0"

from digg_transcriber.models import Segment, TranscriptResult
from digg_transcriber.paths import OutputMode

__all__ = ["Segment", "TranscriptResult", "OutputMode", "__version__"]