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
