# server/tests/test_novel_narrative_state.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.memory import NovelMemory
from server.services.novel.narrative_state import load_state, NarrativeState, summarize_for_context


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
