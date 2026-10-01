from __future__ import annotations

import json
import os
import subprocess
import sys

from subtitle_workbench.merge import find_overlaps, merge_identical
from subtitle_workbench.models import Cue, ParseError
from subtitle_workbench.parser import parse_srt
from subtitle_workbench.pipeline import run
from subtitle_workbench.timeline import apply_offset, format_timestamp, sort_cues


def write_srt(tmp_path, name: str, content: str, bom: bool = False) -> str:
    path = tmp_path / name
    data = content.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    return str(path)


def test_parse_bom_and_multiline(tmp_path):
    path = write_srt(
        tmp_path,
        "a.srt",
        "1\n00:00:01,000 --> 00:00:02,000\nhello\nworld\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\nbye\n",
        bom=True,
    )
    cues = parse_srt(path, 0)
    assert len(cues) == 2
    assert cues[0].text_lines == ("hello", "world")
    assert cues[1].block == 2


def test_parse_errors(tmp_path):
    missing = write_srt(tmp_path, "m.srt", "1\njust text\n")
    try:
        parse_srt(missing, 0)
    except ParseError as exc:
        assert exc.block == 1
        assert "timeline" in exc.reason
    else:
        raise AssertionError("expected ParseError")

    bad_time = write_srt(tmp_path, "t.srt", "1\n00:00:60,000 --> 00:01:01,000\nx\n")
    try:
        parse_srt(bad_time, 0)
    except ParseError as exc:
        assert "59" in exc.reason
    else:
        raise AssertionError("expected ParseError")

    reversed_ = write_srt(tmp_path, "r.srt", "1\n00:00:02,000 --> 00:00:02,000\nx\n")
    try:
        parse_srt(reversed_, 0)
    except ParseError as exc:
        assert "later" in exc.reason
    else:
        raise AssertionError("expected ParseError")


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(3_723_456) == "01:02:03,456"


def cue(start, end, text, file_index=0, block=1):
    return Cue(start, end, tuple(text.split("\n")), file_index, block)


def test_offset_drop_clip_sort():
    cues = [
        cue(-2000, -500, "drop", block=1),
        cue(-1500, 1500, "clip", block=2),
        cue(5000, 6000, "later", block=3),
    ]
    kept, dropped, clipped = apply_offset(cues, 0)
    assert dropped == 1
    assert clipped == 1
    assert kept[0].start == 0
    assert kept[0].end == 1500

    ordered = sort_cues(
        [cue(10, 20, "b", file_index=1, block=9), cue(10, 20, "a", file_index=0, block=3)]
    )
    assert (ordered[0].file_index, ordered[0].block) == (0, 3)


def test_merge_identical_chain():
    cues = [
        cue(0, 1000, "same"),
        cue(1000, 2000, "same", block=2),
        cue(1500, 3000, "same", block=3),
        cue(3000, 4000, "other", block=4),
    ]
    merged = merge_identical(cues)
    assert len(merged) == 2
    assert merged[0].start == 0
    assert merged[0].end == 3000
    assert len(merged[0].sources) == 3


def test_overlap_detection():
    touching = find_overlaps([cue(0, 1000, "a"), cue(1000, 2000, "b", block=2)])
    assert touching == []

    same_text = find_overlaps([cue(0, 2000, "x"), cue(1000, 3000, "x", block=2)])
    assert same_text == []

    overlap = find_overlaps([cue(0, 2000, "a"), cue(1000, 3000, "b", block=2)])
    assert len(overlap) == 1
    assert overlap[0]["start"] == 1000
    assert overlap[0]["end"] == 2000


def test_run_end_to_end_and_parse_error(tmp_path):
    first = write_srt(
        tmp_path,
        "first.srt",
        "1\n00:00:01,000 --> 00:00:02,000\nhi\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\nhi\n",
    )
    second = write_srt(
        tmp_path,
        "second.srt",
        "1\n00:00:00,500 --> 00:00:01,500\nhello world!\n",
    )
    out_dir = tmp_path / "out"
    report = run(
        {
            "files": [
                {"path": first, "offset_ms": 0},
                {"path": second, "offset_ms": 1000},
            ],
            "output_dir": str(out_dir),
            "output_name": "merged.srt",
            "speed_threshold": 5,
        }
    )
    assert report["ok"] is True
    assert report["cue_count"] == 3
    assert report["merged_count"] == 0
    assert len(report["overlaps"]) == 2
    assert report["reading_speed"][1]["warning"] is True
    assert report["reading_speed"][0]["warning"] is False
    output = (out_dir / "merged.srt").read_bytes()
    assert b"\r\n" not in output
    assert output.startswith(b"1\n00:00:01,000")

    original = open(first, "rb").read()
    assert b"hi" in original

    bad = write_srt(tmp_path, "bad.srt", "9\nno timeline here\n")
    fail_report = run(
        {"files": [bad], "output_dir": str(tmp_path / "none"), "output_name": "x.srt"}
    )
    assert fail_report["ok"] is False
    assert fail_report["errors"][0]["block"] == 1
    assert not (tmp_path / "none").exists()


def test_cli_module(tmp_path):
    src = write_srt(
        tmp_path, "c.srt", "1\n00:00:01,000 --> 00:00:02,000\ncli\n"
    )
    payload = json.dumps(
        {
            "files": [[src, 0]],
            "output_dir": str(tmp_path / "cli_out"),
            "output_name": "c.srt",
            "speed_threshold": 100,
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "subtitle_workbench"],
        input=payload.encode("utf-8"),
        capture_output=True,
        check=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    report = json.loads(result.stdout.decode("utf-8"))
    assert report["ok"] is True
    assert report["cue_count"] == 1
