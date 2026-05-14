# SRT 字幕生成器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将中文文字按标点智能分段并生成 SRT 字幕文件

**Architecture:** 单文件脚本，纯 Python 标准库。核心逻辑：文本分段器（按句号/逗号拆分）+ 时间计算器（字数/语速）+ SRT 格式化器

**Tech Stack:** Python 3.13, argparse, re

---

## 文件结构

- `main.py` — 主入口，CLI 参数解析 + 流程编排
- `splitter.py` — 文本分段逻辑
- `srt.py` — SRT 格式生成
- `tests/test_splitter.py` — 分段逻辑测试
- `tests/test_srt.py` — SRT 格式测试

---

### Task 1: 文本分段器

**Files:**
- Create: `splitter.py`
- Create: `tests/test_splitter.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_splitter.py
from splitter import split_text


def test_split_by_sentence():
    text = "你好吗？我很好。今天天气不错！"
    result = split_text(text)
    assert result == ["你好吗？", "我很好。", "今天天气不错！"]


def test_split_long_sentence_by_comma():
    text = "这是一个很长的句子，包含了很多内容，需要在逗号处拆分。"
    result = split_text(text, max_chars=15)
    assert len(result) > 1
    for segment in result:
        assert len(segment) <= 15


def test_force_split_very_long_segment():
    text = "这是一个超级超级超级超级超级超级超级超级超级超级超级长的句子没有标点符号"
    result = split_text(text, max_chars=10)
    for segment in result:
        assert len(segment) <= 10


def test_empty_text():
    result = split_text("")
    assert result == []


def test_whitespace_only():
    result = split_text("   \n  \t  ")
    assert result == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/test_splitter.py -v
```

- [ ] **Step 3: 实现分段器**

```python
# splitter.py
import re


def split_text(text: str, max_chars: int = 20) -> list[str]:
    """将文字按标点智能分段。"""
    text = text.strip()
    if not text:
        return []

    # 按句末标点拆分
    sentences = re.split(r'([。？！…]+)', text)
    # 合并标点到前一个片段
    merged = []
    for i in range(0, len(sentences) - 1, 2):
        merged.append(sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else ""))
    if len(sentences) % 2 == 1 and sentences[-1]:
        merged.append(sentences[-1])

    # 对每个句子检查长度，必要时按逗号拆分
    result = []
    for sentence in merged:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            result.append(sentence)
        else:
            result.extend(_split_by_comma(sentence, max_chars))

    return result


def _split_by_comma(text: str, max_chars: int) -> list[str]:
    """在逗号类标点处拆分长句。"""
    parts = re.split(r'([，、；：,;:]+)', text)
    merged = []
    for i in range(0, len(parts) - 1, 2):
        merged.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
    if len(parts) % 2 == 1 and parts[-1]:
        merged.append(parts[-1])

    result = []
    current = ""
    for part in merged:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
        else:
            if current:
                result.append(current)
            # 如果单个片段仍然超长，强制截断
            while len(part) > max_chars:
                result.append(part[:max_chars])
                part = part[max_chars:]
            current = part
    if current:
        result.append(current)

    return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/test_splitter.py -v
```

- [ ] **Step 5: 提交**

```bash
git add splitter.py tests/test_splitter.py
git commit -m "feat: add text splitter with punctuation-based segmentation"
```

---

### Task 2: SRT 格式生成器

**Files:**
- Create: `srt.py`
- Create: `tests/test_srt.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_srt.py
from srt import generate_srt


def test_generate_srt_basic():
    segments = ["你好吗？", "我很好。"]
    result = generate_srt(segments, chars_per_second=5)
    expected = (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "你好吗？\n"
        "\n"
        "2\n"
        "00:00:01,000 --> 00:00:01,600\n"
        "我很好。"
    )
    assert result == expected


def test_generate_srt_custom_speed():
    segments = ["测试"]
    result = generate_srt(segments, chars_per_second=2)
    assert "00:00:00,000 --> 00:00:01,000" in result


def test_generate_srt_empty():
    result = generate_srt([], chars_per_second=5)
    assert result == ""
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/test_srt.py -v
```

- [ ] **Step 3: 实现 SRT 生成器**

```python
# srt.py


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳。"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list[str], chars_per_second: float = 5) -> str:
    """将字幕片段列表生成 SRT 格式字符串。"""
    if not segments:
        return ""

    lines = []
    current_time = 0.0

    for i, segment in enumerate(segments, 1):
        duration = len(segment) / chars_per_second
        start = _format_timestamp(current_time)
        end = _format_timestamp(current_time + duration)

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(segment)
        if i < len(segments):
            lines.append("")

        current_time += duration

    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/test_srt.py -v
```

- [ ] **Step 5: 提交**

```bash
git add srt.py tests/test_srt.py
git commit -m "feat: add SRT format generator with timestamp calculation"
```

---

### Task 3: CLI 主入口

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 实现 CLI**

```python
# main.py
import argparse
import sys

from splitter import split_text
from srt import generate_srt


def read_input(input_file: str | None) -> str:
    """从文件或标准输入读取文字。"""
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            return f.read()
    print("请输入文字（按 Ctrl+D 结束）：")
    return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(description="将文字生成 SRT 字幕文件")
    parser.add_argument("input_file", nargs="?", help="输入文件路径")
    parser.add_argument("--speed", type=float, default=5, help="语速（字/秒，默认 5）")
    parser.add_argument("--max-chars", type=int, default=20, help="每段最大字数（默认 20）")
    parser.add_argument("-o", default="output.srt", help="输出文件路径（默认 output.srt）")

    args = parser.parse_args()

    text = read_input(args.input_file)
    segments = split_text(text, max_chars=args.max_chars)

    if not segments:
        print("没有检测到有效文字。")
        return

    srt_content = generate_srt(segments, chars_per_second=args.speed)

    with open(args.o, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"已生成 {len(segments)} 段字幕，保存到 {args.o}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试交互模式**

```bash
cd /Users/ckrey/video/script && echo "你好吗？我很好。今天天气不错！" | uv run main.py -o test.srt && cat test.srt
```

- [ ] **Step 3: 测试文件模式**

```bash
cd /Users/ckrey/video/script && echo "这是一段测试文字。包含多个句子！还有问号吗？当然有。" > test_input.txt && uv run main.py test_input.txt -o test_file.srt && cat test_file.srt
```

- [ ] **Step 4: 清理测试文件并提交**

```bash
cd /Users/ckrey/video/script && rm -f test.srt test_file.srt test_input.txt && git add main.py && git commit -m "feat: add CLI entry point with file and stdin support"
```

---

### Task 4: 端到端验证

- [ ] **Step 1: 运行所有测试**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/ -v
```

- [ ] **Step 2: 验证剪映兼容性**

创建一个包含典型内容的测试文件，生成 SRT，确认格式正确：

```bash
cd /Users/ckrey/video/script && cat > demo.txt << 'EOF'
大家好，欢迎来到我的频道。今天我们要讨论一个有趣的话题。这个话题关于人工智能，它正在改变我们的生活。你觉得AI会取代人类吗？欢迎在评论区留言！EOF
uv run main.py demo.txt --speed 4 --max-chars 18 -o demo.srt && cat demo.srt
```

- [ ] **Step 3: 清理并最终提交**

```bash
cd /Users/ckrey/video/script && rm -f demo.txt demo.srt && git add -A && git commit -m "chore: add tests directory to project"
```
