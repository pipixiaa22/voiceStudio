from server.services.tts_planner import SpeechChunk


def build_subtitle_timeline(
    chunks: list[SpeechChunk],
    chunk_durations: list[float],
    gap: float = 0.3,
    subtitle_segments: list[str] | None = None,
) -> list[dict]:
    """根据语音块时长生成字幕时间轴。

    如果一个语音块包含多条字幕，按文本长度分配时长。
    """
    timeline = []
    current_time = 0.0

    for i, (chunk, duration) in enumerate(zip(chunks, chunk_durations)):
        start = current_time
        end = start + duration

        if len(chunk.subtitle_indices) == 1:
            # 单条字幕，直接使用完整时长
            idx = chunk.subtitle_indices[0]
            text = subtitle_segments[idx] if subtitle_segments else chunk.text
            timeline.append({
                'index': len(timeline) + 1,
                'text': text,
                'start': round(start, 3),
                'end': round(end, 3),
                'chunk_index': chunk.index,
            })
        else:
            # 多条字幕，按文本长度分配时长
            if subtitle_segments:
                texts = [subtitle_segments[idx] for idx in chunk.subtitle_indices]
            else:
                texts = [chunk.text] * len(chunk.subtitle_indices)

            total_chars = sum(len(t) for t in texts)
            sub_start = start

            for j, text in enumerate(texts):
                ratio = len(text) / total_chars if total_chars > 0 else 1 / len(texts)
                sub_duration = duration * ratio
                sub_end = sub_start + sub_duration

                # 最后一条字幕强制对齐块结束时间
                if j == len(texts) - 1:
                    sub_end = end

                timeline.append({
                    'index': len(timeline) + 1,
                    'text': text,
                    'start': round(sub_start, 3),
                    'end': round(sub_end, 3),
                    'chunk_index': chunk.index,
                })
                sub_start = sub_end

        current_time = end + gap

    return timeline
