"""Merging identical adjacent cues and detecting overlaps."""

from __future__ import annotations

from .models import Cue


def merge_identical(cues: list[Cue]) -> list[Cue]:
    """Merge consecutive cues with identical text whose ranges touch or overlap."""
    if not cues:
        return []
    merged = [cues[0]]
    for cue in cues[1:]:
        last = merged[-1]
        if (
            cue.text_lines == last.text_lines
            and cue.start <= last.end
            and last.start <= cue.end
        ):
            merged[-1] = Cue(
                min(last.start, cue.start),
                max(last.end, cue.end),
                last.text_lines,
                last.file_index,
                last.block,
                last.sources + cue.sources,
            )
        else:
            merged.append(cue)
    return merged


def find_overlaps(cues: list[Cue]) -> list[dict]:
    """Report strict overlaps (endpoint contact excluded) between differing texts."""
    overlaps: list[dict] = []
    for i in range(len(cues)):
        for j in range(i + 1, len(cues)):
            first = cues[i]
            second = cues[j]
            if second.start >= first.end:
                break
            if (
                first.text_lines != second.text_lines
                and first.start < second.end
                and second.start < first.end
            ):
                overlaps.append(
                    {
                        "first": _describe(first),
                        "second": _describe(second),
                        "start": max(first.start, second.start),
                        "end": min(first.end, second.end),
                    }
                )
    return overlaps


def _describe(cue: Cue) -> dict:
    return {
        "file_index": cue.file_index,
        "block": cue.block,
        "sources": [
            {"file_index": file_index, "block": block}
            for file_index, block in cue.sources
        ],
    }
