# server/tests/test_novel_auto_continue.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter
from server.models.novel.outline import NovelOutlineNode


@pytest.fixture
def project(app):
    p = NovelProject(title='连续续写测试', genre='玄幻', premise='测试连续续写')
    p.settings = {'overall_outline': {'main_arc': '测试主线'}}
    p.words_per_chapter = 100
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def setup_chapters(app, project):
    """Create volume outline and first chapter."""
    vol = NovelOutlineNode(
        project_id=project.id, node_type='volume', title='第一卷',
        summary='开篇', plot_goal='建立世界', order_index=1,
    )
    db.session.add(vol)
    db.session.flush()

    for i in range(1, 4):
        outline = NovelOutlineNode(
            project_id=project.id, parent_id=vol.id, node_type='chapter',
            title=f'第{i}章', summary=f'第{i}章摘要', plot_goal=f'目标{i}',
            order_index=i, target_words=100,
        )
        db.session.add(outline)
        db.session.flush()

        ch = NovelChapter(
            project_id=project.id, outline_node_id=outline.id,
            title=f'第{i}章', content_markdown='', order_index=i, word_count=0,
        )
        db.session.add(ch)

    db.session.commit()
    return project


def test_auto_continue_generates_chapters(app, setup_chapters, monkeypatch):
    """Auto-continue should generate multiple chapters."""
    from server.services.novel import auto_continue
    from server.services.memory import workflow
    from server.services.novel import summarizer

    def fake_workflow(**kwargs):
        ch = NovelChapter.query.get(kwargs['chapter_id'])
        ch.content_markdown = f'第{ch.order_index}章内容。' * 10
        ch.word_count = len(ch.content_markdown)
        db.session.commit()
        return {'version_id': 1, 'needs_human_review': False}

    def fake_summary(**kwargs):
        pass

    monkeypatch.setattr(workflow, 'run_chapter_workflow', fake_workflow)
    monkeypatch.setattr(summarizer, 'generate_summary', fake_summary)

    result = auto_continue.run_auto_continue(
        project_id=setup_chapters.id,
        params={'count': 2, 'version_type': 'steady'},
    )

    assert result['completed'] == 2
    assert len(result['chapters']) == 2
    assert all(r['status'] == 'confirmed' for r in result['chapters'])


def test_auto_continue_pauses_on_review(app, setup_chapters, monkeypatch):
    """Auto-continue should pause when needs_human_review is True."""
    from server.services.novel import auto_continue
    from server.services.memory import workflow
    from server.services.novel import summarizer

    def fake_workflow(**kwargs):
        ch = NovelChapter.query.get(kwargs['chapter_id'])
        ch.content_markdown = f'第{ch.order_index}章内容。' * 10
        ch.word_count = len(ch.content_markdown)
        db.session.commit()
        return {'version_id': 1, 'needs_human_review': True, 'review_result': {'issues': [{'severity': 'high'}]}}

    def fake_summary(**kwargs):
        pass

    monkeypatch.setattr(workflow, 'run_chapter_workflow', fake_workflow)
    monkeypatch.setattr(summarizer, 'generate_summary', fake_summary)

    result = auto_continue.run_auto_continue(
        project_id=setup_chapters.id,
        params={'count': 3, 'version_type': 'steady'},
    )

    assert result['completed'] == 0
    assert len(result['chapters']) == 1
    assert result['chapters'][0]['status'] == 'paused'


def test_auto_continue_pauses_on_low_confidence(app, setup_chapters, monkeypatch):
    """Auto-continue should pause when graph change has low confidence."""
    from server.services.novel import auto_continue
    from server.services.memory import workflow
    from server.services.novel import summarizer

    def fake_workflow(**kwargs):
        ch = NovelChapter.query.get(kwargs['chapter_id'])
        ch.content_markdown = f'第{ch.order_index}章内容。' * 10
        ch.word_count = len(ch.content_markdown)
        db.session.commit()
        return {
            'version_id': 1,
            'needs_human_review': False,
            'structured_result': {
                'knowledge_updates': {
                    'graph_changes': [{'confidence': 0.3}],
                    'memory_changes': [],
                },
            },
        }

    def fake_summary(**kwargs):
        pass

    monkeypatch.setattr(workflow, 'run_chapter_workflow', fake_workflow)
    monkeypatch.setattr(summarizer, 'generate_summary', fake_summary)

    result = auto_continue.run_auto_continue(
        project_id=setup_chapters.id,
        params={'count': 3, 'version_type': 'steady'},
    )

    assert result['completed'] == 0
    assert len(result['chapters']) == 1
    assert result['chapters'][0]['status'] == 'paused'
    assert result['chapters'][0]['reason'] == 'low_confidence_graph_change'


def test_ensure_next_chapter_finds_empty(app, setup_chapters):
    """_ensure_next_chapter should find existing empty chapters."""
    from server.services.novel.auto_continue import _ensure_next_chapter

    chapter = _ensure_next_chapter(setup_chapters.id)
    assert chapter is not None
    assert chapter.content_markdown == ''


def test_ensure_next_chapter_creates_new(app, project):
    """_ensure_next_chapter should create a new chapter when no empty ones exist."""
    from server.services.novel.auto_continue import _ensure_next_chapter

    # Create a volume and chapter outline
    vol = NovelOutlineNode(
        project_id=project.id, node_type='volume', title='第一卷',
        summary='开篇', order_index=1,
    )
    db.session.add(vol)
    db.session.flush()

    outline = NovelOutlineNode(
        project_id=project.id, parent_id=vol.id, node_type='chapter',
        title='第一章', order_index=1, target_words=100,
    )
    db.session.add(outline)
    db.session.flush()

    chapter = _ensure_next_chapter(project.id)
    assert chapter is not None
    assert chapter.order_index == 1
