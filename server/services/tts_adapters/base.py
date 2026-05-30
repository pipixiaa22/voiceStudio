from dataclasses import dataclass, field


@dataclass
class TTSSegmentRequest:
    """Vendor-agnostic TTS segment request."""
    text: str
    voice_description: str = ''
    style_tags: str | None = None
    model: str = ''
    voice: str | None = None
    output_format: str = 'wav'


@dataclass
class TTSResult:
    """Unified TTS result."""
    audio_bytes: bytes
    duration: float = 0.0
    model: str = ''
    provider: str = ''
