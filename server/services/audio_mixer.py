import io
import struct
import wave


def _read_wav(wav_bytes: bytes) -> dict:
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'sample_width': wav.getsampwidth(),
            'framerate': wav.getframerate(),
            'frames': wav.readframes(wav.getnframes()),
        }


def _resample_linear(frames: bytes, src_rate: int, dst_rate: int, sample_width: int, channels: int) -> bytes:
    if src_rate == dst_rate:
        return frames
    num_src_samples = len(frames) // (sample_width * channels)
    ratio = src_rate / dst_rate
    num_dst_samples = int(num_src_samples / ratio)
    out = bytearray()
    for i in range(num_dst_samples):
        src_pos = i * ratio
        idx = int(src_pos)
        frac = src_pos - idx
        byte_idx = idx * sample_width * channels
        next_byte_idx = min(byte_idx + sample_width * channels, len(frames) - sample_width * channels)
        if byte_idx >= len(frames) or next_byte_idx < 0:
            out.extend(b'\x00' * sample_width * channels)
            continue
        s1 = struct.unpack('<h', frames[byte_idx:byte_idx + 2])[0]
        s2 = struct.unpack('<h', frames[next_byte_idx:next_byte_idx + 2])[0]
        interpolated = int(s1 + frac * (s2 - s1))
        interpolated = max(-32768, min(32767, interpolated))
        out.extend(struct.pack('<h', interpolated))
    return bytes(out)


def _loop_or_crop(frames: bytes, target_frames: int, sample_width: int, channels: int) -> bytes:
    frame_bytes = sample_width * channels
    total_frames = len(frames) // frame_bytes
    if total_frames >= target_frames:
        return frames[:target_frames * frame_bytes]
    result = bytearray()
    while len(result) < target_frames * frame_bytes:
        remaining = target_frames * frame_bytes - len(result)
        chunk = frames[:min(len(frames), remaining)]
        result.extend(chunk)
    return bytes(result)


def _apply_fade(frames: bytes, fade_in_sec: float, fade_out_sec: float, 
                sample_width: int, channels: int, framerate: int) -> bytes:
    if fade_in_sec <= 0 and fade_out_sec <= 0:
        return frames
    frame_bytes = sample_width * channels
    total_frames = len(frames) // frame_bytes
    result = bytearray(frames)
    fade_in_frames = int(fade_in_sec * framerate)
    fade_out_frames = int(fade_out_sec * framerate)
    for i in range(min(fade_in_frames, total_frames)):
        gain = i / fade_in_frames
        for c in range(channels):
            offset = i * frame_bytes + c * sample_width
            sample = struct.unpack('<h', result[offset:offset + 2])[0]
            sample = int(sample * gain)
            result[offset:offset + 2] = struct.pack('<h', max(-32768, min(32767, sample)))
    for i in range(min(fade_out_frames, total_frames)):
        idx = total_frames - 1 - i
        gain = i / fade_out_frames
        for c in range(channels):
            offset = idx * frame_bytes + c * sample_width
            sample = struct.unpack('<h', result[offset:offset + 2])[0]
            sample = int(sample * gain)
            result[offset:offset + 2] = struct.pack('<h', max(-32768, min(32767, sample)))
    return bytes(result)


def _mix_pcm(voice: bytes, bgm: bytes, ambient: bytes, 
             voice_vol: float, bgm_vol: float, ambient_vol: float) -> bytes:
    max_len = max(len(voice), len(bgm), len(ambient))
    result = bytearray(max_len)
    for i in range(0, max_len, 2):
        v = struct.unpack('<h', voice[i:i + 2])[0] if i < len(voice) else 0
        b = struct.unpack('<h', bgm[i:i + 2])[0] if i < len(bgm) else 0
        a = struct.unpack('<h', ambient[i:i + 2])[0] if i < len(ambient) else 0
        mixed = int(v * voice_vol + b * bgm_vol + a * ambient_vol)
        mixed = max(-32768, min(32767, mixed))
        result[i:i + 2] = struct.pack('<h', mixed)
    return bytes(result)


def mix_audio(
    voice_wav: bytes,
    bgm_wav: bytes | None = None,
    ambient_wav: bytes | None = None,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.18,
    ambient_volume: float = 0.12,
    fade_in: float = 1.0,
    fade_out: float = 1.5,
) -> bytes:
    voice_info = _read_wav(voice_wav)
    channels = voice_info['channels']
    sample_width = voice_info['sample_width']
    framerate = voice_info['framerate']
    voice_frames = voice_info['frames']
    total_samples = len(voice_frames) // (sample_width * channels)

    bgm_frames = b''
    if bgm_wav:
        bgm_info = _read_wav(bgm_wav)
        bgm_data = bgm_info['frames']
        if bgm_info['framerate'] != framerate:
            bgm_data = _resample_linear(bgm_data, bgm_info['framerate'], framerate, sample_width, channels)
        bgm_frames = _loop_or_crop(bgm_data, total_samples, sample_width, channels)
        bgm_frames = _apply_fade(bgm_frames, fade_in, fade_out, sample_width, channels, framerate)

    ambient_frames = b''
    if ambient_wav:
        ambient_info = _read_wav(ambient_wav)
        ambient_data = ambient_info['frames']
        if ambient_info['framerate'] != framerate:
            ambient_data = _resample_linear(ambient_data, ambient_info['framerate'], framerate, sample_width, channels)
        ambient_frames = _loop_or_crop(ambient_data, total_samples, sample_width, channels)

    mixed = _mix_pcm(voice_frames, bgm_frames, ambient_frames, voice_volume, bgm_volume, ambient_volume)

    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(framerate)
        wav.writeframes(mixed)
    return output.getvalue()
