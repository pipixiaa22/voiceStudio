# Novel Continuation Optimization — Phase 1+2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the novel continuation module with a NarrativeState service, structured chapter_state output, blueprint depth levels, and improved prompts.

**Architecture:** Extract a `narrative_state.py` data aggregation layer that `context_builder.py` delegates to. Add `chapter_state` to the structured LLM output. Add depth levels to blueprint generation. Enhance review prompts with outline deviation detection.

**Tech Stack:** Python 3.13, Flask, SQLAlchemy, LangGraph, Vue 3, Ant Design Vue, Pinia

---

## File Map

### New files:
- `server/services/novel/narrative_state.py` — NarrativeState dataclass + load_state + summarize_for_context
- `server/tests/test_novel_narrative_state.py` — Tests for NarrativeState

### Modified files:
- `server/services/novel/context_builder.py` — Delegate to NarrativeState
- `server/services/novel/chapter_generator.py` — Save chapter_state to version
- `server/services/novel/blueprint_generator.py` — Add depth param
- `server/services/novel/prompt_templates.py` — Add build_outline_deviation_check, enhance review prompt
- `server/services/memory/rag_chain.py` — Add chapter_state to structured output
- `server/models/novel/chapter.py` — Version.to_dict() includes chapter_state
- `server/tests/test_novel_chapter.py` — Add chapter_state test
- `server/tests/test_novel_prompt_templates.py` — Add outline deviation test
- `web/src/components/novel/NovelVersionList.vue` — Show chapter_state tags
- `web/src/components/novel/NovelBlueprintWizard.vue` — Add depth selector
- `web/src/components/novel/NovelGenerationPanel.vue` — Show knowledge increment

---

### Task 1: NarrativeState Dataclass and load_state

**Files:**
- Create: `server/services/novel/narrative_state.py`
- Create: `server/tests/test_novel_narrative_state.py`

- [ ] **Step 1: Write the failing test for NarrativeState**

```python
# server/tests/test_novel_narrative_state.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.memory import NovelMemory
from server.services.novel.narrative_state import load_state, NarrativeState


@pytest.fixture
def project(app):
    p = NovelProject(title='测试小说', genre='玄幻', premise='一个少年的冒险')
    p.settings = {
        'overall_outline': {
            'main_arc': '少年成长为主线',
            'ending_direction': '大团圆',
            'theme': '成长与友情',
            'stage_goals': ['建立世界', '中期冲突', '最终决战'],
        },
        'rules': ['灵力修炼体系'],
        'power_system': '灵力',
    }
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def full_project(project):
    """Project with volume, chapter, characters, events, memories."""
    vol = NovelOutlineNode(
        project_id=project.id, node_type='volume', title='第一卷',
        summary='开篇卷', plot_goal='建立世界', conflict_goal='初始冲突',
        order_index=1,
    )
    vol.characters = ['主角']
    vol.events = ['开端事件']
    vol.foreshadowing = ['神秘遗物']
    db.session.add(vol)
    db.session.flush()

    ch = NovelOutlineNode(
        project_id=project.id, parent_id=vol.id, node_type='chapter',
        title='第一章', summary='少年出发', plot_goal='踏上旅途',
        conflict_goal='遭遇盗贼', order_index=1, target_words=3000,
    )
    ch.characters = ['主角', '盗贼']
    ch.events = ['遭遇战']
    ch.foreshadowing = ['神秘遗物发光']
    db.session.add(ch)
    db.session.flush()

    chapter = NovelChapter(
        project_id=project.id, outline_node_id=ch.id,
        title='第一章', content_markdown='少年踏上了旅途...',
        order_index=1, word_count=10, status='confirmed',
    )
    db.session.add(chapter)
    db.session.flush()

    char = NovelEntity(
        project_id=project.id, entity_type='character',
        name='主角', summary='少年冒险者', importance=10,
    )
    db.session.add(char)
    db.session.flush()

    rel = NovelRelation(
        project_id=project.id,
        source_entity_id=char.id, target_entity_id=char.id,
        relation_type='self', label='主角',
    )
    db.session.add(rel)

    event = NovelEvent(
        project_id=project.id, title='开端事件',
        summary='故事开始', event_type='inciting', timeline_order=1,
    )
    event.participants = ['主角']
    db.session.add(event)
    db.session.flush()

    event_rel = NovelEventRelation(
        project_id=project.id,
        source_event_id=event.id, target_event_id=event.id,
        relation_type='causes', label='因果',
    )
    db.session.add(event_rel)

    memory = NovelMemory(
        project_id=project.id, source_type='project',
        memory_type='world_rule', title='灵力体系',
        content='灵力分九阶', importance=5, status='active',
    )
    db.session.add(memory)
    db.session.commit()

    return project


def test_load_state_returns_narrative_state(full_project):
    state = load_state(full_project.id)
    assert isinstance(state, NarrativeState)
    assert state.project.id == full_project.id
    assert state.overall_outline['main_arc'] == '少年成长为主线'
    assert state.current_volume is not None
    assert state.current_volume.title == '第一卷'
    assert state.current_chapter_outline is not None
    assert state.current_chapter_outline.title == '第一章'
    assert len(state.characters) >= 1
    assert state.characters[0].name == '主角'
    assert len(state.relations) >= 1
    assert len(state.events) >= 1
    assert len(state.event_relations) >= 1
    assert len(state.memories) >= 1
    assert state.memories[0].title == '灵力体系'
    assert len(state.open_foreshadowing) >= 1
    assert '神秘遗物' in state.open_foreshadowing[0] or '神秘遗物发光' in state.open_foreshadowing[0]
    assert len(state.recent_chapters) >= 1
    assert state.world_settings.get('rules') == ['灵力修炼体系']


def test_load_state_without_chapter(project):
    state = load_state(project.id)
    assert isinstance(state, NarrativeState)
    assert state.current_volume is None
    assert state.current_chapter_outline is None
    assert state.recent_chapters == []


def test_load_state_empty_project(app):
    p = NovelProject(title='空项目')
    db.session.add(p)
    db.session.commit()
    state = load_state(p.id)
    assert isinstance(state, NarrativeState)
    assert state.characters == []
    assert state.events == []
    assert state.memories == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_narrative_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.services.novel.narrative_state'`

- [ ] **Step 3: Implement NarrativeState and load_state**

```python
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
    if chapter_id:
        from server.models.novel.chapter import NovelChapter as NC
        chapter = NC.query.get(chapter_id)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_narrative_state.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/novel/narrative_state.py server/tests/test_novel_narrative_state.py
git commit -m "feat: add NarrativeState dataclass and load_state service"
```

---

### Task 2: summarize_for_context

**Files:**
- Modify: `server/services/novel/narrative_state.py`
- Modify: `server/tests/test_novel_narrative_state.py`

- [ ] **Step 1: Write the failing test for summarize_for_context**

Append to `server/tests/test_novel_narrative_state.py`:

```python
from server.services.novel.narrative_state import summarize_for_context


def test_summarize_for_context_returns_dict(full_project):
    state = load_state(full_project.id)
    context = summarize_for_context(state)
    assert isinstance(context, dict)
    assert 'overall_outline' in context
    assert 'volume_outline' in context
    assert 'outline' in context
    assert 'characters' in context
    assert 'events' in context
    assert 'foreshadowing' in context
    assert 'world_building' in context
    assert 'target_words' in context


def test_summarize_for_context_overall_outline(full_project):
    state = load_state(full_project.id)
    context = summarize_for_context(state)
    assert '少年成长为主线' in context['overall_outline']
    assert '大团圆' in context['overall_outline']


def test_summarize_for_context_volume_outline(full_project):
    state = load_state(full_project.id)
    context = summarize_for_context(state)
    assert '第一卷' in context['volume_outline']
    assert '建立世界' in context['volume_outline']


def test_summarize_for_context_chapter_outline(full_project):
    state = load_state(full_project.id)
    context = summarize_for_context(state)
    assert '第一章' in context['outline']
    assert '踏上旅途' in context['outline']


def test_summarize_for_context_budget_truncation(full_project):
    state = load_state(full_project.id)
    context = summarize_for_context(state, max_budget=200)
    total = sum(len(str(v)) for v in context.values())
    assert total <= 2000  # generous bound for truncation


def test_summarize_for_context_backward_compatible(full_project):
    """Output keys match what context_builder.build_context currently returns."""
    from server.services.novel.context_builder import build_context
    state = load_state(full_project.id)
    new_context = summarize_for_context(state)
    old_context = build_context(full_project.id)
    # Both should have the same top-level keys
    expected_keys = {'overall_outline', 'volume_outline', 'outline', 'characters',
                     'events', 'foreshadowing', 'world_building', 'target_words'}
    assert expected_keys <= set(new_context.keys())
    assert expected_keys <= set(old_context.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_narrative_state.py -v -k summarize`
Expected: FAIL with `ImportError: cannot import name 'summarize_for_context'`

- [ ] **Step 3: Implement summarize_for_context**

Append to `server/services/novel/narrative_state.py`:

```python
def summarize_for_context(state, max_budget=12000):
    """Produce a context dict compatible with context_builder.build_context() format."""
    context = {}
    used = 0

    # 1. Overall outline
    text = _format_overall_outline(state)
    context['overall_outline'] = _truncate(text, 1800)
    used += len(context['overall_outline'])

    # 2. Volume outline
    text = _format_outline_node(state.current_volume, '卷大纲')
    context['volume_outline'] = _truncate(text, 1800)
    used += len(context['volume_outline'])

    # 3. Chapter outline
    text = _format_outline_node(state.current_chapter_outline, '章大纲')
    context['outline'] = _truncate(text, 1800)
    used += len(context['outline'])

    # 4. Continuation brief
    context['continuation_brief'] = _build_continuation_brief(state)
    used += len(context['continuation_brief'])

    # 5. Text tail
    context['text_tail'] = _build_text_tail(state)
    used += len(context.get('text_tail', ''))

    # 6. Previous summaries
    context['previous_summaries'] = _build_previous_summaries(state)
    used += len(context.get('previous_summaries', ''))

    # 7. Characters
    remaining = max_budget - used
    char_budget = min(3000, max(1000, remaining // 3))
    context['characters'] = _format_characters(state, char_budget)
    used += len(context['characters'])

    # 8. Events
    remaining = max_budget - used
    event_budget = min(1500, max(500, remaining // 4))
    context['events'] = _format_events(state, event_budget)
    used += len(context['events'])

    # 9. World building
    context['world_building'] = _format_world_settings(state.world_settings)
    context['world_building'] = _truncate(context['world_building'], 1500)

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
        from server.models.novel.chapter import NovelChapter
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
        if ch.outline_node_id == (state.current_chapter_outline.id if state.current_chapter_outline else None):
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


# Import at module level for use in _build_continuation_brief
from server.models.novel.outline import NovelOutlineNode
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_narrative_state.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/novel/narrative_state.py server/tests/test_novel_narrative_state.py
git commit -m "feat: add summarize_for_context to NarrativeState"
```

---

### Task 3: Refactor context_builder to delegate to NarrativeState

**Files:**
- Modify: `server/services/novel/context_builder.py`

- [ ] **Step 1: Run existing context_builder tests to establish baseline**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/ -v -k "context" 2>/dev/null || echo "No context tests found"`
Expected: Tests pass or no tests found

- [ ] **Step 2: Refactor build_context to delegate to NarrativeState**

Replace the `build_context` function in `server/services/novel/context_builder.py`. Keep all the existing helper functions (`_build_continuation_brief`, `_build_previous_summaries`, `_build_character_context`, etc.) because `consistency_reviewer.py` imports them. They will be migrated in Task 6.

Replace only the `build_context` function:

```python
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


# --- Helper functions below are kept for consistency_reviewer.py ---
# They will be migrated to NarrativeState in Task 6.
# All other code below this line is UNCHANGED from the original.
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_chapter.py server/tests/test_novel_prompt_templates.py -v`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add server/services/novel/context_builder.py
git commit -m "refactor: delegate context_builder to NarrativeState service"
```

---

### Task 4: chapter_state in structured output

**Files:**
- Modify: `server/services/memory/rag_chain.py`
- Modify: `server/services/novel/chapter_generator.py`
- Modify: `server/models/novel/chapter.py`

- [ ] **Step 1: Write the failing test for chapter_state parsing**

Append to `server/tests/test_novel_chapter.py`:

```python
def test_generate_single_version_saves_chapter_state(app, project, chapter, monkeypatch):
    from server.services.novel.chapter_generator import generate_single_version
    from server.services.memory import rag_chain

    def fake_generate_with_memory(**kwargs):
        return {
            'content_markdown': '少年踏上了旅途，打败了盗贼。',
            'knowledge_updates': {
                'graph_changes': [],
                'memory_changes': [],
            },
            'chapter_state': {
                'completed_plot_goals': ['踏上旅途'],
                'open_threads': ['神秘遗物的秘密'],
                'new_questions': ['遗物的来源是什么'],
                'next_chapter_hooks': ['前方出现神秘女子'],
            },
        }

    monkeypatch.setattr(rag_chain, 'generate_with_memory', fake_generate_with_memory)

    version = generate_single_version(project.id, chapter.id, version_type='steady')

    assert version.content_markdown == '少年踏上了旅途，打败了盗贼。'
    # chapter_state should be in the version dict
    version_dict = version.to_dict()
    assert 'chapter_state' in version_dict
    assert version_dict['chapter_state']['completed_plot_goals'] == ['踏上旅途']
    assert version_dict['chapter_state']['next_chapter_hooks'] == ['前方出现神秘女子']


def test_generate_single_version_backward_compat_no_chapter_state(app, project, chapter, monkeypatch):
    """Versions without chapter_state should still work."""
    from server.services.novel.chapter_generator import generate_single_version
    from server.services.memory import rag_chain

    def fake_generate_with_memory(**kwargs):
        return {
            'content_markdown': '正文内容',
            'knowledge_updates': {'graph_changes': [], 'memory_changes': []},
        }

    monkeypatch.setattr(rag_chain, 'generate_with_memory', fake_generate_with_memory)

    version = generate_single_version(project.id, chapter.id, version_type='steady')
    version_dict = version.to_dict()
    # chapter_state should be absent or None for old-format outputs
    assert version_dict.get('chapter_state') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_chapter.py -v -k chapter_state`
Expected: FAIL with `KeyError: 'chapter_state'` or assertion error

- [ ] **Step 3: Update rag_chain.py structured output instruction**

In `server/services/memory/rag_chain.py`, replace the `_build_structured_output_instruction` function:

```python
def _build_structured_output_instruction(target_words):
    return f"""【输出要求】
- 必须只输出一个 JSON 对象，不要使用 Markdown 代码块，不要解释。
- 正文必须放在 content_markdown 字段，目标字数：{target_words}字。
- 正文要紧接前文自然续写，不用摘要式开场。
- 每一场都要推进人物目标、冲突或信息揭示，避免原地水文。
- 新增设定、能力、关系和时间线必须服从长期记忆与已有人物事件。
- 如果本次续写引入新人物、道具、地点、势力、事件、伏笔或世界规则，必须同时写入 knowledge_updates，不能只写进正文。
- 必须同时输出 chapter_state，记录本章的剧情推进状态。

JSON 结构：
{{
  "content_markdown": "小说正文 Markdown",
  "knowledge_updates": {{
    "graph_changes": [
      {{
        "change_type": "add|modify",
        "target_type": "entity|event",
        "after": {{
          "entity_type": "character|item|location|faction",
          "name": "实体名称",
          "summary": "简介",
          "importance": 1-10,
          "attributes": {{}}
        }},
        "confidence": 0.0-1.0,
        "description": "为什么需要写入图谱"
      }}
    ],
    "memory_changes": [
      {{
        "change_type": "add|modify",
        "after": {{
          "title": "记忆标题",
          "content": "需要长期记住的事实、伏笔、道具能力、人物目标或世界规则",
          "memory_type": "character|world_rule|event|foreshadowing|relationship|style|summary",
          "importance": 1-5,
          "summary": "一句话摘要"
        }},
        "description": "为什么需要写入长期记忆"
      }}
    ]
  }},
  "chapter_state": {{
    "completed_plot_goals": ["本章完成的剧情目标，对照章大纲的 plot_goal 和 conflict_goal"],
    "open_threads": ["本章未解决的悬念或未完成的目标"],
    "new_questions": ["本章新提出的问题或谜团"],
    "next_chapter_hooks": ["为下一章铺设的钩子或悬念"]
  }}
}}"""
```

- [ ] **Step 4: Update _parse_structured_generation to extract chapter_state**

In `server/services/memory/rag_chain.py`, replace the `_parse_structured_generation` function:

```python
def _parse_structured_generation(text):
    data = parse_memory_json(text)
    if not isinstance(data, dict):
        raise ValueError('无法解析小说续写结构化 JSON 输出')

    content = data.get('content_markdown') or data.get('content') or ''
    if not isinstance(content, str) or not content.strip():
        raise ValueError('小说续写结构化输出缺少 content_markdown')

    updates = data.get('knowledge_updates') or {}
    if not isinstance(updates, dict):
        updates = {}

    graph_changes = updates.get('graph_changes') or []
    memory_changes = updates.get('memory_changes') or []
    if not isinstance(graph_changes, list):
        graph_changes = []
    if not isinstance(memory_changes, list):
        memory_changes = []

    # chapter_state is optional for backward compatibility
    chapter_state = data.get('chapter_state')
    if chapter_state and not isinstance(chapter_state, dict):
        chapter_state = None

    result = {
        'content_markdown': content.strip(),
        'knowledge_updates': {
            'graph_changes': graph_changes,
            'memory_changes': memory_changes,
        },
    }
    if chapter_state:
        result['chapter_state'] = chapter_state

    return result
```

- [ ] **Step 5: Update chapter_generator to save chapter_state**

In `server/services/novel/chapter_generator.py`, replace the `generate_single_version` function body (after the `content = structured_result['content_markdown']` line):

Find this block in `generate_single_version`:
```python
    content = structured_result['content_markdown']
    knowledge_updates = structured_result.get('knowledge_updates') or {}
```

Replace with:
```python
    content = structured_result['content_markdown']
    knowledge_updates = structured_result.get('knowledge_updates') or {}
    chapter_state = structured_result.get('chapter_state')
```

Find this block:
```python
    version.prompt = {'system': system_prompt, 'user': user_instruction}
    version.context_snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}
```

Replace with:
```python
    version.prompt = {'system': system_prompt, 'user': user_instruction}
    snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}
    if chapter_state:
        snapshot['chapter_state'] = chapter_state
    version.context_snapshot = snapshot
```

- [ ] **Step 6: Update NovelChapterVersion.to_dict() to include chapter_state**

In `server/models/novel/chapter.py`, find the `to_dict` method of `NovelChapterVersion`:

```python
    def to_dict(self):
        data = {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'version_type': self.version_type,
            'title': self.title,
            'content_markdown': self.content_markdown,
            'model': self.model,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

Replace with:
```python
    def to_dict(self):
        data = {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'version_type': self.version_type,
            'title': self.title,
            'content_markdown': self.content_markdown,
            'model': self.model,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        snapshot = self.context_snapshot
        if snapshot and isinstance(snapshot, dict) and snapshot.get('chapter_state'):
            data['chapter_state'] = snapshot['chapter_state']
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_chapter.py -v`
Expected: All tests PASS (including new chapter_state tests)

- [ ] **Step 8: Commit**

```bash
git add server/services/memory/rag_chain.py server/services/novel/chapter_generator.py server/models/novel/chapter.py server/tests/test_novel_chapter.py
git commit -m "feat: add chapter_state to structured generation output"
```

---

### Task 5: Blueprint depth levels

**Files:**
- Modify: `server/services/novel/blueprint_generator.py`
- Modify: `server/tests/test_novel_chapter.py` (add blueprint depth test)

- [ ] **Step 1: Write the failing test for blueprint depth**

Append to `server/tests/test_novel_chapter.py`:

```python
def test_resolve_outline_chapter_count_by_depth(app):
    from server.services.novel.blueprint_generator import _resolve_outline_chapter_count
    from server.models.novel.project import NovelProject

    p = NovelProject(title='test', target_chapters=100)
    db.session.add(p)
    db.session.commit()

    # Quick: fewer chapters
    quick = _resolve_outline_chapter_count(p, {'depth': 'quick'})
    assert quick <= 8

    # Standard: default behavior
    standard = _resolve_outline_chapter_count(p, {'depth': 'standard'})
    assert 3 <= standard <= 12

    # Deep: more chapters
    deep = _resolve_outline_chapter_count(p, {'depth': 'deep'})
    assert deep >= standard
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_chapter.py -v -k depth`
Expected: FAIL (quick returns same as standard because depth param is not yet handled)

- [ ] **Step 3: Update _resolve_outline_chapter_count**

In `server/services/novel/blueprint_generator.py`, replace `_resolve_outline_chapter_count`:

```python
def _resolve_outline_chapter_count(project, params):
    depth = params.get('depth', 'standard')
    requested = params.get('outline_chapters') or params.get('chapter_count')

    if requested:
        try:
            requested = int(requested)
        except (TypeError, ValueError):
            requested = None

    if requested:
        return max(3, min(requested, project.target_chapters or requested, 20))

    # Default by depth
    if depth == 'quick':
        return max(3, min(8, project.target_chapters or 8))
    elif depth == 'deep':
        return max(6, min(15, project.target_chapters or 15))
    else:  # standard
        return max(3, min(12, project.target_chapters or 12))
```

- [ ] **Step 4: Update generate_blueprint to use depth in prompt**

In `server/services/novel/blueprint_generator.py`, find the `generate_blueprint` function. After `outline_chapters = _resolve_outline_chapter_count(project, params)`, add:

```python
    depth = params.get('depth', 'standard')
```

Then find the line:
```python
    每章字数：{project.words_per_chapter}
    卷数：{project.volume_count}
```

After it, add:
```python
    生成深度：{depth}
```

Then find the prompt requirements section that starts with `要求：`. Replace it with a depth-aware version:

```python
    depth_instructions = {
        'quick': '''要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
- 主要角色 2-4 个，道具/地点/势力 2-4 个。
- 只生成 1 卷。
- 关键事件 2-3 个，伏笔 1-2 个。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。''',
        'standard': f'''要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
- 主要角色 4-8 个，道具/地点/势力 4-10 个。
- 必须有关键事件、伏笔、道具或地点，不能只输出章节标题。
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。
- 如果整体故事超过 {outline_chapters} 章，也要给出全书主线骨架、关键事件和伏笔清单；章节只展开前 {outline_chapters} 章。''',
        'deep': f'''要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
- 主要角色 6-10 个，道具/地点/势力 6-12 个。
- 必须有关键事件 5-8 个、伏笔 3-5 个、道具/地点/势力详细描述。
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 尽可能覆盖全书卷纲，每卷都要有详细的 plot_goal、conflict_goal、characters、events、foreshadowing。
- memory_seeds 必须包含详细的世界规则、人物背景、道具能力、伏笔线索。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。''',
    }
```

Then replace the existing `要求：...` block in the system_prompt with:
```python
    system_prompt += '\n' + depth_instructions.get(depth, depth_instructions['standard'])
```

Wait, actually the prompt is built as a single f-string. Let me re-read the file structure more carefully.

The system_prompt is a single long f-string. The cleanest approach is to replace the entire `要求：` section at the end of the f-string. Let me find the exact text.

Looking at the blueprint_generator.py, the system_prompt ends with:
```
要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
- 主要角色 4-8 个，道具/地点/势力 4-10 个。
- 必须有关键事件、伏笔、道具或地点，不能只输出章节标题。
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。
- 如果整体故事超过 {outline_chapters} 章，也要给出全书主线骨架、关键事件和伏笔清单；章节只展开前 {outline_chapters} 章。"""
```

So the approach is:
1. Add `depth = params.get('depth', 'standard')` after `outline_chapters = ...`
2. Replace the `要求：..."""` section at the end of the f-string with a depth-aware version

Let me write the exact edit. The old_string is the end of the system_prompt f-string starting from `要求：` to the closing `"""`.

Old string:
```
要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
- 主要角色 4-8 个，道具/地点/势力 4-10 个。
- 必须有关键事件、伏笔、道具或地点，不能只输出章节标题。
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。
- 如果整体故事超过 {outline_chapters} 章，也要给出全书主线骨架、关键事件和伏笔清单；章节只展开前 {outline_chapters} 章。"""
```

But this is inside an f-string, so I need to be careful with the replacement. Actually, looking at the code, the system_prompt is built as a regular f-string. Let me just provide the exact replacement.

Actually, I realize the approach in the plan step is slightly wrong. The depth_instructions dict I wrote uses f-strings inside, but those would need to be regular strings since they're already inside an f-string. Let me simplify the approach.

The cleanest way is to:
1. Add `depth = params.get('depth', 'standard')` after the outline_chapters line
2. Build the depth requirements as a separate variable before the system_prompt
3. Insert it into the system_prompt

Let me restructure the plan step.


The system_prompt in `generate_blueprint` is one long f-string. The cleanest approach is to build the depth-specific requirements separately and insert them. Here's the exact change:

Find this in `generate_blueprint`:
```python
    outline_chapters = _resolve_outline_chapter_count(project, params)
```

Replace with:
```python
    outline_chapters = _resolve_outline_chapter_count(project, params)
    depth = params.get('depth', 'standard')
```

Then find the end of the system_prompt f-string (the `要求：` section through the closing `"""`). Replace it with:

```python
    depth_requirements = {
        'quick': f'- 主要角色 2-4 个，道具/地点/势力 2-4 个。\n- 只生成 1 卷。\n- 关键事件 2-3 个，伏笔 1-2 个。',
        'standard': f'- 主要角色 4-8 个，道具/地点/势力 4-10 个。\n- 必须有关键事件、伏笔、道具或地点，不能只输出章节标题。\n- 如果整体故事超过 {outline_chapters} 章，也要给出全书主线骨架、关键事件和伏笔清单；章节只展开前 {outline_chapters} 章。',
        'deep': f'- 主要角色 6-10 个，道具/地点/势力 6-12 个。\n- 必须有关键事件 5-8 个、伏笔 3-5 个、道具/地点/势力详细描述。\n- 尽可能覆盖全书卷纲，每卷都要有详细的 plot_goal、conflict_goal、characters、events、foreshadowing。\n- memory_seeds 必须包含详细的世界规则、人物背景、道具能力、伏笔线索。',
    }
    depth_req = depth_requirements.get(depth, depth_requirements['standard'])

    system_prompt = f"""...（前面不变）...
要求：
- 严格输出 JSON，不要使用 Markdown 代码块。
{depth_req}
- 必须明确三层大纲：overall_outline 决定全书走向；volume summary/plot_goal/conflict_goal 决定本卷方向；chapter summary/plot_goal/conflict_goal 刻画具体情节。
- 全部 volumes 下的 chapters 总数必须等于 {outline_chapters}。"""
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_chapter.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/services/novel/blueprint_generator.py server/tests/test_novel_chapter.py
git commit -m "feat: add blueprint depth levels (quick/standard/deep)"
```

---

### Task 6: Prompt strategy — outline deviation check in review

**Files:**
- Modify: `server/services/novel/prompt_templates.py`
- Modify: `server/services/novel/consistency_reviewer.py`
- Modify: `server/tests/test_novel_prompt_templates.py`

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_novel_prompt_templates.py`:

```python
def test_build_review_prompt_includes_outline_context():
    from server.services.novel.prompt_templates import build_review_prompt

    context = {
        'characters': '人物设定',
        'world_rules': '世界观规则',
        'previous_summaries': '前文摘要',
        'overall_outline': '全书主线：少年成长',
        'volume_outline': '卷大纲：第一卷开篇',
        'outline': '章大纲：第一章踏上旅途',
    }
    prompt = build_review_prompt('章节正文', context)
    assert '少年成长' in prompt
    assert '第一卷开篇' in prompt
    assert '踏上旅途' in prompt
    assert '偏离' in prompt or '偏离主线' in prompt or '主线偏离' in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_prompt_templates.py -v -k outline_deviation`
Expected: FAIL (outline context not in prompt)

- [ ] **Step 3: Update build_review_prompt**

In `server/services/novel/prompt_templates.py`, find `build_review_prompt`:

```python
def build_review_prompt(chapter_content, context):
    parts = ['请对以下章节进行一致性审稿。']

    if context.get('characters'):
        parts.append(f'【已有人物设定】\n{context["characters"]}')
    if context.get('world_rules'):
        parts.append(f'【世界观规则】\n{context["world_rules"]}')
    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')
```

Replace with:

```python
def build_review_prompt(chapter_content, context):
    parts = ['请对以下章节进行一致性审稿。']

    if context.get('overall_outline'):
        parts.append(f'【总大纲：全书走向】\n{context["overall_outline"]}')
    if context.get('volume_outline'):
        parts.append(f'【卷大纲：阶段方向】\n{context["volume_outline"]}')
    if context.get('outline'):
        parts.append(f'【章大纲：本章情节】\n{context["outline"]}')
    if context.get('characters'):
        parts.append(f'【已有人物设定】\n{context["characters"]}')
    if context.get('world_rules'):
        parts.append(f'【世界观规则】\n{context["world_rules"]}')
    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')
```

Then find the review dimensions list:
```python
    parts.append(f"""请检查以下方面：
1. 人设是否崩坏（性格、能力、行为是否与设定一致）
2. 世界观规则是否冲突
3. 时间线是否合理
4. 人物位置是否合理
5. 事件因果是否断裂
6. 伏笔是否遗忘
7. 本章是否推进了冲突
8. 是否与前文重复
9. 是否水文（无意义的填充内容）
```

Replace with:
```python
    parts.append(f"""请检查以下方面：
1. 人设是否崩坏（性格、能力、行为是否与设定一致）
2. 世界观规则是否冲突
3. 时间线是否合理
4. 人物位置是否合理
5. 事件因果是否断裂
6. 伏笔是否遗忘
7. 本章是否推进了冲突
8. 是否与前文重复
9. 是否水文（无意义的填充内容）
10. 是否偏离总大纲方向（提前完结主线、逆转结局方向、违反主题）
11. 是否偏离卷大纲目标（跳过本卷冲突、提前进入下一卷阶段）
12. 是否偏离章大纲目标（未完成本章剧情目标、未推进本章冲突）
```

- [ ] **Step 4: Update consistency_reviewer to pass outline context**

In `server/services/novel/consistency_reviewer.py`, find the `review_chapter` function:

```python
    context = {
        'characters': _build_character_context(project_id, chapter),
        'previous_summaries': _build_previous_summaries(project_id, chapter),
        'world_rules': _format_world_rules(project.settings),
    }
```

Replace with:
```python
    from server.services.novel.narrative_state import load_state, summarize_for_context
    state = load_state(project_id, chapter_id)
    state_context = summarize_for_context(state)

    context = {
        'characters': _build_character_context(project_id, chapter),
        'previous_summaries': _build_previous_summaries(project_id, chapter),
        'world_rules': _format_world_rules(project.settings),
        'overall_outline': state_context.get('overall_outline', ''),
        'volume_outline': state_context.get('volume_outline', ''),
        'outline': state_context.get('outline', ''),
    }
```

Also update `review_content` the same way:

```python
def review_content(project_id, chapter_id, content, params=None):
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    from server.services.novel.narrative_state import load_state, summarize_for_context
    state = load_state(project_id, chapter_id)
    state_context = summarize_for_context(state)

    context = {
        'characters': _build_character_context(project_id, chapter),
        'previous_summaries': _build_previous_summaries(project_id, chapter),
        'world_rules': _format_world_rules(project.settings),
        'overall_outline': state_context.get('overall_outline', ''),
        'volume_outline': state_context.get('volume_outline', ''),
        'outline': state_context.get('outline', ''),
    }

    return _do_review(project_id, chapter_id, content, context, params=params)
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/test_novel_prompt_templates.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/services/novel/prompt_templates.py server/services/novel/consistency_reviewer.py server/tests/test_novel_prompt_templates.py
git commit -m "feat: add outline deviation detection to review prompt"
```

---

### Task 7: Frontend — NovelVersionList chapter_state display

**Files:**
- Modify: `web/src/components/novel/NovelVersionList.vue`

- [ ] **Step 1: Add chapter_state tags to version cards**

In `web/src/components/novel/NovelVersionList.vue`, find the version-meta div:

```html
        <div class="version-meta">
          {{ v.content_markdown?.length || 0 }} 字 · {{ formatDate(v.created_at) }}
        </div>
```

After it, add:

```html
        <div v-if="v.chapter_state" class="version-state">
          <div v-if="v.chapter_state.completed_plot_goals?.length" class="state-section">
            <span class="state-label">已完成目标</span>
            <a-tag v-for="g in v.chapter_state.completed_plot_goals" :key="g" color="green" size="small">{{ g }}</a-tag>
          </div>
          <div v-if="v.chapter_state.open_threads?.length" class="state-section">
            <span class="state-label">未解决悬念</span>
            <a-tag v-for="t in v.chapter_state.open_threads" :key="t" color="orange" size="small">{{ t }}</a-tag>
          </div>
          <div v-if="v.chapter_state.next_chapter_hooks?.length" class="state-section">
            <span class="state-label">下章钩子</span>
            <a-tag v-for="h in v.chapter_state.next_chapter_hooks" :key="h" color="blue" size="small">{{ h }}</a-tag>
          </div>
        </div>
```

Then add CSS:

```css
.version-state { margin-bottom: 8px; }
.state-section { margin-bottom: 4px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.state-label { font-size: 11px; color: var(--text-muted); margin-right: 4px; }
```

- [ ] **Step 2: Verify in dev server**

Run: `cd /Users/ckrey/video/script/web && pnpm run dev`
Then open browser and navigate to a novel workspace with existing versions. Verify chapter_state tags appear when available.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelVersionList.vue
git commit -m "feat: show chapter_state tags in version list"
```

---

### Task 8: Frontend — Blueprint depth selector

**Files:**
- Modify: `web/src/components/novel/NovelBlueprintWizard.vue`

- [ ] **Step 1: Add depth selector**

In `web/src/components/novel/NovelBlueprintWizard.vue`, find the form items:

```html
    <a-form layout="vertical">
      <a-form-item label="一句话创意" required>
        <a-textarea v-model:value="premise" placeholder="描述你的小说核心创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
      </a-form-item>
      <a-form-item label="章节节点数">
        <a-input-number v-model:value="outlineChapters" :min="3" :max="12" :step="1" style="width: 100%" />
      </a-form-item>
    </a-form>
```

Replace with:

```html
    <a-form layout="vertical">
      <a-form-item label="一句话创意" required>
        <a-textarea v-model:value="premise" placeholder="描述你的小说核心创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
      </a-form-item>
      <a-form-item label="生成深度">
        <a-radio-group v-model:value="depth" button-style="solid">
          <a-radio-button value="quick">快速蓝图</a-radio-button>
          <a-radio-button value="standard">标准蓝图</a-radio-button>
          <a-radio-button value="deep">深度蓝图</a-radio-button>
        </a-radio-group>
        <div class="depth-hint">{{ depthHint }}</div>
      </a-form-item>
      <a-form-item label="章节节点数">
        <a-input-number v-model:value="outlineChapters" :min="3" :max="20" :step="1" style="width: 100%" />
      </a-form-item>
    </a-form>
```

In the script section, add the depth ref and computed:

```javascript
const depth = ref('standard')
const depthHint = computed(() => {
  if (depth.value === 'quick') return '快速探索创意：少量角色和事件，1卷骨架'
  if (depth.value === 'deep') return '完整世界构建：详细角色、事件、伏笔、道具和记忆种子'
  return '平衡模式：多卷骨架 + 当前卷详细章纲'
})
```

Update handleGenerate to pass depth:

```javascript
    await store.startGeneration('blueprint', {
      premise: premise.value,
      outline_chapters: outlineChapters.value,
      depth: depth.value,
    })
```

Add CSS:

```css
.depth-hint { margin-top: 4px; font-size: 12px; color: var(--text-muted); }
```

- [ ] **Step 2: Verify in dev server**

Run: `cd /Users/ckrey/video/script/web && pnpm run dev`
Then open browser and test the blueprint wizard with different depth levels.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelBlueprintWizard.vue
git commit -m "feat: add blueprint depth selector (quick/standard/deep)"
```

---

### Task 9: Frontend — Knowledge increment display

**Files:**
- Modify: `web/src/components/novel/NovelGenerationPanel.vue`

- [ ] **Step 1: Add knowledge increment summary**

In `web/src/components/novel/NovelGenerationPanel.vue`, find the template section after the success/failed conditions. The generation panel shows a form when not generating. Add a success summary above the form.

Find:
```html
    <template v-else>
      <div class="gen-summary">
```

Replace with:
```html
    <template v-else>
      <div v-if="knowledgeIncrement" class="knowledge-increment">
        <a-alert type="info" show-icon>
          <template #message>
            本次生成引入
            <a-tag v-if="knowledgeIncrement.graphChanges > 0" color="blue" size="small">{{ knowledgeIncrement.graphChanges }} 条图谱变更</a-tag>
            <a-tag v-if="knowledgeIncrement.memoryChanges > 0" color="purple" size="small">{{ knowledgeIncrement.memoryChanges }} 条记忆变更</a-tag>
            <span v-if="!knowledgeIncrement.graphChanges && !knowledgeIncrement.memoryChanges">无知识变更</span>
          </template>
        </a-alert>
      </div>
      <div class="gen-summary">
```

In the script section, add the computed:

```javascript
const knowledgeIncrement = computed(() => {
  const gen = store.generation
  if (!gen || gen.status !== 'completed' || gen.generation_type !== 'chapter_version') return null
  const result = gen.result
  if (!result?.versions) return null
  const graphChanges = result.versions.reduce((sum, v) => sum + (v.generated_graph_changes?.length || 0), 0)
  const memoryChanges = store.memoryChanges?.length || 0
  return { graphChanges, memoryChanges }
})
```

Add CSS:

```css
.knowledge-increment { margin-bottom: 12px; }
```

- [ ] **Step 2: Verify in dev server**

Run: `cd /Users/ckrey/video/script/web && pnpm run dev`
Generate a chapter version and verify the knowledge increment bar appears.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelGenerationPanel.vue
git commit -m "feat: show knowledge increment after generation"
```

---

### Task 10: Run full test suite

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/ckrey/video/script && uv run pytest server/tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend build check**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Final commit if needed**

If any fixes were needed:
```bash
git add -A
git commit -m "fix: address test failures from Phase 1+2 changes"
```
