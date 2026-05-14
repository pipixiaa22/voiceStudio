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
