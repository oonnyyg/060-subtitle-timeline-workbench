"""Timeline transforms: offset, clip, drop, sort and merge cues."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import Cue


@dataclass
class Overlap:
    a: Cue
    b: Cue


def apply_offset(cues: list[Cue], offset_ms: int) -> tuple[list[Cue], int, int]:
    """Apply an offset, dropping cues ending at/before zero and clipping starts."""
    kept: list[Cue] = []
    dropped = 0
    clipped = 0
    for cue in cues:
        start = cue.start_ms + offset_ms
        end = cue.end_ms + offset_ms
        if end <= 0:
            dropped += 1
            continue
        if start < 0:
            start = 0
            clipped += 1
        kept.append(
            Cue(
                start,
                end,
                list(cue.text_lines),
                cue.file_index,
                cue.block_index,
                list(cue.sources),
            )
        )
    return kept, dropped, clipped


def sort_cues(cues: list[Cue]) -> list[Cue]:
    """Sort by start, then end, then input file order and original block."""
    return sorted(
        cues,
        key=lambda c: (c.start_ms, c.end_ms, c.file_index, c.block_index),
    )


def _same_text(a: Cue, b: Cue) -> bool:
    return a.text_lines == b.text_lines


def _touch(a: Cue, b: Cue) -> bool:
    """Intervals intersect or touch at an endpoint."""
    return a.start_ms <= b.end_ms and b.start_ms <= a.end_ms


def merge_adjacent(cues: list[Cue]) -> list[Cue]:
    """Merge consecutive sorted cues with identical text and touching intervals."""
    if not cues:
        return []
    merged: list[Cue] = []
    current = Cue(
        cues[0].start_ms,
        cues[0].end_ms,
        list(cues[0].text_lines),
        cues[0].file_index,
        cues[0].block_index,
        list(cues[0].sources),
    )
    for cue in cues[1:]:
        if _same_text(current, cue) and _touch(current, cue):
            current.start_ms = min(current.start_ms, cue.start_ms)
            current.end_ms = max(current.end_ms, cue.end_ms)
            current.sources.extend(cue.sources)
        else:
            merged.append(current)
            current = Cue(
                cue.start_ms,
                cue.end_ms,
                list(cue.text_lines),
                cue.file_index,
                cue.block_index,
                list(cue.sources),
            )
    merged.append(current)
    return merged


def find_overlaps(cues: list[Cue]) -> list[Overlap]:
    """Report all pairs with strict interval overlap (endpoint touch excluded)."""
    overlaps: list[Overlap] = []
    ordered = sort_cues(cues)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            if b.start_ms >= a.end_ms:
                break
            if a.start_ms < b.end_ms and b.start_ms < a.end_ms:
                overlaps.append(Overlap(a, b))
    return overlaps
