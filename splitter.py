# splitter.py
import re


def _merge_with_delimiters(parts: list[str]) -> list[str]:
    """Merge re.split results so each delimiter is attached to the preceding segment."""
    merged = []
    for i in range(0, len(parts) - 1, 2):
        merged.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
    if len(parts) % 2 == 1 and parts[-1]:
        merged.append(parts[-1])
    return merged


def split_text(text: str, max_chars: int = 20) -> list[str]:
    """将文字按标点智能分段。"""
    text = text.strip()
    if not text:
        return []

    # 按句末标点拆分
    sentences = re.split(r'([。？！…]+)', text)
    merged = _merge_with_delimiters(sentences)

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
    merged = _merge_with_delimiters(parts)

    result = []
    current = ""
    for part in merged:
        # Skip whitespace-only parts; do not strip meaningful whitespace
        if not part.strip():
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
