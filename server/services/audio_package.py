import io
import json
import wave
import zipfile
from urllib.parse import quote


def read_wav_info(audio_bytes: bytes) -> dict:
    """读取 WAV 文件信息。"""
    with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'sample_width': wav.getsampwidth(),
            'framerate': wav.getframerate(),
            'frames': wav.getnframes(),
            'params': wav.getparams(),
            'frame_bytes': wav.readframes(wav.getnframes()),
        }


def concat_wavs(wav_infos: list[dict], gap: float = 0.3) -> bytes:
    """拼接多个 WAV 文件，中间插入静音间隔。"""
    if not wav_infos:
        return b''

    base = wav_infos[0]
    for info in wav_infos[1:]:
        if (
            info['channels'] != base['channels']
            or info['sample_width'] != base['sample_width']
            or info['framerate'] != base['framerate']
        ):
            raise ValueError('音频参数不一致，无法拼接')

    silence_frames = round(gap * base['framerate'])
    silence = b'\x00' * silence_frames * base['channels'] * base['sample_width']

    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(base['channels'])
        wav.setsampwidth(base['sample_width'])
        wav.setframerate(base['framerate'])
        for index, info in enumerate(wav_infos):
            if index:
                wav.writeframes(silence)
            wav.writeframes(info['frame_bytes'])
    return output.getvalue()


def _format_srt_timestamp(seconds: float) -> str:
    """格式化 SRT 时间戳。"""
    total_millis = round(seconds * 1000)
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def build_srt(timeline: list[dict]) -> str:
    """根据时间轴生成 SRT 字幕。"""
    lines = []
    for i, item in enumerate(timeline, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_timestamp(item['start'])} --> {_format_srt_timestamp(item['end'])}")
        lines.append(item['text'].replace('\n', ' '))
        lines.append('')
    return '\n'.join(lines)


def build_zip_package(
    title: str,
    full_audio: bytes,
    srt_content: str,
    manifest: dict,
    chunk_files: list[tuple[str, bytes]],
) -> bytes:
    """打包 ZIP 文件。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{title}_完整音频.wav', full_audio)
        zf.writestr(f'{title}_同步字幕.srt', srt_content)
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, audio_bytes in chunk_files:
            zf.writestr(filename, audio_bytes)
    buf.seek(0)
    return buf.getvalue()
