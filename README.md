# Subtitle Timeline Workbench

用 Python 标准库整理本地 SRT 字幕：合并时间轴、丢弃/截短越界字幕、检测文本重叠并生成质量报告。原文件不会被修改。

## 运行方式

从标准输入读取一个 JSON 请求，向标准输出返回 JSON 报告，并将整理后的 SRT 写入指定目录：

```sh
python -m subtitle_workbench < request.json
```

请求字段：

```json
{
  "files": [
    {"path": "part1.srt", "offset_ms": 0},
    {"path": "part2.srt", "offset_ms": 1500}
  ],
  "output_dir": "build/subtitles",
  "output_name": "merged.srt",
  "speed_threshold": 17
}
```

- `files`：**有序**文件列表。`offset_ms` 为整数毫秒偏移，可省略（默认 0）。
- `output_dir`：输出目录，不存在时自动创建。
- `output_name`：输出文件名，默认 `merged.srt`。
- `speed_threshold`：阅读速度警告阈值（字符/秒），默认 17；仅当速度**超过**阈值时警告。

成功时退出码为 0；任一文件解析失败时退出码为 1。

## 解析规则

- 接受 UTF-8 编码及可选的 UTF-8 BOM，兼容 CRLF 与 LF 换行。
- 时间格式固定为 `HH:MM:SS,mmm`；分钟、秒不得超过 59（小时不限）。
- 字幕文本可跨多行，块之间以空行分隔；序号行可有可无。
- 以下问题会报告 `file_index`、文件路径与块位置，且**整批不产生任何输出文件**：
  - 块内缺少合法时间行（`missing_time_line`）；
  - 结束时间不晚于开始时间（`end_not_after_start`）；
  - 文件不是合法 UTF-8（`not_utf8`，块位置为 0）。

## 时间轴处理

1. 将每个文件的 `offset_ms` 同时加到开始与结束时间。
2. 结束时间不大于 0 的字幕直接**丢弃**；开始时间小于 0 但结束时间为正的字幕把开始时间**截到 0**。
3. 按 `(开始时间, 结束时间, 输入文件顺序, 原块位置)` 排序。
4. 相邻字幕仅在**文本逐行完全相同**且区间相交或端点接触时合并为一条；合并结果继续与下一条比较，所有来源（文件、块）都保留在报告中。
5. 不同文本的重叠保持原样；报告中列出**全部严格重叠对**（端点接触不算重叠）。
6. 最终字幕按顺序重新连续编号，输出统一为 UTF-8、LF 换行。

## 报告字段

成功响应示例：

```json
{
  "ok": true,
  "output_file": "build/subtitles/merged.srt",
  "cue_count": 12,
  "dropped": 1,
  "clipped": 1,
  "overlaps": [
    {
      "a": [{"file_index": 0, "block": 3}],
      "b": [{"file_index": 1, "block": 1}],
      "a_start_ms": 1000,
      "a_end_ms": 3000,
      "b_start_ms": 2500,
      "b_end_ms": 5000
    }
  ],
  "speed_threshold": 17,
  "speed_warnings": [
    {"index": 4, "chars": 40, "duration_ms": 2000, "speed": 20.0}
  ],
  "total_chars": 230
}
```

- `dropped` / `clipped`：丢弃与截短的字幕数量。
- `speed_warnings`：逐条字幕计算「去掉全部空白后的字符数 ÷ 显示秒数」，超过阈值才列出。

失败响应示例：

```json
{
  "ok": false,
  "errors": [
    {"file_index": 1, "file": "part2.srt", "block": 7, "reason": "missing_time_line"}
  ]
}
```

## 运行测试

```sh
python -m unittest discover -s tests -v
```
