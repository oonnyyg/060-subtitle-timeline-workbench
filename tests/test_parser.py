import unittest

from subtitle_workbench.parser import decode_srt, parse_srt, parse_time_line


class ParseTimeLineTests(unittest.TestCase):
    def test_valid_line(self):
        self.assertEqual(
            parse_time_line("00:01:02,500 --> 01:02:03,000"),
            (62_500, 3_723_000),
        )

    def test_minute_second_boundaries(self):
        self.assertIsNotNone(parse_time_line("00:59:59,999 --> 01:00:00,000"))
        self.assertIsNone(parse_time_line("00:60:00,000 --> 01:00:00,000"))
        self.assertIsNone(parse_time_line("00:00:60,000 --> 01:00:00,000"))


class DecodeTests(unittest.TestCase):
    def test_bom_stripped(self):
        self.assertEqual(decode_srt("\ufeffhello".encode("utf-8")), "hello")

    def test_plain_utf8(self):
        self.assertEqual(decode_srt("你好".encode("utf-8")), "你好")


class ParseSrtTests(unittest.TestCase):
    def test_multiline_text_and_blocks(self):
        content = "1\n00:00:01,000 --> 00:00:02,000\nline one\nline two\n\n2\n00:00:03,000 --> 00:00:04,000\nend\n"
        cues, errors = parse_srt(content, 0, "f.srt")
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text_lines, ["line one", "line two"])
        self.assertEqual(cues[0].block_index, 1)
        self.assertEqual(errors, [])

    def test_missing_time_line(self):
        content = "1\njust some text\n"
        cues, errors = parse_srt(content, 2, "bad.srt")
        self.assertEqual(cues, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].reason, "missing_time_line")
        self.assertEqual((errors[0].file_index, errors[0].block_index), (2, 1))

    def test_end_not_after_start(self):
        content = "1\n00:00:02,000 --> 00:00:02,000\nx\n"
        cues, errors = parse_srt(content, 0, "f.srt")
        self.assertEqual(cues, [])
        self.assertEqual(errors[0].reason, "end_not_after_start")

    def test_crlf_blocks(self):
        content = "1\r\n00:00:01,000 --> 00:00:02,000\r\nhi\r\n\r\n2\r\n00:00:03,000 --> 00:00:04,000\r\nbye\r\n"
        cues, errors = parse_srt(content, 0, "f.srt")
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].text_lines, ["bye"])


if __name__ == "__main__":
    unittest.main()
