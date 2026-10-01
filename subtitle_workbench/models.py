"""Data models for the subtitle workbench."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParseError(Exception):
    """A fatal parse problem located by file name and 1-based block index."""

    file: str
    block: int
    reason: str

    def __str__(self) -> str:
        return f"{self.file} block {self.block}: {self.reason}"


@dataclass
class Cue:
    """One subtitle cue on a millisecond timeline."""

    start: int
    end: int
    text_lines: tuple[str, ...]
    file_index: int
    block: int
    sources: tuple[tuple[int, int], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = ((self.file_index, self.block),)

    @property
    def text(self) -> str:
        return "\n".join(self.text_lines)


@dataclass(frozen=True)
class Request:
    files: tuple[tuple[str, int], ...]
    output_dir: str
    output_name: str
    speed_threshold: float
