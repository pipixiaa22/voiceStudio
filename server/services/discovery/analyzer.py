import hashlib
import json
from server.services.model_registry import ModelRegistry

ANALYSIS_SYSTEM_PROMPT = '你是一个修仙短视频小说的选题分析师。根据热门视频的元数据，分析其成功要素，并生成一个原创脚本。所有输出必须是合法的 JSON 格式。'

ANALYSIS_PROMPT_TEMPLATE = '''分析以下视频元数据，生成原创脚本。直接输出JSON，不要其他内容。

视频：{title} | {platform} | {duration}秒 | 播放{views} | 赞{likes} | 评{comments}
标签：{tags}
评分：{reasons}

JSON字段：
{{
  "title_pattern": "标题套路",
  "hook": "前3秒钩子",
  "plot_skeleton": "剧情骨架",
  "subtitle_rhythm": "字幕节奏",
  "generated_title": "原创标题",
  "generated_content": "原创脚本（分段，每段15-20字）",
  "recommended_template": "xianxia_narration",
  "recommended_voice_desc": "声线",
  "recommended_max_chars": 16
}}'''

DEFAULT_PROVIDER = 'mimo'
DEFAULT_MODEL = 'mimo-v2.5-pro'


def _get_llm_config() -> tuple[str, str, str, str]:
    """获取 LLM 配置：(provider_key, api_key, base_url, model)"""
    from server.models.provider import CustomProvider
    from server.models.discovery import DiscoverySource

    src = DiscoverySource.query.filter_by(platform_key='_llm_config').first()
    if src:
        config = json.loads(src.config_json) if src.config_json else {}
        if config.get('api_key'):
            return (
                config.get('provider_key', DEFAULT_PROVIDER),
                config['api_key'],
                config.get('base_url', ''),
                config.get('model', DEFAULT_MODEL),
            )

    cp = CustomProvider.query.first()
    if cp:
        models = json.loads(cp.models_json) if cp.models_json else []
        llm_model = next((m for m in models if 'llm' in str(m.get('capabilities', []))), None)
        if llm_model:
            return (cp.provider_key, '', cp.base_url, llm_model.get('model_key', ''))

    return DEFAULT_PROVIDER, '', '', DEFAULT_MODEL


def _try_fix_truncated_json(text: str) -> dict:
    """尝试修复被截断的 JSON 响应"""
    import re
    text = text.strip()

    # 提取已有的 key-value 对
    result = {}
    # 匹配 "key": "value" 模式（value 可能含换行）
    for match in re.finditer(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
        result[match.group(1)] = match.group(2)

    # 匹配 "key": number 模式
    for match in re.finditer(r'"(\w+)"\s*:\s*(\d+(?:\.\d+)?)', text):
        if match.group(1) not in result:
            result[match.group(1)] = float(match.group(2)) if '.' in match.group(2) else int(match.group(2))

    if result:
        return result

    raise ValueError(f'LLM 返回的内容无法解析为 JSON: {text[:200]}')


def analyze_item(item: dict, score_result: dict, api_key: str = '', force_refresh: bool = False) -> dict:
    """调用 LLM 分析视频并生成原创脚本"""
    from server.services.redis_client import redis_key, cache_get_json, cache_set_json

    registry = ModelRegistry()

    if api_key:
        provider_key, _, base_url, model = _get_llm_config()
    else:
        provider_key, api_key, base_url, model = _get_llm_config()

    if not api_key:
        raise ValueError('LLM API key 未配置。请在模型设置中配置 API key。')

    # Check LLM analysis cache — key must cover every input that affects the prompt
    stats = item.get('stats') or {}
    tags = item.get('tags') or []
    reasons = score_result.get('reasons') or []
    cache_input = json.dumps({
        'title': item.get('title'),
        'platform_key': item.get('platform_key'),
        'source_id': item.get('source_id'),
        'duration': item.get('duration'),
        'views': stats.get('views'), 'likes': stats.get('likes'), 'comments': stats.get('comments'),
        'tags': tags,
        'reasons': reasons,
        'prompt_version': 'v1',
        'provider_key': provider_key,
        'model': model,
        'base_url': base_url,
    }, sort_keys=True)
    item_hash = hashlib.sha256(cache_input.encode()).hexdigest()[:16]
    cache_k = redis_key('llm', 'analysis', item_hash)
    if not force_refresh:
        cached = cache_get_json(cache_k)
        if cached is not None:
            return cached

    provider = registry.create_provider(
        provider_key, api_key=api_key, base_url=base_url,
    )

    title = item.get('title') or '未知标题'
    platform = item.get('platform_key', '未知')
    duration = item.get('duration') or 0
    stats = item.get('stats') or {}
    tags = item.get('tags') or []
    reasons = score_result.get('reasons') or []

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        title=title,
        platform=platform,
        duration=int(duration),
        views=stats.get('views', 0),
        likes=stats.get('likes', 0),
        comments=stats.get('comments', 0),
        tags=', '.join(tags),
        reasons='\n'.join(f'- {r}' for r in reasons),
    )

    messages = [{'role': 'user', 'content': prompt}]
    result_text = provider.complete(messages, model, system_prompt=ANALYSIS_SYSTEM_PROMPT, max_tokens=3000, timeout=120)

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
            except json.JSONDecodeError:
                result = _try_fix_truncated_json(match.group(1))
        else:
            start = result_text.find('{')
            end = result_text.rfind('}')
            if start >= 0 and end > start:
                try:
                    result = json.loads(result_text[start:end + 1])
                except json.JSONDecodeError:
                    result = _try_fix_truncated_json(result_text[start:end + 1])
            else:
                result = _try_fix_truncated_json(result_text)

    if not isinstance(result, dict):
        raise ValueError(f'LLM 返回的内容无法解析为 JSON: {result_text[:200]}')

    cache_set_json(cache_k, result, ttl=86400 * 7)  # 7 days
    return result
