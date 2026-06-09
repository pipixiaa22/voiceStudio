# server/tests/test_novel_workflow.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.graph_change import NovelGraphChange
from server.models.novel.memory import NovelMemoryChange


@pytest.fixture
def project(app):
    p = NovelProject(title='流水线测试', genre='玄幻', premise='测试流水线')
    p.settings = {'overall_outline': {'main_arc': '测试主线'}}
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def chapter(app, project):
    vol = NovelOutlineNode(
        project_id=project.id, node_type='volume', title='第一卷',
        summary='开篇', plot_goal='建立世界', order_index=1,
    )
    db.session.add(vol)
    db.session.flush()

    outline = NovelOutlineNode(
        project_id=project.id, parent_id=vol.id, node_type='chapter',
        title='第一章', summary='少年出发', plot_goal='踏上旅途',
        conflict_goal='遭遇盗贼', order_index=1, target_words=3000,
    )
    db.session.add(outline)
    db.session.flush()

    ch = NovelChapter(
        project_id=project.id, outline_node_id=outline.id,
        title='第一章', content_markdown='', order_index=1, word_count=0,
    )
    db.session.add(ch)
    db.session.commit()
    return ch


def test_workflow_produces_structured_output(app, project, chapter, monkeypatch):
    """The workflow should produce a version with chapter_state and knowledge changes."""
    from server.services.memory import workflow
    from server.services.memory import rag_chain
    from server.services.novel import consistency_reviewer

    def fake_generate_with_memory(*args, **kwargs):
        return {
            'content_markdown': '少年踏上了旅途，打败了盗贼。新人物林照夜登场。',
            'knowledge_updates': {
                'graph_changes': [
                    {
                        'change_type': 'add',
                        'target_type': 'entity',
                        'after': {'entity_type': 'character', 'name': '林照夜', 'summary': '新角色', 'importance': 7},
                        'confidence': 0.9,
                    }
                ],
                'memory_changes': [
                    {
                        'change_type': 'add',
                        'after': {'title': '旅途开始', 'content': '少年踏上旅途', 'memory_type': 'event', 'importance': 3, 'summary': '旅途开始'},
                    }
                ],
            },
            'chapter_state': {
                'completed_plot_goals': ['踏上旅途'],
                'open_threads': ['林照夜的身份'],
                'new_questions': ['林照夜是谁'],
                'next_chapter_hooks': ['前方出现神秘女子'],
            },
        }

    def fake_review_content(*args, **kwargs):
        return {'chapter_id': chapter.id, 'issues': [], 'overall_score': 90, 'summary': '良好'}

    monkeypatch.setattr(rag_chain, 'generate_with_memory', fake_generate_with_memory)
    monkeypatch.setattr(consistency_reviewer, 'review_content', fake_review_content)

    result = workflow.run_chapter_workflow(
        project_id=project.id,
        chapter_id=chapter.id,
        version_type='steady',
    )

    assert result.get('version_id')
    assert result.get('needs_human_review') is False or result.get('needs_human_review') is None

    version = NovelChapterVersion.query.get(result['version_id'])
    assert version is not None
    assert '少年踏上了旅途' in version.content_markdown

    snapshot = version.context_snapshot
    assert snapshot.get('chapter_state', {}).get('completed_plot_goals') == ['踏上旅途']

    graph_changes = NovelGraphChange.query.filter_by(project_id=project.id, chapter_id=chapter.id).all()
    assert len(graph_changes) >= 1
    assert any(c.after.get('name') == '林照夜' for c in graph_changes)

    memory_changes = NovelMemoryChange.query.filter_by(project_id=project.id).all()
    assert len(memory_changes) >= 1


def test_workflow_pauses_on_high_review_issues(app, project, chapter, monkeypatch):
    """When review finds high issues that survive revision, needs_human_review should be True."""
    from server.services.memory import workflow
    from server.services.memory import rag_chain
    from server.services.novel import consistency_reviewer

    def fake_generate_with_memory(*args, **kwargs):
        return {
            'content_markdown': '正文内容。',
            'knowledge_updates': {'graph_changes': [], 'memory_changes': []},
            'chapter_state': {'completed_plot_goals': [], 'open_threads': [], 'new_questions': [], 'next_chapter_hooks': []},
        }

    def fake_review_content(*args, **kwargs):
        return {
            'chapter_id': chapter.id,
            'issues': [{'severity': 'high', 'category': 'character', 'description': '人设崩坏', 'suggestion': '修复'}],
            'overall_score': 30,
            'summary': '严重问题',
        }

    monkeypatch.setattr(rag_chain, 'generate_with_memory', fake_generate_with_memory)
    monkeypatch.setattr(consistency_reviewer, 'review_content', fake_review_content)

    result = workflow.run_chapter_workflow(
        project_id=project.id,
        chapter_id=chapter.id,
        version_type='steady',
    )

    assert result.get('needs_human_review') is True
    assert result.get('version_id') is not None
