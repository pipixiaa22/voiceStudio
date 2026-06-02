# Novel Backend Design Spec

## Overview

Backend implementation for the Novel Continuation & Knowledge Graph module — a long-form AI novel writing workstation. Users create novel projects with characters, world-building, and outlines, then the system generates chapters via AI with multi-version support, maintaining consistency through editable knowledge graphs (character relationships and event causality).

**Scope:** All 5 phases — project CRUD, outline, chapters, character graph, event graph, AI extraction, consistency review.

**Key decisions:**
- Reuse existing `ModelProvider` abstraction for all LLM calls
- Share single `db` SQLAlchemy instance with existing modules (MySQL when `DATABASE_URL` set, else SQLite)
- Async generation via background threads + Redis state (same pattern as `video_job.py`)
- Backend stores graph data + node coordinates; frontend renders canvas

## Architecture

### File Structure

```
server/
├── models/
│   └── novel/
│       ├── __init__.py          # Unified exports
│       ├── project.py           # NovelProject
│       ├── outline.py           # NovelOutlineNode
│       ├── chapter.py           # NovelChapter, NovelChapterVersion
│       ├── entity.py            # NovelEntity, NovelRelation
│       ├── event.py             # NovelEvent, NovelEventRelation
│       └── graph_change.py      # NovelGraphChange, NovelGeneration
├── routes/
│   └── novels/
│       ├── __init__.py          # Blueprint registration
│       ├── projects.py          # Project CRUD
│       ├── outline.py           # Outline management + blueprint generation
│       ├── chapters.py          # Chapter CRUD + version generation
│       ├── entities.py          # Entity & relation CRUD
│       ├── events.py            # Event & event-relation CRUD
│       └── graph.py             # Graph queries, AI extract, review
└── services/
    └── novel/
        ├── __init__.py
        ├── context_builder.py   # Context assembly with budget control
        ├── chapter_generator.py # Single chapter generation
        ├── version_generator.py # Multi-version generation
        ├── blueprint_generator.py # Full-book blueprint from premise
        ├── graph_extractor.py   # AI graph extraction from chapters
        ├── consistency_reviewer.py # Consistency checking
        ├── summarizer.py        # Chapter summary generation
        └── prompt_templates.py  # Genre-specific prompt templates
```

## Data Models

### NovelProject

```python
class NovelProject(db.Model):
    __tablename__ = 'novel_projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(50), nullable=False, default='玄幻')
    premise = db.Column(db.Text, nullable=True)  # One-line premise
    target_total_words = db.Column(db.Integer, nullable=False, default=300000)
    target_chapters = db.Column(db.Integer, nullable=False, default=100)
    words_per_chapter = db.Column(db.Integer, nullable=False, default=3000)
    volume_count = db.Column(db.Integer, nullable=False, default=1)
    style_guide_json = db.Column(db.Text, nullable=True)  # POV, tone, platform style, taboos
    settings_json = db.Column(db.Text, nullable=True)  # World-building, genre-specific config
    knowledge_update_mode = db.Column(db.String(20), nullable=False, default='ai_confirm')
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
```

### NovelOutlineNode

```python
class NovelOutlineNode(db.Model):
    __tablename__ = 'novel_outline_nodes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('novel_outline_nodes.id'), nullable=True)
    node_type = db.Column(db.String(20), nullable=False)  # book/volume/section/chapter/scene
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    target_words = db.Column(db.Integer, nullable=True)
    plot_goal = db.Column(db.Text, nullable=True)
    conflict_goal = db.Column(db.Text, nullable=True)
    characters_json = db.Column(db.Text, nullable=True)  # List of entity IDs
    events_json = db.Column(db.Text, nullable=True)  # List of event IDs
    foreshadowing_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planning')
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
```

### NovelChapter + NovelChapterVersion

```python
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
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


class NovelChapterVersion(db.Model):
    __tablename__ = 'novel_chapter_versions'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=False)
    version_type = db.Column(db.String(30), nullable=False, default='custom')
    title = db.Column(db.String(200), nullable=True)
    content_markdown = db.Column(db.Text, nullable=False, default='')
    prompt_json = db.Column(db.Text, nullable=True)  # Stored prompt used
    context_snapshot_json = db.Column(db.Text, nullable=True)  # Context hash for cache
    model = db.Column(db.String(100), nullable=True)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=now)
```

### NovelEntity + NovelRelation

```python
class NovelEntity(db.Model):
    __tablename__ = 'novel_entities'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # character/faction/location/item/rule
    name = db.Column(db.String(100), nullable=False)
    aliases_json = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    attributes_json = db.Column(db.Text, nullable=True)  # Type-specific attributes
    importance = db.Column(db.Integer, nullable=False, default=5)  # 1-10
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


class NovelRelation(db.Model):
    __tablename__ = 'novel_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    target_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    relation_type = db.Column(db.String(30), nullable=False)
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    strength = db.Column(db.Float, nullable=False, default=0.5)  # 0-1
    status = db.Column(db.String(20), nullable=False, default='active')
    evidence_json = db.Column(db.Text, nullable=True)  # Chapter references
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
```

### NovelEvent + NovelEventRelation

```python
class NovelEvent(db.Model):
    __tablename__ = 'novel_events'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(20), nullable=False, default='event')
    timeline_order = db.Column(db.Float, nullable=False, default=0)
    participants_json = db.Column(db.Text, nullable=True)  # List of entity IDs
    location_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=True)
    effects_json = db.Column(db.Text, nullable=True)
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


class NovelEventRelation(db.Model):
    __tablename__ = 'novel_event_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    target_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    relation_type = db.Column(db.String(20), nullable=False)  # causes/blocks/drives/reverses/reveals/recycles/escalates/resolves
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=1.0)  # 0-1, lower for AI-generated
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
```

### NovelGraphChange + NovelGeneration

```python
class NovelGraphChange(db.Model):
    __tablename__ = 'novel_graph_changes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    change_type = db.Column(db.String(10), nullable=False)  # add/modify/delete
    target_type = db.Column(db.String(20), nullable=False)  # entity/relation/event/event_relation
    target_id = db.Column(db.Integer, nullable=True)  # Null for add
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(20), nullable=False, default='manual')
    confidence = db.Column(db.Float, nullable=True)
    accepted = db.Column(db.Boolean, nullable=True)  # Null=pending, True=accepted, False=rejected
    created_at = db.Column(db.DateTime, default=now)


class NovelGeneration(db.Model):
    __tablename__ = 'novel_generations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    generation_type = db.Column(db.String(30), nullable=False)  # blueprint/chapter_version/review/extract/summary
    target_id = db.Column(db.Integer, nullable=True)  # chapter_id or project_id
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/running/completed/failed
    progress = db.Column(db.Integer, nullable=False, default=0)  # 0-100
    result_json = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=now)
    completed_at = db.Column(db.DateTime, nullable=True)
```

## API Routes

### Projects (`/api/novels`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels` | List projects (pagination, status filter) |
| POST | `/api/novels` | Create project |
| GET | `/api/novels/<id>` | Get project with progress stats |
| PUT | `/api/novels/<id>` | Update project settings |
| DELETE | `/api/novels/<id>` | Delete project (cascade all) |

### Outline (`/api/novels/<id>/outline`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/<id>/outline` | Get outline tree |
| POST | `/api/novels/<id>/outline` | Create outline node |
| PUT | `/api/novels/<id>/outline/<nid>` | Update node |
| DELETE | `/api/novels/<id>/outline/<nid>` | Delete node |
| POST | `/api/novels/<id>/blueprint/generate` | AI generate full blueprint (async) |

### Chapters (`/api/novels/<id>/chapters`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/<id>/chapters` | List chapters |
| POST | `/api/novels/<id>/chapters` | Create chapter |
| GET | `/api/novels/<id>/chapters/<cid>` | Get chapter detail |
| PUT | `/api/novels/<id>/chapters/<cid>` | Update chapter content |
| POST | `/api/novels/<id>/chapters/<cid>/confirm` | Confirm as final draft |
| POST | `/api/novels/<id>/chapters/<cid>/generate-versions` | AI multi-version generate (async) |
| GET | `/api/novels/<id>/chapters/<cid>/versions` | List versions |
| POST | `/api/novels/<id>/chapters/<cid>/versions/<vid>/accept` | Accept version |
| DELETE | `/api/novels/<id>/chapters/<cid>/versions/<vid>` | Delete version |

### Entities (`/api/novels/<id>/entities`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/<id>/entities` | List entities (type filter) |
| POST | `/api/novels/<id>/entities` | Create entity |
| GET | `/api/novels/<id>/entities/<eid>` | Get entity |
| PUT | `/api/novels/<id>/entities/<eid>` | Update entity |
| DELETE | `/api/novels/<id>/entities/<eid>` | Delete entity |
| GET | `/api/novels/<id>/relations` | List relations |
| POST | `/api/novels/<id>/relations` | Create relation |
| PUT | `/api/novels/<id>/relations/<rid>` | Update relation |
| DELETE | `/api/novels/<id>/relations/<rid>` | Delete relation |

### Events (`/api/novels/<id>/events`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/<id>/events` | List events |
| POST | `/api/novels/<id>/events` | Create event |
| GET | `/api/novels/<id>/events/<eid>` | Get event |
| PUT | `/api/novels/<id>/events/<eid>` | Update event |
| DELETE | `/api/novels/<id>/events/<eid>` | Delete event |
| POST | `/api/novels/<id>/event-relations` | Create event relation |
| PUT | `/api/novels/<id>/event-relations/<rid>` | Update event relation |
| DELETE | `/api/novels/<id>/event-relations/<rid>` | Delete event relation |

### Graph & AI (`/api/novels/<id>/graph`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/<id>/graph/characters` | Character graph data (nodes + edges) |
| GET | `/api/novels/<id>/graph/events` | Event graph data (nodes + edges) |
| PUT | `/api/novels/<id>/graph/layout` | Batch update node positions |
| POST | `/api/novels/<id>/chapters/<cid>/extract-graph` | AI extract graph candidates (async) |
| POST | `/api/novels/<id>/graph-changes/<gid>/accept` | Accept graph change |
| POST | `/api/novels/<id>/graph-changes/<gid>/reject` | Reject graph change |
| POST | `/api/novels/<id>/chapters/<cid>/review` | AI consistency review (async) |

### Generation Status

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/novels/generations/<gid>` | Get generation status |
| GET | `/api/novels/generations/<gid>/stream` | SSE stream for generation progress |

## AI Service Layer

### Context Builder (`context_builder.py`)

Assembles context for chapter generation with budget control:

| Component | Budget | Priority |
|-----------|--------|----------|
| Project settings | 500-1000 chars | 6 (lowest) |
| World-building | 800-1500 chars | 5 |
| Character cards | 200-500 chars each | 3 |
| Previous summaries | 1000-2500 chars | 4 |
| Current text tail | 2000-4000 chars | 1 (highest) |
| Event causality | 800-1500 chars | 2 |
| User instruction | Unlimited | 0 (override) |

Truncation strategy: summarize long items, select most relevant characters by chapter association.

### Chapter Generator (`chapter_generator.py`)

1. Acquire Redis lock for chapter
2. Build context via `context_builder`
3. Call `ModelProvider.complete()` with assembled prompt
4. Parse response: content, summary, metadata
5. Store version in `NovelChapterVersion`
6. Release lock

### Version Generator (`version_generator.py`)

Generates 1-6 versions per chapter with different narrative directions:
- steady: balanced progression
- conflict: maximize tension
- climax: power fantasy / payoff
- suspense: mystery and twists
- romance: emotional focus
- polish: style refinement

Each uses a different system prompt prefix while sharing the same context.

### Blueprint Generator (`blueprint_generator.py`)

Input: premise, genre, target words, target chapters, style
Output: Creates project + outline tree + initial character entities

Steps:
1. Generate novel synopsis and structure via LLM
2. Create `NovelProject`
3. Create `NovelOutlineNode` tree (book → volume → chapter)
4. Create initial `NovelEntity` records for main characters
5. Create initial `NovelRelation` records

### Graph Extractor (`graph_extractor.py`)

From chapter text, extract candidates:
- New characters (name, type, summary)
- New relationships (source, target, type, description)
- New events (title, summary, type, participants)
- New causality edges (source event, target event, type)
- Character state changes (location, affiliation, mood)
- Relationship changes (type shift, status change)

Returns list of `NovelGraphChange` records with confidence scores.

### Consistency Reviewer (`consistency_reviewer.py`)

Checks against project knowledge base:
- Character consistency (personality, abilities, behavior)
- World-building rules (no violations of established rules)
- Timeline coherence (no temporal contradictions)
- Location logic (characters at correct locations)
- Event causality (no broken chains)
- Foreshadowing tracking (no forgotten setups)
- Plot progression (chapter advances conflicts)
- Redundancy detection (no repetition with prior chapters)
- Padding detection (filler content flagging)

Returns structured list of issues with severity, location, description, and fix suggestion.

### Prompt Templates (`prompt_templates.py`)

Genre-specific prompt templates stored as Python dicts:
- Each genre has: system prompt, chapter generation prompt, review criteria
- Templates can be overridden by `style_guide_json` on the project
- Version type modifiers adjust the system prompt for different narrative directions

## Async Generation

### Pattern

Follows the same pattern as `video_job.py`:
1. Route handler creates `NovelGeneration` record (status=pending)
2. Starts `threading.Thread` targeting the generation function
3. Thread updates `NovelGeneration` status and Redis key
4. Frontend polls `GET /api/novels/generations/<id>` or subscribes to SSE

### Redis Keys

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `novel:generation:{id}` | Generation task state (JSON) | 1 hour |
| `novel:versions:{chapter_id}:{hash}` | Cached version results | 24 hours |
| `novel:extract:{chapter_id}:lock` | Prevent concurrent extraction | 5 min |
| `novel:review:{chapter_id}:{hash}` | Cached review results | 1 hour |
| `novel:active_tasks:{project_id}` | Active task count | Auto-expire |
| `ratelimit:novel-generate:{ip}` | Rate limiting | 1 min |

### Concurrency Control

- Same chapter: only 1 generation at a time (Redis lock)
- Same project: max 3 concurrent generations (Redis counter)
- Per IP: 10 generation requests per minute (rate limiter)

## Integration

### app.py Registration

```python
from server.routes.novels import novels_bp
app.register_blueprint(novels_bp)
```

### models/__init__.py

Add all novel model imports and exports.

## Testing

### Test Files

```
server/tests/
├── test_novel_project.py      # Project CRUD
├── test_novel_outline.py      # Outline tree operations
├── test_novel_chapter.py      # Chapter + version management
├── test_novel_entity.py       # Entity + relation CRUD
├── test_novel_event.py        # Event + event-relation CRUD
├── test_novel_graph.py        # Graph queries + changes
├── test_novel_context_builder.py  # Context assembly
└── test_novel_prompt_templates.py # Prompt template logic
```

### Test Approach

- SQLite in-memory database for all tests
- Mock `ModelProvider.complete()` to avoid real LLM calls
- Fixtures: Flask app, sample project, sample characters, sample chapters
- Each test file is independent, creates its own test data
