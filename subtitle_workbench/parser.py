"""SRT parsing and validation."""

from __future__ import annotations

import re

from .models import Cue, ParseError

TIMESTAMP = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*$"
)


def _to_ms(hours: str, minutes: str, seconds: str, millis: str) -> int:
    minute = int(minutes)
    second = int(seconds)
    if minute > 59 or second > 59:
        raise ValueError("minutes and seconds must be at most 59")
    return int(hours) * 3_600_000 + minute * 60_000 + second * 1_000 + int(millis)


def _split_blocks(content: str) -> list[list[str]]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in normalized.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def parse_srt(path: str, file_index: int) -> list[Cue]:
    """Read an SRT file and return its cues in original block order."""
    with open(path, "rb") as handle:
        raw = handle.read()
    content = raw.decode("utf-8-sig")

    cues: list[Cue] = []
    for block_index, lines in enumerate(_split_blocks(content), start=1):
        time_line_index = next(
            (i for i, line in enumerate(lines) if "-->" in line), None
        )
        if time_line_index is None:
            raise ParseError(path, block_index, "missing timeline line")
        match = TIMESTAMP.match(lines[time_line_index])
        if not match:
            raise ParseError(
                path, block_index, "malformed timeline line or time value"
            )
        groups = match.groups()
        try:
            start = _to_ms(*groups[0:4])
            end = _to_ms(*groups[4:8])
        except ValueError:
            raise ParseError(
                path, block_index, "minutes and seconds must be at most 59"
            ) from None
        if end <= start:
            raise ParseError(
                path, block_index, "end timestamp must be later than start"
            )
        text_lines = tuple(lines[time_line_index + 1 :])
        cues.append(Cue(start, end, text_lines, file_index, block_index))
    return cues
