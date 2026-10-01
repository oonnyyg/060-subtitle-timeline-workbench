import unittest

from subtitle_workbench.parser import Cue
from subtitle_workbench.timeline import (
    apply_offset,
    find_overlaps,
    merge_adjacent,
    sort_cues,
)


def cue(start, end, text, file_index=0, block=1):
    return Cue(start, end, [text], file_index, block)


class OffsetTests(unittest.TestCase):
    def test_drop_when_end_not_positive(self):
        kept, dropped, clipped = apply_offset([cue(0, 1000, "x")], -1000)
        self.assertEqual(kept, [])
        self.assertEqual(dropped, 1)
        self.assertEqual(clipped, 0)

    def test_clip_negative_start(self):
        kept, dropped, clipped = apply_offset([cue(500, 2000, "x")], -1000)
        self.assertEqual(dropped, 0)
        self.assertEqual(clipped, 1)
        self.assertEqual((kept[0].start_ms, kept[0].end_ms), (0, 1000))

    def test_positive_offset(self):
        kept, dropped, clipped = apply_offset([cue(0, 1000, "x")], 250)
        self.assertEqual((kept[0].start_ms, kept[0].end_ms), (250, 1250))
        self.assertEqual(dropped + clipped, 0)


class SortTests(unittest.TestCase):
    def test_sort_keys(self):
        cues = [
            cue(100, 500, "a", file_index=1, block=1),
            cue(0, 200, "b", file_index=0, block=2),
            cue(0, 200, "c", file_index=0, block=1),
        ]
        ordered = sort_cues(cues)
        self.assertEqual([c.text_lines[0] for c in ordered], ["c", "b", "a"])


class MergeTests(unittest.TestCase):
    def test_identical_touching_merge_chains(self):
        cues = [cue(0, 1000, "x"), cue(1000, 2000, "x"), cue(2000, 3000, "x")]
        merged = merge_adjacent(cues)
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0].start_ms, merged[0].end_ms), (0, 3000))
        self.assertEqual(len(merged[0].sources), 3)

    def test_different_text_not_merged_even_overlapping(self):
        cues = [cue(0, 2000, "a"), cue(1000, 3000, "b")]
        self.assertEqual(len(merge_adjacent(cues)), 2)

    def test_identical_but_disjoint_not_merged(self):
        cues = [cue(0, 1000, "x"), cue(2000, 3000, "x")]
        self.assertEqual(len(merge_adjacent(cues)), 2)

    def test_multiline_text_must_match_line_by_line(self):
        first = Cue(0, 1000, ["a", "b"], 0, 1)
        second = Cue(1000, 2000, ["a b"], 0, 2)
        self.assertEqual(len(merge_adjacent([first, second])), 2)


class OverlapTests(unittest.TestCase):
    def test_endpoint_touch_not_overlap(self):
        self.assertEqual(find_overlaps([cue(0, 1000, "a"), cue(1000, 2000, "b")]), [])

    def test_strict_overlap_reported(self):
        overlaps = find_overlaps([cue(0, 2000, "a"), cue(1000, 3000, "b")])
        self.assertEqual(len(overlaps), 1)


if __name__ == "__main__":
    unittest.main()
