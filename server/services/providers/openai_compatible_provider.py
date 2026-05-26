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
