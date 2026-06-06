# server/services/novel/graph_extractor.py
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.graph_change import NovelGraphChange
from server.services.novel.prompt_templates import build_extract_prompt


def extract_graph_changes(project_id, chapter_id, params=None):
    """Extract graph change candidates from chapter content."""
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    # Build prompt
    prompt = build_extract_prompt(chapter.content_markdown)

    # Call LLM
    from server.services.novel import get_llm_provider
    params = params or {}
    provider, default_model = get_llm_provider(params.get('model_config'))

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model=default_model,
        system_prompt='你是一位小说知识图谱分析专家，擅长从小说文本中提取人物、关系、事件和因果关系。',
        max_tokens=4096,
        timeout=60,
    )

    # Parse response
    from server.services.memory.utils import parse_memory_json
    result = parse_memory_json(response) or {}
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


