"""SRT serialization with LF line endings."""

from __future__ import annotations

from .parser import Cue


def format_time(ms: int) -> str:
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def serialize_srt(cues: list[Cue]) -> str:
    blocks: list[str] = []
    for index, cue in enumerate(cues, start=1):
        block = "\n".join(
            [
                str(index),
                f"{format_time(cue.start_ms)} --> {format_time(cue.end_ms)}",
                *cue.text_lines,
            ]
        )
        blocks.append(block)
    return "\n\n".join(blocks) + "\n"
