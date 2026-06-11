"""Output format writers for digg-transcriber."""

import json
from pathlib import Path

from digg_transcriber.models import Segment


def _ts_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(seconds: float) -> str:
    return _ts_srt(seconds).replace(",", ".")


def _cue_text(seg: Segment) -> str:
    text = seg.text.strip()
    if seg.speaker:
        return f"{seg.speaker}: {text}"
    return text


def format_full_text(segments: list[Segment]) -> str:
    parts = [_cue_text(seg) for seg in segments if seg.text.strip()]
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def format_srt(segments: list[Segment]) -> str:
    blocks = []
    for i, seg in enumerate(segments, start=1):
        blocks.append(
            f"{i}\n{_ts_srt(seg.start)} --> {_ts_srt(seg.end)}\n{_cue_text(seg)}\n"
        )
    return "\n".join(blocks).strip() + "\n"


def format_vtt(segments: list[Segment]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.append(f"{_ts_vtt(seg.start)} --> {_ts_vtt(seg.end)}")
        lines.append(_cue_text(seg))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_formats(
    full_text: str,
    segments: list[Segment],
    output_paths: dict[str, Path],
    *,
    formats: list[str],
) -> None:
    text = full_text
    if any(s.speaker for s in segments):
        text = format_full_text(segments)
    for fmt in formats:
        path = output_paths[fmt]
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "txt":
            path.write_text(text.strip() + "\n", encoding="utf-8")
        elif fmt == "srt":
            path.write_text(format_srt(segments), encoding="utf-8")
        elif fmt == "vtt":
            path.write_text(format_vtt(segments), encoding="utf-8")
        elif fmt == "json":
            payload = {
                "text": text.strip(),
                "segments": [
                    {
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        **({"speaker": s.speaker} if s.speaker else {}),
                    }
                    for s in segments
                ],
            }
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            raise ValueError(f"unsupported format: {fmt}")


__all__ = [
    "format_full_text",
    "format_srt",
    "format_vtt",
    "write_formats",
]