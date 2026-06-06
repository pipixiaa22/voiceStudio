from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.services.novel.narrative_state import load_state, summarize_for_context


def build_context(project_id, chapter_id, user_instruction='', target_words=None):
    """Build context for chapter generation with budget control.

    This is now a thin wrapper around NarrativeState for backward compatibility.
    The helper functions below are still used by consistency_reviewer.py
    and will be migrated to NarrativeState in a subsequent task.
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


def _build_continuation_brief(project, chapter):
    """Build a concise handoff brief for continuation generation."""
    if not chapter:
        return ''

    parts = [
        f'当前任务：续写《{project.title}》第{chapter.order_index}章《{chapter.title}》。',
    ]

    previous_chapter = _get_previous_chapter(project.id, chapter.order_index)
    if previous_chapter:
        previous_line = f'承接上一章：第{previous_chapter.order_index}章《{previous_chapter.title}》'
        if previous_chapter.summary:
            previous_line += f'，摘要：{previous_chapter.summary}'
        elif previous_chapter.content_markdown:
            previous_line += f'，结尾：{_tail_sentence(previous_chapter.content_markdown, 260)}'
        parts.append(previous_line)
    elif chapter.content_markdown:
        parts.append(f'承接当前草稿结尾：{_tail_sentence(chapter.content_markdown, 260)}')

    current_outline = _get_outline_node(chapter.outline_node_id)
    next_outline = _get_next_outline_node(project.id, chapter, current_outline)

    if current_outline:
        goal_bits = []
        if current_outline.plot_goal:
            goal_bits.append(f'剧情目标：{current_outline.plot_goal}')
        if current_outline.conflict_goal:
            goal_bits.append(f'冲突目标：{current_outline.conflict_goal}')
        if current_outline.foreshadowing:
            goal_bits.append('本章可铺设/回应伏笔：' + '；'.join(current_outline.foreshadowing[:5]))
        if goal_bits:
            parts.append('本章推进：' + '；'.join(goal_bits))

    if next_outline:
        next_bits = [f'后续衔接：下一节点《{next_outline.title}》']
        if next_outline.summary:
            next_bits.append(f'方向：{next_outline.summary}')
        parts.append('，'.join(next_bits))

    style_guide = project.style_guide or {}
    continuity_bits = []
    if style_guide.get('pov'):
        continuity_bits.append(f'保持{style_guide["pov"]}')
    if style_guide.get('tone'):
        tone = style_guide['tone']
        if isinstance(tone, list):
            tone = '、'.join(tone)
        continuity_bits.append(f'延续{tone}的文风')
    if continuity_bits:
        parts.append('叙事连续性：' + '；'.join(continuity_bits))

    parts.append(
        '续写边界：紧接前文自然开场；不要重写已发生情节；不要跳过本章关键冲突；'
        '不要擅自完结主线；新增设定必须与人物、事件和长期记忆一致。'
    )

    return _truncate('\n'.join(parts), 1800)


def _build_overall_outline(project):
    """Build project-level outline that controls the whole story direction."""
    settings = project.settings or {}
    overall = settings.get('overall_outline') or {}
    parts = [
        f'作品：{project.title}',
        f'类型：{project.genre}',
    ]
    if project.premise:
        parts.append(f'一句话创意：{project.premise}')
    if settings.get('main_conflict'):
        parts.append(f'主线冲突：{settings["main_conflict"]}')
    if isinstance(overall, dict):
        if overall.get('main_arc'):
            parts.append(f'全书主线：{overall["main_arc"]}')
        if overall.get('ending_direction'):
            parts.append(f'结局方向：{overall["ending_direction"]}')
        if overall.get('theme'):
            parts.append(f'主题表达：{overall["theme"]}')
        if overall.get('stage_goals'):
            goals = overall['stage_goals']
            if isinstance(goals, list):
                goals = '；'.join(str(g) for g in goals)
            parts.append(f'阶段目标：{goals}')
    elif overall:
        parts.append(f'总大纲：{overall}')
    return _truncate('\n'.join(p for p in parts if p), 1800)


def _build_outline_node_text(node, label):
    """Format a volume or chapter outline node for the LLM."""
    if not node:
        return ''
    parts = [f'{label}：{node.title}']
    if node.summary:
        parts.append(f'摘要：{node.summary}')
    if node.plot_goal:
        parts.append(f'剧情目标：{node.plot_goal}')
    if node.conflict_goal:
        parts.append(f'冲突目标：{node.conflict_goal}')
    if node.characters:
        parts.append('关联人物：' + '、'.join(str(c) for c in node.characters[:8]))
    if node.events:
        parts.append('关键事件：' + '；'.join(str(e) for e in node.events[:8]))
    if node.foreshadowing:
        parts.append('伏笔：' + '；'.join(str(f) for f in node.foreshadowing[:8]))
    return _truncate('\n'.join(parts), 1800)


def _get_outline_node(node_id):
    if not node_id:
        return None
    from server.models.novel.outline import NovelOutlineNode
    return NovelOutlineNode.query.get(node_id)


def _get_next_outline_node(project_id, chapter, current_outline):
    from server.models.novel.outline import NovelOutlineNode

    if current_outline:
        next_sibling = NovelOutlineNode.query.filter(
            NovelOutlineNode.project_id == project_id,
            NovelOutlineNode.parent_id == current_outline.parent_id,
            NovelOutlineNode.order_index > current_outline.order_index,
        ).order_by(NovelOutlineNode.order_index).first()
        if next_sibling:
            return next_sibling

    next_chapter = NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        NovelChapter.order_index > chapter.order_index,
        NovelChapter.outline_node_id.isnot(None),
    ).order_by(NovelChapter.order_index).first()
    if next_chapter:
        return _get_outline_node(next_chapter.outline_node_id)

    return None


def _tail_sentence(text, max_chars):
    if not text:
        return ''
    compact = ' '.join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[-max_chars:]


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
