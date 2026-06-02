# LangChain RAG 长期记忆系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为小说续写模块引入 LangChain RAG 长期记忆，解决长篇创作中的上下文膨胀、设定冲突、人设漂移问题。

**Architecture:** 新增 `server/services/memory/` 作为 RAG 编排层，不替换现有 ModelProvider。NovelMemory 模型存储元数据，Chroma 存储向量索引。多路检索 + 预算控制组装上下文。LangGraph 管理多步骤生成工作流。

**Tech Stack:** Python 3.13, Flask, SQLAlchemy, LangChain, ChromaDB, LangGraph, Vue 3, Pinia, Ant Design Vue

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|---|---|
| `server/models/novel/memory.py` | NovelMemory + NovelMemoryChange 模型 |
| `server/services/memory/__init__.py` | 包初始化 |
| `server/services/memory/document_types.py` | 记忆文档类型定义 |
| `server/services/memory/chunker.py` | 章节/设定文本切片 |
| `server/services/memory/embeddings.py` | Embedding 模型封装 |
| `server/services/memory/vector_store.py` | Chroma 向量库封装 |
| `server/services/memory/retriever.py` | 多路检索 + 排序压缩 |
| `server/services/memory/rag_chain.py` | LangChain 编排：检索 -> prompt -> LLM |
| `server/services/memory/memory_writer.py` | 记忆写入（手动 + AI 抽取） |
| `server/services/memory/conflict_detector.py` | 设定冲突检测 |
| `server/routes/novels/memories.py` | 记忆 CRUD + 检索 + 变更确认 API |
| `server/tests/test_novel_memory.py` | 后端测试 |
| `web/src/components/novel/NovelMemoryPanel.vue` | 记忆管理面板 |
| `web/src/components/novel/NovelMemorySearch.vue` | 检索预览面板 |
| `web/src/components/novel/NovelMemoryChangeReview.vue` | 待确认记忆变更面板 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `pyproject.toml` | 添加 langchain, chromadb, langgraph 依赖 |
| `server/models/novel/__init__.py` | 导出 NovelMemory, NovelMemoryChange |
| `server/routes/novels/__init__.py` | 注册 memories 路由 |
| `server/services/novel/chapter_generator.py` | 接入 RAG 检索 |
| `server/services/novel/context_builder.py` | 合并记忆上下文 |
| `server/routes/novels/chapters.py` | 确认章节后触发记忆抽取 |
| `server/services/novel/generation_runner.py` | 新增 memory_extract 任务类型 |
| `web/src/api/index.js` | 添加 novelsApi 记忆相关端点 |
| `web/src/stores/novels.js` | 添加 memories/memoryChanges 状态和 actions |
| `web/src/views/NovelWorkspace.vue` | 新增"记忆"模式 |
| `web/src/components/novel/NovelGenerationPanel.vue` | 启用长期记忆开关 |

---

## P0：最小可用 RAG

### Task 1: 依赖安装与验证

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加 LangChain 和 ChromaDB 依赖**

在 `pyproject.toml` 的 `dependencies` 列表末尾添加：

```toml
dependencies = [
    # ... existing deps ...
    "langchain>=0.3.0",
    "langchain-openai>=0.3.0",
    "langchain-community>=0.3.0",
    "chromadb>=0.6.0",
]
```

- [ ] **Step 2: 安装依赖并验证**

```bash
cd /Users/ckrey/video/script && uv sync
```

Expected: 依赖安装成功，无冲突。

- [ ] **Step 3: 验证导入**

```bash
uv run python -c "import langchain; import chromadb; print('OK:', langchain.__version__, chromadb.__version__)"
```

Expected: 打印版本号，无 ImportError。

- [ ] **Step 4: 运行现有测试确保无回归**

```bash
uv run pytest server/tests/ -q
```

Expected: 所有测试通过（322+ tests）。

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add langchain, chromadb dependencies for RAG memory"
```

---

### Task 2: NovelMemory 和 NovelMemoryChange 模型

**Files:**
- Create: `server/models/novel/memory.py`
- Modify: `server/models/novel/__init__.py`

- [ ] **Step 1: 创建 memory 模型文件**

创建 `server/models/novel/memory.py`：

```python
import json
from datetime import datetime, timezone
from server.models.base import db


def _now():
    return datetime.now(timezone.utc)


def _json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _json_dumps(value):
    return json.dumps(value or {}, ensure_ascii=False)


class NovelMemory(db.Model):
    __tablename__ = 'novel_memories'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    source_id = db.Column(db.Integer, nullable=True)
    memory_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=3)
    status = db.Column(db.String(20), nullable=False, default='active')
    vector_status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def metadata_(self):
        return _json_loads(self.metadata_json, {})

    @metadata_.setter
    def metadata_(self, value):
        self.metadata_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'memory_type': self.memory_type,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'metadata': self.metadata_,
            'importance': self.importance,
            'status': self.status,
            'vector_status': self.vector_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelMemoryChange(db.Model):
    __tablename__ = 'novel_memory_changes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False, index=True)
    memory_id = db.Column(db.Integer, nullable=True, index=True)
    change_type = db.Column(db.String(30), nullable=False)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False, default='user_manual')
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=_now)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    @property
    def before(self):
        return _json_loads(self.before_json, None)

    @before.setter
    def before(self, value):
        self.before_json = _json_dumps(value)

    @property
    def after(self):
        return _json_loads(self.after_json, None)

    @after.setter
    def after(self, value):
        self.after_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'memory_id': self.memory_id,
            'change_type': self.change_type,
            'before': self.before,
            'after': self.after,
            'source': self.source,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
```

- [ ] **Step 2: 更新 __init__.py 导出**

修改 `server/models/novel/__init__.py`，添加：

```python
from server.models.novel.memory import NovelMemory, NovelMemoryChange

__all__ = [
    'NovelProject',
    'NovelOutlineNode',
    'NovelChapter', 'NovelChapterVersion',
    'NovelEntity', 'NovelRelation',
    'NovelEvent', 'NovelEventRelation',
    'NovelGraphChange', 'NovelGeneration',
    'NovelMemory', 'NovelMemoryChange',
]
```

- [ ] **Step 3: 验证模型创建**

```bash
uv run python -c "
from server.app import create_app
app = create_app()
with app.app_context():
    from server.models.novel import NovelMemory, NovelMemoryChange
    print('Models OK:', NovelMemory.__tablename__, NovelMemoryChange.__tablename__)
"
```

Expected: 打印表名，无错误。

- [ ] **Step 4: Commit**

```bash
git add server/models/novel/memory.py server/models/novel/__init__.py
git commit -m "feat: add NovelMemory and NovelMemoryChange models"
```

---

### Task 3: 后端测试 — NovelMemory 模型 CRUD

**Files:**
- Create: `server/tests/test_novel_memory.py`

- [ ] **Step 1: 创建测试文件**

创建 `server/tests/test_novel_memory.py`：

```python
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.memory import NovelMemory, NovelMemoryChange


@pytest.fixture
def sample_project(client):
    project = NovelProject(title='测试小说', genre='玄幻')
    db.session.add(project)
    db.session.commit()
    return project


def test_create_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '主角设定',
        'content': '张三，男，25岁，修炼火属性功法',
        'memory_type': 'character',
        'source_type': 'manual_note',
        'importance': 5,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '主角设定'
    assert data['memory_type'] == 'character'
    assert data['importance'] == 5
    assert data['status'] == 'active'
    assert data['vector_status'] == 'pending'


def test_list_memories(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆1', 'content': '内容1', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆2', 'content': '内容2', 'memory_type': 'world_rule', 'source_type': 'manual_note',
    })
    resp = client.get(f'/api/novels/{sample_project.id}/memories')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_list_memories_filter(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '人物', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '世界', 'content': '内容', 'memory_type': 'world_rule', 'source_type': 'manual_note',
    })
    resp = client.get(f'/api/novels/{sample_project.id}/memories?memory_type=character')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['memory_type'] == 'character'


def test_update_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '原始', 'content': '原始内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/{sample_project.id}/memories/{mid}', json={
        'title': '更新后', 'importance': 1,
    })
    assert resp.status_code == 200
    assert resp.get_json()['title'] == '更新后'
    assert resp.get_json()['importance'] == 1


def test_delete_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '待删', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.delete(f'/api/novels/{sample_project.id}/memories/{mid}')
    assert resp.status_code == 204
    resp = client.get(f'/api/novels/{sample_project.id}/memories')
    assert len(resp.get_json()) == 0


def test_memory_requires_title_and_content(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'memory_type': 'character', 'source_type': 'manual_note',
    })
    assert resp.status_code == 400


def test_memory_belongs_to_project(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/99999/memories/{mid}', json={'title': 'x'})
    assert resp.status_code in (404, 400)


def test_memory_changes_list(client, sample_project):
    resp = client.get(f'/api/novels/{sample_project.id}/memory-changes')
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
```

- [ ] **Step 2: 运行测试确认全部失败**

```bash
uv run pytest server/tests/test_novel_memory.py -v 2>&1 | head -40
```

Expected: 测试失败（路由不存在）。

- [ ] **Step 3: Commit（测试先行）**

```bash
git add server/tests/test_novel_memory.py
git commit -m "test: add NovelMemory CRUD and memory-changes tests"
```

---

### Task 4: 记忆 CRUD API 路由

**Files:**
- Create: `server/routes/novels/memories.py`
- Modify: `server/routes/novels/__init__.py`

- [ ] **Step 1: 创建 memories 路由**

创建 `server/routes/novels/memories.py`：

```python
from datetime import datetime, timezone
from flask import request
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.memory import NovelMemory, NovelMemoryChange
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/memories', methods=['GET'])
def list_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    query = NovelMemory.query.filter_by(project_id=project_id, status='active')

    memory_type = request.args.get('memory_type')
    if memory_type:
        query = query.filter_by(memory_type=memory_type)

    source_type = request.args.get('source_type')
    if source_type:
        query = query.filter_by(source_type=source_type)

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            db.or_(
                NovelMemory.title.contains(keyword),
                NovelMemory.content.contains(keyword),
            )
        )

    memories = query.order_by(NovelMemory.importance.desc(), NovelMemory.updated_at.desc()).all()
    return [m.to_dict() for m in memories]


@novels_bp.route('/api/novels/<int:project_id>/memories', methods=['POST'])
def create_memory(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    if not data.get('content'):
        return {'error': '内容不能为空'}, 400

    memory = NovelMemory(
        project_id=project_id,
        source_type=data.get('source_type', 'manual_note'),
        source_id=data.get('source_id'),
        memory_type=data.get('memory_type', 'summary'),
        title=data.get('title'),
        content=data['content'],
        summary=data.get('summary'),
        importance=data.get('importance', 3),
        status='active',
        vector_status='pending',
    )
    if data.get('metadata'):
        memory.metadata_ = data['metadata']

    db.session.add(memory)
    db.session.commit()
    return memory.to_dict(), 201


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['PATCH'])
def update_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return {'error': '记忆不属于该项目'}, 400

    data = request.get_json() or {}
    for field in ('title', 'content', 'summary', 'memory_type', 'source_type', 'importance', 'status'):
        if field in data:
            setattr(memory, field, data[field])
    if 'metadata' in data:
        memory.metadata_ = data['metadata']
    if 'content' in data:
        memory.vector_status = 'pending'

    db.session.commit()
    return memory.to_dict()


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['DELETE'])
def delete_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return {'error': '记忆不属于该项目'}, 400

    db.session.delete(memory)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/memory-changes', methods=['GET'])
def list_memory_changes(project_id):
    NovelProject.query.get_or_404(project_id)
    changes = NovelMemoryChange.query.filter_by(
        project_id=project_id, status='pending'
    ).order_by(NovelMemoryChange.created_at.desc()).all()
    return [c.to_dict() for c in changes]


@novels_bp.route('/api/novels/<int:project_id>/memory-changes/<int:change_id>/confirm', methods=['POST'])
def confirm_memory_change(project_id, change_id):
    NovelProject.query.get_or_404(project_id)
    change = NovelMemoryChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return {'error': '变更不属于该项目'}, 400

    after = change.after
    if not after:
        return {'error': '变更数据为空'}, 400

    if change.change_type == 'add':
        memory = NovelMemory(
            project_id=project_id,
            source_type=after.get('source_type', 'ai_extract'),
            source_id=after.get('source_id'),
            memory_type=after.get('memory_type', 'summary'),
            title=after.get('title'),
            content=after.get('content', ''),
            summary=after.get('summary'),
            importance=after.get('importance', 3),
            status='active',
            vector_status='pending',
        )
        db.session.add(memory)
        db.session.flush()
        change.memory_id = memory.id
    elif change.change_type == 'modify' and change.memory_id:
        memory = NovelMemory.query.get(change.memory_id)
        if memory:
            for field in ('title', 'content', 'summary', 'importance', 'memory_type'):
                if field in after:
                    setattr(memory, field, after[field])
            memory.vector_status = 'pending'

    change.status = 'confirmed'
    change.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()
    return change.to_dict()


@novels_bp.route('/api/novels/<int:project_id>/memory-changes/<int:change_id>/reject', methods=['POST'])
def reject_memory_change(project_id, change_id):
    NovelProject.query.get_or_404(project_id)
    change = NovelMemoryChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return {'error': '变更不属于该项目'}, 400

    change.status = 'rejected'
    db.session.commit()
    return change.to_dict()
```

- [ ] **Step 2: 注册路由**

修改 `server/routes/novels/__init__.py`，添加导入：

```python
from server.routes.novels import memories
```

- [ ] **Step 3: 运行测试**

```bash
uv run pytest server/tests/test_novel_memory.py -v
```

Expected: 所有 8 个测试通过。

- [ ] **Step 4: 运行全部测试确保无回归**

```bash
uv run pytest server/tests/ -q
```

Expected: 全部通过。

- [ ] **Step 5: Commit**

```bash
git add server/routes/novels/memories.py server/routes/novels/__init__.py
git commit -m "feat: add memory CRUD and memory-changes API routes"
```

---

### Task 5: document_types 和 chunker 模块

**Files:**
- Create: `server/services/memory/__init__.py`
- Create: `server/services/memory/document_types.py`
- Create: `server/services/memory/chunker.py`

- [ ] **Step 1: 创建 memory 包初始化**

创建 `server/services/memory/__init__.py`：

```python
```

- [ ] **Step 2: 创建 document_types.py**

创建 `server/services/memory/document_types.py`：

```python
"""Long-term memory document type definitions."""

MEMORY_TYPES = (
    'world_rule',      # 世界观规则
    'character',       # 人物设定
    'relationship',    # 人物关系
    'event',           # 事件
    'foreshadowing',   # 伏笔
    'style',           # 文风
    'summary',         # 摘要
)

SOURCE_TYPES = (
    'project',      # 项目级设定
    'chapter',      # 章节
    'outline',      # 大纲
    'entity',       # 人物/实体
    'event',        # 事件
    'manual_note',  # 手动笔记
    'ai_extract',   # AI 抽取
)

VECTOR_STATUS = ('pending', 'indexed', 'failed')
MEMORY_STATUS = ('active', 'archived', 'superseded')
CHANGE_STATUS = ('pending', 'confirmed', 'rejected')
```

- [ ] **Step 3: 创建 chunker.py**

创建 `server/services/memory/chunker.py`：

```python
"""Text chunking for long-term memory indexing."""


def chunk_text(text, max_chunk_size=500, overlap=50):
    """Split text into chunks for embedding.

    Args:
        text: Input text to chunk.
        max_chunk_size: Maximum characters per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text:
        return []
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('。')
            last_question = chunk.rfind('？')
            last_exclaim = chunk.rfind('！')
            break_point = max(last_period, last_question, last_exclaim)
            if break_point > max_chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]


def chunk_chapter(content, title='', max_chunk_size=500, overlap=50):
    """Chunk a chapter's content with title prefix.

    Returns:
        List of (chunk_text, metadata) tuples.
    """
    if not content:
        return []

    chunks = chunk_text(content, max_chunk_size, overlap)
    result = []
    for i, chunk in enumerate(chunks):
        prefix = f'【{title}】' if title else ''
        result.append((f'{prefix}{chunk}', {'chunk_index': i}))

    return result
```

- [ ] **Step 4: Commit**

```bash
git add server/services/memory/
git commit -m "feat: add memory document_types and chunker modules"
```

---

### Task 6: embeddings 和 vector_store 模块

**Files:**
- Create: `server/services/memory/embeddings.py`
- Create: `server/services/memory/vector_store.py`

- [ ] **Step 1: 创建 embeddings.py**

创建 `server/services/memory/embeddings.py`：

```python
"""Embedding model wrapper for memory indexing and retrieval."""

import os
import logging

logger = logging.getLogger(__name__)

_embeddings = None


def get_embeddings():
    """Get or create the embedding model instance.

    Uses OpenAI-compatible embedding API. Checks for API key in order:
    1. OPENAI_API_KEY (for OpenAI embeddings)
    2. DEEPSEEK_API_KEY (for DeepSeek embeddings, if supported)
    """
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    from langchain_openai import OpenAIEmbeddings

    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('DEEPSEEK_API_KEY')
    base_url = None

    if os.environ.get('DEEPSEEK_API_KEY') and not os.environ.get('OPENAI_API_KEY'):
        base_url = 'https://api.deepseek.com/v1'

    if not api_key:
        logger.warning('No embedding API key found. Memory indexing will not work.')
        return None

    _embeddings = OpenAIEmbeddings(
        api_key=api_key,
        base_url=base_url,
    )
    return _embeddings


def reset_embeddings():
    """Reset the cached embedding instance (for testing)."""
    global _embeddings
    _embeddings = None
```

- [ ] **Step 2: 创建 vector_store.py**

创建 `server/services/memory/vector_store.py`：

```python
"""Chroma vector store wrapper with project-level isolation."""

import os
import logging

logger = logging.getLogger(__name__)

_stores = {}


def get_vector_store(project_id):
    """Get or create a Chroma vector store for a project.

    Each project gets its own collection to prevent cross-project contamination.
    """
    project_id = str(project_id)
    if project_id in _stores:
        return _stores[project_id]

    from server.services.memory.embeddings import get_embeddings
    embeddings = get_embeddings()
    if embeddings is None:
        return None

    persist_dir = os.path.join(os.getcwd(), 'data', 'chromadb')
    os.makedirs(persist_dir, exist_ok=True)

    from langchain_community.vectorstores import Chroma
    store = Chroma(
        collection_name=f'novel_{project_id}',
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )
    _stores[project_id] = store
    return store


def add_documents(project_id, texts, metadatas=None):
    """Add documents to the project's vector store.

    Returns:
        List of document IDs, or None if store unavailable.
    """
    store = get_vector_store(project_id)
    if store is None:
        return None

    ids = store.add_texts(texts=texts, metadatas=metadatas)
    return ids


def search(project_id, query, k=10, filter_dict=None):
    """Search the project's vector store.

    Returns:
        List of (Document, score) tuples, or empty list if store unavailable.
    """
    store = get_vector_store(project_id)
    if store is None:
        return []

    kwargs = {'k': k}
    if filter_dict:
        kwargs['filter'] = filter_dict

    return store.similarity_search_with_score(query, **kwargs)


def delete_by_memory_id(project_id, memory_id):
    """Delete all chunks belonging to a memory from the vector store."""
    store = get_vector_store(project_id)
    if store is None:
        return

    try:
        store.delete(where={'memory_id': str(memory_id)})
    except Exception:
        logger.warning(f'Failed to delete vectors for memory {memory_id}')


def rebuild_index(project_id, memories):
    """Rebuild the entire vector index for a project from memory records.

    Args:
        project_id: Project ID.
        memories: List of NovelMemory objects.

    Returns:
        Number of indexed chunks.
    """
    store = get_vector_store(project_id)
    if store is None:
        return 0

    # Clear existing collection
    try:
        store._collection.delete(where={})
    except Exception:
        pass

    from server.services.memory.chunker import chunk_text
    from server.models.novel.memory import NovelMemory

    texts = []
    metadatas = []
    for mem in memories:
        chunks = chunk_text(mem.content)
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                'memory_id': str(mem.id),
                'memory_type': mem.memory_type,
                'source_type': mem.source_type,
                'source_id': str(mem.source_id) if mem.source_id else '',
                'importance': mem.importance,
                'chunk_index': i,
            })

    if texts:
        store.add_texts(texts=texts, metadatas=metadatas)

    return len(texts)


def reset_stores():
    """Reset cached stores (for testing)."""
    global _stores
    _stores = {}
```

- [ ] **Step 3: Commit**

```bash
git add server/services/memory/embeddings.py server/services/memory/vector_store.py
git commit -m "feat: add embeddings and Chroma vector_store modules"
```

---

### Task 7: retriever 模块

**Files:**
- Create: `server/services/memory/retriever.py`

- [ ] **Step 1: 创建 retriever.py**

创建 `server/services/memory/retriever.py`：

```python
"""Multi-retrieval with ranking and compression for RAG memory."""

from server.services.memory.vector_store import search


# Budget allocation for memory types (relative weights)
MEMORY_TYPE_WEIGHTS = {
    'character': 1.0,
    'world_rule': 0.9,
    'event': 0.8,
    'relationship': 0.8,
    'foreshadowing': 0.7,
    'style': 0.5,
    'summary': 0.6,
}


def retrieve_memories(project_id, query, chapter_context=None, k=10):
    """Retrieve relevant memories for chapter generation.

    Args:
        project_id: Project ID.
        query: Search query (chapter outline + user instruction).
        chapter_context: Optional dict with current chapter info for filtering.
        k: Number of results to retrieve.

    Returns:
        List of memory dicts sorted by relevance, with 'content' and 'metadata'.
    """
    if not query or not query.strip():
        return []

    results = search(project_id, query, k=k)
    if not results:
        return []

    memories = []
    for doc, score in results:
        meta = doc.metadata or {}
        importance = meta.get('importance', 3)
        # Combine vector similarity score with importance
        combined_score = (1 - score) * 0.7 + (importance / 5) * 0.3

        memories.append({
            'content': doc.page_content,
            'memory_type': meta.get('memory_type', ''),
            'memory_id': meta.get('memory_id', ''),
            'importance': importance,
            'score': combined_score,
            'vector_score': 1 - score,
        })

    # Sort by combined score descending
    memories.sort(key=lambda m: m['score'], reverse=True)
    return memories


def retrieve_by_type(project_id, memory_type, query, k=5):
    """Retrieve memories filtered by type.

    Args:
        project_id: Project ID.
        memory_type: Filter to this memory type.
        query: Search query.
        k: Number of results.

    Returns:
        List of memory dicts.
    """
    results = search(project_id, query, k=k, filter_dict={'memory_type': memory_type})
    if not results:
        return []

    memories = []
    for doc, score in results:
        meta = doc.metadata or {}
        memories.append({
            'content': doc.page_content,
            'memory_type': memory_type,
            'memory_id': meta.get('memory_id', ''),
            'importance': meta.get('importance', 3),
            'score': 1 - score,
        })

    memories.sort(key=lambda m: m['score'], reverse=True)
    return memories


def format_memories_for_prompt(memories, max_chars=3000):
    """Format retrieved memories into a prompt section.

    Args:
        memories: List of memory dicts from retrieve_memories().
        max_chars: Maximum character budget for the memories section.

    Returns:
        Formatted string for prompt injection.
    """
    if not memories:
        return ''

    parts = []
    total = 0
    for mem in memories:
        text = mem['content']
        if total + len(text) > max_chars:
            remaining = max_chars - total
            if remaining > 50:
                text = text[:remaining] + '...'
            else:
                break
        parts.append(text)
        total += len(text)

    return '\n\n'.join(parts)
```

- [ ] **Step 2: Commit**

```bash
git add server/services/memory/retriever.py
git commit -m "feat: add multi-retrieval retriever with ranking"
```

---

### Task 8: rag_chain 模块 — 生成链路集成

**Files:**
- Create: `server/services/memory/rag_chain.py`
- Modify: `server/services/novel/chapter_generator.py`

- [ ] **Step 1: 创建 rag_chain.py**

创建 `server/services/memory/rag_chain.py`：

```python
"""LangChain RAG orchestration: retrieval -> prompt -> LLM -> output."""

from server.services.memory.retriever import retrieve_memories, format_memories_for_prompt


def generate_with_memory(project, chapter, context, system_prompt, user_instruction='',
                         model_key=None, version_type='custom'):
    """Generate chapter content with RAG memory augmentation.

    Args:
        project: NovelProject instance.
        chapter: NovelChapter instance.
        context: Context dict from context_builder.build_context().
        system_prompt: System prompt from prompt_templates.
        user_instruction: User's generation instruction.
        model_key: Optional model override.
        version_type: Version type for generation.

    Returns:
        Generated content string.
    """
    # Build retrieval query from context
    query_parts = []
    if context.get('outline'):
        query_parts.append(context['outline'])
    if user_instruction:
        query_parts.append(user_instruction)
    if context.get('characters'):
        query_parts.append(context['characters'][:500])
    query = ' '.join(query_parts) if query_parts else ''

    # Retrieve relevant memories
    memory_text = ''
    if query:
        memories = retrieve_memories(project.id, query, k=10)
        memory_text = format_memories_for_prompt(memories, max_chars=3000)

    # Build enhanced user prompt with memory section
    prompt_sections = []
    if context.get('outline'):
        prompt_sections.append(f'【大纲】\n{context["outline"]}')
    if context.get('previous_summaries'):
        prompt_sections.append(f'【前文摘要】\n{context["previous_summaries"]}')
    if context.get('text_tail'):
        prompt_sections.append(f'【前文末尾】\n{context["text_tail"]}')
    if memory_text:
        prompt_sections.append(f'【长期记忆】\n{memory_text}')
    if context.get('characters'):
        prompt_sections.append(f'【人物设定】\n{context["characters"]}')
    if context.get('events'):
        prompt_sections.append(f'【事件时间线】\n{context["events"]}')
    if context.get('world_building'):
        prompt_sections.append(f'【世界观】\n{context["world_building"]}')
    if context.get('foreshadowing'):
        prompt_sections.append(f'【伏笔】\n{context["foreshadowing"]}')
    if user_instruction:
        prompt_sections.append(f'【用户指令】\n{user_instruction}')

    target_words = context.get('target_words', 3000)
    prompt_sections.append(f'【输出要求】\n- 只输出正文 Markdown。\n- 不要解释。\n- 目标字数：{target_words}字')

    user_prompt = '\n\n'.join(prompt_sections)

    # Get LLM provider
    from server.services.novel import get_llm_provider
    provider, default_model = get_llm_provider()

    # Call LLM
    messages = [{'role': 'user', 'content': user_prompt}]
    content = provider.complete(
        messages,
        model=model_key or default_model,
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    return content
```

- [ ] **Step 2: 修改 chapter_generator.py 接入 RAG**

修改 `server/services/novel/chapter_generator.py`，在 `build_context()` 后使用 `rag_chain.generate_with_memory()`：

```python
# server/services/novel/chapter_generator.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.services.novel.context_builder import build_context
from server.services.novel.prompt_templates import build_chapter_system_prompt


def generate_single_version(project_id, chapter_id, version_type='custom', user_instruction='', model_key=None):
    """Generate a single version for a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    # Build context
    context = build_context(project_id, chapter_id, user_instruction, project.words_per_chapter)

    # Build system prompt
    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=version_type,
        style_guide=project.style_guide,
    )

    # Generate with RAG memory
    from server.services.memory.rag_chain import generate_with_memory
    content = generate_with_memory(
        project=project,
        chapter=chapter,
        context=context,
        system_prompt=system_prompt,
        user_instruction=user_instruction,
        model_key=model_key,
        version_type=version_type,
    )

    # Create version
    version = NovelChapterVersion(
        chapter_id=chapter_id,
        version_type=version_type,
        title=f'{version_type}版',
        content_markdown=content,
        model=model_key or 'unknown',
        accepted=False,
    )
    version.prompt = {'system': system_prompt, 'user': user_instruction}
    version.context_snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}

    db.session.add(version)
    db.session.commit()

    return version
```

- [ ] **Step 3: 运行现有测试确保无回归**

```bash
uv run pytest server/tests/ -q
```

Expected: 全部通过（rag_chain 在无 API key 时会 fallback）。

- [ ] **Step 4: Commit**

```bash
git add server/services/memory/rag_chain.py server/services/novel/chapter_generator.py
git commit -m "feat: integrate RAG memory into chapter generation pipeline"
```

---

### Task 9: reindex 和 search API

**Files:**
- Modify: `server/routes/novels/memories.py`

- [ ] **Step 1: 在 memories.py 中添加 reindex 和 search 端点**

在 `server/routes/novels/memories.py` 末尾添加：

```python
@novels_bp.route('/api/novels/<int:project_id>/memories/reindex', methods=['POST'])
def reindex_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    memories = NovelMemory.query.filter_by(project_id=project_id, status='active').all()

    from server.services.memory.vector_store import rebuild_index
    from server.models.novel.memory import NovelMemory as MemModel

    count = rebuild_index(project_id, memories)

    # Update vector_status
    for mem in memories:
        mem.vector_status = 'indexed'
    db.session.commit()

    return {'indexed_chunks': count, 'memories': len(memories)}


@novels_bp.route('/api/novels/<int:project_id>/memories/search', methods=['POST'])
def search_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    query = data.get('query', '')
    k = data.get('k', 10)
    memory_type = data.get('memory_type')

    from server.services.memory.retriever import retrieve_memories, retrieve_by_type

    if memory_type:
        results = retrieve_by_type(project_id, memory_type, query, k=k)
    else:
        results = retrieve_memories(project_id, query, k=k)

    return {'results': results, 'query': query}
```

- [ ] **Step 2: 添加前端 API 端点**

修改 `web/src/api/index.js` 的 `novelsApi`，添加：

```javascript
// Memories
listMemories: (pid, params) => api.get(`/novels/${pid}/memories`, { params }),
createMemory: (pid, data) => api.post(`/novels/${pid}/memories`, data),
updateMemory: (pid, mid, data) => api.patch(`/novels/${pid}/memories/${mid}`, data),
deleteMemory: (pid, mid) => api.delete(`/novels/${pid}/memories/${mid}`),
searchMemories: (pid, data) => api.post(`/novels/${pid}/memories/search`, data),
reindexMemories: (pid) => api.post(`/novels/${pid}/memories/reindex`),
listMemoryChanges: (pid) => api.get(`/novels/${pid}/memory-changes`),
confirmMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/confirm`),
rejectMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/reject`),
```

- [ ] **Step 3: 运行测试**

```bash
uv run pytest server/tests/test_novel_memory.py -v
```

Expected: 全部通过。

- [ ] **Step 4: Commit**

```bash
git add server/routes/novels/memories.py web/src/api/index.js
git commit -m "feat: add reindex and search API endpoints"
```

---

### Task 10: memory_writer 模块

**Files:**
- Create: `server/services/memory/memory_writer.py`

- [ ] **Step 1: 创建 memory_writer.py**

创建 `server/services/memory/memory_writer.py`：

```python
"""Memory write operations: create, update, index."""

from server.models import db
from server.models.novel.memory import NovelMemory


def create_memory(project_id, content, memory_type, title=None, source_type='manual_note',
                  source_id=None, importance=3, summary=None, metadata=None):
    """Create a new memory record and queue it for indexing.

    Returns:
        The created NovelMemory instance.
    """
    memory = NovelMemory(
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        memory_type=memory_type,
        title=title,
        content=content,
        summary=summary,
        importance=importance,
        status='active',
        vector_status='pending',
    )
    if metadata:
        memory.metadata_ = metadata

    db.session.add(memory)
    db.session.commit()
    return memory


def index_memory(memory):
    """Index a single memory into the vector store.

    Updates vector_status to 'indexed' on success, 'failed' on error.
    """
    from server.services.memory.vector_store import add_documents, delete_by_memory_id
    from server.services.memory.chunker import chunk_text

    chunks = chunk_text(memory.content)
    if not chunks:
        memory.vector_status = 'indexed'
        db.session.commit()
        return

    metadatas = [{
        'memory_id': str(memory.id),
        'memory_type': memory.memory_type,
        'source_type': memory.source_type,
        'source_id': str(memory.source_id) if memory.source_id else '',
        'importance': memory.importance,
        'chunk_index': i,
    } for i in range(len(chunks))]

    try:
        # Delete old vectors first
        delete_by_memory_id(memory.project_id, memory.id)
        add_documents(memory.project_id, chunks, metadatas)
        memory.vector_status = 'indexed'
    except Exception:
        memory.vector_status = 'failed'

    db.session.commit()


def create_and_index(project_id, content, memory_type, **kwargs):
    """Create a memory and immediately index it.

    Returns:
        The created NovelMemory instance.
    """
    memory = create_memory(project_id, content, memory_type, **kwargs)
    index_memory(memory)
    return memory
```

- [ ] **Step 2: 更新 create_memory 路由以自动索引**

修改 `server/routes/novels/memories.py` 的 `create_memory` 函数，在 `db.session.commit()` 后添加索引调用：

```python
    db.session.commit()

    # Index into vector store (best effort)
    try:
        from server.services.memory.memory_writer import index_memory
        index_memory(memory)
    except Exception:
        pass

    return memory.to_dict(), 201
```

同样修改 `update_memory` 和 `confirm_memory_change`，在内容变更后重新索引。

- [ ] **Step 3: Commit**

```bash
git add server/services/memory/memory_writer.py server/routes/novels/memories.py
git commit -m "feat: add memory_writer with create-and-index pipeline"
```

---

### Task 11: 前端 Store 和 API 层

**Files:**
- Modify: `web/src/stores/novels.js`

- [ ] **Step 1: 在 novels store 中添加记忆状态和 actions**

在 `web/src/stores/novels.js` 的 `state` 中添加：

```javascript
// Memories
memories: [],
memoryChanges: [],
memorySearchResults: [],
memoryLoading: false,
```

在 `actions` 中添加：

```javascript
// --- Memories ---
async fetchMemories(pid, params = {}) {
  this.memoryLoading = true
  try {
    const { data } = await novelsApi.listMemories(pid, params)
    this.memories = data
  } finally {
    this.memoryLoading = false
  }
},

async createMemory(pid, memoryData) {
  const { data } = await novelsApi.createMemory(pid, memoryData)
  this.memories.unshift(data)
  return data
},

async updateMemory(pid, mid, memoryData) {
  const { data } = await novelsApi.updateMemory(pid, mid, memoryData)
  const idx = this.memories.findIndex(m => m.id === mid)
  if (idx !== -1) this.memories[idx] = data
  return data
},

async deleteMemory(pid, mid) {
  await novelsApi.deleteMemory(pid, mid)
  this.memories = this.memories.filter(m => m.id !== mid)
},

async searchMemories(pid, query) {
  const { data } = await novelsApi.searchMemories(pid, { query, k: 10 })
  this.memorySearchResults = data.results || []
  return data
},

async fetchMemoryChanges(pid) {
  const { data } = await novelsApi.listMemoryChanges(pid)
  this.memoryChanges = data
},

async confirmMemoryChange(pid, cid) {
  await novelsApi.confirmMemoryChange(pid, cid)
  this.memoryChanges = this.memoryChanges.filter(c => c.id !== cid)
},

async rejectMemoryChange(pid, cid) {
  await novelsApi.rejectMemoryChange(pid, cid)
  this.memoryChanges = this.memoryChanges.filter(c => c.id !== cid)
},

async reindexMemories(pid) {
  await novelsApi.reindexMemories(pid)
},
```

在 `cleanup()` 中添加：

```javascript
this.memories = []
this.memoryChanges = []
this.memorySearchResults = []
```

- [ ] **Step 2: 验证前端构建**

```bash
cd /Users/ckrey/video/script/web && pnpm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add web/src/stores/novels.js
git commit -m "feat: add memory state and actions to novels store"
```

---

### Task 12: NovelMemoryPanel 前端组件

**Files:**
- Create: `web/src/components/novel/NovelMemoryPanel.vue`

- [ ] **Step 1: 创建 NovelMemoryPanel.vue**

创建 `web/src/components/novel/NovelMemoryPanel.vue`：

```vue
<template>
  <div class="novel-memory-panel">
    <div class="memory-header">
      <a-input-search
        v-model:value="searchKeyword"
        placeholder="搜索记忆..."
        size="small"
        @search="handleSearch"
      />
      <div class="memory-filters">
        <a-select v-model:value="filterType" placeholder="类型" size="small" allow-clear style="width: 100px">
          <a-select-option value="character">人物</a-select-option>
          <a-select-option value="world_rule">世界观</a-select-option>
          <a-select-option value="event">事件</a-select-option>
          <a-select-option value="foreshadowing">伏笔</a-select-option>
          <a-select-option value="relationship">关系</a-select-option>
          <a-select-option value="style">文风</a-select-option>
          <a-select-option value="summary">摘要</a-select-option>
        </a-select>
        <a-button size="small" @click="showCreateModal = true">新增</a-button>
        <a-button size="small" @click="handleReindex">重建索引</a-button>
      </div>
    </div>

    <a-spin :spinning="store.memoryLoading">
      <a-list :data-source="filteredMemories" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <span>{{ item.title || item.memory_type }}</span>
                <a-tag :color="typeColor(item.memory_type)" size="small" style="margin-left: 8px">
                  {{ typeLabel(item.memory_type) }}
                </a-tag>
                <a-tag :color="item.vector_status === 'indexed' ? 'green' : 'orange'" size="small">
                  {{ item.vector_status }}
                </a-tag>
              </template>
              <template #description>
                <div class="memory-content">{{ item.content?.slice(0, 100) }}...</div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button size="small" type="link" @click="handleEdit(item)">编辑</a-button>
              <a-popconfirm title="确认删除？" @confirm="handleDelete(item.id)">
                <a-button size="small" type="link" danger>删除</a-button>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-spin>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingMemory ? '编辑记忆' : '新增记忆'"
      @ok="handleSave"
      width="600px"
    >
      <a-form layout="vertical">
        <a-form-item label="标题">
          <a-input v-model:value="form.title" />
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="form.memory_type">
            <a-select-option value="character">人物</a-select-option>
            <a-select-option value="world_rule">世界观</a-select-option>
            <a-select-option value="event">事件</a-select-option>
            <a-select-option value="foreshadowing">伏笔</a-select-option>
            <a-select-option value="relationship">关系</a-select-option>
            <a-select-option value="style">文风</a-select-option>
            <a-select-option value="summary">摘要</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="内容">
          <a-textarea v-model:value="form.content" :rows="6" />
        </a-form-item>
        <a-form-item label="重要性">
          <a-rate v-model:value="form.importance" :count="5" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const searchKeyword = ref('')
const filterType = ref(undefined)
const showCreateModal = ref(false)
const editingMemory = ref(null)
const form = ref({ title: '', content: '', memory_type: 'character', importance: 3 })

const filteredMemories = computed(() => {
  let list = store.memories
  if (filterType.value) {
    list = list.filter(m => m.memory_type === filterType.value)
  }
  return list
})

const typeLabel = (t) => ({
  character: '人物', world_rule: '世界观', event: '事件',
  foreshadowing: '伏笔', relationship: '关系', style: '文风', summary: '摘要',
}[t] || t)

const typeColor = (t) => ({
  character: 'blue', world_rule: 'purple', event: 'orange',
  foreshadowing: 'gold', relationship: 'cyan', style: 'green', summary: 'default',
}[t] || 'default')

const handleSearch = () => {
  const params = {}
  if (searchKeyword.value) params.keyword = searchKeyword.value
  if (filterType.value) params.memory_type = filterType.value
  store.fetchMemories(store.currentProject.id, params)
}

const handleEdit = (item) => {
  editingMemory.value = item
  form.value = { title: item.title, content: item.content, memory_type: item.memory_type, importance: item.importance }
  showCreateModal.value = true
}

const handleSave = async () => {
  try {
    if (editingMemory.value) {
      await store.updateMemory(store.currentProject.id, editingMemory.value.id, form.value)
      message.success('已更新')
    } else {
      await store.createMemory(store.currentProject.id, { ...form.value, source_type: 'manual_note' })
      message.success('已创建')
    }
    showCreateModal.value = false
    editingMemory.value = null
    form.value = { title: '', content: '', memory_type: 'character', importance: 3 }
  } catch {
    message.error('操作失败')
  }
}

const handleDelete = async (id) => {
  try {
    await store.deleteMemory(store.currentProject.id, id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}

const handleReindex = async () => {
  try {
    await store.reindexMemories(store.currentProject.id)
    await store.fetchMemories(store.currentProject.id)
    message.success('索引已重建')
  } catch {
    message.error('重建失败')
  }
}

watch(filterType, () => handleSearch())

onMounted(() => {
  if (store.currentProject) {
    store.fetchMemories(store.currentProject.id)
  }
})
</script>

<style scoped>
.novel-memory-panel { padding: 8px; }
.memory-header { margin-bottom: 12px; }
.memory-filters { display: flex; gap: 4px; margin-top: 8px; }
.memory-content { font-size: 12px; color: var(--text-muted); }
</style>
```

- [ ] **Step 2: 验证构建**

```bash
cd /Users/ckrey/video/script/web && pnpm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelMemoryPanel.vue
git commit -m "feat: add NovelMemoryPanel component"
```

---

### Task 13: NovelMemorySearch 和 NovelMemoryChangeReview 组件

**Files:**
- Create: `web/src/components/novel/NovelMemorySearch.vue`
- Create: `web/src/components/novel/NovelMemoryChangeReview.vue`

- [ ] **Step 1: 创建 NovelMemorySearch.vue**

创建 `web/src/components/novel/NovelMemorySearch.vue`：

```vue
<template>
  <div class="novel-memory-search">
    <a-input-search
      v-model:value="query"
      placeholder="输入章节目标或关键词，预览 RAG 召回结果"
      size="small"
      @search="handleSearch"
      :loading="searching"
    />
    <div v-if="store.memorySearchResults.length" class="search-results">
      <div v-for="(r, i) in store.memorySearchResults" :key="i" class="search-item">
        <div class="search-item-header">
          <a-tag :color="typeColor(r.memory_type)" size="small">{{ r.memory_type }}</a-tag>
          <span class="search-score">相关度: {{ (r.score * 100).toFixed(0) }}%</span>
        </div>
        <p class="search-item-content">{{ r.content }}</p>
      </div>
    </div>
    <a-empty v-else-if="searched" description="未找到相关记忆" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const query = ref('')
const searching = ref(false)
const searched = ref(false)

const typeColor = (t) => ({
  character: 'blue', world_rule: 'purple', event: 'orange',
  foreshadowing: 'gold', relationship: 'cyan', style: 'green', summary: 'default',
}[t] || 'default')

const handleSearch = async () => {
  if (!query.value.trim() || !store.currentProject) return
  searching.value = true
  searched.value = true
  try {
    await store.searchMemories(store.currentProject.id, query.value)
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.novel-memory-search { padding: 8px; }
.search-results { margin-top: 12px; }
.search-item { padding: 8px; border-bottom: 1px solid var(--surface-border); }
.search-item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.search-score { font-size: 11px; color: var(--text-muted); }
.search-item-content { font-size: 12px; color: var(--text-secondary); margin: 0; }
</style>
```

- [ ] **Step 2: 创建 NovelMemoryChangeReview.vue**

创建 `web/src/components/novel/NovelMemoryChangeReview.vue`：

```vue
<template>
  <div class="novel-memory-change-review">
    <a-empty v-if="!store.memoryChanges.length" description="暂无待确认的记忆变更" />
    <div v-else>
      <div v-for="change in store.memoryChanges" :key="change.id" class="change-card">
        <div class="change-header">
          <a-tag :color="change.change_type === 'add' ? 'green' : 'blue'" size="small">
            {{ change.change_type === 'add' ? '新增' : '修改' }}
          </a-tag>
          <span class="change-type">{{ change.after?.memory_type || '未知' }}</span>
        </div>
        <div class="change-body">
          <strong>{{ change.after?.title || '无标题' }}</strong>
          <p>{{ change.after?.content?.slice(0, 200) || '无内容' }}...</p>
        </div>
        <div class="change-actions">
          <a-button size="small" type="primary" @click="handleConfirm(change.id)">确认</a-button>
          <a-button size="small" danger @click="handleReject(change.id)">拒绝</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

const handleConfirm = async (cid) => {
  try {
    await store.confirmMemoryChange(store.currentProject.id, cid)
    message.success('已确认')
  } catch {
    message.error('确认失败')
  }
}

const handleReject = async (cid) => {
  try {
    await store.rejectMemoryChange(store.currentProject.id, cid)
    message.success('已拒绝')
  } catch {
    message.error('拒绝失败')
  }
}

onMounted(() => {
  if (store.currentProject) {
    store.fetchMemoryChanges(store.currentProject.id)
  }
})
</script>

<style scoped>
.change-card { padding: 12px; border: 1px solid var(--surface-border); border-radius: 6px; margin-bottom: 8px; }
.change-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.change-type { font-size: 12px; color: var(--text-muted); }
.change-body p { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.change-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
```

- [ ] **Step 3: 验证构建**

```bash
cd /Users/ckrey/video/script/web && pnpm run build
```

Expected: 构建成功。

- [ ] **Step 4: Commit**

```bash
git add web/src/components/novel/NovelMemorySearch.vue web/src/components/novel/NovelMemoryChangeReview.vue
git commit -m "feat: add NovelMemorySearch and NovelMemoryChangeReview components"
```

---

### Task 14: NovelWorkspace 集成记忆模式

**Files:**
- Modify: `web/src/views/NovelWorkspace.vue`

- [ ] **Step 1: 在 NovelWorkspace 中集成记忆模式**

修改 `web/src/views/NovelWorkspace.vue`：

1. 导入新组件：

```javascript
import NovelMemoryPanel from '../components/novel/NovelMemoryPanel.vue'
import NovelMemorySearch from '../components/novel/NovelMemorySearch.vue'
import NovelMemoryChangeReview from '../components/novel/NovelMemoryChangeReview.vue'
```

2. 在 top-center 的 segmented 中添加"记忆"选项：

```javascript
{ label: '记忆', value: 'memory' }
```

3. 在 workspace-main 中添加 memory 模式布局：

```vue
<!-- Memory mode -->
<div v-else-if="store.activeMode === 'memory'" class="workspace-main">
  <div class="workspace-left">
    <NovelMemoryPanel />
  </div>
  <div class="workspace-center">
    <NovelMemorySearch />
  </div>
  <div class="workspace-right">
    <a-tabs size="small">
      <a-tab-pane key="changes" tab="待确认">
        <NovelMemoryChangeReview />
      </a-tab-pane>
    </a-tabs>
  </div>
</div>
```

- [ ] **Step 2: 验证构建**

```bash
cd /Users/ckrey/video/script/web && pnpm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add web/src/views/NovelWorkspace.vue
git commit -m "feat: integrate memory mode into NovelWorkspace"
```

---

## P1：章节确认后自动抽取记忆

### Task 15: 结构化抽取 prompt

**Files:**
- Modify: `server/services/novel/prompt_templates.py`

- [ ] **Step 1: 添加记忆抽取 prompt 构建函数**

在 `server/services/novel/prompt_templates.py` 末尾添加：

```python
def build_memory_extract_prompt(chapter_content, context=None):
    """Build prompt for extracting memories from a confirmed chapter.

    Returns a prompt asking the LLM to identify new facts, character changes,
    world rules, foreshadowing, and events as structured JSON.
    """
    context_section = ''
    if context:
        if context.get('characters'):
            context_section += f'\n【已有设定】\n{context["characters"][:1000]}'

    return f"""你是一个小说长期记忆管理助手。请从以下章节中提取需要记住的新事实和变更。

{context_section}

【章节内容】
{chapter_content[:6000]}

请以 JSON 格式输出，包含以下字段：
{{
  "new_memories": [
    {{
      "title": "记忆标题",
      "content": "详细内容",
      "memory_type": "character|world_rule|event|foreshadowing|relationship|style|summary",
      "importance": 1-5,
      "summary": "一句话摘要"
    }}
  ],
  "updates": [
    {{
      "existing_title": "已有设定标题",
      "new_content": "更新后的内容",
      "memory_type": "character|world_rule|event|foreshadowing|relationship|style|summary",
      "reason": "更新原因"
    }}
  ],
  "conflicts": [
    {{
      "description": "冲突描述",
      "severity": "high|medium|low"
    }}
  ]
}}

只输出 JSON，不要解释。"""
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/prompt_templates.py
git commit -m "feat: add memory extraction prompt template"
```

---

### Task 16: 记忆抽取服务

**Files:**
- Modify: `server/services/memory/memory_writer.py`

- [ ] **Step 1: 在 memory_writer.py 中添加 extract_and_create_changes 函数**

在 `server/services/memory/memory_writer.py` 末尾添加：

```python
def extract_and_create_changes(project_id, chapter_id, chapter_content):
    """Extract memories from a chapter and create pending change records.

    Called after chapter confirmation. Uses LLM to identify new facts.

    Returns:
        List of created NovelMemoryChange instances.
    """
    from server.models.novel.memory import NovelMemoryChange
    from server.services.novel.prompt_templates import build_memory_extract_prompt
    from server.services.novel import get_llm_provider
    from server.services.novel.context_builder import build_context
    from server.models.novel.chapter import NovelChapter

    chapter = NovelChapter.query.get(chapter_id)
    context = build_context(project_id, chapter_id) if chapter else {}

    prompt = build_memory_extract_prompt(chapter_content, context)

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = provider.complete(
            messages,
            model=default_model,
            system_prompt='你是小说记忆管理助手，只输出 JSON。',
            max_tokens=4096,
            timeout=60,
        )
    except Exception:
        return []

    # Parse response
    result = _parse_memory_json(response)
    if not result:
        return []

    changes = []

    # Create "add" changes for new memories
    for item in result.get('new_memories', []):
        if not item.get('content'):
            continue
        change = NovelMemoryChange(
            project_id=project_id,
            change_type='add',
            after={
                'title': item.get('title', ''),
                'content': item['content'],
                'memory_type': item.get('memory_type', 'summary'),
                'importance': item.get('importance', 3),
                'summary': item.get('summary', ''),
                'source_type': 'ai_extract',
                'source_id': chapter_id,
            },
            source='ai_extract',
            status='pending',
        )
        db.session.add(change)
        changes.append(change)

    # Create "modify" changes for updates
    for item in result.get('updates', []):
        change = NovelMemoryChange(
            project_id=project_id,
            change_type='modify',
            after={
                'title': item.get('existing_title', ''),
                'content': item.get('new_content', ''),
                'memory_type': item.get('memory_type', 'summary'),
            },
            source='ai_extract',
            status='pending',
        )
        db.session.add(change)
        changes.append(change)

    db.session.commit()
    return changes


def _parse_memory_json(text):
    """Parse JSON from LLM response, handling markdown code blocks."""
    import json
    import re

    # Try markdown code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try raw JSON
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try brace-delimited
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    return None
```

- [ ] **Step 2: Commit**

```bash
git add server/services/memory/memory_writer.py
git commit -m "feat: add memory extraction from confirmed chapters"
```

---

### Task 17: 章节确认触发记忆抽取

**Files:**
- Modify: `server/routes/novels/chapters.py`

- [ ] **Step 1: 在 confirm_chapter 路由中触发记忆抽取**

修改 `server/routes/novels/chapters.py` 的 `confirm_chapter` 函数，在设置 `status = 'confirmed'` 并 commit 后，添加：

```python
    # Trigger memory extraction in background
    if chapter.content_markdown:
        try:
            from server.services.memory.memory_writer import extract_and_create_changes
            import threading
            threading.Thread(
                target=extract_and_create_changes,
                args=(project_id, chapter_id, chapter.content_markdown),
                daemon=True,
            ).start()
        except Exception:
            pass
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/chapters.py
git commit -m "feat: trigger memory extraction on chapter confirmation"
```

---

## P2：冲突检测与记忆压缩

### Task 18: conflict_detector 模块

**Files:**
- Create: `server/services/memory/conflict_detector.py`

- [ ] **Step 1: 创建 conflict_detector.py**

创建 `server/services/memory/conflict_detector.py`：

```python
"""Detect conflicts between new chapter goals and existing memories."""

from server.services.memory.retriever import retrieve_memories


def detect_conflicts(project_id, chapter_goal, existing_memories=None):
    """Check if chapter goal conflicts with existing memories.

    Args:
        project_id: Project ID.
        chapter_goal: Text describing the chapter's plot/conflict goals.
        existing_memories: Optional pre-fetched memories. If None, will retrieve.

    Returns:
        List of conflict dicts with 'description', 'severity', 'memory_id'.
    """
    if not chapter_goal:
        return []

    if existing_memories is None:
        existing_memories = retrieve_memories(project_id, chapter_goal, k=10)

    if not existing_memories:
        return []

    from server.services.novel import get_llm_provider

    memory_text = '\n'.join(
        f'- [{m["memory_type"]}] {m["content"][:200]}'
        for m in existing_memories[:5]
    )

    prompt = f"""你是小说设定一致性检查助手。请检查以下章节目标是否与已有设定冲突。

【已有设定】
{memory_text}

【章节目标】
{chapter_goal}

请以 JSON 格式输出冲突列表：
{{
  "conflicts": [
    {{
      "description": "冲突描述",
      "severity": "high|medium|low",
      "memory_type": "冲突涉及的设定类型"
    }}
  ]
}}

如果没有冲突，输出 {{"conflicts": []}}。
只输出 JSON，不要解释。"""

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        response = provider.complete(
            messages,
            model=default_model,
            system_prompt='你是设定一致性检查助手，只输出 JSON。',
            max_tokens=2048,
            timeout=30,
        )
    except Exception:
        return []

    from server.services.memory.memory_writer import _parse_memory_json
    result = _parse_memory_json(response)
    if not result:
        return []

    return result.get('conflicts', [])


def summarize_old_chapter(project_id, chapter_content, max_length=500):
    """Compress an old chapter's content into a summary for memory.

    Args:
        project_id: Project ID.
        chapter_content: Full chapter content.
        max_length: Target summary length.

    Returns:
        Summary string.
    """
    if not chapter_content or len(chapter_content) <= max_length:
        return chapter_content

    from server.services.novel import get_llm_provider

    prompt = f"""请将以下章节内容压缩为 {max_length} 字以内的摘要，保留关键剧情、人物行为、设定变更和伏笔。

【章节内容】
{chapter_content[:6000]}

只输出摘要，不要解释。"""

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        return provider.complete(
            messages,
            model=default_model,
            system_prompt='你是小说摘要助手。',
            max_tokens=2048,
            timeout=30,
        )
    except Exception:
        return chapter_content[:max_length]
```

- [ ] **Step 2: Commit**

```bash
git add server/services/memory/conflict_detector.py
git commit -m "feat: add conflict_detector for setting consistency checks"
```

---

### Task 19: 生成前冲突检测集成

**Files:**
- Modify: `server/services/memory/rag_chain.py`

- [ ] **Step 1: 在 rag_chain.py 的 generate_with_memory 中添加冲突检测**

在 `generate_with_memory()` 函数中，检索记忆后、组装 prompt 前，添加冲突检测：

```python
    # Check for conflicts (best effort)
    conflicts = []
    if memory_text and context.get('outline'):
        try:
            from server.services.memory.conflict_detector import detect_conflicts
            conflicts = detect_conflicts(project.id, context['outline'], memories)
        except Exception:
            pass

    # Add conflict warnings to prompt if found
    if conflicts:
        conflict_text = '\n'.join(
            f'- [{c.get("severity", "medium")}] {c["description"]}'
            for c in conflicts
        )
        prompt_sections.insert(0, f'【设定冲突警告】\n{conflict_text}\n请在生成时避免加剧这些冲突。')
```

- [ ] **Step 2: Commit**

```bash
git add server/services/memory/rag_chain.py
git commit -m "feat: integrate conflict detection into generation pipeline"
```

---

## P3：多步骤工作流（LangGraph）

### Task 20: LangGraph 依赖安装

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加 langgraph 依赖**

在 `pyproject.toml` 的 `dependencies` 中添加：

```toml
    "langgraph>=0.2.0",
```

- [ ] **Step 2: 安装并验证**

```bash
cd /Users/ckrey/video/script && uv sync
uv run python -c "import langgraph; print('OK:', langgraph.__version__)"
```

Expected: 导入成功。

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add langgraph for multi-step workflow"
```

---

### Task 21: LangGraph 工作流定义

**Files:**
- Create: `server/services/memory/workflow.py`

- [ ] **Step 1: 创建 workflow.py**

创建 `server/services/memory/workflow.py`：

```python
"""LangGraph multi-step chapter generation workflow."""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END


class ChapterState(TypedDict):
    """State for the chapter generation workflow."""
    project_id: int
    chapter_id: int
    user_instruction: str
    version_type: str
    model_key: str

    # Intermediate results
    context: dict
    memories: list
    conflicts: list
    draft: str
    review_result: dict
    revised_draft: str
    memory_changes: list
    version_id: int


def retrieve_memory_node(state: ChapterState) -> dict:
    """Node: Retrieve relevant memories."""
    from server.services.novel.context_builder import build_context
    from server.services.memory.retriever import retrieve_memories

    context = build_context(
        state['project_id'], state['chapter_id'],
        state.get('user_instruction', ''),
    )
    query = context.get('outline', '') + ' ' + state.get('user_instruction', '')
    memories = retrieve_memories(state['project_id'], query, k=10)

    return {'context': context, 'memories': memories}


def check_conflicts_node(state: ChapterState) -> dict:
    """Node: Check for setting conflicts."""
    from server.services.memory.conflict_detector import detect_conflicts

    conflicts = []
    if state.get('context', {}).get('outline'):
        try:
            conflicts = detect_conflicts(
                state['project_id'],
                state['context']['outline'],
                state.get('memories'),
            )
        except Exception:
            pass

    return {'conflicts': conflicts}


def draft_chapter_node(state: ChapterState) -> dict:
    """Node: Generate chapter draft with RAG."""
    from server.models.novel.project import NovelProject
    from server.models.novel.chapter import NovelChapter
    from server.services.novel.prompt_templates import build_chapter_system_prompt
    from server.services.memory.rag_chain import generate_with_memory

    project = NovelProject.query.get_or_404(state['project_id'])
    chapter = NovelChapter.query.get_or_404(state['chapter_id'])

    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=state.get('version_type', 'custom'),
        style_guide=project.style_guide,
    )

    draft = generate_with_memory(
        project=project,
        chapter=chapter,
        context=state.get('context', {}),
        system_prompt=system_prompt,
        user_instruction=state.get('user_instruction', ''),
        model_key=state.get('model_key'),
        version_type=state.get('version_type', 'custom'),
    )

    return {'draft': draft}


def review_draft_node(state: ChapterState) -> dict:
    """Node: Review draft for consistency."""
    from server.services.novel.consistency_reviewer import review_chapter

    try:
        result = review_chapter(state['project_id'], state['chapter_id'])
    except Exception:
        result = {'score': 0, 'issues': []}

    return {'review_result': result}


def revise_draft_node(state: ChapterState) -> dict:
    """Node: Revise draft based on review feedback."""
    review = state.get('review_result', {})
    issues = review.get('issues', [])
    high_issues = [i for i in issues if i.get('severity') == 'high']

    if not high_issues:
        return {'revised_draft': state.get('draft', '')}

    from server.services.novel import get_llm_provider

    issue_text = '\n'.join(f'- {i["description"]}' for i in high_issues[:5])
    prompt = f"""请根据以下审稿意见修改章节内容，只修改有问题的部分，保持其他内容不变。

【审稿意见】
{issue_text}

【原稿】
{state.get('draft', '')[:8000]}

请输出修改后的完整章节内容。只输出正文，不要解释。"""

    provider, default_model = get_llm_provider()
    messages = [{'role': 'user', 'content': prompt}]

    try:
        revised = provider.complete(
            messages,
            model=state.get('model_key') or default_model,
            system_prompt='你是小说修改助手。',
            max_tokens=8192,
            timeout=120,
        )
    except Exception:
        revised = state.get('draft', '')

    return {'revised_draft': revised}


def extract_memory_node(state: ChapterState) -> dict:
    """Node: Extract memory changes from final draft."""
    from server.services.memory.memory_writer import extract_and_create_changes

    content = state.get('revised_draft') or state.get('draft', '')
    if not content:
        return {'memory_changes': []}

    try:
        changes = extract_and_create_changes(
            state['project_id'], state['chapter_id'], content
        )
        return {'memory_changes': [c.id for c in changes]}
    except Exception:
        return {'memory_changes': []}


def persist_version_node(state: ChapterState) -> dict:
    """Node: Save the final version."""
    from server.models import db
    from server.models.novel.chapter import NovelChapterVersion
    import json

    content = state.get('revised_draft') or state.get('draft', '')
    if not content:
        return {}

    version = NovelChapterVersion(
        chapter_id=state['chapter_id'],
        version_type=state.get('version_type', 'custom'),
        title=f'{state.get("version_type", "custom")}版',
        content_markdown=content,
        model=state.get('model_key', 'workflow'),
        accepted=False,
    )
    db.session.add(version)
    db.session.commit()

    return {'version_id': version.id}


def build_chapter_workflow():
    """Build the LangGraph workflow for chapter generation.

    Flow: retrieve_memory -> check_conflicts -> draft -> review -> revise -> extract_memory -> persist
    """
    graph = StateGraph(ChapterState)

    graph.add_node('retrieve_memory', retrieve_memory_node)
    graph.add_node('check_conflicts', check_conflicts_node)
    graph.add_node('draft_chapter', draft_chapter_node)
    graph.add_node('review_draft', review_draft_node)
    graph.add_node('revise_draft', revise_draft_node)
    graph.add_node('extract_memory', extract_memory_node)
    graph.add_node('persist_version', persist_version_node)

    graph.set_entry_point('retrieve_memory')
    graph.add_edge('retrieve_memory', 'check_conflicts')
    graph.add_edge('check_conflicts', 'draft_chapter')
    graph.add_edge('draft_chapter', 'review_draft')
    graph.add_edge('review_draft', 'revise_draft')
    graph.add_edge('revise_draft', 'extract_memory')
    graph.add_edge('extract_memory', 'persist_version')
    graph.add_edge('persist_version', END)

    return graph.compile()


def run_chapter_workflow(project_id, chapter_id, user_instruction='',
                         version_type='custom', model_key=None):
    """Run the full chapter generation workflow.

    Returns:
        Final state dict with version_id and memory_changes.
    """
    workflow = build_chapter_workflow()

    initial_state = {
        'project_id': project_id,
        'chapter_id': chapter_id,
        'user_instruction': user_instruction,
        'version_type': version_type,
        'model_key': model_key or '',
        'context': {},
        'memories': [],
        'conflicts': [],
        'draft': '',
        'review_result': {},
        'revised_draft': '',
        'memory_changes': [],
        'version_id': 0,
    }

    result = workflow.invoke(initial_state)
    return result
```

- [ ] **Step 2: Commit**

```bash
git add server/services/memory/workflow.py
git commit -m "feat: add LangGraph multi-step chapter generation workflow"
```

---

### Task 22: 工作流集成到 generation_runner

**Files:**
- Modify: `server/services/novel/generation_runner.py`

- [ ] **Step 1: 在 generation_runner 中添加 workflow 任务类型**

修改 `server/services/novel/generation_runner.py`，在 `_run_generation()` 的 dispatch 逻辑中添加：

```python
    elif gen.generation_type == 'chapter_workflow':
        _run_chapter_workflow(gen, params)
```

并添加处理函数：

```python
def _run_chapter_workflow(gen, params):
    """Run the LangGraph chapter workflow."""
    from server.services.memory.workflow import run_chapter_workflow

    result = run_chapter_workflow(
        project_id=gen.project_id,
        chapter_id=gen.target_id,
        user_instruction=params.get('user_instruction', ''),
        version_type=params.get('version_type', 'custom'),
        model_key=params.get('model_key'),
    )

    gen.result = {
        'version_id': result.get('version_id'),
        'memory_changes': result.get('memory_changes', []),
        'conflicts': result.get('conflicts', []),
    }
```

- [ ] **Step 2: 添加前端 API 端点**

在 `web/src/api/index.js` 的 `novelsApi` 中添加：

```javascript
generateWorkflow: (pid, cid, params) => api.post(`/novels/${pid}/chapters/${cid}/generate-workflow`, params),
```

- [ ] **Step 3: Commit**

```bash
git add server/services/novel/generation_runner.py web/src/api/index.js
git commit -m "feat: integrate LangGraph workflow into generation runner"
```

---

## 最终验证

### Task 23: 全量测试与构建验证

- [ ] **Step 1: 运行全部后端测试**

```bash
uv run pytest server/tests/ -v
```

Expected: 所有测试通过（包括新增的记忆测试）。

- [ ] **Step 2: 运行前端构建**

```bash
cd /Users/ckrey/video/script/web && pnpm run build
```

Expected: 构建成功，无错误。

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete LangChain RAG memory system (P0-P3)"
```
