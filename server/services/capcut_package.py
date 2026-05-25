import io
import json
import zipfile


def build_manifest(
    title: str,
    template_key: str,
    duration: float,
    resolution: list[int],
    scenes: list[dict],
    voice_chunks: list[dict],
    subtitles: list[dict],
    audio: dict,
) -> dict:
    return {
        'title': title,
        'template_key': template_key,
        'duration': round(duration, 3),
        'resolution': resolution,
        'scenes': scenes,
        'voice_chunks': voice_chunks,
        'subtitles': subtitles,
        'audio': audio,
    }


def build_capcut_zip(
    title: str,
    video_bytes: bytes,
    voice_audio: bytes,
    mixed_audio: bytes,
    srt_content: str,
    manifest: dict,
    scene_files: list[tuple[str, bytes]],
    bgm_bytes: bytes | None = None,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{title}_成片.mp4', video_bytes)
        zf.writestr(f'{title}_完整旁白.wav', voice_audio)
        zf.writestr(f'{title}_混音音频.wav', mixed_audio)
        zf.writestr(f'{title}_同步字幕.srt', srt_content)
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, data in scene_files:
            zf.writestr(filename, data)
        if bgm_bytes:
            zf.writestr('audio/bgm.mp3', bgm_bytes)
    buf.seek(0)
    return buf.getvalue()
