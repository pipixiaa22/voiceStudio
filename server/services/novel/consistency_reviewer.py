# server/services/novel/consistency_reviewer.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent
from server.services.novel.context_builder import _build_character_context, _build_previous_summaries
from server.services.novel.prompt_templates import build_review_prompt
from server.services.model_registry import ModelRegistry


def review_chapter(project_id, chapter_id):
    """Run consistency review on a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    # Build review context
    context = {
        'characters': _build_character_context(project_id, chapter),
        'previous_summaries': _build_previous_summaries(project_id, chapter),
        'world_rules': _format_world_rules(project.settings),
    }

    # Build prompt
    prompt = build_review_prompt(chapter.content_markdown, context)

    # Call LLM
    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt='你是一位资深小说编辑，擅长检查小说的一致性和质量。',
        max_tokens=4096,
        timeout=60,
    )

    # Parse response
    result = _parse_json_response(response)

    return {
        'chapter_id': chapter_id,
        'issues': result.get('issues', []),
        'overall_score': result.get('overall_score', 0),
        'summary': result.get('summary', ''),
    }


def _format_world_rules(settings):
    if not settings:
        return ''
    parts = []
    for key, value in settings.items():
        if value:
            if isinstance(value, list):
                value = '、'.join(str(v) for v in value)
            elif isinstance(value, dict):
                value = ', '.join(f'{k}={v}' for k, v in value.items())
            parts.append(f'{key}：{value}')
    return '\n'.join(parts)


def _parse_json_response(text):
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError('无法解析 AI 返回的 JSON')


def _get_active_provider():
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    return 'mimo', ''
