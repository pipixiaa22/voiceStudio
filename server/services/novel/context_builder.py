from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation


def build_context(project_id, chapter_id, user_instruction='', target_words=None):
    """Build context for chapter generation with budget control."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id) if chapter_id else None

    context = {}

    # 1. Outline (priority 1)
    if chapter and chapter.outline_node_id:
        from server.models.novel.outline import NovelOutlineNode
        node = NovelOutlineNode.query.get(chapter.outline_node_id)
        if node:
            outline_text = f'标题：{node.title}'
            if node.summary:
                outline_text += f'\n摘要：{node.summary}'
            if node.plot_goal:
                outline_text += f'\n剧情目标：{node.plot_goal}'
            if node.conflict_goal:
                outline_text += f'\n冲突目标：{node.conflict_goal}'
            context['outline'] = _truncate(outline_text, 1500)

    # 2. Text tail (priority 2) - end of previous chapter or current chapter
    if chapter and chapter.content_markdown:
        tail = chapter.content_markdown[-3000:]
        context['text_tail'] = tail
    else:
        # Get previous chapter's content
        prev_chapter = _get_previous_chapter(project_id, chapter.order_index if chapter else 0)
        if prev_chapter and prev_chapter.content_markdown:
            context['text_tail'] = prev_chapter.content_markdown[-3000:]

    # 3. Previous summaries (priority 3)
    context['previous_summaries'] = _build_previous_summaries(project_id, chapter)

    # 4. Characters (priority 4)
    context['characters'] = _build_character_context(project_id, chapter)

    # 5. Events (priority 5)
    context['events'] = _build_event_context(project_id, chapter)

    # 6. World building (priority 6)
    if project.settings:
        world_text = _format_world_settings(project.settings)
        context['world_building'] = _truncate(world_text, 1500)

    # 7. Foreshadowing
    context['foreshadowing'] = _build_foreshadowing(project_id)

    # 8. User instruction
    if user_instruction:
        context['user_instruction'] = user_instruction

    # 9. Target words
    if target_words:
        context['target_words'] = target_words
    elif chapter and chapter.target_words:
        context['target_words'] = chapter.target_words
    else:
        context['target_words'] = project.words_per_chapter

    return context


def _get_previous_chapter(project_id, current_order_index):
    return NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        NovelChapter.order_index < current_order_index
    ).order_by(NovelChapter.order_index.desc()).first()


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

    # Add relationships
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


def _build_event_context(project_id, chapter):
    query = NovelEvent.query.filter_by(project_id=project_id)
    if chapter:
        query = query.filter(NovelEvent.chapter_id != chapter.id)
    events = query.order_by(NovelEvent.timeline_order.desc()).limit(10).all()

    if not events:
        return ''

    parts = []
    for e in events:
        event_text = f'【{e.title}】({e.event_type})'
        if e.summary:
            event_text += f'\n{e.summary}'
        parts.append(event_text)

    # Add causality
    relations = NovelEventRelation.query.filter_by(project_id=project_id).limit(10).all()
    if relations:
        rel_parts = []
        for r in relations:
            rel_parts.append(f'{r.source_event.title} →[{r.relation_type}]→ {r.target_event.title}')
        parts.append('\n事件因果：\n' + '\n'.join(rel_parts))

    return _truncate('\n\n'.join(parts), 1500)


def _build_foreshadowing(project_id):
    from server.models.novel.outline import NovelOutlineNode
    nodes = NovelOutlineNode.query.filter_by(project_id=project_id).all()
    foreshadows = []
    for node in nodes:
        if node.foreshadowing:
            foreshadows.extend(node.foreshadowing)
    if not foreshadows:
        return ''
    return _truncate('\n'.join(f'- {f}' for f in foreshadows), 1000)


def _format_world_settings(settings):
    parts = []
    for key, value in settings.items():
        if value and key not in ('genre',):
            if isinstance(value, list):
                value = '、'.join(str(v) for v in value)
            elif isinstance(value, dict):
                value = ', '.join(f'{k}={v}' for k, v in value.items())
            parts.append(f'{key}：{value}')
    return '\n'.join(parts)


def _truncate(text, max_chars):
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars] + '...'
