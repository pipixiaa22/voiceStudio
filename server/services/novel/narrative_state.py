# server/services/novel/narrative_state.py
from dataclasses import dataclass, field
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.memory import NovelMemory


@dataclass
class NarrativeState:
    project: NovelProject
    overall_outline: dict = field(default_factory=dict)
    current_volume: NovelOutlineNode | None = None
    current_chapter_outline: NovelOutlineNode | None = None
    characters: list = field(default_factory=list)
    relations: list = field(default_factory=list)
    events: list = field(default_factory=list)
    event_relations: list = field(default_factory=list)
    memories: list = field(default_factory=list)
    open_foreshadowing: list = field(default_factory=list)
    recent_chapters: list = field(default_factory=list)
    world_settings: dict = field(default_factory=dict)


def load_state(project_id, chapter_id=None):
    """Load all narrative context from the database."""
    project = NovelProject.query.get_or_404(project_id)
    settings = project.settings or {}

    # Overall outline
    overall_outline = settings.get('overall_outline') or {}

    # Current chapter outline and volume
    current_chapter_outline = None
    current_volume = None
    chapter = None
    if chapter_id:
        chapter = NovelChapter.query.get(chapter_id)
    else:
        # Auto-detect: get the latest confirmed chapter
        chapter = NovelChapter.query.filter(
            NovelChapter.project_id == project_id,
            NovelChapter.status == 'confirmed',
        ).order_by(NovelChapter.order_index.desc()).first()

    if chapter and chapter.outline_node_id:
        current_chapter_outline = NovelOutlineNode.query.get(chapter.outline_node_id)
        if current_chapter_outline and current_chapter_outline.parent_id:
            parent = NovelOutlineNode.query.get(current_chapter_outline.parent_id)
            if parent and parent.node_type == 'volume':
                current_volume = parent

    # Characters (top 10 by importance)
    characters = NovelEntity.query.filter_by(
        project_id=project_id, entity_type='character',
    ).order_by(NovelEntity.importance.desc()).limit(10).all()

    # Relations (active, up to 20)
    relations = NovelRelation.query.filter_by(
        project_id=project_id, status='active',
    ).limit(20).all()

    # Events (up to 10 by timeline)
    events = NovelEvent.query.filter_by(
        project_id=project_id,
    ).order_by(NovelEvent.timeline_order.desc()).limit(10).all()

    # Event relations (up to 10)
    event_relations = NovelEventRelation.query.filter_by(
        project_id=project_id,
    ).limit(10).all()

    # Memories (active, up to 15 by importance)
    memories = NovelMemory.query.filter_by(
        project_id=project_id, status='active',
    ).order_by(NovelMemory.importance.desc()).limit(15).all()

    # Open foreshadowing from outline nodes
    open_foreshadowing = []
    nodes = NovelOutlineNode.query.filter_by(project_id=project_id).all()
    for node in nodes:
        if node.foreshadowing:
            open_foreshadowing.extend(node.foreshadowing)

    # Recent confirmed chapters (up to 5)
    recent_chapters = NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        NovelChapter.status == 'confirmed',
    ).order_by(NovelChapter.order_index.desc()).limit(5).all()

    # World settings (excluding overall_outline which is handled separately)
    world_settings = {k: v for k, v in settings.items() if k != 'overall_outline'}

    return NarrativeState(
        project=project,
        overall_outline=overall_outline,
        current_volume=current_volume,
        current_chapter_outline=current_chapter_outline,
        characters=characters,
        relations=relations,
        events=events,
        event_relations=event_relations,
        memories=memories,
        open_foreshadowing=open_foreshadowing,
        recent_chapters=recent_chapters,
        world_settings=world_settings,
    )


def summarize_for_context(state, max_budget=12000):
    """Produce a context dict compatible with context_builder.build_context() format."""
    context = {}

    # 1. Overall outline
    text = _format_overall_outline(state)
    context['overall_outline'] = _truncate(text, 1800)

    # 2. Volume outline
    text = _format_outline_node(state.current_volume, '卷大纲')
    context['volume_outline'] = _truncate(text, 1800)

    # 3. Chapter outline
    text = _format_outline_node(state.current_chapter_outline, '章大纲')
    context['outline'] = _truncate(text, 1800)

    # 4. Continuation brief
    context['continuation_brief'] = _build_continuation_brief(state)

    # 5. Text tail
    context['text_tail'] = _build_text_tail(state)

    # 6. Previous summaries
    context['previous_summaries'] = _build_previous_summaries(state)

    # 7. Characters
    context['characters'] = _format_characters(state, 3000)

    # 8. Events
    context['events'] = _format_events(state, 1500)

    # 9. World building
    context['world_building'] = _truncate(_format_world_settings(state.world_settings), 1500)

    # 10. Foreshadowing
    context['foreshadowing'] = _format_foreshadowing(state)

    # 11. Target words
    if state.current_chapter_outline and state.current_chapter_outline.target_words:
        context['target_words'] = state.current_chapter_outline.target_words
    else:
        context['target_words'] = state.project.words_per_chapter

    return context


def _format_overall_outline(state):
    parts = [
        f'作品：{state.project.title}',
        f'类型：{state.project.genre}',
    ]
    if state.project.premise:
        parts.append(f'一句话创意：{state.project.premise}')
    if state.world_settings.get('main_conflict'):
        parts.append(f'主线冲突：{state.world_settings["main_conflict"]}')
    overall = state.overall_outline
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
    return '\n'.join(p for p in parts if p)


def _format_outline_node(node, label):
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
    return '\n'.join(parts)


def _build_continuation_brief(state):
    """Build a concise handoff brief for continuation generation."""
    project = state.project
    chapter = None
    if state.current_chapter_outline:
        chapter = NovelChapter.query.filter_by(
            project_id=project.id,
            outline_node_id=state.current_chapter_outline.id,
        ).first()

    if not chapter:
        return ''

    parts = [f'当前任务：续写《{project.title}》第{chapter.order_index}章《{chapter.title}》。']

    # Previous chapter
    prev = None
    if state.recent_chapters:
        for ch in state.recent_chapters:
            if ch.order_index < chapter.order_index:
                prev = ch
                break
    if prev:
        prev_line = f'承接上一章：第{prev.order_index}章《{prev.title}》'
        if prev.summary:
            prev_line += f'，摘要：{prev.summary}'
        parts.append(prev_line)

    # Current outline goals
    outline = state.current_chapter_outline
    if outline:
        goal_bits = []
        if outline.plot_goal:
            goal_bits.append(f'剧情目标：{outline.plot_goal}')
        if outline.conflict_goal:
            goal_bits.append(f'冲突目标：{outline.conflict_goal}')
        if outline.foreshadowing:
            goal_bits.append('本章可铺设/回应伏笔：' + '；'.join(outline.foreshadowing[:5]))
        if goal_bits:
            parts.append('本章推进：' + '；'.join(goal_bits))

    # Next outline node
    if outline and outline.parent_id:
        siblings = NovelOutlineNode.query.filter(
            NovelOutlineNode.parent_id == outline.parent_id,
            NovelOutlineNode.order_index > outline.order_index,
        ).order_by(NovelOutlineNode.order_index).first()
        if siblings:
            next_bits = [f'后续衔接：下一节点《{siblings.title}》']
            if siblings.summary:
                next_bits.append(f'方向：{siblings.summary}')
            parts.append('，'.join(next_bits))

    # Style guide
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


def _build_text_tail(state):
    """Get text tail from current chapter or previous chapter."""
    if not state.recent_chapters:
        return ''
    # Try current chapter first
    for ch in state.recent_chapters:
        if state.current_chapter_outline and ch.outline_node_id == state.current_chapter_outline.id:
            if ch.content_markdown:
                return ch.content_markdown[-3000:]
    # Fall back to most recent chapter
    if state.recent_chapters and state.recent_chapters[0].content_markdown:
        return state.recent_chapters[0].content_markdown[-3000:]
    return ''


def _build_previous_summaries(state):
    parts = []
    for ch in reversed(state.recent_chapters):
        if ch.summary:
            parts.append(f'第{ch.order_index}章 {ch.title}：{ch.summary}')
    return _truncate('\n'.join(parts), 2500)


def _format_characters(state, budget):
    parts = []
    for e in state.characters:
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

    if state.relations:
        rel_parts = []
        for r in state.relations:
            rel_parts.append(
                f'{r.source_entity.name} →[{r.relation_type}]→ {r.target_entity.name}'
                + (f'：{r.description}' if r.description else '')
            )
        parts.append('\n人物关系：\n' + '\n'.join(rel_parts))

    return _truncate('\n\n'.join(parts), budget)


def _format_events(state, budget):
    parts = []
    for e in state.events:
        event_text = f'【{e.title}】({e.event_type})'
        if e.summary:
            event_text += f'\n{e.summary}'
        parts.append(event_text)

    if state.event_relations:
        rel_parts = []
        for r in state.event_relations:
            rel_parts.append(f'{r.source_event.title} →[{r.relation_type}]→ {r.target_event.title}')
        parts.append('\n事件因果：\n' + '\n'.join(rel_parts))

    return _truncate('\n\n'.join(parts), budget)


def _format_world_settings(settings):
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


def _format_foreshadowing(state):
    if not state.open_foreshadowing:
        return ''
    return _truncate('\n'.join(f'- {f}' for f in state.open_foreshadowing), 1000)


def _truncate(text, max_chars):
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars] + '...'
