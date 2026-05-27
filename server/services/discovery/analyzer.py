import json
from server.services.model_registry import ModelRegistry

ANALYSIS_SYSTEM_PROMPT = '你是一个修仙短视频小说的选题分析师。根据热门视频的元数据，分析其成功要素，并生成一个原创脚本。所有输出必须是合法的 JSON 格式。'

ANALYSIS_PROMPT_TEMPLATE = '''根据以下热门视频的元数据，分析其成功要素并生成原创脚本。

## 视频信息
- 标题：{title}
- 平台：{platform}
- 时长：{duration}秒
- 播放量：{views}
- 点赞：{likes}
- 评论：{comments}
- 标签：{tags}

## 评分理由
{reasons}

## 要求
1. 分析标题套路（爽点/冲突/身份反转）
2. 分析开头钩子（前3秒要抛出的危机或反差）
3. 提取剧情骨架（主角身份、压迫者、金手指、第一次反击、悬念）
4. 建议字幕节奏（每句12-20字，短句优先）
5. 生成一个原创标题（不要复制原标题，要换人物/换冲突/换世界观）
6. 生成原创脚本正文（分段，每段对应一个字幕时间段，用换行分隔）
7. 推荐视频参数

以 JSON 格式输出，字段如下：
{{
  "title_pattern": "标题套路分析",
  "hook": "开头钩子描述",
  "plot_skeleton": "剧情骨架",
  "subtitle_rhythm": "字幕节奏建议",
  "generated_title": "原创标题",
  "generated_content": "原创脚本正文",
  "recommended_template": "xianxia_narration",
  "recommended_voice_desc": "推荐声线描述",
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


def analyze_item(item: dict, score_result: dict) -> dict:
    """调用 LLM 分析视频并生成原创脚本"""
    registry = ModelRegistry()
    provider_key, api_key, base_url, model = _get_llm_config()

    if not api_key:
        raise ValueError('LLM API key 未配置。请在模型设置中配置 API key。')

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
    result_text = provider.complete(messages, model, system_prompt=ANALYSIS_SYSTEM_PROMPT, max_tokens=2000)

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result_text, re.DOTALL)
        if match:
            result = json.loads(match.group(1))
        else:
            start = result_text.find('{')
            end = result_text.rfind('}')
            if start >= 0 and end > start:
                result = json.loads(result_text[start:end + 1])
            else:
                raise ValueError(f'LLM 返回的内容无法解析为 JSON: {result_text[:200]}')

    return result
