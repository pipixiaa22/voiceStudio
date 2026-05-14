# Web 界面实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 SRT 字幕生成器添加 Vue 3 + Flask Web 界面，支持文本管理、分组、标签和导出

**Architecture:** 前后端分离架构，Vue 3 + Vite 构建前端，Flask + SQLAlchemy 提供 REST API，SQLite 存储数据。现有 CLI 功能完全保留。

**Tech Stack:** Vue 3, Vite, Pinia, Vue Router, Flask, SQLAlchemy, SQLite

---

## 文件结构

### 后端文件
- `server/__init__.py` — 包初始化
- `server/app.py` — Flask 应用入口
- `server/models.py` — SQLAlchemy 数据模型
- `server/routes/__init__.py` — 路由包
- `server/routes/texts.py` — 文本 API 路由
- `server/routes/folders.py` — 文件夹 API 路由
- `server/routes/tags.py` — 标签 API 路由
- `server/tests/test_texts.py` — 文本 API 测试
- `server/tests/test_folders.py` — 文件夹 API 测试
- `server/tests/test_tags.py` — 标签 API 测试

### 前端文件
- `web/package.json` — Node.js 依赖配置
- `web/vite.config.js` — Vite 构建配置
- `web/index.html` — HTML 入口
- `web/src/main.js` — Vue 应用入口
- `web/src/App.vue` — 根组件
- `web/src/router/index.js` — 路由配置
- `web/src/api/index.js` — API 调用封装
- `web/src/stores/texts.js` — 文本状态管理
- `web/src/stores/folders.js` — 文件夹状态管理
- `web/src/stores/tags.js` — 标签状态管理
- `web/src/views/TextList.vue` — 文本列表页
- `web/src/views/TextEdit.vue` — 文本编辑页
- `web/src/views/Import.vue` — 导入页
- `web/src/components/FolderTree.vue` — 文件夹树组件
- `web/src/components/TagSelector.vue` — 标签选择器组件

### 修改的现有文件
- `pyproject.toml` — 添加 Flask 依赖

---

### Task 1: Flask 应用基础 + 数据模型

**Files:**
- Create: `server/__init__.py`
- Create: `server/app.py`
- Create: `server/models.py`
- Create: `server/tests/__init__.py`
- Create: `server/tests/conftest.py`
- Create: `server/tests/test_models.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加 Python 依赖**

在 `pyproject.toml` 的 `dependencies` 中添加：
```
dependencies = [
    "flask>=3.0.0",
    "flask-sqlalchemy>=3.1.0",
    "flask-cors>=4.0.0",
]
```

运行：`uv sync`

- [ ] **Step 2: 创建数据模型**

```python
# server/models.py
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}
```

- [ ] **Step 3: 创建 Flask 应用**

```python
# server/app.py
import os
from flask import Flask
from flask_cors import CORS
from server.models import db


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static', static_url_path='')

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        from server.routes.texts import texts_bp
        from server.routes.folders import folders_bp
        from server.routes.tags import tags_bp
        app.register_blueprint(texts_bp)
        app.register_blueprint(folders_bp)
        app.register_blueprint(tags_bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
```

- [ ] **Step 4: 创建测试配置和模型测试**

```python
# server/tests/__init__.py
# (empty)
```

```python
# server/tests/conftest.py
import pytest
from server.app import create_app
from server.models import db as _db


@pytest.fixture
def app():
    app = create_app(test_config={
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db
```

```python
# server/tests/test_models.py
from server.models import Text, Folder, Tag


def test_create_text(app, db):
    with app.app_context():
        text = Text(title='测试标题', content='测试内容')
        db.session.add(text)
        db.session.commit()
        assert text.id is not None
        assert text.title == '测试标题'


def test_create_folder(app, db):
    with app.app_context():
        folder = Folder(name='测试文件夹')
        db.session.add(folder)
        db.session.commit()
        assert folder.id is not None


def test_create_tag(app, db):
    with app.app_context():
        tag = Tag(name='测试标签')
        db.session.add(tag)
        db.session.commit()
        assert tag.id is not None


def test_text_with_folder(app, db):
    with app.app_context():
        folder = Folder(name='文件夹')
        db.session.add(folder)
        db.session.flush()
        text = Text(title='标题', content='内容', folder_id=folder.id)
        db.session.add(text)
        db.session.commit()
        assert text.folder_id == folder.id


def test_text_with_tags(app, db):
    with app.app_context():
        tag1 = Tag(name='标签1')
        tag2 = Tag(name='标签2')
        db.session.add_all([tag1, tag2])
        db.session.flush()
        text = Text(title='标题', content='内容', tags=[tag1, tag2])
        db.session.add(text)
        db.session.commit()
        assert len(text.tags) == 2
```

- [ ] **Step 5: 运行测试**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_models.py -v
```

- [ ] **Step 6: 提交**

```bash
git add server/ pyproject.toml uv.lock
git commit -m "feat: add Flask app with SQLAlchemy models"
```

---

### Task 2: 文件夹 API

**Files:**
- Create: `server/routes/__init__.py`
- Create: `server/routes/folders.py`
- Create: `server/tests/test_folders.py`

- [ ] **Step 1: 创建路由包**

```python
# server/routes/__init__.py
# (empty)
```

- [ ] **Step 2: 写失败的测试**

```python
# server/tests/test_folders.py
import json


def test_create_folder(client):
    response = client.post('/api/folders', json={'name': '测试文件夹'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == '测试文件夹'
    assert data['id'] is not None


def test_get_folders(client):
    client.post('/api/folders', json={'name': '文件夹1'})
    client.post('/api/folders', json={'name': '文件夹2'})
    response = client.get('/api/folders')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_create_nested_folder(client):
    parent = client.post('/api/folders', json={'name': '父文件夹'}).get_json()
    response = client.post('/api/folders', json={'name': '子文件夹', 'parent_id': parent['id']})
    assert response.status_code == 201
    data = response.get_json()
    assert data['parent_id'] == parent['id']


def test_delete_folder(client):
    folder = client.post('/api/folders', json={'name': '待删除'}).get_json()
    response = client.delete(f"/api/folders/{folder['id']}")
    assert response.status_code == 204
    response = client.get('/api/folders')
    assert len(response.get_json()) == 0
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_folders.py -v
```

- [ ] **Step 4: 实现文件夹路由**

```python
# server/routes/folders.py
from flask import Blueprint, request, jsonify
from server.models import db, Folder

folders_bp = Blueprint('folders', __name__)


@folders_bp.route('/api/folders', methods=['GET'])
def get_folders():
    folders = Folder.query.order_by(Folder.created_at).all()
    return jsonify([f.to_dict() for f in folders])


@folders_bp.route('/api/folders', methods=['POST'])
def create_folder():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '文件夹名称不能为空'}), 400

    folder = Folder(name=data['name'], parent_id=data.get('parent_id'))
    db.session.add(folder)
    db.session.commit()
    return jsonify(folder.to_dict()), 201


@folders_bp.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    db.session.delete(folder)
    db.session.commit()
    return '', 204
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_folders.py -v
```

- [ ] **Step 6: 提交**

```bash
git add server/routes/ server/tests/test_folders.py
git commit -m "feat: add folder CRUD API"
```

---

### Task 3: 标签 API

**Files:**
- Create: `server/routes/tags.py`
- Create: `server/tests/test_tags.py`

- [ ] **Step 1: 写失败的测试**

```python
# server/tests/test_tags.py


def test_create_tag(client):
    response = client.post('/api/tags', json={'name': '测试标签'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == '测试标签'


def test_get_tags(client):
    client.post('/api/tags', json={'name': '标签1'})
    client.post('/api/tags', json={'name': '标签2'})
    response = client.get('/api/tags')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_create_duplicate_tag(client):
    client.post('/api/tags', json={'name': '重复标签'})
    response = client.post('/api/tags', json={'name': '重复标签'})
    assert response.status_code == 409
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_tags.py -v
```

- [ ] **Step 3: 实现标签路由**

```python
# server/routes/tags.py
from flask import Blueprint, request, jsonify
from server.models import db, Tag

tags_bp = Blueprint('tags', __name__)


@tags_bp.route('/api/tags', methods=['GET'])
def get_tags():
    tags = Tag.query.order_by(Tag.name).all()
    return jsonify([t.to_dict() for t in tags])


@tags_bp.route('/api/tags', methods=['POST'])
def create_tag():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '标签名称不能为空'}), 400

    if Tag.query.filter_by(name=data['name']).first():
        return jsonify({'error': '标签已存在'}), 409

    tag = Tag(name=data['name'])
    db.session.add(tag)
    db.session.commit()
    return jsonify(tag.to_dict()), 201
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_tags.py -v
```

- [ ] **Step 5: 提交**

```bash
git add server/routes/tags.py server/tests/test_tags.py
git commit -m "feat: add tag CRUD API"
```

---

### Task 4: 文本 CRUD API

**Files:**
- Create: `server/routes/texts.py`
- Create: `server/tests/test_texts.py`

- [ ] **Step 1: 写失败的测试**

```python
# server/tests/test_texts.py


def test_create_text(client):
    response = client.post('/api/texts', json={
        'title': '测试标题',
        'content': '测试内容'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == '测试标题'
    assert data['content'] == '测试内容'


def test_get_texts(client):
    client.post('/api/texts', json={'title': '标题1', 'content': '内容1'})
    client.post('/api/texts', json={'title': '标题2', 'content': '内容2'})
    response = client.get('/api/texts')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_get_texts_by_folder(client):
    folder = client.post('/api/folders', json={'name': '文件夹'}).get_json()
    client.post('/api/texts', json={'title': '标题', 'content': '内容', 'folder_id': folder['id']})
    response = client.get(f"/api/texts?folder_id={folder['id']}")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1


def test_get_texts_by_tag(client):
    tag = client.post('/api/tags', json={'name': '标签'}).get_json()
    client.post('/api/texts', json={'title': '标题', 'content': '内容', 'tag_ids': [tag['id']]})
    response = client.get('/api/texts?tag=标签')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1


def test_update_text(client):
    text = client.post('/api/texts', json={'title': '原标题', 'content': '原内容'}).get_json()
    response = client.put(f"/api/texts/{text['id']}", json={'title': '新标题'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == '新标题'


def test_delete_text(client):
    text = client.post('/api/texts', json={'title': '待删除', 'content': '内容'}).get_json()
    response = client.delete(f"/api/texts/{text['id']}")
    assert response.status_code == 204


def test_sort_texts(client):
    client.post('/api/texts', json={'title': '第一个', 'content': '内容'})
    client.post('/api/texts', json={'title': '第二个', 'content': '内容'})
    response = client.get('/api/texts?sort_by=created_at&order=desc')
    data = response.get_json()
    assert data[0]['title'] == '第二个'
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_texts.py -v
```

- [ ] **Step 3: 实现文本路由**

```python
# server/routes/texts.py
from flask import Blueprint, request, jsonify
from server.models import db, Text, Tag

texts_bp = Blueprint('texts', __name__)


@texts_bp.route('/api/texts', methods=['GET'])
def get_texts():
    query = Text.query

    folder_id = request.args.get('folder_id')
    if folder_id:
        query = query.filter_by(folder_id=folder_id)

    tag_name = request.args.get('tag')
    if tag_name:
        query = query.filter(Text.tags.any(Tag.name == tag_name))

    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    sort_column = getattr(Text, sort_by, Text.created_at)
    query = query.order_by(sort_column.desc() if order == 'desc' else sort_column.asc())

    texts = query.all()
    return jsonify([t.to_dict() for t in texts])


@texts_bp.route('/api/texts', methods=['POST'])
def create_text():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    text = Text(
        title=data.get('title', '未命名'),
        content=data['content'],
        folder_id=data.get('folder_id'),
    )

    tag_ids = data.get('tag_ids', [])
    if tag_ids:
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        text.tags = tags

    db.session.add(text)
    db.session.commit()
    return jsonify(text.to_dict()), 201


@texts_bp.route('/api/texts/<int:text_id>', methods=['PUT'])
def update_text(text_id):
    text = Text.query.get_or_404(text_id)
    data = request.get_json()

    if 'title' in data:
        text.title = data['title']
    if 'content' in data:
        text.content = data['content']
    if 'folder_id' in data:
        text.folder_id = data['folder_id']
    if 'tag_ids' in data:
        tags = Tag.query.filter(Tag.id.in_(data['tag_ids'])).all()
        text.tags = tags

    db.session.commit()
    return jsonify(text.to_dict())


@texts_bp.route('/api/texts/<int:text_id>', methods=['DELETE'])
def delete_text(text_id):
    text = Text.query.get_or_404(text_id)
    db.session.delete(text)
    db.session.commit()
    return '', 204
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_texts.py -v
```

- [ ] **Step 5: 提交**

```bash
git add server/routes/texts.py server/tests/test_texts.py
git commit -m "feat: add text CRUD API with filtering and sorting"
```

---

### Task 5: 导入导出 API

**Files:**
- Modify: `server/routes/texts.py`
- Modify: `server/tests/test_texts.py`

- [ ] **Step 1: 写失败的测试**

在 `server/tests/test_texts.py` 中添加：

```python
def test_import_txt(client):
    data = {
        'file': (io.BytesIO('测试内容'.encode('utf-8')), 'test.txt'),
    }
    response = client.post('/api/texts/import', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    result = response.get_json()
    assert result['content'] == '测试内容'


def test_export_srt(client):
    text = client.post('/api/texts', json={'title': '测试', 'content': '你好吗？我很好。'}).get_json()
    response = client.get(f"/api/texts/{text['id']}/srt?speed=5&max_chars=20")
    assert response.status_code == 200
    assert '00:00:00' in response.text
```

需要在文件顶部添加 `import io`。

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_texts.py::test_import_txt -v
cd /Users/ckrey/video/script && uv run pytest server/tests/test_texts.py::test_export_srt -v
```

- [ ] **Step 3: 实现导入导出路由**

在 `server/routes/texts.py` 中添加：

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from splitter import split_text
from srt import generate_srt


@texts_bp.route('/api/texts/import', methods=['POST'])
def import_text():
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({'error': '只支持 .txt 文件'}), 400

    content = file.read().decode('utf-8')
    title = file.filename.replace('.txt', '')

    text = Text(title=title, content=content)
    db.session.add(text)
    db.session.commit()
    return jsonify(text.to_dict()), 201


@texts_bp.route('/api/texts/<int:text_id>/srt', methods=['GET'])
def export_srt(text_id):
    text = Text.query.get_or_404(text_id)

    speed = float(request.args.get('speed', 5))
    max_chars = int(request.args.get('max_chars', 20))

    segments = split_text(text.content, max_chars=max_chars)
    srt_content = generate_srt(segments, chars_per_second=speed)

    return srt_content, 200, {
        'Content-Type': 'text/srt',
        'Content-Disposition': f'attachment; filename="{text.title}.srt"'
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_texts.py -v
```

- [ ] **Step 5: 提交**

```bash
git add server/routes/texts.py server/tests/test_texts.py
git commit -m "feat: add text import/export API"
```

---

### Task 6: Vue 前端项目初始化

**Files:**
- Create: `web/` 目录结构

- [ ] **Step 1: 创建 Vue 项目**

```bash
cd /Users/ckrey/video/script && npm create vite@latest web -- --template vue
cd web && npm install
npm install vue-router pinia axios
```

- [ ] **Step 2: 配置 Vite 代理**

```javascript
// web/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: '../server/static',
    emptyOutDir: true,
  }
})
```

- [ ] **Step 3: 创建基础路由**

```javascript
// web/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import TextList from '../views/TextList.vue'
import TextEdit from '../views/TextEdit.vue'
import Import from '../views/Import.vue'

const routes = [
  { path: '/', component: TextList },
  { path: '/edit/:id?', component: TextEdit },
  { path: '/import', component: Import },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 4: 创建 API 封装**

```javascript
// web/src/api/index.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export const textsApi = {
  list: (params) => api.get('/texts', { params }),
  get: (id) => api.get(`/texts/${id}`),
  create: (data) => api.post('/texts', data),
  update: (id, data) => api.put(`/texts/${id}`, data),
  delete: (id) => api.delete(`/texts/${id}`),
  import: (formData) => api.post('/texts/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  exportSrt: (id, params) => api.get(`/texts/${id}/srt`, { params, responseType: 'blob' }),
}

export const foldersApi = {
  list: () => api.get('/folders'),
  create: (data) => api.post('/folders', data),
  delete: (id) => api.delete(`/folders/${id}`),
}

export const tagsApi = {
  list: () => api.get('/tags'),
  create: (data) => api.post('/tags', data),
}

export default api
```

- [ ] **Step 5: 创建主入口和根组件**

```javascript
// web/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

```vue
<!-- web/src/App.vue -->
<template>
  <div id="app">
    <nav class="navbar">
      <router-link to="/">文本列表</router-link>
      <router-link to="/import">导入</router-link>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.navbar {
  background: #2c3e50;
  padding: 1rem;
  display: flex;
  gap: 1rem;
}
.navbar a {
  color: white;
  text-decoration: none;
}
.navbar a.router-link-active {
  color: #42b883;
}
main {
  padding: 1rem;
}
</style>
```

- [ ] **Step 6: 创建占位页面组件**

```vue
<!-- web/src/views/TextList.vue -->
<template>
  <div>
    <h1>文本列表</h1>
    <p>待实现</p>
  </div>
</template>
```

```vue
<!-- web/src/views/TextEdit.vue -->
<template>
  <div>
    <h1>编辑文本</h1>
    <p>待实现</p>
  </div>
</template>
```

```vue
<!-- web/src/views/Import.vue -->
<template>
  <div>
    <h1>导入文本</h1>
    <p>待实现</p>
  </div>
</template>
```

- [ ] **Step 7: 验证项目可启动**

```bash
cd /Users/ckrey/video/script/web && npm run dev
```

访问 http://localhost:3000 确认页面显示正常。

- [ ] **Step 8: 提交**

```bash
cd /Users/ckrey/video/script && git add web/ && git commit -m "feat: initialize Vue 3 frontend project"
```

---

### Task 7: Pinia 状态管理

**Files:**
- Create: `web/src/stores/texts.js`
- Create: `web/src/stores/folders.js`
- Create: `web/src/stores/tags.js`

- [ ] **Step 1: 创建文本 store**

```javascript
// web/src/stores/texts.js
import { defineStore } from 'pinia'
import { textsApi } from '../api'

export const useTextsStore = defineStore('texts', {
  state: () => ({
    texts: [],
    currentText: null,
    loading: false,
  }),
  actions: {
    async fetchTexts(params = {}) {
      this.loading = true
      try {
        const { data } = await textsApi.list(params)
        this.texts = data
      } finally {
        this.loading = false
      }
    },
    async fetchText(id) {
      const { data } = await textsApi.get(id)
      this.currentText = data
      return data
    },
    async createText(textData) {
      const { data } = await textsApi.create(textData)
      this.texts.unshift(data)
      return data
    },
    async updateText(id, textData) {
      const { data } = await textsApi.update(id, textData)
      const index = this.texts.findIndex(t => t.id === id)
      if (index !== -1) this.texts[index] = data
      this.currentText = data
      return data
    },
    async deleteText(id) {
      await textsApi.delete(id)
      this.texts = this.texts.filter(t => t.id !== id)
    },
    async importText(formData) {
      const { data } = await textsApi.import(formData)
      this.texts.unshift(data)
      return data
    },
    async exportSrt(id, params) {
      const response = await textsApi.exportSrt(id, params)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `${this.currentText?.title || 'output'}.srt`
      link.click()
      window.URL.revokeObjectURL(url)
    },
  },
})
```

- [ ] **Step 2: 创建文件夹 store**

```javascript
// web/src/stores/folders.js
import { defineStore } from 'pinia'
import { foldersApi } from '../api'

export const useFoldersStore = defineStore('folders', {
  state: () => ({
    folders: [],
    loading: false,
  }),
  actions: {
    async fetchFolders() {
      this.loading = true
      try {
        const { data } = await foldersApi.list()
        this.folders = data
      } finally {
        this.loading = false
      }
    },
    async createFolder(folderData) {
      const { data } = await foldersApi.create(folderData)
      this.folders.push(data)
      return data
    },
    async deleteFolder(id) {
      await foldersApi.delete(id)
      this.folders = this.folders.filter(f => f.id !== id)
    },
  },
})
```

- [ ] **Step 3: 创建标签 store**

```javascript
// web/src/stores/tags.js
import { defineStore } from 'pinia'
import { tagsApi } from '../api'

export const useTagsStore = defineStore('tags', {
  state: () => ({
    tags: [],
    loading: false,
  }),
  actions: {
    async fetchTags() {
      this.loading = true
      try {
        const { data } = await tagsApi.list()
        this.tags = data
      } finally {
        this.loading = false
      }
    },
    async createTag(tagData) {
      const { data } = await tagsApi.create(tagData)
      this.tags.push(data)
      return data
    },
  },
})
```

- [ ] **Step 4: 提交**

```bash
cd /Users/ckrey/video/script && git add web/src/stores/ && git commit -m "feat: add Pinia stores for texts, folders, tags"
```

---

### Task 8: 文本列表页面

**Files:**
- Modify: `web/src/views/TextList.vue`
- Create: `web/src/components/FolderTree.vue`

- [ ] **Step 1: 实现文件夹树组件**

```vue
<!-- web/src/components/FolderTree.vue -->
<template>
  <div class="folder-tree">
    <div class="folder-header">
      <h3>文件夹</h3>
      <button @click="showAddFolder = true" class="btn-add">+</button>
    </div>

    <div v-if="showAddFolder" class="add-folder">
      <input v-model="newFolderName" placeholder="文件夹名称" @keyup.enter="handleAdd" />
      <button @click="handleAdd">添加</button>
      <button @click="showAddFolder = false">取消</button>
    </div>

    <div class="folder-list">
      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-item"
        :class="{ active: selectedFolderId === folder.id }"
        @click="$emit('select', folder.id)"
      >
        <span>{{ folder.name }}</span>
        <button @click.stop="handleDelete(folder.id)" class="btn-delete">×</button>
      </div>
      <div
        class="folder-item"
        :class="{ active: selectedFolderId === null }"
        @click="$emit('select', null)"
      >
        <span>全部文本</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useFoldersStore } from '../stores/folders'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select'])
const foldersStore = useFoldersStore()
const showAddFolder = ref(false)
const newFolderName = ref('')

onMounted(() => foldersStore.fetchFolders())

const folders = foldersStore.folders

const handleAdd = async () => {
  if (!newFolderName.value.trim()) return
  await foldersStore.createFolder({ name: newFolderName.value })
  newFolderName.value = ''
  showAddFolder.value = false
}

const handleDelete = async (id) => {
  if (confirm('确定删除此文件夹？')) {
    await foldersStore.deleteFolder(id)
    if (props.selectedFolderId === id) {
      emit('select', null)
    }
  }
}
</script>

<style scoped>
.folder-tree {
  width: 200px;
  border-right: 1px solid #eee;
  padding: 1rem;
}
.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-add {
  background: #42b883;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
}
.folder-item {
  padding: 0.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.folder-item:hover {
  background: #f5f5f5;
}
.folder-item.active {
  background: #e8f5e9;
}
.btn-delete {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 1.2rem;
}
.add-folder {
  margin: 0.5rem 0;
  display: flex;
  gap: 0.5rem;
}
.add-folder input {
  flex: 1;
  padding: 0.25rem;
}
</style>
```

- [ ] **Step 2: 实现文本列表页面**

```vue
<!-- web/src/views/TextList.vue -->
<template>
  <div class="text-list-page">
    <FolderTree
      :selectedFolderId="selectedFolderId"
      @select="selectedFolderId = $event"
    />

    <div class="text-list-content">
      <div class="toolbar">
        <input v-model="searchQuery" placeholder="搜索文本..." class="search-input" />
        <select v-model="sortBy" class="sort-select">
          <option value="created_at">创建时间</option>
          <option value="updated_at">更新时间</option>
        </select>
        <select v-model="sortOrder" class="sort-select">
          <option value="desc">降序</option>
          <option value="asc">升序</option>
        </select>
        <router-link to="/edit" class="btn btn-primary">新建文本</router-link>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <table v-else class="text-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>标签</th>
            <th>创建时间</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="text in filteredTexts" :key="text.id">
            <td>
              <router-link :to="`/edit/${text.id}`">{{ text.title }}</router-link>
            </td>
            <td>
              <span v-for="tag in text.tags" :key="tag.id" class="tag">{{ tag.name }}</span>
            </td>
            <td>{{ formatDate(text.created_at) }}</td>
            <td>{{ formatDate(text.updated_at) }}</td>
            <td>
              <button @click="handleExport(text.id)" class="btn btn-sm">导出SRT</button>
              <button @click="handleDelete(text.id)" class="btn btn-sm btn-danger">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTextsStore } from '../stores/texts'
import FolderTree from '../components/FolderTree.vue'

const textsStore = useTextsStore()
const selectedFolderId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

const loading = computed(() => textsStore.loading)

const fetchTexts = () => {
  textsStore.fetchTexts({
    folder_id: selectedFolderId.value,
    sort_by: sortBy.value,
    order: sortOrder.value,
  })
}

onMounted(fetchTexts)
watch([selectedFolderId, sortBy, sortOrder], fetchTexts)

const filteredTexts = computed(() => {
  if (!searchQuery.value) return textsStore.texts
  const query = searchQuery.value.toLowerCase()
  return textsStore.texts.filter(t =>
    t.title.toLowerCase().includes(query) || t.content.toLowerCase().includes(query)
  )
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleExport = async (id) => {
  await textsStore.exportSrt(id, { speed: 5, max_chars: 20 })
}

const handleDelete = async (id) => {
  if (confirm('确定删除此文本？')) {
    await textsStore.deleteText(id)
  }
}
</script>

<style scoped>
.text-list-page {
  display: flex;
  min-height: calc(100vh - 60px);
}
.text-list-content {
  flex: 1;
  padding: 1rem;
}
.toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: center;
}
.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.sort-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
}
.btn-primary {
  background: #42b883;
  color: white;
}
.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}
.btn-danger {
  background: #e74c3c;
  color: white;
}
.text-table {
  width: 100%;
  border-collapse: collapse;
}
.text-table th,
.text-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}
.text-table th {
  background: #f5f5f5;
}
.tag {
  display: inline-block;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-right: 0.25rem;
}
.loading {
  text-align: center;
  padding: 2rem;
  color: #999;
}
</style>
```

- [ ] **Step 3: 验证页面功能**

启动前后端，访问 http://localhost:3000，确认：
- 文件夹树显示正常
- 文本列表显示正常
- 可以创建文件夹
- 可以按文件夹筛选
- 可以搜索和排序

- [ ] **Step 4: 提交**

```bash
cd /Users/ckrey/video/script && git add web/src/views/TextList.vue web/src/components/FolderTree.vue && git commit -m "feat: implement text list page with folder tree"
```

---

### Task 9: 文本编辑页面

**Files:**
- Modify: `web/src/views/TextEdit.vue`
- Create: `web/src/components/TagSelector.vue`

- [ ] **Step 1: 实现标签选择器组件**

```vue
<!-- web/src/components/TagSelector.vue -->
<template>
  <div class="tag-selector">
    <div class="selected-tags">
      <span v-for="tag in selectedTags" :key="tag.id" class="tag">
        {{ tag.name }}
        <button @click="removeTag(tag.id)" class="tag-remove">×</button>
      </span>
    </div>
    <div class="tag-input">
      <input
        v-model="newTagName"
        placeholder="输入标签名称"
        @keyup.enter="handleAddTag"
      />
      <button @click="handleAddTag">添加</button>
    </div>
    <div class="available-tags">
      <span
        v-for="tag in availableTags"
        :key="tag.id"
        class="tag tag-available"
        @click="addTag(tag)"
      >
        {{ tag.name }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTagsStore } from '../stores/tags'

const props = defineProps({
  modelValue: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])
const tagsStore = useTagsStore()
const newTagName = ref('')

onMounted(() => tagsStore.fetchTags())

const selectedTags = computed(() => props.modelValue)

const availableTags = computed(() =>
  tagsStore.tags.filter(t => !props.modelValue.some(s => s.id === t.id))
)

const addTag = (tag) => {
  emit('update:modelValue', [...props.modelValue, tag])
}

const removeTag = (id) => {
  emit('update:modelValue', props.modelValue.filter(t => t.id !== id))
}

const handleAddTag = async () => {
  if (!newTagName.value.trim()) return
  const tag = await tagsStore.createTag({ name: newTagName.value })
  addTag(tag)
  newTagName.value = ''
}
</script>

<style scoped>
.tag-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tag {
  display: inline-flex;
  align-items: center;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.875rem;
}
.tag-remove {
  background: none;
  border: none;
  margin-left: 0.25rem;
  cursor: pointer;
  color: #2e7d32;
}
.tag-input {
  display: flex;
  gap: 0.5rem;
}
.tag-input input {
  flex: 1;
  padding: 0.25rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.available-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tag-available {
  background: #f5f5f5;
  color: #666;
  cursor: pointer;
}
.tag-available:hover {
  background: #e0e0e0;
}
</style>
```

- [ ] **Step 2: 实现文本编辑页面**

```vue
<!-- web/src/views/TextEdit.vue -->
<template>
  <div class="text-edit-page">
    <div class="edit-header">
      <input v-model="title" placeholder="输入标题..." class="title-input" />
      <div class="edit-actions">
        <button @click="handleSave" class="btn btn-primary" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button v-if="textId" @click="handleExport" class="btn">导出 SRT</button>
      </div>
    </div>

    <div class="edit-meta">
      <div class="meta-item">
        <label>文件夹：</label>
        <select v-model="folderId">
          <option :value="null">无</option>
          <option v-for="folder in folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </option>
        </select>
      </div>
      <div class="meta-item">
        <label>标签：</label>
        <TagSelector v-model="selectedTags" />
      </div>
    </div>

    <textarea
      v-model="content"
      placeholder="输入文本内容..."
      class="content-input"
    ></textarea>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import TagSelector from '../components/TagSelector.vue'

const router = useRouter()
const route = useRoute()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const textId = route.params.id ? parseInt(route.params.id) : null
const title = ref('未命名')
const content = ref('')
const folderId = ref(null)
const selectedTags = ref([])
const saving = ref(false)

const folders = foldersStore.folders

onMounted(async () => {
  foldersStore.fetchFolders()
  if (textId) {
    const text = await textsStore.fetchText(textId)
    title.value = text.title
    content.value = text.content
    folderId.value = text.folder_id
    selectedTags.value = text.tags || []
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    const data = {
      title: title.value,
      content: content.value,
      folder_id: folderId.value,
      tag_ids: selectedTags.value.map(t => t.id),
    }
    if (textId) {
      await textsStore.updateText(textId, data)
    } else {
      const newText = await textsStore.createText(data)
      router.replace(`/edit/${newText.id}`)
    }
  } finally {
    saving.value = false
  }
}

const handleExport = async () => {
  await textsStore.exportSrt(textId, { speed: 5, max_chars: 20 })
}
</script>

<style scoped>
.text-edit-page {
  max-width: 1200px;
  margin: 0 auto;
}
.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.title-input {
  font-size: 1.5rem;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  flex: 1;
  margin-right: 1rem;
}
.edit-actions {
  display: flex;
  gap: 0.5rem;
}
.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary {
  background: #42b883;
  color: white;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.edit-meta {
  margin-bottom: 1rem;
  display: flex;
  gap: 2rem;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.meta-item label {
  font-weight: bold;
  white-space: nowrap;
}
.meta-item select {
  padding: 0.25rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.content-input {
  width: 100%;
  min-height: 400px;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  resize: vertical;
}
</style>
```

- [ ] **Step 3: 验证页面功能**

启动前后端，访问 http://localhost:3000/edit，确认：
- 可以输入标题和内容
- 可以选择文件夹
- 可以添加和选择标签
- 保存后数据持久化
- 可以导出 SRT

- [ ] **Step 4: 提交**

```bash
cd /Users/ckrey/video/script && git add web/src/views/TextEdit.vue web/src/components/TagSelector.vue && git commit -m "feat: implement text editor page with tags and folders"
```

---

### Task 10: 导入页面

**Files:**
- Modify: `web/src/views/Import.vue`

- [ ] **Step 1: 实现导入页面**

```vue
<!-- web/src/views/Import.vue -->
<template>
  <div class="import-page">
    <h1>导入文本</h1>

    <div
      class="drop-zone"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".txt"
        @change="handleFileSelect"
        style="display: none"
      />
      <p v-if="!file">拖拽 .txt 文件到此处，或点击选择文件</p>
      <p v-else>已选择：{{ file.name }}</p>
    </div>

    <div v-if="previewContent" class="preview">
      <h3>预览内容</h3>
      <textarea v-model="previewContent" class="preview-content"></textarea>
    </div>

    <div v-if="previewContent" class="import-options">
      <div class="option">
        <label>标题：</label>
        <input v-model="title" />
      </div>
      <div class="option">
        <label>文件夹：</label>
        <select v-model="folderId">
          <option :value="null">无</option>
          <option v-for="folder in folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </option>
        </select>
      </div>
      <button @click="handleImport" class="btn btn-primary" :disabled="importing">
        {{ importing ? '导入中...' : '确认导入' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'

const router = useRouter()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const fileInput = ref(null)
const file = ref(null)
const previewContent = ref('')
const title = ref('')
const folderId = ref(null)
const importing = ref(false)

const folders = foldersStore.folders

onMounted(() => foldersStore.fetchFolders())

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileSelect = (e) => {
  const selected = e.target.files[0]
  if (selected) readFile(selected)
}

const handleDrop = (e) => {
  const dropped = e.dataTransfer.files[0]
  if (dropped && dropped.name.endsWith('.txt')) {
    readFile(dropped)
  }
}

const readFile = (f) => {
  file.value = f
  title.value = f.name.replace('.txt', '')
  const reader = new FileReader()
  reader.onload = (e) => {
    previewContent.value = e.target.result
  }
  reader.readAsText(f)
}

const handleImport = async () => {
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const text = await textsStore.importText(formData)
    if (folderId.value) {
      await textsStore.updateText(text.id, { folder_id: folderId.value })
    }
    router.push('/')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-page {
  max-width: 800px;
  margin: 0 auto;
}
.drop-zone {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 3rem;
  text-align: center;
  cursor: pointer;
  margin: 1rem 0;
}
.drop-zone:hover {
  border-color: #42b883;
}
.preview {
  margin: 1rem 0;
}
.preview-content {
  width: 100%;
  min-height: 200px;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}
.import-options {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 1rem;
}
.option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.option input,
.option select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary {
  background: #42b883;
  color: white;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 2: 验证页面功能**

启动前后端，访问 http://localhost:3000/import，确认：
- 可以拖拽或选择 .txt 文件
- 预览内容显示正常
- 可以修改标题和选择文件夹
- 导入后跳转到文本列表

- [ ] **Step 3: 提交**

```bash
cd /Users/ckrey/video/script && git add web/src/views/Import.vue && git commit -m "feat: implement text import page"
```

---

### Task 11: 生产构建配置

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加启动脚本**

在 `pyproject.toml` 中添加：

```toml
[project.scripts]
subtitle-web = "server.app:main"

[tool.pytest.ini_options]
pythonpath = [".", "server"]
testpaths = ["tests", "server/tests"]
```

- [ ] **Step 2: 修改 app.py 添加 main 函数**

```python
# server/app.py 末尾添加
def main():
    app = create_app()
    app.run(debug=False, port=5000)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: 构建前端并测试生产模式**

```bash
cd /Users/ckrey/video/script/web && npm run build
cd /Users/ckrey/video/script && uv run python -m server.app
```

访问 http://localhost:5000 确认静态文件服务正常。

- [ ] **Step 4: 提交**

```bash
cd /Users/ckrey/video/script && git add pyproject.toml server/app.py && git commit -m "feat: add production build and startup script"
```

---

### Task 12: 端到端验证

- [ ] **Step 1: 运行所有后端测试**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/ server/tests/ -v
```

- [ ] **Step 2: 验证完整工作流程**

1. 启动开发环境
2. 创建文件夹"测试组"
3. 创建文本"测试文本"，输入内容，选择文件夹
4. 添加标签"测试标签"
5. 保存文本
6. 导出 SRT 文件
7. 导入一个 .txt 文件
8. 验证列表排序和筛选功能

- [ ] **Step 3: 验证 CLI 仍然正常工作**

```bash
cd /Users/ckrey/video/script && echo "测试文字。" | uv run main.py -o /dev/stdout
```

- [ ] **Step 4: 最终提交**

```bash
cd /Users/ckrey/video/script && git add -A && git commit -m "chore: complete web interface implementation"
```
