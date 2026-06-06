from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.services.novel.narrative_state import load_state, summarize_for_context


def build_context(project_id, chapter_id, user_instruction='', target_words=None):
    """Build context for chapter generation with budget control.

    Delegates to NarrativeState for data loading and formatting.
    """
    state = load_state(project_id, chapter_id)
    context = summarize_for_context(state)

    # Override target_words if explicitly provided
    if target_words:
        context['target_words'] = target_words

    # Add user instruction if provided
    if user_instruction:
        context['user_instruction'] = user_instruction

    return context


# --- Helpers retained for consistency_reviewer.py ---

def _build_character_context(project_id, chapter):
    entities = NovelEntity.query.filter_by(
        project_id=project_id, entity_type='character'
    ).order_by(NovelEntity.importance.desc()).limit(10).all()

    if not entities:
        return ''

    parts = []
    for e in entities:
        card = f'【{e.name}】'
        if e.aliases:
            card += f' 别名：{"、".join(e.aliases)}'
        if e.summary:
            card += f'\n{e.summary}'
        attrs = e.attributes
        if attrs:
            for k, v in attrs.items():
                if v:
                    card += f'\n{k}：{v}'
        parts.append(card)

    relations = NovelRelation.query.filter_by(
        project_id=project_id, status='active'
    ).limit(20).all()
    if relations:
        rel_parts = []
        for r in relations:
            rel_parts.append(f'{r.source_entity.name} →[{r.relation_type}]→ {r.target_entity.name}' +
                           (f'：{r.description}' if r.description else ''))
        parts.append('\n人物关系：\n' + '\n'.join(rel_parts))

    return _truncate('\n\n'.join(parts), 3000)


def _build_previous_summaries(project_id, current_chapter):
    query = NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        NovelChapter.summary.isnot(None),
        NovelChapter.summary != '',
    )
    if current_chapter:
        query = query.filter(NovelChapter.order_index < current_chapter.order_index)
    chapters = query.order_by(NovelChapter.order_index.desc()).limit(5).all()

    if not chapters:
        return ''

    parts = []
    for ch in reversed(chapters):
        parts.append(f'第{ch.order_index}章 {ch.title}：{ch.summary}')
    return _truncate('\n'.join(parts), 2500)


def _truncate(text, max_chars):
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars] + '...'
