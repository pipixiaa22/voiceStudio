import pytest
from server.services.model_provider_base import ModelProvider, Capability


def test_capability_enum():
    assert Capability.LLM_TEXT.value == 'llm_text'
    assert Capability.TTS_VOICE_DESIGN.value == 'tts_voice_design'
    assert Capability.TTS_BUILTIN_VOICE.value == 'tts_builtin_voice'


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        ModelProvider(provider_id='test', api_key='key')
