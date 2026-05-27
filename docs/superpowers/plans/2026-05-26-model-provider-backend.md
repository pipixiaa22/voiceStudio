# Backend Model Provider Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a unified model provider registry that supports multiple LLM and TTS providers (MiMo, DeepSeek, OpenAI, MiniMax, custom), with preset configurations and connection testing.

**Architecture:** Abstract base class `ModelProvider` defines the interface. Concrete implementations handle specific API formats. `ModelRegistry` manages provider instances and resolves usage to provider+model. Routes expose presets, testing, and unified call endpoints.

**Tech Stack:** Python 3.13, Flask, requests

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/services/model_provider_base.py` | Abstract base class for all providers |
| `server/services/providers/__init__.py` | Package init |
| `server/services/providers/mimo_provider.py` | MiMo TTS + LLM provider |
| `server/services/providers/openai_compatible_provider.py` | OpenAI-compatible LLM provider (DeepSeek, custom) |
| `server/services/providers/openai_provider.py` | OpenAI provider (LLM + TTS) |
| `server/services/model_registry.py` | Registry, presets, usage resolution |
| `server/routes/models.py` | API routes for presets, testing, unified calls |
| `server/tests/test_model_provider_base.py` | Base class tests |
| `server/tests/test_mimo_provider.py` | MiMo provider tests |
| `server/tests/test_openai_compatible_provider.py` | OpenAI-compatible provider tests |
| `server/tests/test_model_registry.py` | Registry tests |
| `server/tests/test_models_routes.py` | Route tests |

---

## Task 1: Provider Base Class

**Files:**
- Create: `server/services/model_provider_base.py`
- Test: `server/tests/test_model_provider_base.py`

- [ ] **Step 1: Write failing test**

```python
# server/tests/test_model_provider_base.py
import pytest
from server.services.model_provider_base import ModelProvider, Capability


def test_capability_enum():
    assert Capability.LLM_TEXT.value == 'llm_text'
    assert Capability.TTS_VOICE_DESIGN.value == 'tts_voice_design'
    assert Capability.TTS_BUILTIN_VOICE.value == 'tts_builtin_voice'


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        ModelProvider(provider_id='test', api_key='key')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_model_provider_base.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement base class**

```python
# server/services/model_provider_base.py
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass


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
    capabilities: list[str]


@dataclass
class ProviderPreset:
    provider_key: str
    display_name: str
    provider_type: str
    base_url: str
    capabilities: list[str]
    models: list[ModelInfo]


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
        """Test the connection to the provider API."""
        raise NotImplementedError

    def complete(self, messages: list[dict], model: str, **options) -> str:
        """Call LLM completion. Returns text response."""
        raise NotImplementedError(f'{self.provider_id} does not support LLM completion')

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        """Call TTS synthesis. Returns audio bytes (base64 decoded)."""
        raise NotImplementedError(f'{self.provider_id} does not support TTS synthesis')

    def get_models(self) -> list[ModelInfo]:
        """Return available models for this provider."""
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_model_provider_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/model_provider_base.py server/tests/test_model_provider_base.py
git commit -m "feat: add model provider base class and capability enum"
```

---

## Task 2: MiMo Provider

**Files:**
- Create: `server/services/providers/__init__.py`
- Create: `server/services/providers/mimo_provider.py`
- Test: `server/tests/test_mimo_provider.py`

- [ ] **Step 1: Write failing test**

```python
# server/tests/test_mimo_provider.py
import pytest
from server.services.providers.mimo_provider import MimoProvider


def test_mimo_provider_init():
    provider = MimoProvider(api_key='test-key')
    assert provider.provider_id == 'mimo'
    assert provider.api_key == 'test-key'


def test_mimo_provider_get_models():
    provider = MimoProvider(api_key='test-key')
    models = provider.get_models()
    assert len(models) > 0
    model_keys = [m.model_key for m in models]
    assert 'mimo-v2.5-tts-voicedesign' in model_keys
    assert 'mimo-v2.5-pro' in model_keys


def test_mimo_provider_capabilities():
    provider = MimoProvider(api_key='test-key')
    assert 'tts_voice_design' in provider.capabilities
    assert 'llm_text' in provider.capabilities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_mimo_provider.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create providers package and MiMo provider**

```python
# server/services/providers/__init__.py
```

```python
# server/services/providers/mimo_provider.py
import requests
from server.services.model_provider_base import ModelProvider, ModelInfo, ConnectionResult


MIMO_TTS_URL = 'https://api.xiaomimimo.com/v1/chat/completions'
MIMO_LLM_URL = 'https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages'


class MimoProvider(ModelProvider):
    """MiMo provider for TTS and LLM."""

    provider_id = 'mimo'
    provider_type = 'mimo'
    capabilities = ['tts_voice_design', 'tts_voice_clone', 'tts_builtin_voice', 'llm_text', 'llm_voice_prompt_polish']

    def __init__(self, api_key: str, **kwargs):
        super().__init__(provider_id='mimo', api_key=api_key, **kwargs)

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_key='mimo-v2.5-tts-voicedesign',
                display_name='MiMo 音色设计',
                capabilities=['tts_voice_design'],
            ),
            ModelInfo(
                model_key='mimo-v2.5-tts-voiceclone',
                display_name='MiMo 音色复刻',
                capabilities=['tts_voice_clone'],
            ),
            ModelInfo(
                model_key='mimo-v2.5-tts',
                display_name='MiMo 预置音色',
                capabilities=['tts_builtin_voice'],
            ),
            ModelInfo(
                model_key='mimo-v2.5-pro',
                display_name='MiMo Pro',
                capabilities=['llm_text', 'llm_voice_prompt_polish'],
            ),
        ]

    def test_connection(self, model: str = '', capability: str = '') -> ConnectionResult:
        import time
        start = time.time()
        try:
            if capability in ('tts_voice_design', 'tts_voice_clone', 'tts_builtin_voice', ''):
                resp = requests.post(
                    MIMO_TTS_URL,
                    headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
                    json={
                        'model': model or 'mimo-v2.5-tts-voicedesign',
                        'messages': [
                            {'role': 'user', 'content': 'test'},
                            {'role': 'assistant', 'content': 'test'},
                        ],
                        'audio': {'format': 'wav'},
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    latency = int((time.time() - start) * 1000)
                    return ConnectionResult(ok=True, latency_ms=latency, message='连接成功')
                return ConnectionResult(ok=False, message=f'API 返回错误: {resp.status_code}')
            else:
                resp = requests.post(
                    MIMO_LLM_URL,
                    headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
                    json={
                        'model': 'mimo-v2.5-pro',
                        'max_tokens': 10,
                        'messages': [{'role': 'user', 'content': 'hi'}],
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    latency = int((time.time() - start) * 1000)
                    return ConnectionResult(ok=True, latency_ms=latency, message='连接成功')
                return ConnectionResult(ok=False, message=f'API 返回错误: {resp.status_code}')
        except requests.RequestException as e:
            return ConnectionResult(ok=False, message=f'连接失败: {str(e)}')

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        import base64
        style_tags = options.get('style_tags', '')
        voice = options.get('voice', '')

        assistant_text = text
        if style_tags:
            tags = style_tags.strip()
            assistant_text = f'{tags}{text}' if tags[0] in '([（［【' else f'（{tags}）{text}'

        audio_config = {'format': 'wav'}
        if voice:
            audio_config['voice'] = voice

        resp = requests.post(
            MIMO_TTS_URL,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
            json={
                'model': model or 'mimo-v2.5-tts-voicedesign',
                'messages': [
                    {'role': 'user', 'content': voice_description or ''},
                    {'role': 'assistant', 'content': assistant_text},
                ],
                'audio': audio_config,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f'MiMo API 返回错误: {resp.status_code}')
        result = resp.json()
        audio_b64 = result['choices'][0]['message']['audio']['data']
        return base64.b64decode(audio_b64)

    def complete(self, messages: list[dict], model: str, **options) -> str:
        system_prompt = options.get('system_prompt', '')
        max_tokens = options.get('max_tokens', 1024)

        payload = {
            'model': model or 'mimo-v2.5-pro',
            'max_tokens': max_tokens,
            'messages': messages,
        }
        if system_prompt:
            payload['system'] = system_prompt

        resp = requests.post(
            MIMO_LLM_URL,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise ValueError(f'MiMo API 返回错误: {resp.status_code}')
        result = resp.json()
        return result['content'][0]['text']
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_mimo_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/providers/__init__.py server/services/providers/mimo_provider.py server/tests/test_mimo_provider.py
git commit -m "feat: add MiMo provider implementation"
```

---

## Task 3: OpenAI-Compatible Provider

**Files:**
- Create: `server/services/providers/openai_compatible_provider.py`
- Test: `server/tests/test_openai_compatible_provider.py`

- [ ] **Step 1: Write failing test**

```python
# server/tests/test_openai_compatible_provider.py
import pytest
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider


def test_provider_init():
    provider = OpenAICompatibleProvider(
        provider_id='deepseek',
        api_key='test-key',
        base_url='https://api.deepseek.com',
    )
    assert provider.provider_id == 'deepseek'
    assert provider.base_url == 'https://api.deepseek.com'


def test_provider_capabilities():
    provider = OpenAICompatibleProvider(
        provider_id='deepseek',
        api_key='test-key',
        base_url='https://api.deepseek.com',
    )
    assert 'llm_text' in provider.capabilities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_openai_compatible_provider.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement OpenAI-compatible provider**

```python
# server/services/providers/openai_compatible_provider.py
import requests
from server.services.model_provider_base import ModelProvider, ModelInfo, ConnectionResult


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible API provider (DeepSeek, custom endpoints, etc.)."""

    provider_type = 'openai_compatible'
    capabilities = ['llm_text', 'llm_voice_prompt_polish', 'scene_planning', 'script_polish']

    def __init__(self, provider_id: str, api_key: str, base_url: str = 'https://api.openai.com/v1', **kwargs):
        super().__init__(provider_id=provider_id, api_key=api_key, base_url=base_url, **kwargs)

    def get_models(self) -> list[ModelInfo]:
        return self.config.get('models', [])

    def test_connection(self, model: str = '', capability: str = '') -> ConnectionResult:
        import time
        start = time.time()
        try:
            url = f'{self.base_url.rstrip("/")}/chat/completions'
            resp = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model or 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': 'hi'}],
                    'max_tokens': 10,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                latency = int((time.time() - start) * 1000)
                return ConnectionResult(ok=True, latency_ms=latency, message='连接成功')
            return ConnectionResult(ok=False, message=f'API 返回错误: {resp.status_code}')
        except requests.RequestException as e:
            return ConnectionResult(ok=False, message=f'连接失败: {str(e)}')

    def complete(self, messages: list[dict], model: str, **options) -> str:
        system_prompt = options.get('system_prompt', '')
        max_tokens = options.get('max_tokens', 1024)

        url = f'{self.base_url.rstrip("/")}/chat/completions'
        payload = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
        }
        if system_prompt:
            payload['messages'] = [{'role': 'system', 'content': system_prompt}] + payload['messages']

        resp = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise ValueError(f'API 返回错误: {resp.status_code}')
        result = resp.json()
        return result['choices'][0]['message']['content']
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_openai_compatible_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/providers/openai_compatible_provider.py server/tests/test_openai_compatible_provider.py
git commit -m "feat: add OpenAI-compatible provider"
```

---

## Task 4: OpenAI Provider (with TTS)

**Files:**
- Create: `server/services/providers/openai_provider.py`

- [ ] **Step 1: Implement OpenAI provider**

```python
# server/services/providers/openai_provider.py
import requests
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from server.services.model_provider_base import ModelInfo, ConnectionResult


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider with TTS support."""

    provider_id = 'openai'
    provider_type = 'openai'
    capabilities = ['llm_text', 'tts_plain', 'scene_planning', 'script_polish']

    def __init__(self, api_key: str, base_url: str = 'https://api.openai.com/v1', **kwargs):
        super().__init__(provider_id='openai', api_key=api_key, base_url=base_url, **kwargs)

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(model_key='gpt-4.1-mini', display_name='GPT-4.1 Mini', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='gpt-4.1', display_name='GPT-4.1', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='tts-1', display_name='OpenAI TTS', capabilities=['tts_plain']),
        ]

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        voice = options.get('voice', 'alloy')
        url = f'{self.base_url.rstrip("/")}/audio/speech'
        resp = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model or 'tts-1',
                'input': text,
                'voice': voice,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f'OpenAI TTS API 返回错误: {resp.status_code}')
        return resp.content
```

- [ ] **Step 2: Commit**

```bash
git add server/services/providers/openai_provider.py
git commit -m "feat: add OpenAI provider with TTS support"
```

---

## Task 5: Model Registry with Presets

**Files:**
- Create: `server/services/model_registry.py`
- Test: `server/tests/test_model_registry.py`

- [ ] **Step 1: Write failing test**

```python
# server/tests/test_model_registry.py
import pytest
from server.services.model_registry import ModelRegistry


def test_registry_get_presets():
    registry = ModelRegistry()
    presets = registry.get_presets()
    assert len(presets) >= 3
    keys = [p.provider_key for p in presets]
    assert 'mimo' in keys
    assert 'deepseek' in keys
    assert 'openai' in keys


def test_registry_create_provider_mimo():
    registry = ModelRegistry()
    provider = registry.create_provider('mimo', api_key='test-key')
    assert provider.provider_id == 'mimo'


def test_registry_create_provider_deepseek():
    registry = ModelRegistry()
    provider = registry.create_provider('deepseek', api_key='test-key')
    assert provider.provider_id == 'deepseek'
    assert provider.base_url == 'https://api.deepseek.com'


def test_registry_create_provider_custom():
    registry = ModelRegistry()
    provider = registry.create_provider(
        'custom',
        api_key='test-key',
        base_url='https://my-api.com/v1',
        provider_type='openai_compatible',
        display_name='My API',
    )
    assert provider.provider_id == 'custom'
    assert provider.base_url == 'https://my-api.com/v1'


def test_registry_get_all_models():
    registry = ModelRegistry()
    models = registry.get_all_models()
    assert len(models) > 0
    mimo_models = [m for m in models if m['provider_key'] == 'mimo']
    assert len(mimo_models) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_model_registry.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement registry**

```python
# server/services/model_registry.py
from server.services.model_provider_base import ModelProvider, ProviderPreset, ModelInfo
from server.services.providers.mimo_provider import MimoProvider
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from server.services.providers.openai_provider import OpenAIProvider


BUILTIN_PRESETS = [
    ProviderPreset(
        provider_key='mimo',
        display_name='MiMo',
        provider_type='mimo',
        base_url='',
        capabilities=['tts_voice_design', 'tts_voice_clone', 'tts_builtin_voice', 'llm_text', 'llm_voice_prompt_polish'],
        models=[
            ModelInfo(model_key='mimo-v2.5-tts-voicedesign', display_name='MiMo 音色设计', capabilities=['tts_voice_design']),
            ModelInfo(model_key='mimo-v2.5-tts-voiceclone', display_name='MiMo 音色复刻', capabilities=['tts_voice_clone']),
            ModelInfo(model_key='mimo-v2.5-tts', display_name='MiMo 预置音色', capabilities=['tts_builtin_voice']),
            ModelInfo(model_key='mimo-v2.5-pro', display_name='MiMo Pro', capabilities=['llm_text', 'llm_voice_prompt_polish']),
        ],
    ),
    ProviderPreset(
        provider_key='deepseek',
        display_name='DeepSeek',
        provider_type='openai_compatible',
        base_url='https://api.deepseek.com',
        capabilities=['llm_text', 'llm_voice_prompt_polish', 'scene_planning', 'script_polish'],
        models=[
            ModelInfo(model_key='deepseek-chat', display_name='DeepSeek Chat', capabilities=['llm_text', 'llm_voice_prompt_polish', 'scene_planning']),
        ],
    ),
    ProviderPreset(
        provider_key='openai',
        display_name='ChatGPT / OpenAI',
        provider_type='openai',
        base_url='https://api.openai.com/v1',
        capabilities=['llm_text', 'tts_plain', 'scene_planning', 'script_polish'],
        models=[
            ModelInfo(model_key='gpt-4.1-mini', display_name='GPT-4.1 Mini', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='gpt-4.1', display_name='GPT-4.1', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='tts-1', display_name='OpenAI TTS', capabilities=['tts_plain']),
        ],
    ),
    ProviderPreset(
        provider_key='minimax',
        display_name='MiniMax',
        provider_type='openai_compatible',
        base_url='https://api.minimax.chat/v1',
        capabilities=['llm_text', 'tts_plain'],
        models=[
            ModelInfo(model_key='minimax-text-default', display_name='MiniMax 文本模型', capabilities=['llm_text']),
            ModelInfo(model_key='minimax-tts-default', display_name='MiniMax TTS', capabilities=['tts_plain']),
        ],
    ),
]


class ModelRegistry:
    """Registry for model providers."""

    def __init__(self):
        self._presets = {p.provider_key: p for p in BUILTIN_PRESETS}

    def get_presets(self) -> list[ProviderPreset]:
        return list(self._presets.values())

    def get_preset(self, provider_key: str) -> ProviderPreset | None:
        return self._presets.get(provider_key)

    def create_provider(
        self,
        provider_key: str,
        api_key: str,
        base_url: str = '',
        provider_type: str = '',
        **kwargs,
    ) -> ModelProvider:
        """Create a provider instance."""
        preset = self._presets.get(provider_key)

        if provider_key == 'mimo' or (preset and preset.provider_type == 'mimo'):
            return MimoProvider(api_key=api_key)

        if provider_key == 'openai' or (preset and preset.provider_type == 'openai'):
            url = base_url or (preset.base_url if preset else 'https://api.openai.com/v1')
            return OpenAIProvider(api_key=api_key, base_url=url)

        if preset and preset.provider_type == 'openai_compatible':
            return OpenAICompatibleProvider(
                provider_id=provider_key,
                api_key=api_key,
                base_url=base_url or preset.base_url,
            )

        if provider_type == 'openai_compatible':
            return OpenAICompatibleProvider(
                provider_id=provider_key,
                api_key=api_key,
                base_url=base_url,
            )

        raise ValueError(f'Unknown provider: {provider_key}')

    def get_all_models(self) -> list[dict]:
        """Return all available models grouped by provider."""
        result = []
        for preset in self._presets.values():
            for model in preset.models:
                result.append({
                    'provider_key': preset.provider_key,
                    'provider_name': preset.display_name,
                    'model_key': model.model_key,
                    'model_name': model.display_name,
                    'capabilities': model.capabilities,
                })
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_model_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/model_registry.py server/tests/test_model_registry.py
git commit -m "feat: add model registry with builtin presets"
```

---

## Task 6: API Routes

**Files:**
- Create: `server/routes/models.py`
- Modify: `server/app.py`
- Test: `server/tests/test_models_routes.py`

- [ ] **Step 1: Write failing test**

```python
# server/tests/test_models_routes.py
import pytest


def test_get_presets(client):
    response = client.get('/api/model-providers/presets')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 3
    keys = [p['provider_key'] for p in data]
    assert 'mimo' in keys
    assert 'deepseek' in keys


def test_get_all_models(client):
    response = client.get('/api/models')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
    assert 'provider_key' in data[0]
    assert 'model_key' in data[0]


def test_test_connection_missing_params(client):
    response = client.post('/api/model-providers/test', json={})
    assert response.status_code == 400


def test_llm_complete_missing_params(client):
    response = client.post('/api/models/llm/complete', json={})
    assert response.status_code == 400


def test_tts_synthesize_missing_params(client):
    response = client.post('/api/models/tts/synthesize', json={})
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_models_routes.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement routes**

```python
# server/routes/models.py
from flask import Blueprint, request, jsonify
from server.services.model_registry import ModelRegistry

models_bp = Blueprint('models', __name__)
registry = ModelRegistry()


@models_bp.route('/api/model-providers/presets', methods=['GET'])
def get_presets():
    presets = registry.get_presets()
    return jsonify([
        {
            'provider_key': p.provider_key,
            'display_name': p.display_name,
            'provider_type': p.provider_type,
            'base_url': p.base_url,
            'capabilities': p.capabilities,
            'models': [
                {
                    'model_key': m.model_key,
                    'display_name': m.display_name,
                    'capabilities': m.capabilities,
                }
                for m in p.models
            ],
        }
        for p in presets
    ])


@models_bp.route('/api/models', methods=['GET'])
def get_all_models():
    return jsonify(registry.get_all_models())


@models_bp.route('/api/model-providers/test', methods=['POST'])
def test_connection():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    provider_type = data.get('provider_type', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    capability = data.get('capability', '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    try:
        provider = registry.create_provider(
            provider_key or provider_type,
            api_key=api_key,
            base_url=base_url,
            provider_type=provider_type,
        )
        result = provider.test_connection(model=model, capability=capability)
        return jsonify({
            'ok': result.ok,
            'latency_ms': result.latency_ms,
            'message': result.message,
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500


@models_bp.route('/api/models/llm/complete', methods=['POST'])
def llm_complete():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    messages = data.get('messages', [])
    system_prompt = data.get('system_prompt', '')
    max_tokens = data.get('max_tokens', 1024)

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not messages:
        return jsonify({'error': '请提供消息'}), 400

    try:
        provider = registry.create_provider(
            provider_key, api_key=api_key, base_url=base_url,
        )
        result = provider.complete(
            messages, model,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )
        return jsonify({'text': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@models_bp.route('/api/models/tts/synthesize', methods=['POST'])
def tts_synthesize():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    text = data.get('text', '')
    voice_description = data.get('voice_description', '')
    voice = data.get('voice', '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not text:
        return jsonify({'error': '请提供文本'}), 400

    try:
        import base64
        provider = registry.create_provider(
            provider_key, api_key=api_key, base_url=base_url,
        )
        audio_bytes = provider.synthesize(
            text, model,
            voice_description=voice_description,
            voice=voice,
        )
        return jsonify({'audio_base64': base64.b64encode(audio_bytes).decode()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Register blueprint in app.py**

Add to `server/app.py` in the `create_app` function:

```python
from server.routes.models import models_bp
app.register_blueprint(models_bp)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest server/tests/test_models_routes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/routes/models.py server/app.py server/tests/test_models_routes.py
git commit -m "feat: add model provider API routes"
```

---

## Task 7: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete backend model provider registry"
```
