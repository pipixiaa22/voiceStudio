# JianYing Folder Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the manual JianYing path text input with a server-side folder browser, keeping manual input as fallback.

**Architecture:** Add a Flask endpoint that lists directories on the server filesystem. Add a Vue modal component that calls this endpoint and lets users navigate and select a folder. Wire it into both JianYing export modals.

**Tech Stack:** Flask (Python), Vue 3 + Ant Design Vue (frontend)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `server/routes/system.py` | Create | New blueprint with `GET /api/system/ls` |
| `server/app.py:47-51` | Modify | Register `system_bp` |
| `server/tests/test_system.py` | Create | Tests for the endpoint |
| `web/src/api/index.js:147` | Modify | Add `systemApi` |
| `web/src/components/FolderBrowser.vue` | Create | Reusable folder browser modal |
| `web/src/views/VoiceWorkflowView.vue:127-135` | Modify | Add folder picker to Jianying modal |
| `web/src/components/SrtExportModal.vue:33-36` | Modify | Add folder picker to Jianying section |

---

### Task 1: Backend — system route with folder listing

**Files:**
- Create: `server/routes/system.py`
- Modify: `server/app.py:47-51`
- Test: `server/tests/test_system.py`

- [ ] **Step 1: Create `server/routes/system.py`**

```python
import os
from pathlib import Path
from flask import Blueprint, request, jsonify

system_bp = Blueprint('system', __name__)

DEFAULT_JIANYING_DIR = os.path.expanduser(
    '~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft'
)


@system_bp.route('/api/system/ls', methods=['GET'])
def list_directories():
    raw_path = request.args.get('path', '').strip()
    if not raw_path:
        target = Path(DEFAULT_JIANYING_DIR)
    else:
        target = Path(os.path.expanduser(raw_path)).resolve()

    if not target.exists():
        return jsonify({'error': '路径不存在'}), 400
    if not target.is_dir():
        return jsonify({'error': '不是目录'}), 400

    try:
        entries = sorted(
            [
                {'name': item.name, 'path': str(item)}
                for item in target.iterdir()
                if item.is_dir() and not item.name.startswith('.')
            ],
            key=lambda e: e['name'].lower(),
        )
    except PermissionError:
        return jsonify({'error': '没有访问权限'}), 403

    parent = str(target.parent) if target.parent != target else None
    return jsonify({
        'current': str(target),
        'parent': parent,
        'entries': entries,
    })
```

- [ ] **Step 2: Register blueprint in `server/app.py`**

After line 51 (`app.register_blueprint(voice_workflows_bp)`), add:

```python
        from server.routes.system import system_bp
        app.register_blueprint(system_bp)
```

- [ ] **Step 3: Create `server/tests/test_system.py`**

```python
import os
import tempfile
from pathlib import Path


def test_ls_default_returns_200_or_400(client):
    """Default path may not exist on CI, but the endpoint should respond."""
    resp = client.get('/api/system/ls')
    assert resp.status_code in (200, 400)


def test_ls_specific_directory(client):
    """Listing a known directory should return entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / 'subA').mkdir()
        (Path(tmpdir) / 'subB').mkdir()
        (Path(tmpdir) / '.hidden').mkdir()
        resp = client.get(f'/api/system/ls?path={tmpdir}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current'] == tmpdir
        assert data['parent'] is not None
        names = [e['name'] for e in data['entries']]
        assert 'subA' in names
        assert 'subB' in names
        assert '.hidden' not in names


def test_ls_nonexistent_path(client):
    resp = client.get('/api/system/ls?path=/nonexistent/path/xyz')
    assert resp.status_code == 400
    assert '不存在' in resp.get_json()['error']


def test_ls_file_not_directory(client):
    with tempfile.NamedTemporaryFile(suffix='.txt') as f:
        resp = client.get(f'/api/system/ls?path={f.name}')
        assert resp.status_code == 400
        assert '不是目录' in resp.get_json()['error']
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest server/tests/test_system.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/routes/system.py server/app.py server/tests/test_system.py
git commit -m "feat: add /api/system/ls endpoint for folder browsing"
```

---

### Task 2: Frontend — API layer

**Files:**
- Modify: `web/src/api/index.js:147`

- [ ] **Step 1: Add `systemApi` to `web/src/api/index.js`**

Before the final `export default api` line, add:

```javascript
export const systemApi = {
  ls: (path) => api.get('/system/ls', { params: { path } }),
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/api/index.js
git commit -m "feat: add systemApi.ls to frontend API layer"
```

---

### Task 3: Frontend — FolderBrowser component

**Files:**
- Create: `web/src/components/FolderBrowser.vue`

- [ ] **Step 1: Create `web/src/components/FolderBrowser.vue`**

```vue
<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="选择剪映工程目录"
    @ok="handleConfirm"
    ok-text="选择此文件夹"
    cancel-text="取消"
    width="520px"
  >
    <div class="folder-browser">
      <div class="breadcrumb">
        <span
          v-for="(seg, i) in breadcrumbSegments"
          :key="i"
          class="crumb"
          :class="{ active: i === breadcrumbSegments.length - 1 }"
          @click="navigateTo(seg.path)"
        >{{ seg.name }}</span>
      </div>

      <div class="folder-list" v-if="!loading">
        <div
          v-if="parentPath"
          class="folder-row"
          @click="navigateTo(parentPath)"
        >
          <span class="folder-icon">..</span>
          <span class="folder-name">上一级</span>
        </div>
        <div
          v-for="entry in entries"
          :key="entry.path"
          class="folder-row"
          :class="{ selected: selectedPath === entry.path }"
          @click="selectedPath = entry.path"
          @dblclick="navigateTo(entry.path)"
        >
          <span class="folder-icon">📁</span>
          <span class="folder-name">{{ entry.name }}</span>
        </div>
        <div v-if="!entries.length && !parentPath" class="empty-hint">
          此目录为空
        </div>
      </div>

      <div v-if="loading" class="loading-hint">
        <a-spin size="small" /> 加载中...
      </div>

      <div v-if="error" class="error-hint">
        {{ error }}
        <a-button size="small" @click="load(currentPath)">重试</a-button>
      </div>

      <div class="current-path">
        当前目录：<code>{{ currentPath || '未选择' }}</code>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { systemApi } from '../api'

const props = defineProps({
  open: Boolean,
  startPath: { type: String, default: '' },
})

const emit = defineEmits(['update:open', 'select'])

const DEFAULT_PATH = ''

const currentPath = ref('')
const parentPath = ref(null)
const entries = ref([])
const selectedPath = ref('')
const loading = ref(false)
const error = ref('')

const breadcrumbSegments = computed(() => {
  if (!currentPath.value) return []
  const parts = currentPath.value.split('/').filter(Boolean)
  return parts.map((part, i) => ({
    name: part,
    path: '/' + parts.slice(0, i + 1).join('/'),
  }))
})

const load = async (path) => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await systemApi.ls(path || '')
    currentPath.value = data.current
    parentPath.value = data.parent
    entries.value = data.entries
    selectedPath.value = ''
  } catch (err) {
    error.value = err.response?.data?.error || '加载失败'
  } finally {
    loading.value = false
  }
}

const navigateTo = (path) => {
  load(path)
}

const handleConfirm = () => {
  const path = selectedPath.value || currentPath.value
  if (!path) return
  emit('select', path)
  emit('update:open', false)
}

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    const initial = props.startPath || localStorage.getItem('jianying_draft_dir') || DEFAULT_PATH
    load(initial)
  }
})
</script>

<style scoped>
.folder-browser {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  font-size: 12px;
  padding: var(--space-xs) 0;
}

.crumb {
  cursor: pointer;
  color: var(--text-muted);
  padding: 2px 4px;
  border-radius: 3px;
}

.crumb:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.crumb.active {
  color: var(--text-primary);
  font-weight: 500;
}

.crumb::after {
  content: ' / ';
  color: var(--text-muted);
  margin-left: 2px;
}

.crumb:last-child::after {
  content: '';
}

.folder-list {
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  max-height: 300px;
  overflow-y: auto;
  background: var(--paper-soft);
}

.folder-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid var(--surface-border);
}

.folder-row:last-child {
  border-bottom: none;
}

.folder-row:hover {
  background: var(--surface-hover);
}

.folder-row.selected {
  background: var(--primary-bg);
  color: var(--primary);
}

.folder-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-hint,
.empty-hint {
  padding: var(--space-lg);
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.error-hint {
  padding: var(--space-sm);
  text-align: center;
  color: var(--error);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
}

.current-path {
  font-size: 12px;
  color: var(--text-muted);
  padding-top: var(--space-xs);
}

.current-path code {
  background: var(--paper-soft);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  word-break: break-all;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/FolderBrowser.vue
git commit -m "feat: add FolderBrowser component for JianYing path selection"
```

---

### Task 4: Integrate into VoiceWorkflowView

**Files:**
- Modify: `web/src/views/VoiceWorkflowView.vue`

- [ ] **Step 1: Add import for FolderBrowser**

After line 151 (`import TimelineAuditionBar ...`), add:

```javascript
import FolderBrowser from '../components/FolderBrowser.vue'
```

- [ ] **Step 2: Add reactive state**

After line 186 (`const jianyingDraftDir = ref(...)`), add:

```javascript
const showFolderBrowser = ref(false)
```

- [ ] **Step 3: Replace the input in the Jianying modal**

Replace lines 127-134:

```html
        <a-form layout="vertical">
          <a-form-item label="剪映工程目录">
            <a-input
              v-model:value="jianyingDraftDir"
              placeholder="/Users/你的用户名/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID"
            />
          </a-form-item>
        </a-form>
```

With:

```html
        <a-form layout="vertical">
          <a-form-item label="剪映工程目录">
            <div style="display: flex; gap: 8px;">
              <a-input
                v-model:value="jianyingDraftDir"
                placeholder="/Users/你的用户名/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID"
                style="flex: 1"
              />
              <a-button @click="showFolderBrowser = true">浏览</a-button>
            </div>
          </a-form-item>
        </a-form>
        <FolderBrowser
          v-model:open="showFolderBrowser"
          @select="jianyingDraftDir = $event"
        />
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/VoiceWorkflowView.vue
git commit -m "feat: add folder browser to JianYing export modal in VoiceWorkflowView"
```

---

### Task 5: Integrate into SrtExportModal

**Files:**
- Modify: `web/src/components/SrtExportModal.vue`

- [ ] **Step 1: Add import for FolderBrowser**

After line 65 (`import SrtOptionsPanel ...`), add:

```javascript
import FolderBrowser from './FolderBrowser.vue'
```

- [ ] **Step 2: Add reactive state**

After line 83 (`const jianyingDraftDir = ref(...)`), add:

```javascript
const showFolderBrowser = ref(false)
```

- [ ] **Step 3: Replace the input in the Jianying section**

Replace lines 33-36:

```html
        <a-input
          v-model:value="jianyingDraftDir"
          placeholder="/Users/你的用户名/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID"
        />
```

With:

```html
        <div style="display: flex; gap: 8px;">
          <a-input
            v-model:value="jianyingDraftDir"
            placeholder="/Users/你的用户名/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID"
            style="flex: 1"
          />
          <a-button @click="showFolderBrowser = true">浏览</a-button>
        </div>
```

- [ ] **Step 4: Add FolderBrowser component after the modal**

Before the closing `</template>` tag (line 58), add inside the `<a-modal>` but after the export-actions div:

Actually, the FolderBrowser needs to be outside the `<a-modal>` since it's a modal itself. Place it after the `</a-modal>` closing tag but still inside the root `<div>` or after the component. Let me check the template structure.

The template root is `<a-modal>`. FolderBrowser should be placed after it. Since the root element is the modal itself, add FolderBrowser as a sibling by wrapping both in a fragment. But Vue 3 supports fragments, so simply add after the `</a-modal>`:

Replace the template to add FolderBrowser after the modal. After line 57 (`</a-modal>`), add:

```html
    <FolderBrowser
      v-model:open="showFolderBrowser"
      @select="jianyingDraftDir = $event"
    />
```

Since Vue 3 supports multiple root nodes, this will work as a sibling of the `<a-modal>`.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/SrtExportModal.vue
git commit -m "feat: add folder browser to JianYing import section in SrtExportModal"
```

---

### Task 6: Verify everything works

- [ ] **Step 1: Run all tests**

Run: `uv run pytest -v`
Expected: All tests pass, including the new `test_system.py` tests.

- [ ] **Step 2: Start servers and manual test**

Run: `./start.sh start`
Open `http://localhost:3000`, navigate to a voice workflow, open the JianYing export modal, click "浏览", verify the folder browser opens and navigates correctly.

- [ ] **Step 3: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: polish folder browser integration"
```
