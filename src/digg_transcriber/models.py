"""Data models for digg-transcriber."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    segments: list[Segment]
    language: Optional[str] = None


__all__ = ["Segment", "TranscriptResult"]