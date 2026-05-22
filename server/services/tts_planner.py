from dataclasses import dataclass, field


@dataclass
class SpeechChunk:
    """语音块：TTS 实际调用单位。"""
    index: int
    text: str
    subtitle_indices: list[int] = field(default_factory=list)


def plan_speech_chunks(subtitle_segments: list[str], max_chars: int = 200) -> list[SpeechChunk]:
    """将字幕段合并为语音块。

    规则：
    1. 尽量将连续字幕段合并到一个语音块
    2. 每个语音块不超过 max_chars 字符
    3. 保持字幕段顺序
    """
    if not subtitle_segments:
        return []

    chunks = []
    current_text = ''
    current_indices = []
    chunk_index = 1
    just_split = False

    for i, seg in enumerate(subtitle_segments):
        seg = seg.strip()
        if not seg:
            continue

        # 如果当前块加上新段会超限，先保存当前块
        # 刚拆分后强制接纳下一段，避免碎片化
        if not just_split and current_text and len(current_text) + len(seg) > max_chars:
            chunks.append(SpeechChunk(
                index=chunk_index,
                text=current_text,
                subtitle_indices=current_indices,
            ))
            chunk_index += 1
            current_text = ''
            current_indices = []
            just_split = True
        else:
            just_split = False

        current_text += seg
        current_indices.append(i)

    # 保存最后一个块
    if current_text:
        chunks.append(SpeechChunk(
            index=chunk_index,
            text=current_text,
            subtitle_indices=current_indices,
        ))

    return chunks
