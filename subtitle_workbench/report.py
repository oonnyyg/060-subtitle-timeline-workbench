"""Reading speed statistics."""

from __future__ import annotations

from .parser import Cue


def text_char_count(cue: Cue) -> int:
    """Count characters after removing every whitespace character."""
    return sum(len("".join(line.split())) for line in cue.text_lines)


def reading_speed(cue: Cue) -> float:
    """Characters (whitespace removed) per displayed second."""
    duration_seconds = (cue.end_ms - cue.start_ms) / 1000
    if duration_seconds <= 0:
        return 0.0
    return text_char_count(cue) / duration_seconds
