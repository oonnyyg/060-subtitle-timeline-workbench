"""SRT subtitle parsing with strict time validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TIME_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    r"\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*$"
)


class ParseError(Exception):
    """Raised for unrecoverable encoding problems."""


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text_lines: list[str]
    file_index: int
    block_index: int
    sources: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [(self.file_index, self.block_index)]


@dataclass
class BlockError:
    file_index: int
    file_path: str
    block_index: int
    reason: str


def decode_srt(raw: bytes) -> str:
    """Decode bytes as UTF-8, accepting an optional BOM."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8")


def _to_ms(hours: str, minutes: str, seconds: str, millis: str) -> int | None:
    minute = int(minutes)
    second = int(seconds)
    if minute > 59 or second > 59:
        return None
    return int(hours) * 3_600_000 + minute * 60_000 + second * 1_000 + int(millis)


def parse_time_line(line: str) -> tuple[int, int] | None:
    match = TIME_RE.match(line)
    if not match:
        return None
    h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
    start = _to_ms(h1, m1, s1, ms1)
    end = _to_ms(h2, m2, s2, ms2)
    if start is None or end is None:
        return None
    return start, end


def _split_blocks(content: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in content.split("\n"):
        line = raw_line.rstrip("\r")
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def parse_srt(content: str, file_index: int, file_path: str) -> tuple[list[Cue], list[BlockError]]:
    """Parse SRT text, returning cues and per-block errors."""
    cues: list[Cue] = []
    errors: list[BlockError] = []
    blocks = _split_blocks(content)

    for block_index, lines in enumerate(blocks, start=1):
        timing_pos = None
        timing: tuple[int, int] | None = None
        for pos, line in enumerate(lines):
            candidate = parse_time_line(line.strip())
            if candidate is not None:
                timing_pos = pos
                timing = candidate
                break

        if timing is None:
            errors.append(BlockError(file_index, file_path, block_index, "missing_time_line"))
            continue

        start_ms, end_ms = timing
        if end_ms <= start_ms:
            errors.append(BlockError(file_index, file_path, block_index, "end_not_after_start"))
            continue

        text_lines = lines[timing_pos + 1 :]
        cues.append(Cue(start_ms, end_ms, text_lines, file_index, block_index))

    return cues, errors
