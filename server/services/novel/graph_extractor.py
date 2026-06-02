# server/services/novel/graph_extractor.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.graph_change import NovelGraphChange
from server.services.novel.prompt_templates import build_extract_prompt
from server.services.model_registry import ModelRegistry


def extract_graph_changes(project_id, chapter_id):
    """Extract graph change candidates from chapter content."""
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    # Build prompt
    prompt = build_extract_prompt(chapter.content_markdown)

    # Call LLM
    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt='你是一位小说知识图谱分析专家，擅长从小说文本中提取人物、关系、事件和因果关系。',
        max_tokens=4096,
        timeout=60,
    )

    # Parse response
    result = _parse_json_response(response)
    changes_data = result.get('changes', [])

    # Create GraphChange records
    changes = []
    for item in changes_data:
        change = NovelGraphChange(
            project_id=project_id,
            chapter_id=chapter_id,
            change_type=item.get('change_type', 'add'),
            target_type=item.get('target_type', 'entity'),
            source='ai_confirm',
            confidence=item.get('confidence', 0.7),
        )
        if 'before' in item:
            change.before = item['before']
        if 'after' in item:
            change.after = item['after']
        db.session.add(change)
        changes.append(change)

    db.session.commit()

    return {
        'chapter_id': chapter_id,
        'changes_count': len(changes),
        'changes': [c.to_dict() for c in changes],
    }


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
