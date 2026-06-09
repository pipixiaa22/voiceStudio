# server/services/novel/consistency_reviewer.py
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent
from server.services.novel.narrative_state import load_state, summarize_for_context, _format_characters, _format_world_settings
from server.services.novel.prompt_templates import build_review_prompt


def review_chapter(project_id, chapter_id, params=None):
    """Run consistency review on a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    state = load_state(project_id, chapter_id)
    state_context = summarize_for_context(state)

    context = {
        'characters': _format_characters(state, 3000),
        'previous_summaries': _build_previous_summaries_from_state(state),
        'world_rules': _format_world_settings(state.world_settings),
        'overall_outline': state_context.get('overall_outline', ''),
        'volume_outline': state_context.get('volume_outline', ''),
        'outline': state_context.get('outline', ''),
    }

    return _do_review(project_id, chapter_id, chapter.content_markdown, context, params=params)


def review_content(project_id, chapter_id, content, params=None):
    """Run consistency review on arbitrary content (e.g. a draft not yet saved).

    Args:
        project_id: Project ID.
        chapter_id: Chapter ID (used for context building).
        content: The content to review.

    Returns:
        Review result dict with issues, score, summary.
    """
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    state = load_state(project_id, chapter_id)
    state_context = summarize_for_context(state)

    context = {
        'characters': _format_characters(state, 3000),
        'previous_summaries': _build_previous_summaries_from_state(state),
        'world_rules': _format_world_settings(state.world_settings),
        'overall_outline': state_context.get('overall_outline', ''),
        'volume_outline': state_context.get('volume_outline', ''),
        'outline': state_context.get('outline', ''),
    }

    return _do_review(project_id, chapter_id, content, context, params=params)


def _build_previous_summaries_from_state(state):
    """Build previous summaries from NarrativeState (no extra DB queries)."""
    parts = []
    for ch in reversed(state.recent_chapters):
        if ch.summary:
            parts.append(f'第{ch.order_index}章 {ch.title}：{ch.summary}')
    if not parts:
        return ''
    text = '\n'.join(parts)
    return text[:2500] + '...' if len(text) > 2500 else text


def _do_review(project_id, chapter_id, content, context, params=None):
    """Internal review implementation."""
    prompt = build_review_prompt(content, context)

    from server.services.novel import get_llm_provider
    params = params or {}
    provider, default_model = get_llm_provider(params.get('model_config'))

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model=default_model,
        system_prompt='你是一位资深小说编辑，擅长检查小说的一致性和质量。',
        max_tokens=4096,
        timeout=60,
    )

    from server.services.memory.utils import parse_memory_json
    result = parse_memory_json(response) or {}

    return {
        'chapter_id': chapter_id,
        'issues': result.get('issues', []),
        'overall_score': result.get('overall_score', 0),
        'summary': result.get('summary', ''),
    }
