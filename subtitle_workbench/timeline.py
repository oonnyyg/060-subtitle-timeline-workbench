"""Timestamp formatting and timeline transforms."""

from __future__ import annotations

from .models import Cue


def format_timestamp(ms: int) -> str:
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def apply_offset(cues: list[Cue], offset: int) -> tuple[list[Cue], int, int]:
    """Shift cues; drop cues ending at/before zero, clip starts crossing zero."""
    kept: list[Cue] = []
    dropped = 0
    clipped = 0
    for cue in cues:
        start = cue.start + offset
        end = cue.end + offset
        if end <= 0:
            dropped += 1
            continue
        if start < 0:
            start = 0
            clipped += 1
        kept.append(
            Cue(start, end, cue.text_lines, cue.file_index, cue.block, cue.sources)
        )
    return kept, dropped, clipped


def sort_cues(cues: list[Cue]) -> list[Cue]:
    return sorted(cues, key=lambda cue: (cue.start, cue.end, cue.file_index, cue.block))
