# Novel Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete backend for a novel continuation & knowledge graph module — 10 data models, 30+ API endpoints, 8 AI service files, async generation with SSE.

**Architecture:** Flask + SQLAlchemy (shared db instance), routes split into 6 blueprint files under `server/routes/novels/`, models split into 6 files under `server/models/novel/`, AI services under `server/services/novel/`. Async generation uses background threads + Redis (same pattern as `video_job.py`).

**Tech Stack:** Python 3.13, Flask, SQLAlchemy, Redis (optional), existing ModelProvider abstraction for LLM calls.

---

## File Map

### Models (Create)
- `server/models/novel/__init__.py` — Unified exports for all novel models
- `server/models/novel/project.py` — NovelProject
- `server/models/novel/outline.py` — NovelOutlineNode
- `server/models/novel/chapter.py` — NovelChapter, NovelChapterVersion
- `server/models/novel/entity.py` — NovelEntity, NovelRelation
- `server/models/novel/event.py` — NovelEvent, NovelEventRelation
- `server/models/novel/graph_change.py` — NovelGraphChange, NovelGeneration

### Routes (Create)
- `server/routes/novels/__init__.py` — Blueprint registration
- `server/routes/novels/projects.py` — Project CRUD
- `server/routes/novels/outline.py` — Outline management
- `server/routes/novels/chapters.py` — Chapter + version management
- `server/routes/novels/entities.py` — Entity + relation CRUD
- `server/routes/novels/events.py` — Event + event-relation CRUD
- `server/routes/novels/graph.py` — Graph queries, AI extract, review, generation status

### Services (Create)
- `server/services/novel/__init__.py` — Empty
- `server/services/novel/prompt_templates.py` — Genre-specific prompt templates
- `server/services/novel/context_builder.py` — Context assembly with budget control
- `server/services/novel/chapter_generator.py` — Single chapter generation
- `server/services/novel/version_generator.py` — Multi-version generation
- `server/services/novel/blueprint_generator.py` — Full-book blueprint from premise
- `server/services/novel/graph_extractor.py` — AI graph extraction
- `server/services/novel/consistency_reviewer.py` — Consistency checking
- `server/services/novel/summarizer.py` — Chapter summary generation
- `server/services/novel/generation_runner.py` — Async generation framework (thread + SSE + Redis)

### Modify (Existing)
- `server/models/__init__.py` — Add novel model imports
- `server/app.py` — Register novels blueprint

### Tests (Create)
- `server/tests/test_novel_project.py`
- `server/tests/test_novel_outline.py`
- `server/tests/test_novel_chapter.py`
- `server/tests/test_novel_entity.py`
- `server/tests/test_novel_event.py`
- `server/tests/test_novel_graph.py`
- `server/tests/test_novel_context_builder.py`
- `server/tests/test_novel_prompt_templates.py`

---

## Task 1: Data Models — NovelProject

**Files:**
- Create: `server/models/novel/__init__.py`
- Create: `server/models/novel/project.py`
- Modify: `server/models/__init__.py`

- [ ] **Step 1: Create the novel models package `__init__.py`**

```python
# server/models/novel/__init__.py
```

Create empty file (will populate after all models exist).

- [ ] **Step 2: Create NovelProject model**

```python
# server/models/novel/project.py
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


class NovelProject(db.Model):
    __tablename__ = 'novel_projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名小说')
    genre = db.Column(db.String(50), nullable=False, default='玄幻')
    premise = db.Column(db.Text, nullable=True)
    target_total_words = db.Column(db.Integer, nullable=False, default=300000)
    target_chapters = db.Column(db.Integer, nullable=False, default=100)
    words_per_chapter = db.Column(db.Integer, nullable=False, default=3000)
    volume_count = db.Column(db.Integer, nullable=False, default=1)
    style_guide_json = db.Column(db.Text, nullable=True)
    settings_json = db.Column(db.Text, nullable=True)
    knowledge_update_mode = db.Column(db.String(20), nullable=False, default='ai_confirm')
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def style_guide(self):
        return _json_loads(self.style_guide_json, {})

    @style_guide.setter
    def style_guide(self, value):
        self.style_guide_json = _json_dumps(value)

    @property
    def settings(self):
        return _json_loads(self.settings_json, {})

    @settings.setter
    def settings(self, value):
        self.settings_json = _json_dumps(value)

    def to_dict(self, include_stats=False):
        data = {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'premise': self.premise,
            'target_total_words': self.target_total_words,
            'target_chapters': self.target_chapters,
            'words_per_chapter': self.words_per_chapter,
            'volume_count': self.volume_count,
            'style_guide': self.style_guide,
            'settings': self.settings,
            'knowledge_update_mode': self.knowledge_update_mode,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_stats:
            from server.models.novel.chapter import NovelChapter
            chapters = NovelChapter.query.filter_by(project_id=self.id).all()
            data['stats'] = {
                'chapter_count': len(chapters),
                'total_words': sum(c.word_count for c in chapters),
                'confirmed_chapters': sum(1 for c in chapters if c.status == 'confirmed'),
            }
        return data
```

- [ ] **Step 3: Update `server/models/__init__.py` to import NovelProject**

Add to imports:
```python
from server.models.novel.project import NovelProject
```

Add `'NovelProject'` to `__all__`.

- [ ] **Step 4: Commit**

```bash
git add server/models/novel/ server/models/__init__.py
git commit -m "feat(novel): add NovelProject model"
```

---

## Task 2: Data Models — NovelOutlineNode

**Files:**
- Create: `server/models/novel/outline.py`
- Modify: `server/models/novel/__init__.py`
- Modify: `server/models/__init__.py`

- [ ] **Step 1: Create NovelOutlineNode model**

```python
# server/models/novel/outline.py
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


class NovelOutlineNode(db.Model):
    __tablename__ = 'novel_outline_nodes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('novel_outline_nodes.id'), nullable=True)
    node_type = db.Column(db.String(20), nullable=False, default='chapter')
    title = db.Column(db.String(200), nullable=False, default='未命名节点')
    summary = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    target_words = db.Column(db.Integer, nullable=True)
    plot_goal = db.Column(db.Text, nullable=True)
    conflict_goal = db.Column(db.Text, nullable=True)
    characters_json = db.Column(db.Text, nullable=True)
    events_json = db.Column(db.Text, nullable=True)
    foreshadowing_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planning')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    children = db.relationship(
        'NovelOutlineNode',
        backref=db.backref('parent', remote_side='NovelOutlineNode.id'),
        lazy=True,
        cascade='all, delete-orphan',
        order_by='NovelOutlineNode.order_index',
    )

    @property
    def characters(self):
        return _json_loads(self.characters_json, [])

    @characters.setter
    def characters(self, value):
        self.characters_json = _json_dumps(value)

    @property
    def events(self):
        return _json_loads(self.events_json, [])

    @events.setter
    def events(self, value):
        self.events_json = _json_dumps(value)

    @property
    def foreshadowing(self):
        return _json_loads(self.foreshadowing_json, [])

    @foreshadowing.setter
    def foreshadowing(self, value):
        self.foreshadowing_json = _json_dumps(value)

    def to_dict(self, include_children=False):
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'node_type': self.node_type,
            'title': self.title,
            'summary': self.summary,
            'order_index': self.order_index,
            'target_words': self.target_words,
            'plot_goal': self.plot_goal,
            'conflict_goal': self.conflict_goal,
            'characters': self.characters,
            'events': self.events,
            'foreshadowing': self.foreshadowing,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            data['children'] = [c.to_dict(include_children=True) for c in self.children]
        return data

    def to_tree_dict(self):
        """Return tree structure with nested children."""
        data = self.to_dict()
        data['children'] = [c.to_tree_dict() for c in self.children]
        return data
```

- [ ] **Step 2: Update model exports**

Add to `server/models/novel/__init__.py`:
```python
from server.models.novel.outline import NovelOutlineNode
```

Add to `server/models/__init__.py` imports and `__all__`.

- [ ] **Step 3: Commit**

```bash
git add server/models/novel/outline.py server/models/novel/__init__.py server/models/__init__.py
git commit -m "feat(novel): add NovelOutlineNode model"
```

---

## Task 3: Data Models — Chapter & Version

**Files:**
- Create: `server/models/novel/chapter.py`
- Modify: `server/models/novel/__init__.py`
- Modify: `server/models/__init__.py`

- [ ] **Step 1: Create NovelChapter and NovelChapterVersion models**

```python
# server/models/novel/chapter.py
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


class NovelChapter(db.Model):
    __tablename__ = 'novel_chapters'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    outline_node_id = db.Column(db.Integer, db.ForeignKey('novel_outline_nodes.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False, default='未命名章节')
    content_markdown = db.Column(db.Text, nullable=False, default='')
    summary = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    target_words = db.Column(db.Integer, nullable=True)
    word_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    versions = db.relationship(
        'NovelChapterVersion',
        backref='chapter',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='NovelChapterVersion.created_at.desc()',
    )

    def to_dict(self, include_content=True, include_versions=False):
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'outline_node_id': self.outline_node_id,
            'title': self.title,
            'summary': self.summary,
            'order_index': self.order_index,
            'target_words': self.target_words,
            'word_count': self.word_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data['content_markdown'] = self.content_markdown
        if include_versions:
            data['versions'] = [v.to_dict() for v in self.versions]
        return data


class NovelChapterVersion(db.Model):
    __tablename__ = 'novel_chapter_versions'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=False)
    version_type = db.Column(db.String(30), nullable=False, default='custom')
    title = db.Column(db.String(200), nullable=True)
    content_markdown = db.Column(db.Text, nullable=False, default='')
    prompt_json = db.Column(db.Text, nullable=True)
    context_snapshot_json = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_now)

    @property
    def prompt(self):
        return _json_loads(self.prompt_json, {})

    @prompt.setter
    def prompt(self, value):
        self.prompt_json = _json_dumps(value)

    @property
    def context_snapshot(self):
        return _json_loads(self.context_snapshot_json, {})

    @context_snapshot.setter
    def context_snapshot(self, value):
        self.context_snapshot_json = _json_dumps(value)

    def to_dict(self):
        return {
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

- [ ] **Step 2: Update model exports**

Add to `server/models/novel/__init__.py` and `server/models/__init__.py`.

- [ ] **Step 3: Commit**

```bash
git add server/models/novel/chapter.py server/models/novel/__init__.py server/models/__init__.py
git commit -m "feat(novel): add NovelChapter and NovelChapterVersion models"
```

---

## Task 4: Data Models — Entity & Relation

**Files:**
- Create: `server/models/novel/entity.py`
- Modify: `server/models/novel/__init__.py`
- Modify: `server/models/__init__.py`

- [ ] **Step 1: Create NovelEntity and NovelRelation models**

```python
# server/models/novel/entity.py
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


class NovelEntity(db.Model):
    __tablename__ = 'novel_entities'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False, default='character')
    name = db.Column(db.String(100), nullable=False)
    aliases_json = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    attributes_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=5)
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def aliases(self):
        return _json_loads(self.aliases_json, [])

    @aliases.setter
    def aliases(self, value):
        self.aliases_json = _json_dumps(value)

    @property
    def attributes(self):
        return _json_loads(self.attributes_json, {})

    @attributes.setter
    def attributes(self, value):
        self.attributes_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'entity_type': self.entity_type,
            'name': self.name,
            'aliases': self.aliases,
            'summary': self.summary,
            'attributes': self.attributes,
            'importance': self.importance,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelRelation(db.Model):
    __tablename__ = 'novel_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    target_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    relation_type = db.Column(db.String(30), nullable=False)
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    strength = db.Column(db.Float, nullable=False, default=0.5)
    status = db.Column(db.String(20), nullable=False, default='active')
    evidence_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    source_entity = db.relationship('NovelEntity', foreign_keys=[source_entity_id], backref='outgoing_relations')
    target_entity = db.relationship('NovelEntity', foreign_keys=[target_entity_id], backref='incoming_relations')

    @property
    def evidence(self):
        return _json_loads(self.evidence_json, [])

    @evidence.setter
    def evidence(self, value):
        self.evidence_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_entity_id': self.source_entity_id,
            'target_entity_id': self.target_entity_id,
            'relation_type': self.relation_type,
            'label': self.label,
            'description': self.description,
            'strength': self.strength,
            'status': self.status,
            'evidence': self.evidence,
            'source_name': self.source_entity.name if self.source_entity else None,
            'target_name': self.target_entity.name if self.target_entity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 2: Update model exports**

- [ ] **Step 3: Commit**

```bash
git add server/models/novel/entity.py server/models/novel/__init__.py server/models/__init__.py
git commit -m "feat(novel): add NovelEntity and NovelRelation models"
```

---

## Task 5: Data Models — Event & EventRelation

**Files:**
- Create: `server/models/novel/event.py`
- Modify: `server/models/novel/__init__.py`
- Modify: `server/models/__init__.py`

- [ ] **Step 1: Create NovelEvent and NovelEventRelation models**

```python
# server/models/novel/event.py
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


class NovelEvent(db.Model):
    __tablename__ = 'novel_events'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(20), nullable=False, default='event')
    timeline_order = db.Column(db.Float, nullable=False, default=0)
    participants_json = db.Column(db.Text, nullable=True)
    location_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=True)
    effects_json = db.Column(db.Text, nullable=True)
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    location_entity = db.relationship('NovelEntity', foreign_keys=[location_entity_id])

    @property
    def participants(self):
        return _json_loads(self.participants_json, [])

    @participants.setter
    def participants(self, value):
        self.participants_json = _json_dumps(value)

    @property
    def effects(self):
        return _json_loads(self.effects_json, [])

    @effects.setter
    def effects(self, value):
        self.effects_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'chapter_id': self.chapter_id,
            'title': self.title,
            'summary': self.summary,
            'event_type': self.event_type,
            'timeline_order': self.timeline_order,
            'participants': self.participants,
            'location_entity_id': self.location_entity_id,
            'location_name': self.location_entity.name if self.location_entity else None,
            'effects': self.effects,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelEventRelation(db.Model):
    __tablename__ = 'novel_event_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    target_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    relation_type = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    source_event = db.relationship('NovelEvent', foreign_keys=[source_event_id], backref='outgoing_event_relations')
    target_event = db.relationship('NovelEvent', foreign_keys=[target_event_id], backref='incoming_event_relations')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_event_id': self.source_event_id,
            'target_event_id': self.target_event_id,
            'relation_type': self.relation_type,
            'label': self.label,
            'description': self.description,
            'confidence': self.confidence,
            'source_title': self.source_event.title if self.source_event else None,
            'target_title': self.target_event.title if self.target_event else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 2: Update model exports**

- [ ] **Step 3: Commit**

```bash
git add server/models/novel/event.py server/models/novel/__init__.py server/models/__init__.py
git commit -m "feat(novel): add NovelEvent and NovelEventRelation models"
```

---

## Task 6: Data Models — GraphChange & Generation

**Files:**
- Create: `server/models/novel/graph_change.py`
- Update: `server/models/novel/__init__.py` — Finalize with all exports
- Update: `server/models/__init__.py` — Finalize with all exports

- [ ] **Step 1: Create NovelGraphChange and NovelGeneration models**

```python
# server/models/novel/graph_change.py
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


class NovelGraphChange(db.Model):
    __tablename__ = 'novel_graph_changes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    change_type = db.Column(db.String(10), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(20), nullable=False, default='manual')
    confidence = db.Column(db.Float, nullable=True)
    accepted = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)

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
            'chapter_id': self.chapter_id,
            'change_type': self.change_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'before': self.before,
            'after': self.after,
            'source': self.source,
            'confidence': self.confidence,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class NovelGeneration(db.Model):
    __tablename__ = 'novel_generations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    generation_type = db.Column(db.String(30), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    progress = db.Column(db.Integer, nullable=False, default=0)
    result_json = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    completed_at = db.Column(db.DateTime, nullable=True)

    @property
    def result(self):
        return _json_loads(self.result_json, None)

    @result.setter
    def result(self, value):
        self.result_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'generation_type': self.generation_type,
            'target_id': self.target_id,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'model': self.model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
```

- [ ] **Step 2: Finalize `server/models/novel/__init__.py`**

```python
# server/models/novel/__init__.py
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.graph_change import NovelGraphChange, NovelGeneration

__all__ = [
    'NovelProject',
    'NovelOutlineNode',
    'NovelChapter', 'NovelChapterVersion',
    'NovelEntity', 'NovelRelation',
    'NovelEvent', 'NovelEventRelation',
    'NovelGraphChange', 'NovelGeneration',
]
```

- [ ] **Step 3: Finalize `server/models/__init__.py`**

Add all novel model imports and update `__all__`.

- [ ] **Step 4: Commit**

```bash
git add server/models/novel/ server/models/__init__.py
git commit -m "feat(novel): add NovelGraphChange and NovelGeneration models, finalize model exports"
```

---

## Task 7: Project CRUD Routes

**Files:**
- Create: `server/routes/novels/__init__.py`
- Create: `server/routes/novels/projects.py`

- [ ] **Step 1: Create the novels routes package `__init__.py`**

```python
# server/routes/novels/__init__.py
from flask import Blueprint

novels_bp = Blueprint('novels', __name__)

from server.routes.novels import projects
from server.routes.novels import outline
from server.routes.novels import chapters
from server.routes.novels import entities
from server.routes.novels import events
from server.routes.novels import graph
```

- [ ] **Step 2: Create project CRUD routes**

```python
# server/routes/novels/projects.py
from flask import request, jsonify
from server.models import db
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels', methods=['GET'])
def list_projects():
    status = request.args.get('status')
    query = NovelProject.query
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(NovelProject.updated_at.desc())
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [p.to_dict(include_stats=True) for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })


@novels_bp.route('/api/novels', methods=['POST'])
def create_project():
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    project = NovelProject(
        title=data['title'],
        genre=data.get('genre', '玄幻'),
        premise=data.get('premise'),
        target_total_words=data.get('target_total_words', 300000),
        target_chapters=data.get('target_chapters', 100),
        words_per_chapter=data.get('words_per_chapter', 3000),
        volume_count=data.get('volume_count', 1),
        knowledge_update_mode=data.get('knowledge_update_mode', 'ai_confirm'),
    )
    if 'style_guide' in data:
        project.style_guide = data['style_guide']
    if 'settings' in data:
        project.settings = data['settings']

    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    return jsonify(project.to_dict(include_stats=True))


@novels_bp.route('/api/novels/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    for field in ('title', 'genre', 'premise', 'target_total_words', 'target_chapters',
                  'words_per_chapter', 'volume_count', 'knowledge_update_mode', 'status'):
        if field in data:
            setattr(project, field, data[field])
    if 'style_guide' in data:
        project.style_guide = data['style_guide']
    if 'settings' in data:
        project.settings = data['settings']

    db.session.commit()
    return jsonify(project.to_dict())


@novels_bp.route('/api/novels/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    # Cascade delete: remove all related data
    from server.models.novel.chapter import NovelChapter, NovelChapterVersion
    from server.models.novel.outline import NovelOutlineNode
    from server.models.novel.entity import NovelEntity, NovelRelation
    from server.models.novel.event import NovelEvent, NovelEventRelation
    from server.models.novel.graph_change import NovelGraphChange, NovelGeneration

    chapter_ids = [c.id for c in NovelChapter.query.filter_by(project_id=project_id).all()]
    if chapter_ids:
        NovelChapterVersion.query.filter(NovelChapterVersion.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
    NovelChapter.query.filter_by(project_id=project_id).delete()
    NovelOutlineNode.query.filter_by(project_id=project_id).delete()
    NovelRelation.query.filter_by(project_id=project_id).delete()
    NovelEntity.query.filter_by(project_id=project_id).delete()
    NovelEventRelation.query.filter_by(project_id=project_id).delete()
    NovelEvent.query.filter_by(project_id=project_id).delete()
    NovelGraphChange.query.filter_by(project_id=project_id).delete()
    NovelGeneration.query.filter_by(project_id=project_id).delete()

    db.session.delete(project)
    db.session.commit()
    return '', 204
```

- [ ] **Step 3: Commit**

```bash
git add server/routes/novels/
git commit -m "feat(novel): add project CRUD routes"
```

---

## Task 8: Outline Routes

**Files:**
- Create: `server/routes/novels/outline.py`

- [ ] **Step 1: Create outline routes**

```python
# server/routes/novels/outline.py
from flask import request, jsonify
from server.models import db
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/outline', methods=['GET'])
def get_outline(project_id):
    NovelProject.query.get_or_404(project_id)
    roots = NovelOutlineNode.query.filter_by(
        project_id=project_id, parent_id=None
    ).order_by(NovelOutlineNode.order_index).all()
    return jsonify([r.to_tree_dict() for r in roots])


@novels_bp.route('/api/novels/<int:project_id>/outline', methods=['POST'])
def create_outline_node(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    # Validate parent belongs to same project
    parent_id = data.get('parent_id')
    if parent_id:
        parent = NovelOutlineNode.query.get_or_404(parent_id)
        if parent.project_id != project_id:
            return jsonify({'error': '父节点不属于该项目'}), 400

    # Auto-calculate order_index
    max_order = db.session.query(db.func.max(NovelOutlineNode.order_index)).filter_by(
        project_id=project_id, parent_id=parent_id
    ).scalar() or 0

    node = NovelOutlineNode(
        project_id=project_id,
        parent_id=parent_id,
        node_type=data.get('node_type', 'chapter'),
        title=data['title'],
        summary=data.get('summary'),
        order_index=data.get('order_index', max_order + 1),
        target_words=data.get('target_words'),
        plot_goal=data.get('plot_goal'),
        conflict_goal=data.get('conflict_goal'),
        status=data.get('status', 'planning'),
    )
    if 'characters' in data:
        node.characters = data['characters']
    if 'events' in data:
        node.events = data['events']
    if 'foreshadowing' in data:
        node.foreshadowing = data['foreshadowing']

    db.session.add(node)
    db.session.commit()
    return jsonify(node.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/outline/<int:node_id>', methods=['PUT'])
def update_outline_node(project_id, node_id):
    node = NovelOutlineNode.query.get_or_404(node_id)
    if node.project_id != project_id:
        return jsonify({'error': '节点不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('title', 'summary', 'order_index', 'target_words', 'plot_goal',
                  'conflict_goal', 'node_type', 'status'):
        if field in data:
            setattr(node, field, data[field])
    if 'characters' in data:
        node.characters = data['characters']
    if 'events' in data:
        node.events = data['events']
    if 'foreshadowing' in data:
        node.foreshadowing = data['foreshadowing']

    db.session.commit()
    return jsonify(node.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/outline/<int:node_id>', methods=['DELETE'])
def delete_outline_node(project_id, node_id):
    node = NovelOutlineNode.query.get_or_404(node_id)
    if node.project_id != project_id:
        return jsonify({'error': '节点不属于该项目'}), 400

    db.session.delete(node)
    db.session.commit()
    return '', 204
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/outline.py
git commit -m "feat(novel): add outline CRUD routes"
```

---

## Task 9: Chapter & Version Routes

**Files:**
- Create: `server/routes/novels/chapters.py`

- [ ] **Step 1: Create chapter routes**

```python
# server/routes/novels/chapters.py
from flask import request, jsonify
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/chapters', methods=['GET'])
def list_chapters(project_id):
    NovelProject.query.get_or_404(project_id)
    chapters = NovelChapter.query.filter_by(
        project_id=project_id
    ).order_by(NovelChapter.order_index).all()
    return jsonify([c.to_dict(include_content=False) for c in chapters])


@novels_bp.route('/api/novels/<int:project_id>/chapters', methods=['POST'])
def create_chapter(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    max_order = db.session.query(db.func.max(NovelChapter.order_index)).filter_by(
        project_id=project_id
    ).scalar() or 0

    content = data.get('content_markdown', '')
    chapter = NovelChapter(
        project_id=project_id,
        outline_node_id=data.get('outline_node_id'),
        title=data.get('title', '未命名章节'),
        content_markdown=content,
        order_index=data.get('order_index', max_order + 1),
        target_words=data.get('target_words'),
        word_count=len(content.replace(' ', '').replace('\n', '')),
        status=data.get('status', 'draft'),
    )
    db.session.add(chapter)
    db.session.commit()
    return jsonify(chapter.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    return jsonify(chapter.to_dict(include_versions=True))


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>', methods=['PUT'])
def update_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    if 'title' in data:
        chapter.title = data['title']
    if 'content_markdown' in data:
        chapter.content_markdown = data['content_markdown']
        chapter.word_count = len(data['content_markdown'].replace(' ', '').replace('\n', ''))
    if 'order_index' in data:
        chapter.order_index = data['order_index']
    if 'target_words' in data:
        chapter.target_words = data['target_words']
    if 'outline_node_id' in data:
        chapter.outline_node_id = data['outline_node_id']

    db.session.commit()
    return jsonify(chapter.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/confirm', methods=['POST'])
def confirm_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    chapter.status = 'confirmed'
    db.session.commit()
    # Auto-generate summary in background
    from server.services.novel.summarizer import generate_summary
    try:
        generate_summary(chapter_id)
    except Exception:
        pass  # Summary generation failure should not block confirmation
    return jsonify(chapter.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/generate-versions', methods=['POST'])
def generate_versions(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='chapter_version',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions', methods=['GET'])
def list_versions(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    versions = NovelChapterVersion.query.filter_by(
        chapter_id=chapter_id
    ).order_by(NovelChapterVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions/<int:version_id>/accept', methods=['POST'])
def accept_version(project_id, chapter_id, version_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    version = NovelChapterVersion.query.get_or_404(version_id)
    if version.chapter_id != chapter_id:
        return jsonify({'error': '版本不属于该章节'}), 400

    # Unaccept all other versions
    NovelChapterVersion.query.filter_by(chapter_id=chapter_id).update({'accepted': False})
    version.accepted = True

    # Copy version content to chapter
    chapter.content_markdown = version.content_markdown
    chapter.word_count = len(version.content_markdown.replace(' ', '').replace('\n', ''))

    db.session.commit()
    return jsonify(chapter.to_dict(include_versions=True))


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions/<int:version_id>', methods=['DELETE'])
def delete_version(project_id, chapter_id, version_id):
    version = NovelChapterVersion.query.get_or_404(version_id)
    if version.chapter_id != chapter_id:
        return jsonify({'error': '版本不属于该章节'}), 400
    db.session.delete(version)
    db.session.commit()
    return '', 204
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/chapters.py
git commit -m "feat(novel): add chapter and version routes"
```

---

## Task 10: Entity & Relation Routes

**Files:**
- Create: `server/routes/novels/entities.py`

- [ ] **Step 1: Create entity routes**

```python
# server/routes/novels/entities.py
from flask import request, jsonify
from server.models import db
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/entities', methods=['GET'])
def list_entities(project_id):
    NovelProject.query.get_or_404(project_id)
    entity_type = request.args.get('type')
    query = NovelEntity.query.filter_by(project_id=project_id)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    query = query.order_by(NovelEntity.importance.desc())
    entities = query.all()
    return jsonify([e.to_dict() for e in entities])


@novels_bp.route('/api/novels/<int:project_id>/entities', methods=['POST'])
def create_entity(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': '名称不能为空'}), 400

    entity = NovelEntity(
        project_id=project_id,
        entity_type=data.get('entity_type', 'character'),
        name=data['name'],
        summary=data.get('summary'),
        importance=data.get('importance', 5),
        node_x=data.get('node_x', 0),
        node_y=data.get('node_y', 0),
    )
    if 'aliases' in data:
        entity.aliases = data['aliases']
    if 'attributes' in data:
        entity.attributes = data['attributes']

    db.session.add(entity)
    db.session.commit()
    return jsonify(entity.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['GET'])
def get_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400
    return jsonify(entity.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['PUT'])
def update_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('entity_type', 'name', 'summary', 'importance', 'node_x', 'node_y'):
        if field in data:
            setattr(entity, field, data[field])
    if 'aliases' in data:
        entity.aliases = data['aliases']
    if 'attributes' in data:
        entity.attributes = data['attributes']

    db.session.commit()
    return jsonify(entity.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['DELETE'])
def delete_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400

    # Delete related relations
    NovelRelation.query.filter(
        (NovelRelation.source_entity_id == entity_id) |
        (NovelRelation.target_entity_id == entity_id)
    ).delete()

    db.session.delete(entity)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/relations', methods=['GET'])
def list_relations(project_id):
    NovelProject.query.get_or_404(project_id)
    relations = NovelRelation.query.filter_by(project_id=project_id).all()
    return jsonify([r.to_dict() for r in relations])


@novels_bp.route('/api/novels/<int:project_id>/relations', methods=['POST'])
def create_relation(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('source_entity_id') or not data.get('target_entity_id'):
        return jsonify({'error': '源实体和目标实体不能为空'}), 400
    if not data.get('relation_type'):
        return jsonify({'error': '关系类型不能为空'}), 400

    relation = NovelRelation(
        project_id=project_id,
        source_entity_id=data['source_entity_id'],
        target_entity_id=data['target_entity_id'],
        relation_type=data['relation_type'],
        label=data.get('label'),
        description=data.get('description'),
        strength=data.get('strength', 0.5),
        status=data.get('status', 'active'),
    )
    if 'evidence' in data:
        relation.evidence = data['evidence']

    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/relations/<int:relation_id>', methods=['PUT'])
def update_relation(project_id, relation_id):
    relation = NovelRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('relation_type', 'label', 'description', 'strength', 'status',
                  'source_entity_id', 'target_entity_id'):
        if field in data:
            setattr(relation, field, data[field])
    if 'evidence' in data:
        relation.evidence = data['evidence']

    db.session.commit()
    return jsonify(relation.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/relations/<int:relation_id>', methods=['DELETE'])
def delete_relation(project_id, relation_id):
    relation = NovelRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400
    db.session.delete(relation)
    db.session.commit()
    return '', 204
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/entities.py
git commit -m "feat(novel): add entity and relation CRUD routes"
```

---

## Task 11: Event & EventRelation Routes

**Files:**
- Create: `server/routes/novels/events.py`

- [ ] **Step 1: Create event routes**

```python
# server/routes/novels/events.py
from flask import request, jsonify
from server.models import db
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/events', methods=['GET'])
def list_events(project_id):
    NovelProject.query.get_or_404(project_id)
    events = NovelEvent.query.filter_by(
        project_id=project_id
    ).order_by(NovelEvent.timeline_order).all()
    return jsonify([e.to_dict() for e in events])


@novels_bp.route('/api/novels/<int:project_id>/events', methods=['POST'])
def create_event(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    event = NovelEvent(
        project_id=project_id,
        chapter_id=data.get('chapter_id'),
        title=data['title'],
        summary=data.get('summary'),
        event_type=data.get('event_type', 'event'),
        timeline_order=data.get('timeline_order', 0),
        location_entity_id=data.get('location_entity_id'),
        node_x=data.get('node_x', 0),
        node_y=data.get('node_y', 0),
    )
    if 'participants' in data:
        event.participants = data['participants']
    if 'effects' in data:
        event.effects = data['effects']

    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['GET'])
def get_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400
    return jsonify(event.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['PUT'])
def update_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('title', 'summary', 'event_type', 'timeline_order',
                  'chapter_id', 'location_entity_id', 'node_x', 'node_y'):
        if field in data:
            setattr(event, field, data[field])
    if 'participants' in data:
        event.participants = data['participants']
    if 'effects' in data:
        event.effects = data['effects']

    db.session.commit()
    return jsonify(event.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['DELETE'])
def delete_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400

    # Delete related event relations
    NovelEventRelation.query.filter(
        (NovelEventRelation.source_event_id == event_id) |
        (NovelEventRelation.target_event_id == event_id)
    ).delete()

    db.session.delete(event)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/event-relations', methods=['POST'])
def create_event_relation(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('source_event_id') or not data.get('target_event_id'):
        return jsonify({'error': '源事件和目标事件不能为空'}), 400
    if not data.get('relation_type'):
        return jsonify({'error': '关系类型不能为空'}), 400

    relation = NovelEventRelation(
        project_id=project_id,
        source_event_id=data['source_event_id'],
        target_event_id=data['target_event_id'],
        relation_type=data['relation_type'],
        label=data.get('label'),
        description=data.get('description'),
        confidence=data.get('confidence', 1.0),
    )
    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/event-relations/<int:relation_id>', methods=['PUT'])
def update_event_relation(project_id, relation_id):
    relation = NovelEventRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('relation_type', 'label', 'description', 'confidence'):
        if field in data:
            setattr(relation, field, data[field])

    db.session.commit()
    return jsonify(relation.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/event-relations/<int:relation_id>', methods=['DELETE'])
def delete_event_relation(project_id, relation_id):
    relation = NovelEventRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400
    db.session.delete(relation)
    db.session.commit()
    return '', 204
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/events.py
git commit -m "feat(novel): add event and event-relation CRUD routes"
```

---

## Task 12: Graph Routes

**Files:**
- Create: `server/routes/novels/graph.py`

- [ ] **Step 1: Create graph routes**

```python
# server/routes/novels/graph.py
import json
from flask import request, jsonify, Response
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.chapter import NovelChapter
from server.models.novel.graph_change import NovelGraphChange, NovelGeneration
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/graph/characters', methods=['GET'])
def get_character_graph(project_id):
    NovelProject.query.get_or_404(project_id)
    entities = NovelEntity.query.filter_by(project_id=project_id).all()
    relations = NovelRelation.query.filter_by(project_id=project_id).all()
    return jsonify({
        'nodes': [{
            'id': e.id,
            'type': e.entity_type,
            'name': e.name,
            'importance': e.importance,
            'x': e.node_x,
            'y': e.node_y,
            'summary': e.summary,
        } for e in entities],
        'edges': [{
            'id': r.id,
            'source': r.source_entity_id,
            'target': r.target_entity_id,
            'type': r.relation_type,
            'label': r.label,
            'strength': r.strength,
            'status': r.status,
        } for r in relations],
    })


@novels_bp.route('/api/novels/<int:project_id>/graph/events', methods=['GET'])
def get_event_graph(project_id):
    NovelProject.query.get_or_404(project_id)
    events = NovelEvent.query.filter_by(project_id=project_id).all()
    relations = NovelEventRelation.query.filter_by(project_id=project_id).all()
    return jsonify({
        'nodes': [{
            'id': e.id,
            'type': e.event_type,
            'title': e.title,
            'summary': e.summary,
            'chapter_id': e.chapter_id,
            'timeline_order': e.timeline_order,
            'x': e.node_x,
            'y': e.node_y,
        } for e in events],
        'edges': [{
            'id': r.id,
            'source': r.source_event_id,
            'target': r.target_event_id,
            'type': r.relation_type,
            'label': r.label,
            'confidence': r.confidence,
        } for r in relations],
    })


@novels_bp.route('/api/novels/<int:project_id>/graph/layout', methods=['PUT'])
def update_graph_layout(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    entity_positions = data.get('entity_positions', [])
    for pos in entity_positions:
        entity = NovelEntity.query.get(pos.get('id'))
        if entity and entity.project_id == project_id:
            entity.node_x = pos.get('x', entity.node_x)
            entity.node_y = pos.get('y', entity.node_y)

    event_positions = data.get('event_positions', [])
    for pos in event_positions:
        event = NovelEvent.query.get(pos.get('id'))
        if event and event.project_id == project_id:
            event.node_x = pos.get('x', event.node_x)
            event.node_y = pos.get('y', event.node_y)

    db.session.commit()
    return jsonify({'ok': True})


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/extract-graph', methods=['POST'])
def extract_graph(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='extract',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/<int:project_id>/graph-changes/<int:change_id>/accept', methods=['POST'])
def accept_graph_change(project_id, change_id):
    change = NovelGraphChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    change.accepted = True
    _apply_graph_change(change)
    db.session.commit()
    return jsonify(change.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/graph-changes/<int:change_id>/reject', methods=['POST'])
def reject_graph_change(project_id, change_id):
    change = NovelGraphChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    change.accepted = False
    db.session.commit()
    return jsonify(change.to_dict())


def _apply_graph_change(change):
    """Apply an accepted graph change to the actual data."""
    after = change.after
    if not after:
        return

    if change.change_type == 'add':
        if change.target_type == 'entity':
            entity = NovelEntity(
                project_id=change.project_id,
                entity_type=after.get('entity_type', 'character'),
                name=after.get('name', ''),
                summary=after.get('summary'),
                importance=after.get('importance', 5),
            )
            if 'aliases' in after:
                entity.aliases = after['aliases']
            if 'attributes' in after:
                entity.attributes = after['attributes']
            db.session.add(entity)
            db.session.flush()
            change.target_id = entity.id

        elif change.target_type == 'relation':
            rel = NovelRelation(
                project_id=change.project_id,
                source_entity_id=after['source_entity_id'],
                target_entity_id=after['target_entity_id'],
                relation_type=after['relation_type'],
                label=after.get('label'),
                description=after.get('description'),
                strength=after.get('strength', 0.5),
            )
            db.session.add(rel)
            db.session.flush()
            change.target_id = rel.id

        elif change.target_type == 'event':
            event = NovelEvent(
                project_id=change.project_id,
                chapter_id=change.chapter_id,
                title=after.get('title', ''),
                summary=after.get('summary'),
                event_type=after.get('event_type', 'event'),
                timeline_order=after.get('timeline_order', 0),
            )
            if 'participants' in after:
                event.participants = after['participants']
            db.session.add(event)
            db.session.flush()
            change.target_id = event.id

        elif change.target_type == 'event_relation':
            rel = NovelEventRelation(
                project_id=change.project_id,
                source_event_id=after['source_event_id'],
                target_event_id=after['target_event_id'],
                relation_type=after['relation_type'],
                label=after.get('label'),
                description=after.get('description'),
                confidence=after.get('confidence', 0.8),
            )
            db.session.add(rel)
            db.session.flush()
            change.target_id = rel.id

    elif change.change_type == 'modify':
        if change.target_type == 'entity':
            entity = NovelEntity.query.get(change.target_id)
            if entity:
                for k, v in after.items():
                    if k in ('name', 'summary', 'importance', 'entity_type'):
                        setattr(entity, k, v)
                    elif k == 'aliases':
                        entity.aliases = v
                    elif k == 'attributes':
                        entity.attributes = v

        elif change.target_type == 'relation':
            rel = NovelRelation.query.get(change.target_id)
            if rel:
                for k, v in after.items():
                    if hasattr(rel, k):
                        setattr(rel, k, v)


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/review', methods=['POST'])
def review_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='review',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/generations/<int:gen_id>', methods=['GET'])
def get_generation(gen_id):
    gen = NovelGeneration.query.get_or_404(gen_id)
    return jsonify(gen.to_dict())


@novels_bp.route('/api/novels/generations/<int:gen_id>/stream', methods=['GET'])
def stream_generation(gen_id):
    def generate():
        import time
        gen = NovelGeneration.query.get(gen_id)
        if not gen:
            yield f'event: error\ndata: {json.dumps({"error": "not found"})}\n\n'
            return

        # Check Redis first
        from server.services.redis_client import get_redis, redis_key
        r = get_redis()

        while True:
            db.session.refresh(gen)
            data = gen.to_dict()
            yield f'event: progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'

            if gen.status in ('completed', 'failed'):
                yield f'event: done\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
                break

            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/graph.py
git commit -m "feat(novel): add graph routes, generation status, and SSE stream"
```

---

## Task 13: Prompt Templates

**Files:**
- Create: `server/services/novel/__init__.py`
- Create: `server/services/novel/prompt_templates.py`

- [ ] **Step 1: Create services package `__init__.py`**

```python
# server/services/novel/__init__.py
```

Empty file.

- [ ] **Step 2: Create prompt templates**

```python
# server/services/novel/prompt_templates.py

GENRE_TEMPLATES = {
    '玄幻': {
        'system': '你是一位资深玄幻小说作家，擅长修炼体系设计、战斗描写、升级打怪的节奏把控。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：修炼体系要合理，战斗描写要有画面感，节奏要有爽点。',
        'review_criteria': '修炼体系是否一致，境界差距是否合理，战斗描写是否有画面感，是否有爽点。',
    },
    '仙侠': {
        'system': '你是一位资深仙侠小说作家，擅长仙侠世界观、门派势力、法宝道具的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：仙侠氛围要到位，门派关系要清晰，意境描写要优美。',
        'review_criteria': '仙侠氛围是否到位，门派关系是否清晰，法宝设定是否一致，意境描写是否优美。',
    },
    '都市': {
        'system': '你是一位资深都市小说作家，擅长都市生活、职场商战、人际关系的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：都市感要强，对话要自然，情节要有代入感。',
        'review_criteria': '都市感是否强，对话是否自然，社会关系是否合理，情节是否有代入感。',
    },
    '悬疑': {
        'system': '你是一位资深悬疑小说作家，擅长线索铺设、误导设计、真相揭示的把控。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：悬念要到位，线索要埋好，节奏要紧张。',
        'review_criteria': '悬念是否到位，线索是否合理，误导是否有效，真相揭示是否有冲击力。',
    },
    '言情': {
        'system': '你是一位资深言情小说作家，擅长感情描写、人物心理、情感冲突的刻画。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：感情戏要细腻，心理描写要深入，情感冲突要真实。',
        'review_criteria': '感情戏是否细腻，心理描写是否深入，情感冲突是否真实，人物关系发展是否自然。',
    },
    '科幻': {
        'system': '你是一位资深科幻小说作家，擅长科幻设定、科技描写、世界观构建。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：科幻设定要自洽，科技描写要有想象力，世界观要宏大。',
        'review_criteria': '科幻设定是否自洽，科技描写是否有想象力，世界观是否宏大，逻辑是否严密。',
    },
    '历史': {
        'system': '你是一位资深历史小说作家，擅长历史背景、人物刻画、事件还原的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：历史感要强，人物要立体，事件要有据可循。',
        'review_criteria': '历史感是否强，人物是否立体，事件是否合理，时代氛围是否到位。',
    },
    '末世': {
        'system': '你是一位资深末世小说作家，擅长末世生存、资源争夺、人性考验的描写。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：末世感要强，生存压力要真实，人性冲突要深刻。',
        'review_criteria': '末世感是否强，生存压力是否真实，人性冲突是否深刻，资源设定是否合理。',
    },
    '轻小说': {
        'system': '你是一位资深轻小说作家，擅长轻松幽默、角色互动、日常与冒险的平衡。',
        'chapter_prompt': '请根据以下大纲和上下文，生成本章内容。注意：文风要轻松，对话要有趣，角色要有萌点。',
        'review_criteria': '文风是否轻松，对话是否有趣，角色是否有萌点，节奏是否明快。',
    },
}

VERSION_TYPE_MODIFIERS = {
    'steady': '请稳健推进剧情，保持节奏平稳，注重逻辑连贯性。',
    'conflict': '请最大化冲突和张力，让人物面对更激烈的矛盾。',
    'climax': '请写出爽点爆发的感觉，让读者感到痛快淋漓。',
    'suspense': '请增加悬疑感和反转，让读者意想不到。',
    'romance': '请加强感情戏的描写，让人物之间的情感更细腻动人。',
    'polish': '请精修文笔，提升文字质量和文学性。',
}


def get_genre_template(genre):
    return GENRE_TEMPLATES.get(genre, GENRE_TEMPLATES['玄幻'])


def get_version_modifier(version_type):
    return VERSION_TYPE_MODIFIERS.get(version_type, '')


def build_chapter_system_prompt(genre, version_type=None, style_guide=None):
    template = get_genre_template(genre)
    parts = [template['system']]

    if version_type:
        modifier = get_version_modifier(version_type)
        if modifier:
            parts.append(modifier)

    if style_guide:
        if style_guide.get('pov'):
            parts.append(f'叙事视角：{style_guide["pov"]}')
        if style_guide.get('tone'):
            tone = style_guide['tone']
            if isinstance(tone, list):
                tone = '、'.join(tone)
            parts.append(f'文风基调：{tone}')
        if style_guide.get('taboos'):
            taboos = style_guide['taboos']
            if isinstance(taboos, list):
                taboos = '；'.join(taboos)
            parts.append(f'禁忌：{taboos}')

    return '\n'.join(parts)


def build_chapter_user_prompt(context):
    parts = []

    if context.get('outline'):
        parts.append(f'【本章大纲】\n{context["outline"]}')

    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')

    if context.get('text_tail'):
        parts.append(f'【上一章结尾】\n{context["text_tail"]}')

    if context.get('characters'):
        parts.append(f'【相关人物】\n{context["characters"]}')

    if context.get('events'):
        parts.append(f'【相关事件】\n{context["events"]}')

    if context.get('world_building'):
        parts.append(f'【世界观设定】\n{context["world_building"]}')

    if context.get('foreshadowing'):
        parts.append(f'【未回收伏笔】\n{context["foreshadowing"]}')

    parts.append(f'目标字数：{context.get("target_words", 3000)} 字')
    parts.append('请直接输出正文 Markdown，不要输出其他内容。')

    return '\n\n'.join(parts)


def build_extract_prompt(chapter_content):
    return f"""请从以下章节正文中提取知识图谱变更候选。

要求提取：
1. 新出现的人物（姓名、类型、简介）
2. 新出现的关系（谁和谁、关系类型、描述）
3. 新发生的事件（标题、摘要、类型、参与者）
4. 新的因果关系（哪个事件导致了哪个事件）
5. 人物状态变化（所在地、阵营、目标、情绪变化）
6. 关系变化（关系类型或状态变化）

请以 JSON 格式输出，结构如下：
{{
  "changes": [
    {{
      "change_type": "add|modify",
      "target_type": "entity|relation|event|event_relation",
      "after": {{ ... }},
      "confidence": 0.0-1.0,
      "description": "变更描述"
    }}
  ]
}}

【章节正文】
{chapter_content}"""


def build_review_prompt(chapter_content, context):
    parts = ['请对以下章节进行一致性审稿。']

    if context.get('characters'):
        parts.append(f'【已有人物设定】\n{context["characters"]}')
    if context.get('world_rules'):
        parts.append(f'【世界观规则】\n{context["world_rules"]}')
    if context.get('previous_summaries'):
        parts.append(f'【前文摘要】\n{context["previous_summaries"]}')

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

请以 JSON 格式输出：
{{
  "issues": [
    {{
      "severity": "high|medium|low",
      "category": "character|world|timeline|location|causality|foreshadow|progression|redundancy|padding",
      "location": "问题位置描述",
      "description": "问题描述",
      "suggestion": "修复建议"
    }}
  ],
  "overall_score": 0-100,
  "summary": "总体评价"
}}

【章节正文】
{chapter_content}""")

    return '\n\n'.join(parts)
```

- [ ] **Step 3: Commit**

```bash
git add server/services/novel/
git commit -m "feat(novel): add prompt templates for genre-specific generation"
```

---

## Task 14: Context Builder

**Files:**
- Create: `server/services/novel/context_builder.py`

- [ ] **Step 1: Create context builder**

```python
# server/services/novel/context_builder.py
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
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/context_builder.py
git commit -m "feat(novel): add context builder with budget control"
```

---

## Task 15: Generation Runner (Async Framework)

**Files:**
- Create: `server/services/novel/generation_runner.py`

- [ ] **Step 1: Create generation runner**

```python
# server/services/novel/generation_runner.py
import json
import threading
import traceback
from datetime import datetime, timezone

from server.models import db
from server.models.novel.graph_change import NovelGeneration
from server.services.redis_client import get_redis, redis_key, acquire_lock, release_lock


_sse_subscribers = {}
_sse_lock = threading.Lock()


def _sse_broadcast(gen_id, event, data):
    from server.services.redis_client import get_redis, redis_key
    r = get_redis()
    payload = f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
    if r is not None:
        try:
            r.publish(redis_key('novel', 'generation', str(gen_id), 'events'), payload)
        except Exception:
            pass
    else:
        with _sse_lock:
            subscribers = list(_sse_subscribers.get(gen_id, []))
        for q in subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                pass


def _update_progress(gen, progress, status=None):
    gen.progress = progress
    if status:
        gen.status = status
    db.session.commit()
    _sse_broadcast(gen.id, 'progress', gen.to_dict())


def start_generation(project_id, generation_type, target_id=None, params=None):
    """Create a generation record and start background thread."""
    gen = NovelGeneration(
        project_id=project_id,
        generation_type=generation_type,
        target_id=target_id,
        status='pending',
        progress=0,
    )
    db.session.add(gen)
    db.session.commit()

    # Check concurrency limits
    active_count = NovelGeneration.query.filter(
        NovelGeneration.project_id == project_id,
        NovelGeneration.status.in_(['pending', 'running']),
    ).count()
    if active_count > 3:
        gen.status = 'failed'
        gen.error = '该项目同时进行的任务过多，请等待完成后再试'
        db.session.commit()
        return gen

    # Check chapter-level lock for chapter_version and extract
    if generation_type in ('chapter_version', 'extract', 'review') and target_id:
        lock_key = redis_key('novel', 'lock', generation_type, str(target_id))
        token = acquire_lock(lock_key, ttl=300)
        if token is None:
            gen.status = 'failed'
            gen.error = '该章节正在生成中，请稍后再试'
            db.session.commit()
            return gen
    else:
        lock_key = None
        token = None

    thread = threading.Thread(
        target=_run_generation,
        args=(gen.id, params or {}, lock_key, token),
        daemon=True,
    )
    thread.start()

    return gen


def _run_generation(gen_id, params, lock_key, token):
    """Background thread that runs the actual generation."""
    from server.app import create_app
    app = create_app()
    with app.app_context():
        gen = NovelGeneration.query.get(gen_id)
        if not gen:
            return

        try:
            gen.status = 'running'
            db.session.commit()
            _sse_broadcast(gen.id, 'progress', gen.to_dict())

            if gen.generation_type == 'blueprint':
                _run_blueprint(gen, params)
            elif gen.generation_type == 'chapter_version':
                _run_chapter_version(gen, params)
            elif gen.generation_type == 'extract':
                _run_extract(gen, params)
            elif gen.generation_type == 'review':
                _run_review(gen, params)
            else:
                raise ValueError(f'未知的生成类型: {gen.generation_type}')

            gen.status = 'completed'
            gen.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            _sse_broadcast(gen.id, 'completed', gen.to_dict())

        except Exception as e:
            gen.status = 'failed'
            gen.error = str(e)
            gen.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            _sse_broadcast(gen.id, 'failed', gen.to_dict())

        finally:
            if lock_key and token:
                release_lock(lock_key, token)


def _run_blueprint(gen, params):
    from server.services.novel.blueprint_generator import generate_blueprint
    _update_progress(gen, 10)
    result = generate_blueprint(gen.project_id, params)
    gen.result = result
    _update_progress(gen, 100)


def _run_chapter_version(gen, params):
    from server.services.novel.version_generator import generate_versions
    _update_progress(gen, 10)
    result = generate_versions(gen.project_id, gen.target_id, params)
    gen.result = result
    _update_progress(gen, 100)


def _run_extract(gen, params):
    from server.services.novel.graph_extractor import extract_graph_changes
    _update_progress(gen, 10)
    result = extract_graph_changes(gen.project_id, gen.target_id)
    gen.result = result
    _update_progress(gen, 100)


def _run_review(gen, params):
    from server.services.novel.consistency_reviewer import review_chapter
    _update_progress(gen, 10)
    result = review_chapter(gen.project_id, gen.target_id)
    gen.result = result
    _update_progress(gen, 100)
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/generation_runner.py
git commit -m "feat(novel): add async generation runner with SSE support"
```

---

## Task 16: Chapter Generator

**Files:**
- Create: `server/services/novel/chapter_generator.py`

- [ ] **Step 1: Create chapter generator**

```python
# server/services/novel/chapter_generator.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.project import NovelProject
from server.services.novel.context_builder import build_context
from server.services.novel.prompt_templates import build_chapter_system_prompt, build_chapter_user_prompt
from server.services.model_registry import ModelRegistry


def generate_single_version(project_id, chapter_id, version_type='custom', user_instruction='', model_key=None):
    """Generate a single version for a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    # Build context
    context = build_context(project_id, chapter_id, user_instruction, project.words_per_chapter)

    # Build prompts
    system_prompt = build_chapter_system_prompt(
        project.genre,
        version_type=version_type,
        style_guide=project.style_guide,
    )
    user_prompt = build_chapter_user_prompt(context)

    # Get LLM provider
    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    # Call LLM
    messages = [{'role': 'user', 'content': user_prompt}]
    content = provider.complete(
        messages,
        model=model_key or 'mimo-v2.5-pro',
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    # Create version
    version = NovelChapterVersion(
        chapter_id=chapter_id,
        version_type=version_type,
        title=f'{version_type}版',
        content_markdown=content,
        model=model_key or 'mimo-v2.5-pro',
        accepted=False,
    )
    version.prompt = {'system': system_prompt, 'user': user_prompt}
    version.context_snapshot = {'context_hash': hash(json.dumps(context, sort_keys=True, default=str))}

    db.session.add(version)
    db.session.commit()

    return version


def _get_active_provider():
    """Get the active model provider from settings."""
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    # Fallback to first available
    return 'mimo', ''
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/chapter_generator.py
git commit -m "feat(novel): add chapter generator service"
```

---

## Task 17: Version Generator

**Files:**
- Create: `server/services/novel/version_generator.py`

- [ ] **Step 1: Create version generator**

```python
# server/services/novel/version_generator.py
from server.models import db
from server.models.novel.chapter import NovelChapterVersion
from server.services.novel.chapter_generator import generate_single_version


DEFAULT_VERSION_TYPES = ['steady', 'conflict', 'suspense']


def generate_versions(project_id, chapter_id, params):
    """Generate multiple versions for a chapter."""
    version_types = params.get('version_types', DEFAULT_VERSION_TYPES)
    user_instruction = params.get('user_instruction', '')
    model_key = params.get('model_key')

    results = []
    for vtype in version_types:
        try:
            version = generate_single_version(
                project_id=project_id,
                chapter_id=chapter_id,
                version_type=vtype,
                user_instruction=user_instruction,
                model_key=model_key,
            )
            results.append(version.to_dict())
        except Exception as e:
            results.append({
                'version_type': vtype,
                'error': str(e),
            })

    return {'versions': results}
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/version_generator.py
git commit -m "feat(novel): add version generator for multi-version chapter generation"
```

---

## Task 18: Blueprint Generator

**Files:**
- Create: `server/services/novel/blueprint_generator.py`

- [ ] **Step 1: Create blueprint generator**

```python
# server/services/novel/blueprint_generator.py
import json
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.entity import NovelEntity, NovelRelation
from server.services.model_registry import ModelRegistry


def generate_blueprint(project_id, params):
    """Generate a full novel blueprint from premise."""
    project = NovelProject.query.get_or_404(project_id)

    premise = params.get('premise', project.premise or '')
    if not premise:
        raise ValueError('请提供小说创意')

    # Build prompt
    system_prompt = f"""你是一位资深小说策划师，擅长根据一句话创意扩展成完整的小说蓝图。
请根据以下信息生成完整的小说蓝图：

类型：{project.genre}
目标字数：{project.target_total_words}
目标章节数：{project.target_chapters}
每章字数：{project.words_per_chapter}
卷数：{project.volume_count}

请以 JSON 格式输出，包含以下字段：
{{
  "title": "小说标题",
  "premise": "一句话简介",
  "main_character": {{
    "name": "主角名",
    "summary": "主角简介",
    "attributes": {{}}
  }},
  "characters": [
    {{
      "name": "角色名",
      "entity_type": "character",
      "summary": "角色简介",
      "importance": 1-10
    }}
  ],
  "world_settings": {{}},
  "volumes": [
    {{
      "title": "卷标题",
      "summary": "卷简介",
      "chapters": [
        {{
          "title": "章节标题",
          "summary": "章节摘要",
          "plot_goal": "剧情目标",
          "conflict_goal": "冲突目标",
          "target_words": 3000
        }}
      ]
    }}
  ],
  "main_conflict": "主线冲突描述",
  "key_events": ["事件1", "事件2"]
}}"""

    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': f'一句话创意：{premise}'}]
    response = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt=system_prompt,
        max_tokens=8192,
        timeout=120,
    )

    # Parse response
    result = _parse_json_response(response)

    # Update project
    if result.get('title'):
        project.title = result['title']
    if result.get('premise'):
        project.premise = result['premise']
    if result.get('world_settings'):
        project.settings = result['world_settings']
    project.status = 'active'

    # Create main character
    main_char = result.get('main_character', {})
    if main_char.get('name'):
        entity = NovelEntity(
            project_id=project_id,
            entity_type='character',
            name=main_char['name'],
            summary=main_char.get('summary'),
            importance=10,
        )
        if main_char.get('attributes'):
            entity.attributes = main_char['attributes']
        db.session.add(entity)
        db.session.flush()

    # Create other characters
    char_entities = {}
    for char in result.get('characters', []):
        if not char.get('name'):
            continue
        entity = NovelEntity(
            project_id=project_id,
            entity_type=char.get('entity_type', 'character'),
            name=char['name'],
            summary=char.get('summary'),
            importance=char.get('importance', 5),
        )
        db.session.add(entity)
        db.session.flush()
        char_entities[char['name']] = entity

    # Create outline tree
    chapter_order = 0
    for vol_idx, volume in enumerate(result.get('volumes', []), 1):
        vol_node = NovelOutlineNode(
            project_id=project_id,
            node_type='volume',
            title=volume.get('title', f'第{vol_idx}卷'),
            summary=volume.get('summary'),
            order_index=vol_idx,
        )
        db.session.add(vol_node)
        db.session.flush()

        for ch_idx, chapter in enumerate(volume.get('chapters', []), 1):
            chapter_order += 1
            ch_node = NovelOutlineNode(
                project_id=project_id,
                parent_id=vol_node.id,
                node_type='chapter',
                title=chapter.get('title', f'第{chapter_order}章'),
                summary=chapter.get('summary'),
                order_index=ch_idx,
                target_words=chapter.get('target_words', project.words_per_chapter),
                plot_goal=chapter.get('plot_goal'),
                conflict_goal=chapter.get('conflict_goal'),
            )
            db.session.add(ch_node)

    db.session.commit()

    return {
        'project_id': project_id,
        'title': project.title,
        'characters_created': len(char_entities) + (1 if main_char.get('name') else 0),
        'volumes_created': len(result.get('volumes', [])),
        'chapters_created': chapter_order,
    }


def _parse_json_response(text):
    """Extract JSON from LLM response."""
    # Try to find JSON block
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find first { and last }
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError('无法解析 AI 返回的 JSON')


def _get_active_provider():
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    return 'mimo', ''
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/blueprint_generator.py
git commit -m "feat(novel): add blueprint generator for full-book outline creation"
```

---

## Task 19: Graph Extractor

**Files:**
- Create: `server/services/novel/graph_extractor.py`

- [ ] **Step 1: Create graph extractor**

```python
# server/services/novel/graph_extractor.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.graph_change import NovelGraphChange
from server.services.novel.prompt_templates import build_extract_prompt
from server.services.model_registry import ModelRegistry


def extract_graph_changes(project_id, chapter_id):
    """Extract graph change candidates from chapter content."""
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    # Build prompt
    prompt = build_extract_prompt(chapter.content_markdown)

    # Call LLM
    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt='你是一位小说知识图谱分析专家，擅长从小说文本中提取人物、关系、事件和因果关系。',
        max_tokens=4096,
        timeout=60,
    )

    # Parse response
    result = _parse_json_response(response)
    changes_data = result.get('changes', [])

    # Create GraphChange records
    changes = []
    for item in changes_data:
        change = NovelGraphChange(
            project_id=project_id,
            chapter_id=chapter_id,
            change_type=item.get('change_type', 'add'),
            target_type=item.get('target_type', 'entity'),
            source='ai_confirm',
            confidence=item.get('confidence', 0.7),
        )
        if 'before' in item:
            change.before = item['before']
        if 'after' in item:
            change.after = item['after']
        db.session.add(change)
        changes.append(change)

    db.session.commit()

    return {
        'chapter_id': chapter_id,
        'changes_count': len(changes),
        'changes': [c.to_dict() for c in changes],
    }


def _parse_json_response(text):
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError('无法解析 AI 返回的 JSON')


def _get_active_provider():
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    return 'mimo', ''
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/graph_extractor.py
git commit -m "feat(novel): add graph extractor for AI-powered knowledge extraction"
```

---

## Task 20: Consistency Reviewer

**Files:**
- Create: `server/services/novel/consistency_reviewer.py`

- [ ] **Step 1: Create consistency reviewer**

```python
# server/services/novel/consistency_reviewer.py
import json
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent
from server.services.novel.context_builder import _build_character_context, _build_previous_summaries
from server.services.novel.prompt_templates import build_review_prompt
from server.services.model_registry import ModelRegistry


def review_chapter(project_id, chapter_id):
    """Run consistency review on a chapter."""
    project = NovelProject.query.get_or_404(project_id)
    chapter = NovelChapter.query.get_or_404(chapter_id)

    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    # Build review context
    context = {
        'characters': _build_character_context(project_id, chapter),
        'previous_summaries': _build_previous_summaries(project_id, chapter),
        'world_rules': _format_world_rules(project.settings),
    }

    # Build prompt
    prompt = build_review_prompt(chapter.content_markdown, context)

    # Call LLM
    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt='你是一位资深小说编辑，擅长检查小说的一致性和质量。',
        max_tokens=4096,
        timeout=60,
    )

    # Parse response
    result = _parse_json_response(response)

    return {
        'chapter_id': chapter_id,
        'issues': result.get('issues', []),
        'overall_score': result.get('overall_score', 0),
        'summary': result.get('summary', ''),
    }


def _format_world_rules(settings):
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


def _parse_json_response(text):
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError('无法解析 AI 返回的 JSON')


def _get_active_provider():
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    return 'mimo', ''
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/consistency_reviewer.py
git commit -m "feat(novel): add consistency reviewer for chapter quality checking"
```

---

## Task 21: Summarizer

**Files:**
- Create: `server/services/novel/summarizer.py`

- [ ] **Step 1: Create summarizer**

```python
# server/services/novel/summarizer.py
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.services.model_registry import ModelRegistry


def generate_summary(chapter_id):
    """Generate a summary for a confirmed chapter."""
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if not chapter.content_markdown:
        raise ValueError('章节内容为空')

    prompt = f"""请为以下章节生成一段 200-500 字的摘要，用于后续章节的前文上下文参考。

摘要要求：
1. 概括本章主要剧情
2. 记录重要人物行为和状态变化
3. 记录新出现的冲突和伏笔
4. 记录已解决的问题
5. 保持客观叙述，不要添加评价

【章节标题】{chapter.title}

【章节正文】
{chapter.content_markdown}"""

    registry = ModelRegistry()
    provider_key, api_key = _get_active_provider()
    provider = registry.create_provider(provider_key, api_key)

    messages = [{'role': 'user', 'content': prompt}]
    summary = provider.complete(
        messages,
        model='mimo-v2.5-pro',
        system_prompt='你是一位小说摘要撰写专家，擅长提炼章节要点。',
        max_tokens=1024,
        timeout=30,
    )

    chapter.summary = summary.strip()
    db.session.commit()

    return {'chapter_id': chapter_id, 'summary': chapter.summary}


def _get_active_provider():
    import os
    api_key = os.environ.get('MIMO_API_KEY', '')
    if api_key:
        return 'mimo', api_key
    return 'mimo', ''
```

- [ ] **Step 2: Commit**

```bash
git add server/services/novel/summarizer.py
git commit -m "feat(novel): add chapter summarizer"
```

---

## Task 22: Blueprint Generate Route

**Files:**
- Modify: `server/routes/novels/outline.py`

- [ ] **Step 1: Add blueprint generate endpoint to outline routes**

Add to the end of `server/routes/novels/outline.py`:

```python
@novels_bp.route('/api/novels/<int:project_id>/blueprint/generate', methods=['POST'])
def generate_blueprint(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    if data.get('premise'):
        project = NovelProject.query.get(project_id)
        project.premise = data['premise']
        db.session.commit()

    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='blueprint',
        target_id=project_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/novels/outline.py
git commit -m "feat(novel): add blueprint generation endpoint"
```

---

## Task 23: Integration — Register Blueprint

**Files:**
- Modify: `server/app.py`

- [ ] **Step 1: Add blueprint registration to `server/app.py`**

In the `create_app()` function, after the existing blueprint registrations, add:

```python
from server.routes.novels import novels_bp
app.register_blueprint(novels_bp)
```

- [ ] **Step 2: Commit**

```bash
git add server/app.py
git commit -m "feat(novel): register novels blueprint in app"
```

---

## Task 24: Tests — Project CRUD

**Files:**
- Create: `server/tests/test_novel_project.py`

- [ ] **Step 1: Create project CRUD tests**

```python
# server/tests/test_novel_project.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject


@pytest.fixture
def sample_project(app):
    project = NovelProject(
        title='测试小说',
        genre='玄幻',
        target_total_words=300000,
        target_chapters=100,
        words_per_chapter=3000,
    )
    db.session.add(project)
    db.session.commit()
    return project


def test_create_project(client):
    resp = client.post('/api/novels', json={
        'title': '新小说',
        'genre': '仙侠',
        'target_total_words': 500000,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '新小说'
    assert data['genre'] == '仙侠'


def test_create_project_missing_title(client):
    resp = client.post('/api/novels', json={'genre': '玄幻'})
    assert resp.status_code == 400


def test_list_projects(client, sample_project):
    resp = client.get('/api/novels')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 1


def test_get_project(client, sample_project):
    resp = client.get(f'/api/novels/{sample_project.id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['title'] == '测试小说'
    assert 'stats' in data


def test_update_project(client, sample_project):
    resp = client.put(f'/api/novels/{sample_project.id}', json={
        'title': '修改后标题',
        'genre': '都市',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['title'] == '修改后标题'
    assert data['genre'] == '都市'


def test_delete_project(client, sample_project):
    resp = client.delete(f'/api/novels/{sample_project.id}')
    assert resp.status_code == 204
    resp = client.get(f'/api/novels/{sample_project.id}')
    assert resp.status_code == 404


def test_get_nonexistent_project(client):
    resp = client.get('/api/novels/99999')
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest server/tests/test_novel_project.py -v
```

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_novel_project.py
git commit -m "test(novel): add project CRUD tests"
```

---

## Task 25: Tests — Outline

**Files:**
- Create: `server/tests/test_novel_outline.py`

- [ ] **Step 1: Create outline tests**

```python
# server/tests/test_novel_outline.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode


@pytest.fixture
def project(app):
    p = NovelProject(title='大纲测试小说', genre='玄幻')
    db.session.add(p)
    db.session.commit()
    return p


def test_create_outline_node(client, project):
    resp = client.post(f'/api/novels/{project.id}/outline', json={
        'title': '第一卷',
        'node_type': 'volume',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '第一卷'
    assert data['node_type'] == 'volume'


def test_create_child_node(client, project):
    resp = client.post(f'/api/novels/{project.id}/outline', json={
        'title': '第一卷',
        'node_type': 'volume',
    })
    parent_id = resp.get_json()['id']

    resp = client.post(f'/api/novels/{project.id}/outline', json={
        'title': '第一章',
        'node_type': 'chapter',
        'parent_id': parent_id,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['parent_id'] == parent_id


def test_get_outline_tree(client, project):
    client.post(f'/api/novels/{project.id}/outline', json={'title': '卷一', 'node_type': 'volume'})
    client.post(f'/api/novels/{project.id}/outline', json={'title': '卷二', 'node_type': 'volume'})

    resp = client.get(f'/api/novels/{project.id}/outline')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_update_outline_node(client, project):
    resp = client.post(f'/api/novels/{project.id}/outline', json={'title': '原标题'})
    node_id = resp.get_json()['id']

    resp = client.put(f'/api/novels/{project.id}/outline/{node_id}', json={'title': '新标题'})
    assert resp.status_code == 200
    assert resp.get_json()['title'] == '新标题'


def test_delete_outline_node(client, project):
    resp = client.post(f'/api/novels/{project.id}/outline', json={'title': '待删除'})
    node_id = resp.get_json()['id']

    resp = client.delete(f'/api/novels/{project.id}/outline/{node_id}')
    assert resp.status_code == 204


def test_parent_validation(client, project):
    other_project = NovelProject(title='其他项目')
    db.session.add(other_project)
    db.session.commit()

    resp = client.post(f'/api/novels/{other_project.id}/outline', json={'title': '其他卷'})
    other_node_id = resp.get_json()['id']

    resp = client.post(f'/api/novels/{project.id}/outline', json={
        'title': '错误节点',
        'parent_id': other_node_id,
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest server/tests/test_novel_outline.py -v
```

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_novel_outline.py
git commit -m "test(novel): add outline CRUD tests"
```

---

## Task 26: Tests — Chapters

**Files:**
- Create: `server/tests/test_novel_chapter.py`

- [ ] **Step 1: Create chapter tests**

```python
# server/tests/test_novel_chapter.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.chapter import NovelChapter, NovelChapterVersion


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
    assert data['word_count'] == 5


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


def test_delete_chapter(client, project, chapter):
    resp = client.delete(f'/api/novels/{project.id}/chapters/{chapter.id}')
    assert resp.status_code == 204
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest server/tests/test_novel_chapter.py -v
```

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_novel_chapter.py
git commit -m "test(novel): add chapter and version tests"
```

---

## Task 27: Tests — Entities

**Files:**
- Create: `server/tests/test_novel_entity.py`

- [ ] **Step 1: Create entity tests**

```python
# server/tests/test_novel_entity.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation


@pytest.fixture
def project(app):
    p = NovelProject(title='实体测试小说')
    db.session.add(p)
    db.session.commit()
    return p


def test_create_entity(client, project):
    resp = client.post(f'/api/novels/{project.id}/entities', json={
        'name': '张三',
        'entity_type': 'character',
        'summary': '主角',
        'importance': 10,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == '张三'
    assert data['importance'] == 10


def test_create_entity_missing_name(client, project):
    resp = client.post(f'/api/novels/{project.id}/entities', json={'entity_type': 'character'})
    assert resp.status_code == 400


def test_list_entities(client, project):
    client.post(f'/api/novels/{project.id}/entities', json={'name': 'A'})
    client.post(f'/api/novels/{project.id}/entities', json={'name': 'B'})
    resp = client.get(f'/api/novels/{project.id}/entities')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_entities_filter_type(client, project):
    client.post(f'/api/novels/{project.id}/entities', json={'name': '张三', 'entity_type': 'character'})
    client.post(f'/api/novels/{project.id}/entities', json={'name': '青云宗', 'entity_type': 'faction'})
    resp = client.get(f'/api/novels/{project.id}/entities?type=character')
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['entity_type'] == 'character'


def test_update_entity(client, project):
    resp = client.post(f'/api/novels/{project.id}/entities', json={'name': '原名'})
    eid = resp.get_json()['id']
    resp = client.put(f'/api/novels/{project.id}/entities/{eid}', json={'name': '新名'})
    assert resp.status_code == 200
    assert resp.get_json()['name'] == '新名'


def test_delete_entity(client, project):
    resp = client.post(f'/api/novels/{project.id}/entities', json={'name': '待删除'})
    eid = resp.get_json()['id']
    resp = client.delete(f'/api/novels/{project.id}/entities/{eid}')
    assert resp.status_code == 204


def test_create_relation(client, project):
    e1 = client.post(f'/api/novels/{project.id}/entities', json={'name': 'A'}).get_json()
    e2 = client.post(f'/api/novels/{project.id}/entities', json={'name': 'B'}).get_json()
    resp = client.post(f'/api/novels/{project.id}/relations', json={
        'source_entity_id': e1['id'],
        'target_entity_id': e2['id'],
        'relation_type': '师徒',
        'label': '师父',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['relation_type'] == '师徒'


def test_delete_entity_cascades_relations(client, project):
    e1 = client.post(f'/api/novels/{project.id}/entities', json={'name': 'X'}).get_json()
    e2 = client.post(f'/api/novels/{project.id}/entities', json={'name': 'Y'}).get_json()
    client.post(f'/api/novels/{project.id}/relations', json={
        'source_entity_id': e1['id'],
        'target_entity_id': e2['id'],
        'relation_type': '敌对',
    })
    client.delete(f'/api/novels/{project.id}/entities/{e1['id']}')
    resp = client.get(f'/api/novels/{project.id}/relations')
    assert len(resp.get_json()) == 0
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest server/tests/test_novel_entity.py -v
```

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_novel_entity.py
git commit -m "test(novel): add entity and relation CRUD tests"
```

---

## Task 28: Tests — Events

**Files:**
- Create: `server/tests/test_novel_event.py`

- [ ] **Step 1: Create event tests**

```python
# server/tests/test_novel_event.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.event import NovelEvent, NovelEventRelation


@pytest.fixture
def project(app):
    p = NovelProject(title='事件测试小说')
    db.session.add(p)
    db.session.commit()
    return p


def test_create_event(client, project):
    resp = client.post(f'/api/novels/{project.id}/events', json={
        'title': '大战',
        'event_type': 'conflict',
        'summary': '主角与反派大战',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '大战'
    assert data['event_type'] == 'conflict'


def test_list_events(client, project):
    client.post(f'/api/novels/{project.id}/events', json={'title': '事件A', 'timeline_order': 1})
    client.post(f'/api/novels/{project.id}/events', json={'title': '事件B', 'timeline_order': 2})
    resp = client.get(f'/api/novels/{project.id}/events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]['timeline_order'] <= data[1]['timeline_order']


def test_update_event(client, project):
    resp = client.post(f'/api/novels/{project.id}/events', json={'title': '原标题'})
    eid = resp.get_json()['id']
    resp = client.put(f'/api/novels/{project.id}/events/{eid}', json={'title': '新标题'})
    assert resp.status_code == 200
    assert resp.get_json()['title'] == '新标题'


def test_delete_event(client, project):
    resp = client.post(f'/api/novels/{project.id}/events', json={'title': '待删除'})
    eid = resp.get_json()['id']
    resp = client.delete(f'/api/novels/{project.id}/events/{eid}')
    assert resp.status_code == 204


def test_create_event_relation(client, project):
    e1 = client.post(f'/api/novels/{project.id}/events', json={'title': '因'}).get_json()
    e2 = client.post(f'/api/novels/{project.id}/events', json={'title': '果'}).get_json()
    resp = client.post(f'/api/novels/{project.id}/event-relations', json={
        'source_event_id': e1['id'],
        'target_event_id': e2['id'],
        'relation_type': 'causes',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['relation_type'] == 'causes'


def test_delete_event_cascades_relations(client, project):
    e1 = client.post(f'/api/novels/{project.id}/events', json={'title': 'A'}).get_json()
    e2 = client.post(f'/api/novels/{project.id}/events', json={'title': 'B'}).get_json()
    client.post(f'/api/novels/{project.id}/event-relations', json={
        'source_event_id': e1['id'],
        'target_event_id': e2['id'],
        'relation_type': 'drives',
    })
    client.delete(f'/api/novels/{project.id}/events/{e1['id']}')
    resp = client.get(f'/api/novels/{project.id}/events')
    assert len(resp.get_json()) == 1
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest server/tests/test_novel_event.py -v
```

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_novel_event.py
git commit -m "test(novel): add event and event-relation tests"
```

---

## Task 29: Tests — Graph & Prompt Templates

**Files:**
- Create: `server/tests/test_novel_graph.py`
- Create: `server/tests/test_novel_prompt_templates.py`

- [ ] **Step 1: Create graph tests**

```python
# server/tests/test_novel_graph.py
import pytest
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent
from server.models.novel.graph_change import NovelGraphChange


@pytest.fixture
def project(app):
    p = NovelProject(title='图谱测试小说')
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def sample_entities(app, project):
    e1 = NovelEntity(project_id=project.id, name='张三', entity_type='character', importance=8)
    e2 = NovelEntity(project_id=project.id, name='李四', entity_type='character', importance=6)
    db.session.add_all([e1, e2])
    db.session.flush()
    rel = NovelRelation(
        project_id=project.id,
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        relation_type='师徒',
    )
    db.session.add(rel)
    db.session.commit()
    return e1, e2, rel


def test_character_graph(client, project, sample_entities):
    resp = client.get(f'/api/novels/{project.id}/graph/characters')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['nodes']) == 2
    assert len(data['edges']) == 1
    assert data['edges'][0]['type'] == '师徒'


def test_event_graph(client, project):
    e1 = NovelEvent(project_id=project.id, title='事件A', timeline_order=1)
    e2 = NovelEvent(project_id=project.id, title='事件B', timeline_order=2)
    db.session.add_all([e1, e2])
    db.session.commit()

    resp = client.get(f'/api/novels/{project.id}/graph/events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['nodes']) == 2


def test_update_graph_layout(client, project, sample_entities):
    e1, e2, _ = sample_entities
    resp = client.put(f'/api/novels/{project.id}/graph/layout', json={
        'entity_positions': [
            {'id': e1.id, 'x': 100, 'y': 200},
            {'id': e2.id, 'x': 300, 'y': 400},
        ],
    })
    assert resp.status_code == 200

    # Verify positions updated
    entity = db.session.get(NovelEntity, e1.id)
    assert entity.node_x == 100
    assert entity.node_y == 200


def test_accept_graph_change_add_entity(client, project):
    change = NovelGraphChange(
        project_id=project.id,
        change_type='add',
        target_type='entity',
        source='ai_confirm',
        confidence=0.9,
    )
    change.after = {'name': '新角色', 'entity_type': 'character', 'summary': 'AI提取的角色'}
    db.session.add(change)
    db.session.commit()

    resp = client.post(f'/api/novels/{project.id}/graph-changes/{change.id}/accept')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['accepted'] is True
    assert data['target_id'] is not None

    # Verify entity created
    entity = db.session.get(NovelEntity, data['target_id'])
    assert entity is not None
    assert entity.name == '新角色'


def test_reject_graph_change(client, project):
    change = NovelGraphChange(
        project_id=project.id,
        change_type='add',
        target_type='entity',
        source='ai_confirm',
    )
    change.after = {'name': '不需要的角色'}
    db.session.add(change)
    db.session.commit()

    resp = client.post(f'/api/novels/{project.id}/graph-changes/{change.id}/reject')
    assert resp.status_code == 200
    assert resp.get_json()['accepted'] is False
```

- [ ] **Step 2: Create prompt templates tests**

```python
# server/tests/test_novel_prompt_templates.py
from server.services.novel.prompt_templates import (
    get_genre_template,
    get_version_modifier,
    build_chapter_system_prompt,
    build_chapter_user_prompt,
    build_extract_prompt,
    build_review_prompt,
)


def test_get_genre_template():
    template = get_genre_template('玄幻')
    assert 'system' in template
    assert 'chapter_prompt' in template


def test_get_genre_template_unknown():
    template = get_genre_template('未知类型')
    assert template == get_genre_template('玄幻')


def test_get_version_modifier():
    modifier = get_version_modifier('conflict')
    assert '冲突' in modifier


def test_get_version_modifier_unknown():
    modifier = get_version_modifier('unknown')
    assert modifier == ''


def test_build_chapter_system_prompt():
    prompt = build_chapter_system_prompt('玄幻', version_type='conflict')
    assert '玄幻' in prompt
    assert '冲突' in prompt


def test_build_chapter_system_prompt_with_style():
    prompt = build_chapter_system_prompt('都市', style_guide={
        'pov': '第三人称有限',
        'taboos': ['不要让主角突然无脑'],
    })
    assert '第三人称有限' in prompt
    assert '不要让主角突然无脑' in prompt


def test_build_chapter_user_prompt():
    context = {
        'outline': '本章大纲内容',
        'text_tail': '上一章结尾',
        'target_words': 3000,
    }
    prompt = build_chapter_user_prompt(context)
    assert '本章大纲内容' in prompt
    assert '3000' in prompt


def test_build_extract_prompt():
    prompt = build_extract_prompt('章节正文内容')
    assert '章节正文内容' in prompt
    assert 'JSON' in prompt


def test_build_review_prompt():
    prompt = build_review_prompt('章节正文', {'characters': '人物设定'})
    assert '章节正文' in prompt
    assert '人物设定' in prompt
```

- [ ] **Step 3: Run all novel tests**

```bash
uv run pytest server/tests/test_novel_*.py -v
```

- [ ] **Step 4: Commit**

```bash
git add server/tests/test_novel_graph.py server/tests/test_novel_prompt_templates.py
git commit -m "test(novel): add graph and prompt template tests"
```

---

## Task 30: Final Integration Test

**Files:**
- None (verification only)

- [ ] **Step 1: Run all tests to verify nothing is broken**

```bash
uv run pytest server/tests/ -v
```

- [ ] **Step 2: Verify app starts without errors**

```bash
uv run python -c "from server.app import create_app; app = create_app(); print('OK')"
```

- [ ] **Step 3: Final commit if needed**

```bash
git status
```

If there are uncommitted changes, commit them. Otherwise, the implementation is complete.
