# Subtitle Timeline Workbench

用 Python 标准库整理本地 SRT 字幕：合并多文件时间轴、丢弃/截短越界字幕、
合并重复文本、检测重叠并生成 JSON 质量报告。仅依赖标准库，需 Python 3.12+。

## 输入请求

从标准输入读取一个 UTF-8 JSON 对象（支持 BOM）：

```json
{
  "files": [
    {"path": "part1.srt", "offset_ms": 0},
    {"path": "part2.srt", "offset_ms": 1500}
  ],
  "output_dir": "build",
  "output_name": "merged.srt",
  "speed_threshold": 21
}
```

- `files` 有序，给出文件路径与整数毫秒偏移。也接受 `[path, offset_ms]`
  数组形式或纯路径字符串（偏移为 0）。
- 偏移同时加到开始与结束时间。
- `output_name` 缺省为 `output.srt`，`speed_threshold` 缺省为 `0`。

## 运行

```bash
python -m subtitle_workbench < request.json
```

整理后的 SRT 写入 `output_dir/output_name`，统一为 UTF-8、LF 换行，
编号从 1 连续重排。原文件不会被修改。

## 处理规则

- 时间格式 `HH:MM:SS,mmm`，分钟、秒不得超过 59；接受 UTF-8 与可选 BOM、
  CRLF/LF 换行；字幕文本可多行，空行分隔块。
- 缺少时间行、时间值非法，或结束不晚于开始时立即终止：报告出错文件与
  1-based 块位置，整批不写出任何输出文件。
- 结束时间（偏移后）不大于 0 的字幕丢弃；开始小于 0 但结束为正的字幕，
  开始截到 0。
- 按开始、结束时间排序，同值时按输入文件序号与原块位置排序。
- 排序后相邻字幕若文本逐行完全相同且区间相交或端点接触，则合并为一条
  （区间取并集，`sources` 保留全部来源），合并结果继续与下一条比较。
- 不同文本字幕严格重叠（端点接触不算）不合并、原样保留，报告全部重叠对。
- 每条字幕的阅读速度 = 去空白后字符数 / 显示秒数；仅当严格大于
  `speed_threshold` 时 `warning` 为 `true`。

## 报告字段

成功：

```json
{
  "ok": true,
  "errors": [],
  "output_file": "build/merged.srt",
  "input_file_count": 2,
  "cue_count": 10,
  "dropped_count": 1,
  "clipped_count": 0,
  "merged_count": 2,
  "overlaps": [
    {"first": {"file_index": 0, "block": 3, "sources": []},
     "second": {"file_index": 1, "block": 1, "sources": []},
     "start": 5000, "end": 7000}
  ],
  "reading_speed": [
    {"index": 1, "chars": 12, "display_seconds": 2.0,
     "chars_per_second": 6.0, "warning": false}
  ]
}
```

失败：`ok` 为 `false`，`errors` 含 `file`、`block`、`reason`，
`output_file` 为 `null`，且不创建输出文件。

## 测试

```bash
python -m pytest tests/
```
