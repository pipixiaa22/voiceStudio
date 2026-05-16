def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳。"""
    total_millis = round(seconds * 1000)
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list[str], chars_per_second: float = 5, gap: float = 1.0) -> str:
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
        lines.append(segment.replace("\n", " "))
        lines.append("")

        current_time += duration + gap

    return "\n".join(lines)


def generate_bilingual_srt(segments: list[str], translations: list[str], chars_per_second: float = 5, gap: float = 1.0) -> str:
    """生成双语 SRT：中文在上，英文在下。"""
    if not segments:
        return ""

    lines = []
    current_time = 0.0

    for i, (segment, translation) in enumerate(zip(segments, translations), 1):
        duration = len(segment) / chars_per_second
        start = _format_timestamp(current_time)
        end = _format_timestamp(current_time + duration)

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(segment.replace("\n", " "))
        if translation:
            lines.append(translation.replace("\n", " "))
        lines.append("")

        current_time += duration + gap

    return "\n".join(lines)
