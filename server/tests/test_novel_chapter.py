# server/tests/test_novel_chapter.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.graph_change import NovelGraphChange
from server.models.novel.memory import NovelMemoryChange


@pytest.fixture
def project(app):
    p = NovelProject(title='章节测试小说')
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def chapter(app, project):
    c = NovelChapter(
        project_id=project.id,
        title='第一章',
        content_markdown='这是第一章的内容。',
        order_index=1,
        word_count=8,
    )
    db.session.add(c)
    db.session.commit()
    return c


def test_create_chapter(client, project):
    resp = client.post(f'/api/novels/{project.id}/chapters', json={
        'title': '新章节',
        'content_markdown': '章节正文内容',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '新章节'
    assert data['word_count'] == 6


def test_list_chapters(client, project, chapter):
    resp = client.get(f'/api/novels/{project.id}/chapters')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_get_chapter(client, project, chapter):
    resp = client.get(f'/api/novels/{project.id}/chapters/{chapter.id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['title'] == '第一章'
    assert 'versions' in data


def test_update_chapter(client, project, chapter):
    resp = client.put(f'/api/novels/{project.id}/chapters/{chapter.id}', json={
        'content_markdown': '更新后的内容',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['content_markdown'] == '更新后的内容'
    assert data['word_count'] == 6


def test_confirm_chapter(client, project, chapter):
    resp = client.post(f'/api/novels/{project.id}/chapters/{chapter.id}/confirm')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'confirmed'


def test_accept_version(client, project, chapter):
    version = NovelChapterVersion(
        chapter_id=chapter.id,
        version_type='steady',
        content_markdown='版本内容',
    )
    db.session.add(version)
    db.session.commit()

    resp = client.post(f'/api/novels/{project.id}/chapters/{chapter.id}/versions/{version.id}/accept')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['content_markdown'] == '版本内容'


def test_generate_versions_raises_when_all_versions_fail(app, project, chapter, monkeypatch):
    from server.services.novel import version_generator

    def fail_generation(**kwargs):
        raise ValueError('llm key missing')

    monkeypatch.setattr(version_generator, 'generate_single_version', fail_generation)

    with pytest.raises(RuntimeError, match='steady: llm key missing'):
        version_generator.generate_versions(project.id, chapter.id, {
            'version_types': ['steady'],
        })


def test_generate_single_version_creates_knowledge_change_candidates(app, project, chapter, monkeypatch):
    from server.services.novel.chapter_generator import generate_single_version
    from server.services.memory import rag_chain

    def fake_generate_with_memory(**kwargs):
        return {
            'content_markdown': '新人物林照夜登场，携青铜罗盘指出旧案伏笔。',
            'knowledge_updates': {
                'graph_changes': [
                    {
                        'change_type': 'add',
                        'target_type': 'entity',
                        'after': {
                            'entity_type': 'character',
                            'name': '林照夜',
                            'summary': '携带青铜罗盘的新登场人物',
                            'importance': 7,
                        },
                        'confidence': 0.9,
                    },
                    {
                        'change_type': 'add',
                        'target_type': 'entity',
                        'after': {
                            'entity_type': 'item',
                            'name': '青铜罗盘',
                            'summary': '能够指向旧案线索的道具',
                            'importance': 6,
                        },
                    },
                ],
                'memory_changes': [
                    {
                        'change_type': 'add',
                        'after': {
                            'title': '旧案伏笔',
                            'content': '林照夜的青铜罗盘指向十年前旧案，后续需要回收。',
                            'memory_type': 'foreshadowing',
                            'importance': 4,
                            'summary': '青铜罗盘牵出旧案',
                        },
                    }
                ],
            },
        }

    monkeypatch.setattr(rag_chain, 'generate_with_memory', fake_generate_with_memory)

    version = generate_single_version(project.id, chapter.id, version_type='steady')

    assert version.content_markdown == '新人物林照夜登场，携青铜罗盘指出旧案伏笔。'
    graph_changes = NovelGraphChange.query.filter_by(project_id=project.id, chapter_id=chapter.id).all()
    memory_changes = NovelMemoryChange.query.filter_by(project_id=project.id).all()
    assert len(graph_changes) == 2
    assert {c.after['name'] for c in graph_changes} == {'林照夜', '青铜罗盘'}
    assert len(memory_changes) == 1
    assert memory_changes[0].after['memory_type'] == 'foreshadowing'
    assert version.to_dict()['generated_graph_changes'][0]['after']['name'] == '林照夜'


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
    assert version_dict.get('chapter_state') is None


def test_delete_chapter(client, project, chapter):
    resp = client.delete(f'/api/novels/{project.id}/chapters/{chapter.id}')
    assert resp.status_code == 204
