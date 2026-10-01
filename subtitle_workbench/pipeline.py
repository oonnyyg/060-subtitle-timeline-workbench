"""End-to-end orchestration: request in, report out, SRT written to disk."""

from __future__ import annotations

import os
from typing import Any

from .merge import find_overlaps, merge_identical
from .models import Cue, ParseError
from .parser import parse_srt
from .timeline import apply_offset, sort_cues
from .writer import write_srt


def run(request_obj: Any) -> dict:
    files = _coerce_files(request_obj.get("files", []))
    output_dir = str(request_obj.get("output_dir", "")).strip()
    output_name = str(request_obj.get("output_name", "output.srt")).strip()
    threshold = float(request_obj.get("speed_threshold", 0))

    all_cues: list[Cue] = []
    dropped = 0
    clipped = 0
    try:
        for file_index, (path, offset) in enumerate(files):
            cues = parse_srt(path, file_index)
            shifted, file_dropped, file_clipped = apply_offset(cues, offset)
            dropped += file_dropped
            clipped += file_clipped
            all_cues.extend(shifted)
    except ParseError as exc:
        return {
            "ok": False,
            "errors": [
                {"file": exc.file, "block": exc.block, "reason": exc.reason}
            ],
            "output_file": None,
        }

    ordered = sort_cues(all_cues)
    merged = merge_identical(ordered)
    overlaps = find_overlaps(merged)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)
    write_srt(output_path, merged)

    speed_report = [
        _speed_entry(index, cue, threshold)
        for index, cue in enumerate(merged, start=1)
    ]

    return {
        "ok": True,
        "errors": [],
        "output_file": output_path,
        "input_file_count": len(files),
        "cue_count": len(merged),
        "dropped_count": dropped,
        "clipped_count": clipped,
        "merged_count": len(ordered) - len(merged),
        "overlaps": overlaps,
        "reading_speed": speed_report,
    }


def _coerce_files(raw_files: Any) -> list[tuple[str, int]]:
    files: list[tuple[str, int]] = []
    for entry in raw_files:
        if isinstance(entry, dict):
            path = str(entry["path"])
            offset = int(entry.get("offset_ms", 0))
        elif isinstance(entry, str):
            files.append((entry, 0))
            continue
        elif isinstance(entry, (list, tuple)):
            path = str(entry[0])
            offset = int(entry[1])
        else:
            raise ValueError(f"unsupported files entry: {entry!r}")
        files.append((path, offset))
    return files


def _speed_entry(index: int, cue: Cue, threshold: float) -> dict:
    chars = len("".join(line.strip() for line in cue.text_lines))
    seconds = (cue.end - cue.start) / 1000
    speed = chars / seconds
    return {
        "index": index,
        "chars": chars,
        "display_seconds": (cue.end - cue.start) / 1000,
        "chars_per_second": round(speed, 3),
        "warning": speed > threshold,
    }
