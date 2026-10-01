"""SRT serialization with UTF-8 and LF line endings."""

from __future__ import annotations

from .models import Cue
from .timeline import format_timestamp


def render_srt(cues: list[Cue]) -> str:
    parts: list[str] = []
    for index, cue in enumerate(cues, start=1):
        parts.append(
            f"{index}\n"
            f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(parts)


def write_srt(path: str, cues: list[Cue]) -> None:
    with open(path, "wb") as handle:
        handle.write(render_srt(cues).encode("utf-8"))
