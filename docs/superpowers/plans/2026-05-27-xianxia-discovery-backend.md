# 修仙短视频热点采集 - 后端实现计划（Phase 1 MVP）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现热点采集功能的后端：手动 URL 导入 + YouTube API 搜索 + 修仙相关性评分 + LLM 原创脚本生成 + 一键创建 Text。

**Architecture:** 将 `server/models.py` 重构为目录结构以容纳新模型；新增 `server/services/discovery/` 目录实现 Connector 抽象层和评分/分析服务；新增 `server/routes/discovery.py` 提供 REST API。所有新代码遵循现有 Flask-SQLAlchemy + Blueprint 模式。

**Tech Stack:** Flask, Flask-SQLAlchemy, pytest, requests, YouTube Data API v3, LLM provider (via model_registry)

**Spec:** `docs/superpowers/specs/2026-05-27-xianxia-discovery-backend-design.md`

---

## 文件变更清单

### 新建文件
- `server/models/__init__.py` — 统一导出 db + 所有模型
- `server/models/base.py` — db = SQLAlchemy() 实例
- `server/models/text.py` — Text, Tag, text_tags
- `server/models/folder.py` — Folder
- `server/models/video.py` — VideoTemplate, VideoJob, VideoAsset
- `server/models/provider.py` — CustomProvider
- `server/models/discovery.py` — DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis
- `server/services/discovery/__init__.py` — 注册所有 connector
- `server/services/discovery/base.py` — DiscoveryConnector ABC
- `server/services/discovery/registry.py` — ConnectorRegistry
- `server/services/discovery/manual_url.py` — ManualUrlConnector
- `server/services/discovery/youtube.py` — YoutubeConnector
- `server/services/discovery/scoring.py` — 相关性评分
- `server/services/discovery/analyzer.py` — LLM 分析
- `server/services/discovery/script_adapter.py` — DiscoveryItem → Text
- `server/routes/discovery.py` — discovery_bp 蓝图
- `server/tests/test_discovery_models.py`
- `server/tests/test_discovery_scoring.py`
- `server/tests/test_discovery_connector.py`
- `server/tests/test_discovery_routes.py`

### 修改文件
- `server/models.py` — 删除（替换为 models/ 目录）
- `server/app.py` — 新增 seed_discovery_sources + discovery_bp 注册
- `server/tests/conftest.py` — 新增 seed_discovery_sources 调用

---

## Task 1: 重构 models.py 为目录结构

**目标：** 将 `server/models.py` 拆分为 `server/models/` 目录，保持所有现有 import 路径不变。

**Files:**
- Delete: `server/models.py`
- Create: `server/models/__init__.py`
- Create: `server/models/base.py`
- Create: `server/models/text.py`
- Create: `server/models/folder.py`
- Create: `server/models/video.py`
- Create: `server/models/provider.py`
- Test: `server/tests/test_models.py`（已有，用于回归验证）

- [ ] **Step 1: 创建 server/models/base.py**

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

- [ ] **Step 2: 创建 server/models/text.py**

```python
from datetime import datetime, timezone
from server.models.base import db

text_tags = db.Table(
    'text_tags',
    db.Column('text_id', db.Integer, db.ForeignKey('texts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
)


class Text(db.Model):
    __tablename__ = 'texts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名')
    content = db.Column(db.Text, nullable=False, default='')
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    folder = db.relationship('Folder', backref=db.backref('texts', lazy=True))
    tags = db.relationship('Tag', secondary=text_tags, backref=db.backref('texts', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'folder_id': self.folder_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': [tag.to_dict() for tag in self.tags],
        }


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}
```

- [ ] **Step 3: 创建 server/models/folder.py**

```python
from datetime import datetime, timezone
from server.models.base import db


class Folder(db.Model):
    __tablename__ = 'folders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    parent = db.relationship('Folder', remote_side=[id], backref=db.backref('children', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: 创建 server/models/video.py**

```python
import os
import json
from datetime import datetime, timezone
from server.models.base import db


class VideoTemplate(db.Model):
    __tablename__ = 'video_templates'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    config_json = db.Column(db.Text, nullable=False, default='{}')
    is_builtin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'template_key': self.template_key,
            'name': self.name,
            'config': json.loads(self.config_json) if self.config_json else {},
            'is_builtin': self.is_builtin,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoJob(db.Model):
    __tablename__ = 'video_jobs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False, default='未命名')
    status = db.Column(db.String(20), nullable=False, default='queued')
    progress = db.Column(db.Float, default=0.0)
    stage = db.Column(db.String(50))
    message = db.Column(db.String(500))
    request_json = db.Column(db.Text, nullable=False, default='{}')
    manifest_json = db.Column(db.Text)
    output_path = db.Column(db.String(500))
    video_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'stage': self.stage,
            'message': self.message,
            'error_message': self.error_message,
            'has_video': bool(self.video_path and os.path.exists(self.video_path)),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoAsset(db.Model):
    __tablename__ = 'video_assets'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'asset_type': self.asset_type,
            'filename': self.filename,
            'path': self.path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 5: 创建 server/models/provider.py**

```python
import json
from datetime import datetime, timezone
from server.models.base import db


class CustomProvider(db.Model):
    __tablename__ = 'custom_providers'

    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(500), nullable=False, default='')
    models_json = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'provider_key': self.provider_key,
            'display_name': self.display_name,
            'base_url': self.base_url,
            'models': json.loads(self.models_json) if self.models_json else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 6: 创建 server/models/__init__.py**

```python
from server.models.base import db
from server.models.text import Text, Tag, text_tags
from server.models.folder import Folder
from server.models.video import VideoTemplate, VideoJob, VideoAsset
from server.models.provider import CustomProvider

__all__ = [
    'db',
    'Text', 'Tag', 'text_tags',
    'Folder',
    'VideoTemplate', 'VideoJob', 'VideoAsset',
    'CustomProvider',
]
```

- [ ] **Step 7: 删除旧的 server/models.py**

```bash
rm server/models.py
```

- [ ] **Step 8: 运行回归测试验证**

```bash
uv run pytest server/tests/test_models.py server/tests/test_texts.py server/tests/test_folders.py server/tests/test_tags.py -v
```

Expected: 全部 PASS（import 路径 `from server.models import db, Text, ...` 通过 `__init__.py` 重导出保持不变）

- [ ] **Step 9: 运行全量测试**

```bash
uv run pytest
```

Expected: 全部 PASS

- [ ] **Step 10: 提交**

```bash
git add server/models/ && git rm server/models.py && git commit -m "refactor: split models.py into models/ directory with submodules"
```

---

## Task 2: 新增 Discovery 数据模型

**Files:**
- Create: `server/models/discovery.py`
- Modify: `server/models/__init__.py`
- Test: `server/tests/test_discovery_models.py`

- [ ] **Step 1: 创建 server/models/discovery.py**

```python
from datetime import datetime, timezone
from server.models.base import db


class DiscoverySource(db.Model):
    __tablename__ = 'discovery_sources'

    id = db.Column(db.Integer, primary_key=True)
    platform_key = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    config_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'platform_key': self.platform_key,
            'display_name': self.display_name,
            'is_enabled': self.is_enabled,
            'config': json.loads(self.config_json) if self.config_json else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DiscoveryQuery(db.Model):
    __tablename__ = 'discovery_queries'

    id = db.Column(db.Integer, primary_key=True)
    query_type = db.Column(db.String(20), nullable=False)
    platform_key = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(500), nullable=False)
    filters_json = db.Column(db.Text, default='{}')
    status = db.Column(db.String(20), default='pending')
    item_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'query_type': self.query_type,
            'platform_key': self.platform_key,
            'query_text': self.query_text,
            'filters': json.loads(self.filters_json) if self.filters_json else {},
            'status': self.status,
            'item_count': self.item_count,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiscoveryItem(db.Model):
    __tablename__ = 'discovery_items'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('discovery_queries.id'), nullable=True)
    platform_key = db.Column(db.String(50), nullable=False)
    source_url = db.Column(db.String(1000), nullable=False)
    source_id = db.Column(db.String(200))
    title = db.Column(db.String(500))
    author_name = db.Column(db.String(200))
    cover_url = db.Column(db.String(1000))
    published_at = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    stats_json = db.Column(db.Text, default='{}')
    tags_json = db.Column(db.Text, default='[]')
    raw_json = db.Column(db.Text, default='{}')
    is_favorited = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    query = db.relationship('DiscoveryQuery', backref=db.backref('items', lazy=True))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'query_id': self.query_id,
            'platform_key': self.platform_key,
            'source_url': self.source_url,
            'source_id': self.source_id,
            'title': self.title,
            'author_name': self.author_name,
            'cover_url': self.cover_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'duration': self.duration,
            'stats': json.loads(self.stats_json) if self.stats_json else {},
            'tags': json.loads(self.tags_json) if self.tags_json else [],
            'is_favorited': self.is_favorited,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiscoveryAnalysis(db.Model):
    __tablename__ = 'discovery_analyses'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('discovery_items.id'), unique=True, nullable=False)
    xianxia_score = db.Column(db.Float, default=0.0)
    hot_score = db.Column(db.Float, default=0.0)
    format_score = db.Column(db.Float, default=0.0)
    is_static_image_style = db.Column(db.Boolean, default=False)
    score_reasons_json = db.Column(db.Text, default='[]')
    analysis_json = db.Column(db.Text, default='{}')
    generated_title = db.Column(db.String(500))
    generated_content = db.Column(db.Text)
    recommended_template = db.Column(db.String(50))
    recommended_voice_desc = db.Column(db.String(200))
    recommended_max_chars = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    item = db.relationship('DiscoveryItem', backref=db.backref('analysis', uselist=False))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'item_id': self.item_id,
            'xianxia_score': self.xianxia_score,
            'hot_score': self.hot_score,
            'format_score': self.format_score,
            'is_static_image_style': self.is_static_image_style,
            'score_reasons': json.loads(self.score_reasons_json) if self.score_reasons_json else [],
            'analysis': json.loads(self.analysis_json) if self.analysis_json else {},
            'generated_title': self.generated_title,
            'generated_content': self.generated_content,
            'recommended_template': self.recommended_template,
            'recommended_voice_desc': self.recommended_voice_desc,
            'recommended_max_chars': self.recommended_max_chars,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 2: 更新 server/models/__init__.py**

在现有导入后追加：

```python
from server.models.discovery import DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis
```

在 `__all__` 列表追加：

```python
'DiscoverySource', 'DiscoveryQuery', 'DiscoveryItem', 'DiscoveryAnalysis',
```

- [ ] **Step 3: 创建 server/tests/test_discovery_models.py**

```python
import json
from datetime import datetime, timezone, timedelta
from server.models import (
    db, DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis,
)


def test_discovery_source_create(app, db):
    with app.app_context():
        src = DiscoverySource(platform_key='youtube', display_name='YouTube')
        db.session.add(src)
        db.session.commit()
        assert src.id is not None
        assert src.is_enabled is True


def test_discovery_source_to_dict(app, db):
    with app.app_context():
        src = DiscoverySource(
            platform_key='youtube', display_name='YouTube',
            config_json='{"api_key": "test"}',
        )
        db.session.add(src)
        db.session.commit()
        d = src.to_dict()
        assert d['platform_key'] == 'youtube'
        assert d['config'] == {'api_key': 'test'}


def test_discovery_query_create(app, db):
    with app.app_context():
        q = DiscoveryQuery(
            query_type='keyword', platform_key='youtube',
            query_text='修仙小说', status='pending',
        )
        db.session.add(q)
        db.session.commit()
        assert q.id is not None
        assert q.status == 'pending'
        assert q.item_count == 0


def test_discovery_item_with_query(app, db):
    with app.app_context():
        q = DiscoveryQuery(
            query_type='keyword', platform_key='youtube', query_text='修仙',
        )
        db.session.add(q)
        db.session.flush()

        item = DiscoveryItem(
            query_id=q.id, platform_key='youtube',
            source_url='https://youtube.com/watch?v=abc',
            title='测试视频',
            stats_json='{"views": 1000, "likes": 50}',
            tags_json='["修仙", "重生"]',
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d['stats'] == {'views': 1000, 'likes': 50}
        assert d['tags'] == ['修仙', '重生']
        assert item.query_id == q.id


def test_discovery_item_without_query(app, db):
    with app.app_context():
        item = DiscoveryItem(
            platform_key='manual',
            source_url='https://bilibili.com/video/BV123',
        )
        db.session.add(item)
        db.session.commit()
        assert item.query_id is None


def test_discovery_analysis_one_to_one(app, db):
    with app.app_context():
        item = DiscoveryItem(
            platform_key='manual',
            source_url='https://bilibili.com/video/BV123',
        )
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(
            item_id=item.id,
            xianxia_score=0.86,
            hot_score=0.72,
            format_score=0.5,
            score_reasons_json=json.dumps(['标题命中仙帝/重生']),
            generated_title='原创标题',
            generated_content='原创脚本内容',
            recommended_template='xianxia_narration',
            recommended_voice_desc='沉稳男声',
            recommended_max_chars=16,
        )
        db.session.add(analysis)
        db.session.commit()

        d = analysis.to_dict()
        assert d['xianxia_score'] == 0.86
        assert d['score_reasons'] == ['标题命中仙帝/重生']
        assert d['generated_title'] == '原创标题'

        # Verify one-to-one relationship
        assert item.analysis is not None
        assert item.analysis.id == analysis.id


def test_discovery_analysis_to_dict_empty(app, db):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(item_id=item.id)
        db.session.add(analysis)
        db.session.commit()

        d = analysis.to_dict()
        assert d['score_reasons'] == []
        assert d['analysis'] == {}
        assert d['generated_title'] is None
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest server/tests/test_discovery_models.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: 运行回归测试**

```bash
uv run pytest
```

Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add server/models/discovery.py server/models/__init__.py server/tests/test_discovery_models.py && git commit -m "feat: add DiscoverySource/Query/Item/Analysis models"
```

---

## Task 3: 扩展 Text 模型 + 种子数据

**目标：** 给 Text 模型新增 `source_context_json` 字段，新增 `seed_discovery_sources()` 函数，在 app.py 和 conftest.py 中调用。

**Files:**
- Modify: `server/models/text.py`
- Create: `server/services/discovery_seed.py`
- Modify: `server/app.py`
- Modify: `server/tests/conftest.py`

- [ ] **Step 1: 在 server/models/text.py 的 Text 类中新增字段**

在 `folder_id` 行之后添加：

```python
    source_context_json = db.Column(db.Text, nullable=True)
```

在 `to_dict()` 方法的返回 dict 中，`'tags'` 行之前添加：

```python
            'source_context': json.loads(self.source_context_json) if self.source_context_json else None,
```

并在文件顶部添加 `import json`（如果还没有的话）。

- [ ] **Step 2: 创建 server/services/discovery_seed.py**

```python
from server.models.base import db
from server.models.discovery import DiscoverySource

BUILTIN_SOURCES = [
    {'platform_key': 'manual', 'display_name': '手动链接', 'is_enabled': True},
    {'platform_key': 'youtube', 'display_name': 'YouTube', 'is_enabled': True},
    {'platform_key': 'douyin', 'display_name': '抖音', 'is_enabled': False},
    {'platform_key': 'bilibili', 'display_name': 'B站', 'is_enabled': False},
    {'platform_key': 'kuaishou', 'display_name': '快手', 'is_enabled': False},
]


def seed_discovery_sources():
    for src in BUILTIN_SOURCES:
        existing = DiscoverySource.query.filter_by(platform_key=src['platform_key']).first()
        if not existing:
            db.session.add(DiscoverySource(**src))
    db.session.commit()
```

- [ ] **Step 3: 更新 server/app.py**

在 `from server.services.video_template import seed_builtin_templates` 之后添加：

```python
        from server.services.discovery_seed import seed_discovery_sources
```

在 `seed_builtin_templates()` 调用之后添加：

```python
        seed_discovery_sources()
```

在蓝图注册区域添加：

```python
        from server.routes.discovery import discovery_bp
        app.register_blueprint(discovery_bp)
```

- [ ] **Step 4: 更新 server/tests/conftest.py**

在 `seed_builtin_templates()` 之后添加：

```python
        from server.services.discovery_seed import seed_discovery_sources
        seed_discovery_sources()
```

- [ ] **Step 5: 运行回归测试**

```bash
uv run pytest
```

Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add server/models/text.py server/services/discovery_seed.py server/app.py server/tests/conftest.py && git commit -m "feat: add source_context_json to Text, seed discovery sources"
```

---

## Task 4: Connector 基类与 Registry

**Files:**
- Create: `server/services/discovery/__init__.py`
- Create: `server/services/discovery/base.py`
- Create: `server/services/discovery/registry.py`
- Test: `server/tests/test_discovery_connector.py`

- [ ] **Step 1: 创建 server/services/discovery/base.py**

```python
from abc import ABC, abstractmethod


class DiscoveryConnector(ABC):
    platform_key: str
    display_name: str

    @abstractmethod
    def search(self, query: str, limit: int, filters: dict | None = None) -> list[dict]:
        """关键词搜索，返回 DiscoveryItem 字典列表"""
        ...

    @abstractmethod
    def resolve_url(self, url: str) -> dict:
        """解析单个 URL，返回 DiscoveryItem 字典"""
        ...

    def is_available(self) -> bool:
        """检查平台是否可用（API key 配置等）"""
        return True
```

- [ ] **Step 2: 创建 server/services/discovery/registry.py**

```python
from server.services.discovery.base import DiscoveryConnector


class ConnectorRegistry:
    _connectors: dict[str, DiscoveryConnector] = {}

    @classmethod
    def register(cls, connector: DiscoveryConnector):
        cls._connectors[connector.platform_key] = connector

    @classmethod
    def get(cls, platform_key: str) -> DiscoveryConnector | None:
        return cls._connectors.get(platform_key)

    @classmethod
    def get_all(cls) -> dict[str, DiscoveryConnector]:
        return dict(cls._connectors)

    @classmethod
    def clear(cls):
        """用于测试"""
        cls._connectors.clear()
```

- [ ] **Step 3: 创建 server/services/discovery/__init__.py（空占位）**

```python
```

- [ ] **Step 4: 编写 Connector 测试**

创建 `server/tests/test_discovery_connector.py`：

```python
import pytest
from server.services.discovery.base import DiscoveryConnector
from server.services.discovery.registry import ConnectorRegistry


class DummyConnector(DiscoveryConnector):
    platform_key = 'dummy'
    display_name = 'Dummy'

    def search(self, query, limit, filters=None):
        return [{'title': f'result for {query}', 'platform_key': 'dummy'}]

    def resolve_url(self, url):
        return {'title': 'resolved', 'platform_key': 'dummy', 'source_url': url}


@pytest.fixture(autouse=True)
def clear_registry():
    ConnectorRegistry.clear()
    yield
    ConnectorRegistry.clear()


def test_register_and_get():
    conn = DummyConnector()
    ConnectorRegistry.register(conn)
    assert ConnectorRegistry.get('dummy') is conn


def test_get_nonexistent():
    assert ConnectorRegistry.get('nonexistent') is None


def test_get_all():
    conn = DummyConnector()
    ConnectorRegistry.register(conn)
    all_conns = ConnectorRegistry.get_all()
    assert 'dummy' in all_conns
    assert len(all_conns) == 1


def test_connector_search():
    conn = DummyConnector()
    results = conn.search('test query', 10)
    assert len(results) == 1
    assert results[0]['title'] == 'result for test query'


def test_connector_resolve_url():
    conn = DummyConnector()
    result = conn.resolve_url('https://example.com/video/123')
    assert result['source_url'] == 'https://example.com/video/123'


def test_connector_is_available():
    conn = DummyConnector()
    assert conn.is_available() is True


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        DiscoveryConnector()
```

- [ ] **Step 5: 运行测试**

```bash
uv run pytest server/tests/test_discovery_connector.py -v
```

Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add server/services/discovery/ server/tests/test_discovery_connector.py && git commit -m "feat: add DiscoveryConnector ABC and ConnectorRegistry"
```

---

## Task 5: ManualUrlConnector

**Files:**
- Create: `server/services/discovery/manual_url.py`
- Modify: `server/services/discovery/__init__.py`
- Modify: `server/tests/test_discovery_connector.py`

- [ ] **Step 1: 创建 server/services/discovery/manual_url.py**

```python
import re
import requests
from server.services.discovery.base import DiscoveryConnector

URL_PATTERNS = {
    'douyin': re.compile(r'douyin\.com/video/(\d+)'),
    'bilibili': re.compile(r'bilibili\.com/video/(BV\w+)'),
    'youtube': re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)'),
    'kuaishou': re.compile(r'kuaishou\.com/short-video/(\w+)'),
}

PLATFORM_NAMES = {
    'douyin': '抖音',
    'bilibili': 'B站',
    'youtube': 'YouTube',
    'kuaishou': '快手',
}


def _detect_platform(url: str) -> tuple[str | None, str | None]:
    """返回 (platform_key, source_id) 或 (None, None)"""
    for platform, pattern in URL_PATTERNS.items():
        match = pattern.search(url)
        if match:
            return platform, match.group(1)
    return None, None


def _fetch_youtube_oembed(video_id: str) -> dict:
    """通过 YouTube oEmbed 获取标题和封面"""
    try:
        resp = requests.get(
            'https://www.youtube.com/oembed',
            params={'url': f'https://www.youtube.com/watch?v={video_id}', 'format': 'json'},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            return {
                'title': data.get('title'),
                'author_name': data.get('author_name'),
                'cover_url': data.get('thumbnail_url'),
            }
    except Exception:
        pass
    return {}


def _fetch_page_meta(url: str) -> dict:
    """通过 HTTP GET 获取页面 og:title 和 og:image"""
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; VideoScriptBot/1.0)',
        })
        if not resp.ok:
            return {}
        html = resp.text
        title = None
        cover_url = None

        # og:title
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
        if not match:
            match = re.search(r'<meta\s+content="([^"]*)"\s+property="og:title"', html)
        if match:
            title = match.group(1)
        elif '<title>' in html:
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                title = match.group(1)

        # og:image
        match = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', html)
        if not match:
            match = re.search(r'<meta\s+content="([^"]*)"\s+property="og:image"', html)
        if match:
            cover_url = match.group(1)

        return {'title': title, 'cover_url': cover_url}
    except Exception:
        return {}


class ManualUrlConnector(DiscoveryConnector):
    platform_key = 'manual'
    display_name = '手动链接'

    def search(self, query, limit, filters=None):
        raise NotImplementedError('手动链接不支持关键词搜索')

    def resolve_url(self, url: str) -> dict:
        platform, source_id = _detect_platform(url)

        if not platform:
            return {
                'platform_key': 'manual',
                'source_url': url,
                'source_id': None,
            }

        item = {
            'platform_key': platform,
            'source_url': url,
            'source_id': source_id,
        }

        if platform == 'youtube':
            meta = _fetch_youtube_oembed(source_id)
        else:
            meta = _fetch_page_meta(url)

        item.update({k: v for k, v in meta.items() if v})
        return item
```

- [ ] **Step 2: 更新 server/services/discovery/__init__.py**

```python
from server.services.discovery.registry import ConnectorRegistry
from server.services.discovery.manual_url import ManualUrlConnector

ConnectorRegistry.register(ManualUrlConnector())
```

- [ ] **Step 3: 在测试文件中追加 ManualUrl 测试**

在 `server/tests/test_discovery_connector.py` 末尾追加：

```python
from server.services.discovery.manual_url import ManualUrlConnector, _detect_platform


def test_detect_platform_youtube():
    platform, vid = _detect_platform('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    assert platform == 'youtube'
    assert vid == 'dQw4w9WgXcQ'


def test_detect_platform_youtube_short():
    platform, vid = _detect_platform('https://youtu.be/dQw4w9WgXcQ')
    assert platform == 'youtube'
    assert vid == 'dQw4w9WgXcQ'


def test_detect_platform_bilibili():
    platform, vid = _detect_platform('https://www.bilibili.com/video/BV1xx411c7mD')
    assert platform == 'bilibili'
    assert vid == 'BV1xx411c7mD'


def test_detect_platform_douyin():
    platform, vid = _detect_platform('https://www.douyin.com/video/7123456789')
    assert platform == 'douyin'
    assert vid == '7123456789'


def test_detect_platform_kuaishou():
    platform, vid = _detect_platform('https://www.kuaishou.com/short-video/abc123')
    assert platform == 'kuaishou'
    assert vid == 'abc123'


def test_detect_platform_unknown():
    platform, vid = _detect_platform('https://example.com/video/123')
    assert platform is None
    assert vid is None


def test_manual_url_search_raises():
    conn = ManualUrlConnector()
    with pytest.raises(NotImplementedError):
        conn.search('test', 10)


def test_manual_url_resolve_unknown():
    conn = ManualUrlConnector()
    result = conn.resolve_url('https://example.com/video/123')
    assert result['platform_key'] == 'manual'
    assert result['source_url'] == 'https://example.com/video/123'
    assert result.get('source_id') is None
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest server/tests/test_discovery_connector.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add server/services/discovery/manual_url.py server/services/discovery/__init__.py server/tests/test_discovery_connector.py && git commit -m "feat: add ManualUrlConnector with platform URL detection"
```

---

## Task 6: YoutubeConnector

**Files:**
- Create: `server/services/discovery/youtube.py`
- Modify: `server/services/discovery/__init__.py`
- Modify: `server/tests/test_discovery_connector.py`

- [ ] **Step 1: 创建 server/services/discovery/youtube.py**

```python
import requests
from datetime import datetime, timezone, timedelta
from server.services.discovery.base import DiscoveryConnector
from server.models.discovery import DiscoverySource

YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_VIDEOS_URL = 'https://www.googleapis.com/youtube/v3/videos'

DURATION_MAP = {
    'short': 'short',    # < 4 min
    'medium': 'medium',  # 4-20 min
    'long': 'long',      # > 20 min
}


def _parse_duration(iso_duration: str) -> float | None:
    """Parse ISO 8601 duration (PT1M30S) to seconds."""
    if not iso_duration:
        return None
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YoutubeConnector(DiscoveryConnector):
    platform_key = 'youtube'
    display_name = 'YouTube'

    def __init__(self, api_key: str = ''):
        self._api_key = api_key

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        src = DiscoverySource.query.filter_by(platform_key='youtube').first()
        if src:
            import json
            config = json.loads(src.config_json) if src.config_json else {}
            return config.get('api_key', '')
        return ''

    def is_available(self) -> bool:
        return bool(self._get_api_key())

    def search(self, query, limit=20, filters=None):
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError('YouTube API key 未配置')

        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': min(limit, 50),
            'key': api_key,
        }

        if filters:
            if filters.get('order'):
                params['order'] = filters['order']
            if filters.get('published_days'):
                since = datetime.now(timezone.utc) - timedelta(days=filters['published_days'])
                params['publishedAfter'] = since.strftime('%Y-%m-%dT%H:%M:%SZ')
            if filters.get('duration') and filters['duration'] in DURATION_MAP:
                params['videoDuration'] = DURATION_MAP[filters['duration']]

        resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
        if not resp.ok:
            error = resp.json().get('error', {}).get('message', resp.text)
            raise RuntimeError(f'YouTube API 错误: {error}')

        data = resp.json()
        video_ids = [item['id']['videoId'] for item in data.get('items', [])]
        if not video_ids:
            return []

        # Fetch details for statistics and duration
        details = self._fetch_video_details(video_ids, api_key)
        details_map = {d['id']: d for d in details}

        results = []
        for item in data.get('items', []):
            vid = item['id']['videoId']
            snippet = item.get('snippet', {})
            detail = details_map.get(vid, {})
            stats = detail.get('statistics', {})
            content = detail.get('contentDetails', {})

            results.append({
                'platform_key': 'youtube',
                'source_url': f'https://www.youtube.com/watch?v={vid}',
                'source_id': vid,
                'title': snippet.get('title'),
                'author_name': snippet.get('channelTitle'),
                'cover_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'published_at': snippet.get('publishedAt'),
                'duration': _parse_duration(content.get('duration')),
                'stats': {
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                },
                'tags': snippet.get('tags', []),
            })

        return results

    def resolve_url(self, url: str) -> dict:
        import re
        match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
        if not match:
            raise ValueError(f'无效的 YouTube URL: {url}')

        video_id = match.group(1)
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError('YouTube API key 未配置')

        details = self._fetch_video_details([video_id], api_key)
        if not details:
            raise RuntimeError(f'无法获取视频信息: {video_id}')

        detail = details[0]
        snippet = detail.get('snippet', {})
        stats = detail.get('statistics', {})
        content = detail.get('contentDetails', {})

        return {
            'platform_key': 'youtube',
            'source_url': url,
            'source_id': video_id,
            'title': snippet.get('title'),
            'author_name': snippet.get('channelTitle'),
            'cover_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'published_at': snippet.get('publishedAt'),
            'duration': _parse_duration(content.get('duration')),
            'stats': {
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments': int(stats.get('commentCount', 0)),
            },
            'tags': snippet.get('tags', []),
        }

    def _fetch_video_details(self, video_ids: list[str], api_key: str) -> list[dict]:
        resp = requests.get(YOUTUBE_VIDEOS_URL, params={
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
            'key': api_key,
        }, timeout=15)
        if not resp.ok:
            return []
        return resp.json().get('items', [])
```

- [ ] **Step 2: 更新 server/services/discovery/__init__.py**

在现有内容后追加：

```python
from server.services.discovery.youtube import YoutubeConnector
ConnectorRegistry.register(YoutubeConnector())
```

- [ ] **Step 3: 追加 YouTube 测试**

在 `server/tests/test_discovery_connector.py` 末尾追加：

```python
from unittest.mock import patch, MagicMock
from server.services.discovery.youtube import YoutubeConnector, _parse_duration


def test_parse_duration():
    assert _parse_duration('PT1M30S') == 90
    assert _parse_duration('PT2H1M') == 7260
    assert _parse_duration('PT30S') == 30
    assert _parse_duration('PT1H') == 3600
    assert _parse_duration('') is None
    assert _parse_duration(None) is None


def test_youtube_not_available_without_key():
    conn = YoutubeConnector()
    with patch('server.services.discovery.youtube.DiscoverySource') as mock_src:
        mock_src.query.filter_by.return_value.first.return_value = None
        assert conn.is_available() is False


def test_youtube_search_raises_without_key():
    conn = YoutubeConnector()
    with patch('server.services.discovery.youtube.DiscoverySource') as mock_src:
        mock_src.query.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match='API key'):
            conn.search('test', 10)


@patch('server.services.discovery.youtube.requests.get')
def test_youtube_search_success(mock_get):
    # Mock search response
    search_resp = MagicMock(ok=True)
    search_resp.json.return_value = {
        'items': [{
            'id': {'videoId': 'abc123'},
            'snippet': {
                'title': '测试修仙视频',
                'channelTitle': '测试频道',
                'publishedAt': '2026-05-20T00:00:00Z',
                'thumbnails': {'high': {'url': 'https://img.youtube.com/vi/abc123/hqdefault.jpg'}},
                'tags': ['修仙'],
            },
        }],
    }

    # Mock videos detail response
    detail_resp = MagicMock(ok=True)
    detail_resp.json.return_value = {
        'items': [{
            'id': 'abc123',
            'snippet': {
                'title': '测试修仙视频',
                'channelTitle': '测试频道',
                'publishedAt': '2026-05-20T00:00:00Z',
                'thumbnails': {'high': {'url': 'https://img.youtube.com/vi/abc123/hqdefault.jpg'}},
                'tags': ['修仙'],
            },
            'statistics': {'viewCount': '10000', 'likeCount': '500', 'commentCount': '30'},
            'contentDetails': {'duration': 'PT2M30S'},
        }],
    }

    mock_get.side_effect = [search_resp, detail_resp]

    conn = YoutubeConnector(api_key='test-key')
    results = conn.search('修仙小说', 10)

    assert len(results) == 1
    assert results[0]['title'] == '测试修仙视频'
    assert results[0]['stats']['views'] == 10000
    assert results[0]['duration'] == 150
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest server/tests/test_discovery_connector.py -v
```

Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add server/services/discovery/youtube.py server/services/discovery/__init__.py server/tests/test_discovery_connector.py && git commit -m "feat: add YoutubeConnector with search and resolve_url"
```

---

## Task 7: 评分服务

**Files:**
- Create: `server/services/discovery/scoring.py`
- Test: `server/tests/test_discovery_scoring.py`

- [ ] **Step 1: 创建 server/services/discovery/scoring.py**

```python
from datetime import datetime, timezone

LEVEL1_KEYWORDS = {'修仙': 0.3, '玄幻': 0.3, '仙帝': 0.3, '仙尊': 0.3, '重生': 0.3, '渡劫': 0.3}
LEVEL2_KEYWORDS = {'炼气': 0.15, '筑基': 0.15, '金丹': 0.15, '元婴': 0.15, '宗门': 0.15,
                   '师尊': 0.15, '女帝': 0.15, '系统': 0.1, '逆袭': 0.15}
STRUCTURE_KEYWORDS = {'开局': 0.2, '我竟然': 0.2, '一口气看完': 0.2, '穿越成': 0.2,
                      '被逐出宗门': 0.2, '三千年后归来': 0.2}

FORMAT_KEYWORDS = {'有声小说': 0.4, '小说推文': 0.4, '一张图': 0.4, '书荒推荐': 0.4,
                   '一口气看完': 0.3, '完整版': 0.3, '全集': 0.3}

PLATFORM_VIEW_BASELINES = {
    'youtube': 100_000,
    'bilibili': 500_000,
    'douyin': 500_000,
    'kuaishou': 500_000,
    'manual': 100_000,
}


def _match_keywords(text: str, keywords: dict[str, float]) -> float:
    score = 0.0
    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight
    return min(score, 1.0)


def score_xianxia(title: str, tags: list[str]) -> tuple[float, list[str]]:
    """计算修仙相关性评分"""
    combined = title + ' '.join(tags)
    reasons = []

    s1 = _match_keywords(combined, LEVEL1_KEYWORDS)
    if s1 > 0:
        hit = [k for k in LEVEL1_KEYWORDS if k in combined]
        reasons.append(f'一级关键词命中: {"/".join(hit)}')

    s2 = _match_keywords(combined, LEVEL2_KEYWORDS)
    if s2 > 0:
        hit = [k for k in LEVEL2_KEYWORDS if k in combined]
        reasons.append(f'二级关键词命中: {"/".join(hit)}')

    s3 = _match_keywords(combined, STRUCTURE_KEYWORDS)
    if s3 > 0:
        hit = [k for k in STRUCTURE_KEYWORDS if k in combined]
        reasons.append(f'结构词命中: {"/".join(hit)}')

    total = min(s1 + s2 + s3, 1.0)
    return total, reasons


def score_hot(stats: dict, platform_key: str, published_at=None) -> tuple[float, list[str]]:
    """计算热度评分"""
    reasons = []
    baseline = PLATFORM_VIEW_BASELINES.get(platform_key, 100_000)

    views = stats.get('views', 0)
    likes = stats.get('likes', 0)
    comments = stats.get('comments', 0)
    shares = stats.get('shares', 0)

    # View score (normalized)
    view_score = min(views / baseline, 1.0)

    # Engagement rate
    engagement = 0.0
    if views > 0:
        engagement = min((likes + comments + shares) / views, 0.3)

    # Time decay
    time_multiplier = 1.0
    if published_at:
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                published_at = None
        if published_at:
            days_ago = (datetime.now(timezone.utc) - published_at).days
            if days_ago <= 7:
                time_multiplier = 1.0
                reasons.append('近7天发布')
            elif days_ago <= 30:
                time_multiplier = 0.7
            else:
                time_multiplier = 0.4

    if views > 0:
        reasons.append(f'播放量 {views}')

    total = min((view_score * 0.7 + engagement) * time_multiplier, 1.0)
    return total, reasons


def score_format(title: str, duration: float | None) -> tuple[float, list[str]]:
    """计算单图字幕语音形态评分"""
    reasons = []
    score = 0.0

    # Format keywords
    keyword_score = _match_keywords(title, FORMAT_KEYWORDS)
    if keyword_score > 0:
        score += min(keyword_score, 0.4)
        hit = [k for k in FORMAT_KEYWORDS if k in title]
        reasons.append(f'形态关键词命中: {"/".join(hit)}')

    # Duration check
    if duration is not None and 30 <= duration <= 480:
        score += 0.3
        reasons.append(f'时长 {int(duration)}秒 符合短视频')

    return min(score, 1.0), reasons


def score_item(item: dict) -> dict:
    """综合评分，返回 {xianxia_score, hot_score, format_score, reasons}"""
    title = item.get('title') or ''
    tags = item.get('tags') or []
    stats = item.get('stats') or {}
    platform_key = item.get('platform_key', 'manual')
    duration = item.get('duration')
    published_at = item.get('published_at')

    xianxia, x_reasons = score_xianxia(title, tags)
    hot, h_reasons = score_hot(stats, platform_key, published_at)
    fmt, f_reasons = score_format(title, duration)

    return {
        'xianxia_score': round(xianxia, 2),
        'hot_score': round(hot, 2),
        'format_score': round(fmt, 2),
        'reasons': x_reasons + h_reasons + f_reasons,
    }
```

- [ ] **Step 2: 创建 server/tests/test_discovery_scoring.py**

```python
from datetime import datetime, timezone, timedelta
from server.services.discovery.scoring import (
    score_xianxia, score_hot, score_format, score_item,
)


def test_xianxia_level1_keywords():
    score, reasons = score_xianxia('仙帝重生归来', [])
    assert score >= 0.3
    assert any('一级' in r for r in reasons)


def test_xianxia_level2_keywords():
    score, reasons = score_xianxia('废柴筑基逆袭', [])
    assert score >= 0.15
    assert any('二级' in r for r in reasons)


def test_xianxia_structure_keywords():
    score, reasons = score_xianxia('开局被逐出宗门', [])
    assert score >= 0.2
    assert any('结构' in r for r in reasons)


def test_xianxia_no_match():
    score, reasons = score_xianxia('今天天气真好', [])
    assert score == 0.0
    assert len(reasons) == 0


def test_xianxia_from_tags():
    score, _ = score_xianxia('短视频', ['修仙', '重生'])
    assert score >= 0.3


def test_xianxia_cap_at_1():
    score, _ = score_xianxia('修仙玄幻仙帝仙尊重生渡劫开局穿越成', [])
    assert score <= 1.0


def test_hot_high_views():
    score, reasons = score_hot({'views': 200000, 'likes': 10000, 'comments': 500}, 'youtube')
    assert score > 0.5
    assert any('播放量' in r for r in reasons)


def test_hot_zero_views():
    score, _ = score_hot({'views': 0, 'likes': 0, 'comments': 0}, 'youtube')
    assert score == 0.0


def test_hot_time_decay_recent():
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=3)
    score_recent, reasons = score_hot({'views': 100000}, 'youtube', recent)
    assert any('近7天' in r for r in reasons)

    old = now - timedelta(days=60)
    score_old, _ = score_hot({'views': 100000}, 'youtube', old)
    assert score_recent > score_old


def test_hot_platform_baseline():
    # YouTube baseline is 100k, bilibili is 500k
    score_yt, _ = score_hot({'views': 100000}, 'youtube')
    score_bili, _ = score_hot({'views': 100000}, 'bilibili')
    assert score_yt > score_bili


def test_format_keyword_match():
    score, reasons = score_format('有声小说 修仙', None)
    assert score >= 0.4
    assert any('形态' in r for r in reasons)


def test_format_duration_in_range():
    score, reasons = score_format('普通标题', 120)
    assert score >= 0.3
    assert any('时长' in r for r in reasons)


def test_format_duration_out_of_range():
    score, _ = score_format('普通标题', 10)
    assert score < 0.3


def test_score_item_full():
    item = {
        'title': '仙帝重生归来 有声小说',
        'tags': ['修仙'],
        'stats': {'views': 200000, 'likes': 10000, 'comments': 500},
        'platform_key': 'youtube',
        'duration': 120,
        'published_at': (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    }
    result = score_item(item)
    assert result['xianxia_score'] > 0.5
    assert result['hot_score'] > 0.5
    assert result['format_score'] > 0.5
    assert len(result['reasons']) > 0


def test_score_item_empty():
    item = {'title': '', 'tags': [], 'stats': {}, 'platform_key': 'manual'}
    result = score_item(item)
    assert result['xianxia_score'] == 0.0
    assert result['hot_score'] == 0.0
    assert result['format_score'] == 0.0
```

- [ ] **Step 3: 运行测试**

```bash
uv run pytest server/tests/test_discovery_scoring.py -v
```

Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add server/services/discovery/scoring.py server/tests/test_discovery_scoring.py && git commit -m "feat: add discovery scoring service with xianxia/hot/format scoring"
```

---

## Task 8: LLM 分析 + 脚本适配服务

**Files:**
- Create: `server/services/discovery/analyzer.py`
- Create: `server/services/discovery/script_adapter.py`

- [ ] **Step 1: 创建 server/services/discovery/analyzer.py**

```python
import json
from server.services.model_registry import ModelRegistry

ANALYSIS_SYSTEM_PROMPT = '你是一个修仙短视频小说的选题分析师。根据热门视频的元数据，分析其成功要素，并生成一个原创脚本。所有输出必须是合法的 JSON 格式。'

ANALYSIS_PROMPT_TEMPLATE = '''根据以下热门视频的元数据，分析其成功要素并生成原创脚本。

## 视频信息
- 标题：{title}
- 平台：{platform}
- 时长：{duration}秒
- 播放量：{views}
- 点赞：{likes}
- 评论：{comments}
- 标签：{tags}

## 评分理由
{reasons}

## 要求
1. 分析标题套路（爽点/冲突/身份反转）
2. 分析开头钩子（前3秒要抛出的危机或反差）
3. 提取剧情骨架（主角身份、压迫者、金手指、第一次反击、悬念）
4. 建议字幕节奏（每句12-20字，短句优先）
5. 生成一个原创标题（不要复制原标题，要换人物/换冲突/换世界观）
6. 生成原创脚本正文（分段，每段对应一个字幕时间段，用换行分隔）
7. 推荐视频参数

以 JSON 格式输出，字段如下：
{{
  "title_pattern": "标题套路分析",
  "hook": "开头钩子描述",
  "plot_skeleton": "剧情骨架",
  "subtitle_rhythm": "字幕节奏建议",
  "generated_title": "原创标题",
  "generated_content": "原创脚本正文",
  "recommended_template": "xianxia_narration",
  "recommended_voice_desc": "推荐声线描述",
  "recommended_max_chars": 16
}}'''

# 默认 LLM 配置（MiMo）
DEFAULT_PROVIDER = 'mimo'
DEFAULT_MODEL = 'mimo-v2.5-pro'


def _get_llm_config() -> tuple[str, str, str, str]:
    """获取 LLM 配置：(provider_key, api_key, base_url, model)"""
    from server.models import db
    from server.models.provider import CustomProvider
    from server.models.discovery import DiscoverySource

    # 从 discovery_sources 读取 LLM 配置
    src = DiscoverySource.query.filter_by(platform_key='_llm_config').first()
    if src:
        config = json.loads(src.config_json) if src.config_json else {}
        if config.get('api_key'):
            return (
                config.get('provider_key', DEFAULT_PROVIDER),
                config['api_key'],
                config.get('base_url', ''),
                config.get('model', DEFAULT_MODEL),
            )

    # 从 custom_providers 读取
    cp = CustomProvider.query.first()
    if cp:
        models = json.loads(cp.models_json) if cp.models_json else []
        llm_model = next((m for m in models if 'llm' in str(m.get('capabilities', []))), None)
        if llm_model:
            return (cp.provider_key, '', cp.base_url, llm_model.get('model_key', ''))

    return DEFAULT_PROVIDER, '', '', DEFAULT_MODEL


def analyze_item(item: dict, score_result: dict) -> dict:
    """调用 LLM 分析视频并生成原创脚本"""
    registry = ModelRegistry()
    provider_key, api_key, base_url, model = _get_llm_config()

    if not api_key:
        raise ValueError('LLM API key 未配置。请在模型设置中配置 API key。')

    provider = registry.create_provider(
        provider_key, api_key=api_key, base_url=base_url,
    )

    title = item.get('title') or '未知标题'
    platform = item.get('platform_key', '未知')
    duration = item.get('duration') or 0
    stats = item.get('stats') or {}
    tags = item.get('tags') or []
    reasons = score_result.get('reasons') or []

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        title=title,
        platform=platform,
        duration=int(duration),
        views=stats.get('views', 0),
        likes=stats.get('likes', 0),
        comments=stats.get('comments', 0),
        tags=', '.join(tags),
        reasons='\n'.join(f'- {r}' for r in reasons),
    )

    messages = [{'role': 'user', 'content': prompt}]
    result_text = provider.complete(messages, model, system_prompt=ANALYSIS_SYSTEM_PROMPT, max_tokens=2000)

    # 解析 JSON 响应
    try:
        # 尝试直接解析
        result = json.loads(result_text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result_text, re.DOTALL)
        if match:
            result = json.loads(match.group(1))
        else:
            # 尝试找到第一个 { 和最后一个 }
            start = result_text.find('{')
            end = result_text.rfind('}')
            if start >= 0 and end > start:
                result = json.loads(result_text[start:end + 1])
            else:
                raise ValueError(f'LLM 返回的内容无法解析为 JSON: {result_text[:200]}')

    return result
```

- [ ] **Step 2: 创建 server/services/discovery/script_adapter.py**

```python
import json
from server.models.base import db
from server.models.text import Text, Tag


def create_text_from_analysis(
    item: dict,
    analysis_result: dict,
    folder_id: int | None = None,
    tag_names: list[str] | None = None,
) -> Text:
    """将分析结果转为 Text 模型实例并保存"""
    title = analysis_result.get('generated_title') or item.get('title') or '未命名'
    content = analysis_result.get('generated_content') or ''

    if not content:
        raise ValueError('分析结果中没有原创脚本内容')

    # 构建来源上下文
    source_context = {
        'discovery_item_id': item.get('id'),
        'platform': item.get('platform_key'),
        'source_url': item.get('source_url'),
        'generated_from': 'discovery_analysis',
    }

    text = Text(
        title=title,
        content=content,
        folder_id=folder_id,
        source_context_json=json.dumps(source_context, ensure_ascii=False),
    )

    # 处理标签
    if tag_names:
        tags = []
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)
        text.tags = tags

    db.session.add(text)
    return text
```

- [ ] **Step 3: 运行回归测试**

```bash
uv run pytest
```

Expected: 全部 PASS（新文件无需独立测试，将在 Task 10 的路由测试中端到端验证）

- [ ] **Step 4: 提交**

```bash
git add server/services/discovery/analyzer.py server/services/discovery/script_adapter.py && git commit -m "feat: add LLM analyzer and script adapter for discovery"
```

---

## Task 9: Discovery API 路由

**Files:**
- Create: `server/routes/discovery.py`
- Test: `server/tests/test_discovery_routes.py`

- [ ] **Step 1: 创建 server/routes/discovery.py**

```python
import json
from flask import Blueprint, request, jsonify
from server.models import db, DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis
from server.services.discovery.registry import ConnectorRegistry
from server.services.discovery import scoring as scoring_service
from server.services.discovery.analyzer import analyze_item
from server.services.discovery.script_adapter import create_text_from_analysis

discovery_bp = Blueprint('discovery', __name__)


@discovery_bp.route('/api/discovery/sources', methods=['GET'])
def get_sources():
    sources = DiscoverySource.query.order_by(DiscoverySource.id).all()
    result = []
    for src in sources:
        d = src.to_dict()
        connector = ConnectorRegistry.get(src.platform_key)
        d['needs_api_key'] = connector is not None and hasattr(connector, '_get_api_key')
        result.append(d)
    return jsonify(result)


@discovery_bp.route('/api/discovery/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    platform = data.get('platform', '').strip()
    query_text = data.get('query', '').strip()
    limit = min(int(data.get('limit', 20)), 50)
    filters = data.get('filters') or {}

    if not platform:
        return jsonify({'error': '请选择平台'}), 400
    if not query_text:
        return jsonify({'error': '请输入搜索关键词'}), 400

    source = DiscoverySource.query.filter_by(platform_key=platform).first()
    if not source or not source.is_enabled:
        return jsonify({'error': '该平台未启用'}), 400

    connector = ConnectorRegistry.get(platform)
    if not connector:
        return jsonify({'error': '该平台暂不支持搜索'}), 400

    # Create query record
    dq = DiscoveryQuery(
        query_type='keyword',
        platform_key=platform,
        query_text=query_text,
        filters_json=json.dumps(filters, ensure_ascii=False),
        status='running',
    )
    db.session.add(dq)
    db.session.commit()

    try:
        results = connector.search(query_text, limit, filters)
    except Exception as e:
        dq.status = 'failed'
        dq.error_message = str(e)
        db.session.commit()
        return jsonify({'error': f'搜索失败: {str(e)}'}), 502

    items = []
    for result in results:
        score_result = scoring_service.score_item(result)

        item = DiscoveryItem(
            query_id=dq.id,
            platform_key=result.get('platform_key', platform),
            source_url=result['source_url'],
            source_id=result.get('source_id'),
            title=result.get('title'),
            author_name=result.get('author_name'),
            cover_url=result.get('cover_url'),
            published_at=result.get('published_at'),
            duration=result.get('duration'),
            stats_json=json.dumps(result.get('stats', {}), ensure_ascii=False),
            tags_json=json.dumps(result.get('tags', []), ensure_ascii=False),
            raw_json=json.dumps(result, ensure_ascii=False),
        )
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(
            item_id=item.id,
            xianxia_score=score_result['xianxia_score'],
            hot_score=score_result['hot_score'],
            format_score=score_result['format_score'],
            score_reasons_json=json.dumps(score_result['reasons'], ensure_ascii=False),
        )
        db.session.add(analysis)

        item_dict = item.to_dict()
        item_dict['xianxia_score'] = score_result['xianxia_score']
        item_dict['hot_score'] = score_result['hot_score']
        item_dict['format_score'] = score_result['format_score']
        items.append(item_dict)

    dq.status = 'completed'
    dq.item_count = len(items)
    db.session.commit()

    return jsonify({
        'query_id': dq.id,
        'items': items,
        'total': len(items),
    })


@discovery_bp.route('/api/discovery/resolve-url', methods=['POST'])
def resolve_url():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'error': '请输入视频链接'}), 400

    url = data['url'].strip()

    dq = DiscoveryQuery(
        query_type='url',
        platform_key='manual',
        query_text=url,
        status='running',
    )
    db.session.add(dq)
    db.session.commit()

    connector = ConnectorRegistry.get('manual')
    try:
        result = connector.resolve_url(url)
    except Exception as e:
        dq.status = 'failed'
        dq.error_message = str(e)
        db.session.commit()
        return jsonify({'error': f'解析链接失败: {str(e)}'}), 502

    score_result = scoring_service.score_item(result)

    item = DiscoveryItem(
        query_id=dq.id,
        platform_key=result.get('platform_key', 'manual'),
        source_url=result.get('source_url', url),
        source_id=result.get('source_id'),
        title=result.get('title'),
        author_name=result.get('author_name'),
        cover_url=result.get('cover_url'),
        duration=result.get('duration'),
        stats_json=json.dumps(result.get('stats', {}), ensure_ascii=False),
        tags_json=json.dumps(result.get('tags', []), ensure_ascii=False),
        raw_json=json.dumps(result, ensure_ascii=False),
    )
    db.session.add(item)
    db.session.flush()

    analysis = DiscoveryAnalysis(
        item_id=item.id,
        xianxia_score=score_result['xianxia_score'],
        hot_score=score_result['hot_score'],
        format_score=score_result['format_score'],
        score_reasons_json=json.dumps(score_result['reasons'], ensure_ascii=False),
    )
    db.session.add(analysis)

    dq.status = 'completed'
    dq.item_count = 1
    db.session.commit()

    item_dict = item.to_dict()
    item_dict['xianxia_score'] = score_result['xianxia_score']
    item_dict['hot_score'] = score_result['hot_score']
    item_dict['format_score'] = score_result['format_score']
    return jsonify(item_dict)


@discovery_bp.route('/api/discovery/items', methods=['GET'])
def list_items():
    query = DiscoveryItem.query

    platform = request.args.get('platform')
    if platform:
        query = query.filter_by(platform_key=platform)

    favorited = request.args.get('favorited')
    if favorited == 'true':
        query = query.filter_by(is_favorited=True)

    min_score = request.args.get('min_score')
    if min_score:
        query = query.join(DiscoveryAnalysis).filter(
            DiscoveryAnalysis.xianxia_score >= float(min_score)
        )

    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)

    query = query.order_by(DiscoveryItem.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for item in items:
        d = item.to_dict()
        if item.analysis:
            d['xianxia_score'] = item.analysis.xianxia_score
            d['hot_score'] = item.analysis.hot_score
            d['format_score'] = item.analysis.format_score
        result.append(d)

    return jsonify({'items': result, 'total': total, 'page': page, 'per_page': per_page})


@discovery_bp.route('/api/discovery/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = DiscoveryItem.query.get_or_404(item_id)
    d = item.to_dict()
    if item.analysis:
        d['analysis'] = item.analysis.to_dict()
    return jsonify(d)


@discovery_bp.route('/api/discovery/items/<int:item_id>/analyze', methods=['POST'])
def analyze(item_id):
    item = DiscoveryItem.query.get_or_404(item_id)

    score_result = {
        'xianxia_score': item.analysis.xianxia_score if item.analysis else 0,
        'hot_score': item.analysis.hot_score if item.analysis else 0,
        'format_score': item.analysis.format_score if item.analysis else 0,
        'reasons': json.loads(item.analysis.score_reasons_json) if item.analysis and item.analysis.score_reasons_json else [],
    }

    item_dict = item.to_dict()

    try:
        llm_result = analyze_item(item_dict, score_result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'分析失败: {str(e)}'}), 502

    # Create or update analysis
    if item.analysis:
        analysis = item.analysis
    else:
        analysis = DiscoveryAnalysis(item_id=item.id)
        db.session.add(analysis)

    analysis.xianxia_score = score_result['xianxia_score']
    analysis.hot_score = score_result['hot_score']
    analysis.format_score = score_result['format_score']
    analysis.score_reasons_json = json.dumps(score_result['reasons'], ensure_ascii=False)
    analysis.analysis_json = json.dumps(llm_result, ensure_ascii=False)
    analysis.generated_title = llm_result.get('generated_title')
    analysis.generated_content = llm_result.get('generated_content')
    analysis.recommended_template = llm_result.get('recommended_template')
    analysis.recommended_voice_desc = llm_result.get('recommended_voice_desc')
    analysis.recommended_max_chars = llm_result.get('recommended_max_chars')

    db.session.commit()
    return jsonify(analysis.to_dict())


@discovery_bp.route('/api/discovery/items/<int:item_id>/create-text', methods=['POST'])
def create_text(item_id):
    item = DiscoveryItem.query.get_or_404(item_id)

    if not item.analysis or not item.analysis.generated_content:
        return jsonify({'error': '请先分析该视频并生成原创脚本'}), 400

    data = request.get_json() or {}
    folder_id = data.get('folder_id')
    tag_names = data.get('tag_names', ['热点参考'])

    item_dict = item.to_dict()
    analysis_result = json.loads(item.analysis.analysis_json) if item.analysis.analysis_json else {}
    analysis_result['generated_title'] = item.analysis.generated_title
    analysis_result['generated_content'] = item.analysis.generated_content

    try:
        text = create_text_from_analysis(item_dict, analysis_result, folder_id, tag_names)
        db.session.commit()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'text_id': text.id, 'title': text.title}), 201


@discovery_bp.route('/api/discovery/items/<int:item_id>/favorite', methods=['PUT'])
def toggle_favorite(item_id):
    item = DiscoveryItem.query.get_or_404(item_id)
    item.is_favorited = not item.is_favorited
    db.session.commit()
    return jsonify({'is_favorited': item.is_favorited})


@discovery_bp.route('/api/discovery/queries', methods=['GET'])
def list_queries():
    queries = DiscoveryQuery.query.order_by(DiscoveryQuery.created_at.desc()).limit(50).all()
    return jsonify([q.to_dict() for q in queries])


@discovery_bp.route('/api/discovery/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = DiscoveryItem.query.get_or_404(item_id)
    if item.analysis:
        db.session.delete(item.analysis)
    db.session.delete(item)
    db.session.commit()
    return '', 204
```

- [ ] **Step 2: 创建 server/tests/test_discovery_routes.py**

```python
import json
from unittest.mock import patch, MagicMock


def test_get_sources(client):
    resp = client.get('/api/discovery/sources')
    assert resp.status_code == 200
    sources = resp.get_json()
    assert isinstance(sources, list)
    platform_keys = [s['platform_key'] for s in sources]
    assert 'manual' in platform_keys
    assert 'youtube' in platform_keys


def test_search_missing_params(client):
    resp = client.post('/api/discovery/search', json={})
    assert resp.status_code == 400
    assert '平台' in resp.get_json()['error']


def test_search_empty_query(client):
    resp = client.post('/api/discovery/search', json={'platform': 'youtube', 'query': ''})
    assert resp.status_code == 400


def test_search_disabled_platform(client):
    resp = client.post('/api/discovery/search', json={'platform': 'douyin', 'query': '修仙'})
    assert resp.status_code == 400
    assert '未启用' in resp.get_json()['error']


@patch('server.routes.discovery.ConnectorRegistry.get')
def test_search_success(mock_get, client):
    mock_connector = MagicMock()
    mock_connector.search.return_value = [
        {
            'platform_key': 'youtube',
            'source_url': 'https://youtube.com/watch?v=abc',
            'source_id': 'abc',
            'title': '修仙小说 有声',
            'author_name': '测试频道',
            'stats': {'views': 50000, 'likes': 2000, 'comments': 100},
            'tags': ['修仙'],
            'duration': 120,
        },
    ]
    mock_get.return_value = mock_connector

    resp = client.post('/api/discovery/search', json={
        'platform': 'youtube',
        'query': '修仙小说',
        'limit': 10,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['title'] == '修仙小说 有声'
    assert data['items'][0]['xianxia_score'] > 0
    assert 'query_id' in data


@patch('server.routes.discovery.ConnectorRegistry.get')
def test_resolve_url_success(mock_get, client):
    mock_connector = MagicMock()
    mock_connector.resolve_url.return_value = {
        'platform_key': 'youtube',
        'source_url': 'https://youtube.com/watch?v=xyz',
        'source_id': 'xyz',
        'title': '测试视频',
        'stats': {'views': 10000, 'likes': 500},
    }
    mock_get.return_value = mock_connector

    resp = client.post('/api/discovery/resolve-url', json={
        'url': 'https://youtube.com/watch?v=xyz',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['title'] == '测试视频'


def test_resolve_url_missing_url(client):
    resp = client.post('/api/discovery/resolve-url', json={})
    assert resp.status_code == 400


def test_list_items_empty(client):
    resp = client.get('/api/discovery/items')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['items'] == []
    assert data['total'] == 0


def test_get_item_not_found(client):
    resp = client.get('/api/discovery/items/999')
    assert resp.status_code == 404


def test_toggle_favorite(client, app, db):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.put(f'/api/discovery/items/{item_id}/favorite')
    assert resp.status_code == 200
    assert resp.get_json()['is_favorited'] is True

    resp = client.put(f'/api/discovery/items/{item_id}/favorite')
    assert resp.status_code == 200
    assert resp.get_json()['is_favorited'] is False


def test_create_text_without_analysis(client, app, db):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.post(f'/api/discovery/items/{item_id}/create-text', json={})
    assert resp.status_code == 400
    assert '请先分析' in resp.get_json()['error']


def test_delete_item(client, app, db):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.delete(f'/api/discovery/items/{item_id}')
    assert resp.status_code == 204

    resp = client.get(f'/api/discovery/items/{item_id}')
    assert resp.status_code == 404


def test_list_queries(client):
    resp = client.get('/api/discovery/queries')
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
```

需要在测试文件顶部补充 import：

```python
from server.models import DiscoveryItem
```

- [ ] **Step 3: 运行测试**

```bash
uv run pytest server/tests/test_discovery_routes.py -v
```

Expected: 全部 PASS

- [ ] **Step 4: 运行全量回归测试**

```bash
uv run pytest
```

Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add server/routes/discovery.py server/tests/test_discovery_routes.py && git commit -m "feat: add discovery API routes with search, analyze, create-text"
```

---

## Task 10: 最终验证与前端构建

**目标：** 确保所有后端功能正常，前端构建不受影响。

- [ ] **Step 1: 运行全量测试**

```bash
uv run pytest
```

Expected: 全部 PASS

- [ ] **Step 2: 前端构建验证**

```bash
cd web && pnpm run build
```

Expected: 构建成功（后端 models 重构不影响前端）

- [ ] **Step 3: 手动验证种子数据**

```bash
python -c "
from server.app import create_app
app = create_app()
with app.app_context():
    from server.models import DiscoverySource
    sources = DiscoverySource.query.all()
    for s in sources:
        print(f'{s.platform_key}: enabled={s.is_enabled}')
"
```

Expected: 5 个平台源，manual 和 youtube 启用，其他禁用

- [ ] **Step 4: 提交（如果有遗漏的文件）**

```bash
git status
```

如果有未提交的文件，提交。

- [ ] **Step 5: 创建功能分支并推送（可选）**

如果需要创建 PR：

```bash
git checkout -b feat/discovery-backend
git push -u origin feat/discovery-backend
```
