from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field


class Capability(Enum):
    LLM_TEXT = 'llm_text'
    LLM_VOICE_PROMPT_POLISH = 'llm_voice_prompt_polish'
    TTS_BUILTIN_VOICE = 'tts_builtin_voice'
    TTS_VOICE_DESIGN = 'tts_voice_design'
    TTS_VOICE_CLONE = 'tts_voice_clone'
    TTS_PLAIN = 'tts_plain'
    SCENE_PLANNING = 'scene_planning'
    SCRIPT_POLISH = 'script_polish'


@dataclass
class ModelInfo:
    model_key: str
    display_name: str
    capabilities: list[str] = field(default_factory=list)


@dataclass
class ProviderPreset:
    provider_key: str
    display_name: str
    provider_type: str
    base_url: str
    capabilities: list[str] = field(default_factory=list)
    models: list[ModelInfo] = field(default_factory=list)


@dataclass
class ConnectionResult:
    ok: bool
    latency_ms: int | None = None
    message: str = ''


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    provider_id: str
    provider_type: str
    capabilities: list[str]

    def __init__(self, provider_id: str, api_key: str, base_url: str = '', **kwargs):
        self.provider_id = provider_id
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs

    @abstractmethod
    def test_connection(self, model: str = '', capability: str = '') -> ConnectionResult:
        raise NotImplementedError

    def complete(self, messages: list[dict], model: str, **options) -> str:
        raise NotImplementedError(f'{self.provider_id} does not support LLM completion')

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        raise NotImplementedError(f'{self.provider_id} does not support TTS synthesis')

    def get_models(self) -> list[ModelInfo]:
        return []
