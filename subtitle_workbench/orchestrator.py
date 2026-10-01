"""End-to-end request orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .parser import BlockError, Cue, decode_srt, parse_srt
from .report import reading_speed, text_char_count
from .writer import serialize_srt
from .timeline import (
    apply_offset,
    find_overlaps,
    merge_adjacent,
    sort_cues,
)


def _error_payload(errors: list[BlockError]) -> dict[str, Any]:
    return {
        "ok": False,
        "errors": [
            {
                "file_index": err.file_index,
                "file": err.file_path,
                "block": err.block_index,
                "reason": err.reason,
            }
            for err in errors
        ],
    }


def process_request(
    request: dict[str, Any],
    *,
    read_file: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Process one JSON request; write the SRT only when every file parses."""
    files = request.get("files", [])
    output_dir = request["output_dir"]
    output_name = request.get("output_name", "merged.srt")
    speed_threshold = float(request.get("speed_threshold", 17))

    def default_read(path: str) -> bytes:
        return Path(path).read_bytes()

    reader = read_file or default_read

    all_cues: list[Cue] = []
    errors: list[BlockError] = []
    offsets: dict[int, int] = {}

    for file_index, entry in enumerate(files):
        path = entry["path"]
        offset_ms = int(entry.get("offset_ms", 0))
        offsets[file_index] = offset_ms
        try:
            content = decode_srt(reader(path))
        except UnicodeDecodeError:
            errors.append(BlockError(file_index, path, 0, "not_utf8"))
            continue
        cues, file_errors = parse_srt(content, file_index, path)
        errors.extend(file_errors)
        all_cues.extend(cues)

    if errors:
        return _error_payload(sorted(errors, key=lambda e: (e.file_index, e.block_index)))

    dropped_total = 0
    clipped_total = 0
    transformed: list[Cue] = []
    for file_index, entry in enumerate(files):
        group = [cue for cue in all_cues if cue.file_index == file_index]
        kept, dropped, clipped = apply_offset(group, offsets[file_index])
        transformed.extend(kept)
        dropped_total += dropped
        clipped_total += clipped

    ordered = sort_cues(transformed)
    merged = merge_adjacent(ordered)
    overlaps = find_overlaps(merged)

    overlap_reports = []
    for overlap in overlaps:
        overlap_reports.append(
            {
                "a": _cue_location(overlap.a),
                "b": _cue_location(overlap.b),
                "a_start_ms": overlap.a.start_ms,
                "a_end_ms": overlap.a.end_ms,
                "b_start_ms": overlap.b.start_ms,
                "b_end_ms": overlap.b.end_ms,
            }
        )

    speed_warnings = []
    total_chars = 0
    for index, cue in enumerate(merged, start=1):
        char_count = text_char_count(cue)
        total_chars += char_count
        speed = reading_speed(cue)
        if speed > speed_threshold:
            speed_warnings.append(
                {
                    "index": index,
                    "chars": char_count,
                    "duration_ms": cue.end_ms - cue.start_ms,
                    "speed": round(speed, 2),
                }
            )

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / output_name
    output_path.write_bytes(serialize_srt(merged).encode("utf-8"))

    return {
        "ok": True,
        "output_file": str(output_path),
        "cue_count": len(merged),
        "dropped": dropped_total,
        "clipped": clipped_total,
        "overlaps": overlap_reports,
        "speed_threshold": speed_threshold,
        "speed_warnings": speed_warnings,
        "total_chars": total_chars,
    }


def _cue_location(cue: Cue) -> list[dict[str, int]]:
    return [
        {"file_index": file_index, "block": block}
        for file_index, block in cue.sources
    ]
