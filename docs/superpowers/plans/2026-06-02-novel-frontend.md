# Novel Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete frontend for the novel continuation module — project list, creation workspace with three-panel layout, outline tree, Markdown editor, AI generation, version management, character/event graph canvases, and AI extraction review.

**Architecture:** Vue 3 SFC with `<script setup>`, Pinia store for state, axios-based API layer, Ant Design Vue for UI components, `@vue-flow/core` for graph canvases. Follows existing patterns from VoiceWorkflowView (top/left/center/right/bottom layout).

**Tech Stack:** Vue 3, Vite, Pinia, Ant Design Vue 4, axios, @vue-flow/core

---

## File Map

### Create
- `web/src/stores/novels.js` — Pinia store
- `web/src/views/NovelProjectList.vue` — Project list page
- `web/src/views/NovelWorkspace.vue` — Creation workspace
- `web/src/components/novel/NovelOutlinePanel.vue` — Left panel
- `web/src/components/novel/NovelChapterEditor.vue` — Center editor
- `web/src/components/novel/NovelGenerationPanel.vue` — Right: generation params
- `web/src/components/novel/NovelVersionList.vue` — Right: versions
- `web/src/components/novel/NovelContextPanel.vue` — Right: context preview
- `web/src/components/novel/NovelReviewPanel.vue` — Right: review results
- `web/src/components/novel/NovelCharacterGraph.vue` — Graph: character canvas
- `web/src/components/novel/NovelEventGraph.vue` — Graph: event canvas
- `web/src/components/novel/NovelEntityInspector.vue` — Graph: entity panel
- `web/src/components/novel/NovelRelationInspector.vue` — Graph: relation panel
- `web/src/components/novel/NovelEventInspector.vue` — Graph: event panel
- `web/src/components/novel/NovelExtractionReviewModal.vue` — AI extraction modal
- `web/src/components/novel/NovelBlueprintWizard.vue` — Blueprint wizard

### Modify
- `web/src/api/index.js` — Add novelsApi
- `web/src/router/index.js` — Add /novels routes
- `web/src/App.vue` — Add navigation menu item

---

## Task 1: API Layer

**Files:**
- Modify: `web/src/api/index.js`

- [ ] **Step 1: Add novelsApi to the API module**

Add the following export to `web/src/api/index.js`, before the `export default api` line:

```javascript
export const novelsApi = {
  // Projects
  listProjects: (params) => api.get('/novels', { params }),
  createProject: (data) => api.post('/novels', data),
  getProject: (id) => api.get(`/novels/${id}`),
  updateProject: (id, data) => api.put(`/novels/${id}`, data),
  deleteProject: (id) => api.delete(`/novels/${id}`),

  // Outline
  getOutline: (pid) => api.get(`/novels/${pid}/outline`),
  createOutlineNode: (pid, data) => api.post(`/novels/${pid}/outline`, data),
  updateOutlineNode: (pid, nid, data) => api.put(`/novels/${pid}/outline/${nid}`, data),
  deleteOutlineNode: (pid, nid) => api.delete(`/novels/${pid}/outline/${nid}`),
  generateBlueprint: (pid, data) => api.post(`/novels/${pid}/blueprint/generate`, data),

  // Chapters
  listChapters: (pid) => api.get(`/novels/${pid}/chapters`),
  createChapter: (pid, data) => api.post(`/novels/${pid}/chapters`, data),
  getChapter: (pid, cid) => api.get(`/novels/${pid}/chapters/${cid}`),
  updateChapter: (pid, cid, data) => api.put(`/novels/${pid}/chapters/${cid}`, data),
  deleteChapter: (pid, cid) => api.delete(`/novels/${pid}/chapters/${cid}`),
  confirmChapter: (pid, cid) => api.post(`/novels/${pid}/chapters/${cid}/confirm`),

  // Versions
  generateVersions: (pid, cid, data) => api.post(`/novels/${pid}/chapters/${cid}/generate-versions`, data),
  listVersions: (pid, cid) => api.get(`/novels/${pid}/chapters/${cid}/versions`),
  acceptVersion: (pid, cid, vid) => api.post(`/novels/${pid}/chapters/${cid}/versions/${vid}/accept`),
  deleteVersion: (pid, cid, vid) => api.delete(`/novels/${pid}/chapters/${cid}/versions/${vid}`),

  // Entities & Relations
  listEntities: (pid, params) => api.get(`/novels/${pid}/entities`, { params }),
  createEntity: (pid, data) => api.post(`/novels/${pid}/entities`, data),
  getEntity: (pid, eid) => api.get(`/novels/${pid}/entities/${eid}`),
  updateEntity: (pid, eid, data) => api.put(`/novels/${pid}/entities/${eid}`, data),
  deleteEntity: (pid, eid) => api.delete(`/novels/${pid}/entities/${eid}`),
  listRelations: (pid) => api.get(`/novels/${pid}/relations`),
  createRelation: (pid, data) => api.post(`/novels/${pid}/relations`, data),
  updateRelation: (pid, rid, data) => api.put(`/novels/${pid}/relations/${rid}`, data),
  deleteRelation: (pid, rid) => api.delete(`/novels/${pid}/relations/${rid}`),

  // Events & Event Relations
  listEvents: (pid) => api.get(`/novels/${pid}/events`),
  createEvent: (pid, data) => api.post(`/novels/${pid}/events`, data),
  getEvent: (pid, eid) => api.get(`/novels/${pid}/events/${eid}`),
  updateEvent: (pid, eid, data) => api.put(`/novels/${pid}/events/${eid}`, data),
  deleteEvent: (pid, eid) => api.delete(`/novels/${pid}/events/${eid}`),
  createEventRelation: (pid, data) => api.post(`/novels/${pid}/event-relations`, data),
  updateEventRelation: (pid, rid, data) => api.put(`/novels/${pid}/event-relations/${rid}`, data),
  deleteEventRelation: (pid, rid) => api.delete(`/novels/${pid}/event-relations/${rid}`),

  // Graph
  getCharacterGraph: (pid) => api.get(`/novels/${pid}/graph/characters`),
  getEventGraph: (pid) => api.get(`/novels/${pid}/graph/events`),
  updateGraphLayout: (pid, data) => api.put(`/novels/${pid}/graph/layout`, data),
  extractGraph: (pid, cid, data) => api.post(`/novels/${pid}/chapters/${cid}/extract-graph`, data),
  acceptGraphChange: (pid, gid) => api.post(`/novels/${pid}/graph-changes/${gid}/accept`),
  rejectGraphChange: (pid, gid) => api.post(`/novels/${pid}/graph-changes/${gid}/reject`),
  reviewChapter: (pid, cid, data) => api.post(`/novels/${pid}/chapters/${cid}/review`, data),

  // Generation
  getGeneration: (gid) => api.get(`/novels/generations/${gid}`),
}
```

- [ ] **Step 2: Verify import works**

Run: `cd web && pnpm run dev` — verify no import errors in browser console.

- [ ] **Step 3: Commit**

```bash
git add web/src/api/index.js
git commit -m "feat(novel): add novelsApi to frontend API layer"
```

---

## Task 2: Store

**Files:**
- Create: `web/src/stores/novels.js`

- [ ] **Step 1: Create the Pinia store**

```javascript
// web/src/stores/novels.js
import { defineStore } from 'pinia'
import { novelsApi } from '../api'

export const useNovelsStore = defineStore('novels', {
  state: () => ({
    // Project list
    projects: [],
    projectsLoading: false,

    // Current project
    currentProject: null,

    // Outline
    outlineTree: [],

    // Chapters
    chapters: [],
    currentChapter: null,
    currentChapterLoading: false,

    // Versions
    versions: [],

    // Entities & relations (character graph)
    entities: [],
    relations: [],

    // Events & event relations (event graph)
    events: [],
    eventRelations: [],

    // Graph changes (AI extraction)
    graphChanges: [],

    // Generation
    generation: null,
    generationEventSource: null,

    // UI state
    activeMode: 'write', // 'write' | 'graph' | 'review'
    graphType: 'characters', // 'characters' | 'events'
    selectedEntityId: null,
    selectedRelationId: null,
    selectedEventId: null,
    rightTab: 'generation', // 'generation' | 'versions' | 'context' | 'review'
    leftTab: 'outline', // 'outline' | 'chapters' | 'settings'

    // Save state
    saving: false,
    dirty: false,
    saveError: null,
  }),

  getters: {
    selectedEntity: (state) => state.entities.find(e => e.id === state.selectedEntityId) || null,
    selectedRelation: (state) => state.relations.find(r => r.id === state.selectedRelationId) || null,
    selectedEvent: (state) => state.events.find(e => e.id === state.selectedEventId) || null,
    chapterWordCount: (state) => {
      if (!state.currentChapter?.content_markdown) return 0
      return state.currentChapter.content_markdown.replace(/\s/g, '').length
    },
  },

  actions: {
    // --- Projects ---
    async fetchProjects(params = {}) {
      this.projectsLoading = true
      try {
        const { data } = await novelsApi.listProjects(params)
        this.projects = data.items || data
      } finally {
        this.projectsLoading = false
      }
    },

    async createProject(projectData) {
      const { data } = await novelsApi.createProject(projectData)
      this.projects.unshift(data)
      return data
    },

    async deleteProject(id) {
      await novelsApi.deleteProject(id)
      this.projects = this.projects.filter(p => p.id !== id)
    },

    // --- Workspace loading ---
    async loadWorkspace(projectId) {
      const { data } = await novelsApi.getProject(projectId)
      this.currentProject = data
      await Promise.all([
        this.fetchOutline(projectId),
        this.fetchChapters(projectId),
      ])
    },

    // --- Outline ---
    async fetchOutline(pid) {
      const { data } = await novelsApi.getOutline(pid)
      this.outlineTree = data
    },

    async createOutlineNode(pid, nodeData) {
      const { data } = await novelsApi.createOutlineNode(pid, nodeData)
      await this.fetchOutline(pid)
      return data
    },

    async updateOutlineNode(pid, nid, nodeData) {
      const { data } = await novelsApi.updateOutlineNode(pid, nid, nodeData)
      await this.fetchOutline(pid)
      return data
    },

    async deleteOutlineNode(pid, nid) {
      await novelsApi.deleteOutlineNode(pid, nid)
      await this.fetchOutline(pid)
    },

    // --- Chapters ---
    async fetchChapters(pid) {
      const { data } = await novelsApi.listChapters(pid)
      this.chapters = data
    },

    async loadChapter(pid, cid) {
      this.currentChapterLoading = true
      try {
        const { data } = await novelsApi.getChapter(pid, cid)
        this.currentChapter = data
        this.versions = data.versions || []
        this.dirty = false
      } finally {
        this.currentChapterLoading = false
      }
    },

    async saveChapter(pid, cid, content) {
      this.saving = true
      this.saveError = null
      try {
        const { data } = await novelsApi.updateChapter(pid, cid, { content_markdown: content })
        this.currentChapter = data
        this.dirty = false
      } catch (e) {
        this.saveError = e.message
        throw e
      } finally {
        this.saving = false
      }
    },

    async confirmChapter(pid, cid) {
      const { data } = await novelsApi.confirmChapter(pid, cid)
      this.currentChapter = data
      // Refresh chapter list
      await this.fetchChapters(pid)
      return data
    },

    // --- Versions ---
    async fetchVersions(pid, cid) {
      const { data } = await novelsApi.listVersions(pid, cid)
      this.versions = data
    },

    async acceptVersion(pid, cid, vid) {
      const { data } = await novelsApi.acceptVersion(pid, cid, vid)
      this.currentChapter = data
      this.versions = data.versions || []
      return data
    },

    async deleteVersion(pid, cid, vid) {
      await novelsApi.deleteVersion(pid, cid, vid)
      this.versions = this.versions.filter(v => v.id !== vid)
    },

    // --- Generation ---
    async startGeneration(type, params) {
      this.generation = { status: 'pending', progress: 0 }
      this.rightTab = 'generation'

      let response
      if (type === 'blueprint') {
        response = await novelsApi.generateBlueprint(this.currentProject.id, params)
      } else if (type === 'chapter_version') {
        response = await novelsApi.generateVersions(this.currentProject.id, this.currentChapter.id, params)
      } else if (type === 'extract') {
        response = await novelsApi.extractGraph(this.currentProject.id, this.currentChapter.id, params)
      } else if (type === 'review') {
        response = await novelsApi.reviewChapter(this.currentProject.id, this.currentChapter.id, params)
      }

      const gen = response.data
      this.generation = gen
      this.listenGeneration(gen.id)
      return gen
    },

    listenGeneration(genId) {
      if (this.generationEventSource) {
        this.generationEventSource.close()
      }
      const es = new EventSource(`/api/novels/generations/${genId}/stream`)
      this.generationEventSource = es

      es.addEventListener('progress', (e) => {
        this.generation = JSON.parse(e.data)
      })

      es.addEventListener('completed', async (e) => {
        this.generation = JSON.parse(e.data)
        es.close()
        this.generationEventSource = null
        await this.handleGenerationComplete()
      })

      es.addEventListener('failed', (e) => {
        this.generation = JSON.parse(e.data)
        es.close()
        this.generationEventSource = null
      })
    },

    async handleGenerationComplete() {
      const gen = this.generation
      if (!gen?.result) return

      if (gen.generation_type === 'blueprint') {
        // Reload workspace after blueprint generation
        await this.loadWorkspace(this.currentProject.id)
      } else if (gen.generation_type === 'chapter_version') {
        // Reload versions
        await this.fetchVersions(this.currentProject.id, this.currentChapter.id)
        this.rightTab = 'versions'
      } else if (gen.generation_type === 'extract') {
        // Load graph changes
        this.graphChanges = gen.result.changes || []
        this.rightTab = 'context'
      } else if (gen.generation_type === 'review') {
        this.rightTab = 'review'
      }
    },

    // --- Entities ---
    async fetchEntities(pid, params) {
      const { data } = await novelsApi.listEntities(pid, params)
      this.entities = data
    },

    async createEntity(pid, entityData) {
      const { data } = await novelsApi.createEntity(pid, entityData)
      this.entities.push(data)
      return data
    },

    async updateEntity(pid, eid, entityData) {
      const { data } = await novelsApi.updateEntity(pid, eid, entityData)
      const idx = this.entities.findIndex(e => e.id === eid)
      if (idx !== -1) this.entities[idx] = data
      return data
    },

    async deleteEntity(pid, eid) {
      await novelsApi.deleteEntity(pid, eid)
      this.entities = this.entities.filter(e => e.id !== eid)
      this.relations = this.relations.filter(r => r.source_entity_id !== eid && r.target_entity_id !== eid)
    },

    // --- Relations ---
    async fetchRelations(pid) {
      const { data } = await novelsApi.listRelations(pid)
      this.relations = data
    },

    async createRelation(pid, relData) {
      const { data } = await novelsApi.createRelation(pid, relData)
      this.relations.push(data)
      return data
    },

    async updateRelation(pid, rid, relData) {
      const { data } = await novelsApi.updateRelation(pid, rid, relData)
      const idx = this.relations.findIndex(r => r.id === rid)
      if (idx !== -1) this.relations[idx] = data
      return data
    },

    async deleteRelation(pid, rid) {
      await novelsApi.deleteRelation(pid, rid)
      this.relations = this.relations.filter(r => r.id !== rid)
    },

    // --- Events ---
    async fetchEvents(pid) {
      const { data } = await novelsApi.listEvents(pid)
      this.events = data
    },

    async createEvent(pid, eventData) {
      const { data } = await novelsApi.createEvent(pid, eventData)
      this.events.push(data)
      return data
    },

    async updateEvent(pid, eid, eventData) {
      const { data } = await novelsApi.updateEvent(pid, eid, eventData)
      const idx = this.events.findIndex(e => e.id === eid)
      if (idx !== -1) this.events[idx] = data
      return data
    },

    async deleteEvent(pid, eid) {
      await novelsApi.deleteEvent(pid, eid)
      this.events = this.events.filter(e => e.id !== eid)
      this.eventRelations = this.eventRelations.filter(r => r.source_event_id !== eid && r.target_event_id !== eid)
    },

    // --- Event Relations ---
    async createEventRelation(pid, relData) {
      const { data } = await novelsApi.createEventRelation(pid, relData)
      this.eventRelations.push(data)
      return data
    },

    async deleteEventRelation(pid, rid) {
      await novelsApi.deleteEventRelation(pid, rid)
      this.eventRelations = this.eventRelations.filter(r => r.id !== rid)
    },

    // --- Graph ---
    async loadCharacterGraph(pid) {
      const [entRes, relRes] = await Promise.all([
        novelsApi.getCharacterGraph(pid),
        novelsApi.listRelations(pid),
      ])
      this.entities = entRes.data.nodes || entRes.data
      this.relations = relRes.data
    },

    async loadEventGraph(pid) {
      const [evRes, erRes] = await Promise.all([
        novelsApi.getEventGraph(pid),
        novelsApi.listEvents(pid),
      ])
      this.events = evRes.data.nodes || evRes.data
      this.eventRelations = erRes.data
    },

    async saveGraphLayout(pid, entityPositions, eventPositions) {
      await novelsApi.updateGraphLayout(pid, { entity_positions: entityPositions, event_positions: eventPositions })
    },

    // --- Graph Changes ---
    async acceptGraphChange(pid, gid) {
      const { data } = await novelsApi.acceptGraphChange(pid, gid)
      this.graphChanges = this.graphChanges.filter(c => c.id !== gid)
      return data
    },

    async rejectGraphChange(pid, gid) {
      await novelsApi.rejectGraphChange(pid, gid)
      this.graphChanges = this.graphChanges.filter(c => c.id !== gid)
    },

    // --- Cleanup ---
    cleanup() {
      if (this.generationEventSource) {
        this.generationEventSource.close()
        this.generationEventSource = null
      }
      this.currentProject = null
      this.currentChapter = null
      this.outlineTree = []
      this.chapters = []
      this.versions = []
      this.entities = []
      this.relations = []
      this.events = []
      this.eventRelations = []
      this.graphChanges = []
      this.generation = null
    },
  },
})
```

- [ ] **Step 2: Verify import**

Run: `cd web && pnpm run dev` — verify no errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/stores/novels.js
git commit -m "feat(novel): add novels Pinia store"
```

---

## Task 3: Router & Navigation

**Files:**
- Modify: `web/src/router/index.js`
- Modify: `web/src/App.vue`

- [ ] **Step 1: Add routes to router**

Add lazy imports and routes to `web/src/router/index.js`:

```javascript
const NovelProjectList = () => import('../views/NovelProjectList.vue')
const NovelWorkspace = () => import('../views/NovelWorkspace.vue')
```

Add to the routes array:

```javascript
{ path: '/novels', component: NovelProjectList },
{ path: '/novels/:id', component: NovelWorkspace },
```

- [ ] **Step 2: Add navigation menu item to App.vue**

Add a new menu item after the existing ones in the `a-menu`:

```html
<a-menu-item key="/novels">
  <template #icon>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
  </template>
  <span>剧情续写</span>
</a-menu-item>
```

Update the `selectedKeys` computed to handle `/novels`:

```javascript
if (route.path.startsWith('/novels')) return ['/novels']
```

- [ ] **Step 3: Commit**

```bash
git add web/src/router/index.js web/src/App.vue
git commit -m "feat(novel): add routes and navigation for novel module"
```

---

## Task 4: NovelProjectList Page

**Files:**
- Create: `web/src/views/NovelProjectList.vue`

- [ ] **Step 1: Create the project list page**

```vue
<!-- web/src/views/NovelProjectList.vue -->
<template>
  <div class="novel-project-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">剧情续写</h1>
        <p class="page-subtitle">{{ store.projects.length }} 个小说工程</p>
      </div>
      <a-button type="primary" @click="showCreateModal = true">新建工程</a-button>
    </div>

    <div class="list-tools">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索小说标题"
        allow-clear
        style="max-width: 320px"
      />
      <a-select v-model:value="statusFilter" placeholder="状态" allow-clear style="width: 120px">
        <a-select-option value="draft">草稿</a-select-option>
        <a-select-option value="active">进行中</a-select-option>
        <a-select-option value="completed">已完成</a-select-option>
      </a-select>
    </div>

    <a-empty v-if="!store.projects.length && !store.projectsLoading" description="还没有小说工程">
      <a-button type="primary" @click="showCreateModal = true">新建工程</a-button>
    </a-empty>

    <a-empty v-else-if="!filteredProjects.length" description="没有匹配的工程" />

    <a-spin v-else-if="store.projectsLoading" />

    <div v-else class="project-grid">
      <article
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-item"
      >
        <button class="project-main" @click="$router.push(`/novels/${project.id}`)">
          <strong>{{ project.title || '未命名小说' }}</strong>
          <span class="project-genre">{{ project.genre }}</span>
          <span class="project-progress">
            {{ project.stats?.chapter_count || 0 }} / {{ project.target_chapters }} 章
            · {{ formatWords(project.stats?.total_words || 0) }} / {{ formatWords(project.target_total_words) }}
          </span>
          <span class="project-meta">{{ project.knowledge_update_mode }} · {{ formatDate(project.updated_at) }}</span>
        </button>
        <div class="project-actions">
          <a-button size="small" @click="$router.push(`/novels/${project.id}`)">打开</a-button>
          <a-popconfirm
            title="删除这个工程？所有章节和图谱数据将被永久删除。"
            ok-text="删除"
            cancel-text="取消"
            @confirm="handleDelete(project)"
          >
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </article>
    </div>

    <!-- Create Project Modal -->
    <a-modal
      v-model:open="showCreateModal"
      title="新建小说工程"
      ok-text="创建"
      cancel-text="取消"
      :confirm-loading="creating"
      @ok="handleCreate"
      width="560px"
    >
      <a-form layout="vertical">
        <a-form-item label="小说标题" required>
          <a-input v-model:value="newProject.title" placeholder="例：长夜剑骨" />
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="newProject.genre" style="width: 100%">
            <a-select-option v-for="g in genres" :key="g" :value="g">{{ g }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="一句话创意">
          <a-textarea v-model:value="newProject.premise" placeholder="一句话描述你的小说创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="目标总字数">
              <a-input-number v-model:value="newProject.target_total_words" :min="10000" :step="100000" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="目标章节数">
              <a-input-number v-model:value="newProject.target_chapters" :min="10" :step="50" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="每章字数">
              <a-input-number v-model:value="newProject.words_per_chapter" :min="500" :step="500" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../stores/novels'

const store = useNovelsStore()
const keyword = ref('')
const statusFilter = ref(undefined)
const showCreateModal = ref(false)
const creating = ref(false)

const genres = ['玄幻', '仙侠', '都市', '悬疑', '言情', '科幻', '历史', '末世', '轻小说']

const newProject = ref({
  title: '',
  genre: '玄幻',
  premise: '',
  target_total_words: 300000,
  target_chapters: 100,
  words_per_chapter: 3000,
})

onMounted(() => store.fetchProjects())

const filteredProjects = computed(() => {
  let list = store.projects
  const q = keyword.value.trim().toLowerCase()
  if (q) list = list.filter(p => (p.title || '').toLowerCase().includes(q))
  if (statusFilter.value) list = list.filter(p => p.status === statusFilter.value)
  return list
})

const formatWords = (n) => {
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`
  return `${n}`
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN')
}

const handleCreate = async () => {
  if (!newProject.value.title.trim()) {
    message.warning('请填写小说标题')
    return
  }
  creating.value = true
  try {
    await store.createProject(newProject.value)
    showCreateModal.value = false
    newProject.value = { title: '', genre: '玄幻', premise: '', target_total_words: 300000, target_chapters: 100, words_per_chapter: 3000 }
    message.success('工程创建成功')
  } catch (e) {
    message.error('创建失败: ' + (e.response?.data?.error || e.message))
  } finally {
    creating.value = false
  }
}

const handleDelete = async (project) => {
  try {
    await store.deleteProject(project.id)
    message.success('已删除')
  } catch (e) {
    message.error('删除失败')
  }
}
</script>

<style scoped>
.novel-project-list {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-lg);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-lg);
}
.page-title {
  font-size: 24px;
  font-weight: 650;
  margin: 0;
}
.page-subtitle {
  color: var(--text-muted);
  margin: 4px 0 0;
}
.list-tools {
  display: flex;
  gap: 12px;
  margin-bottom: var(--space-lg);
}
.project-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.project-item {
  display: flex;
  align-items: center;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  background: var(--surface-card);
  overflow: hidden;
}
.project-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 16px;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
}
.project-main:hover { background: var(--surface-hover); }
.project-main strong { font-size: 15px; }
.project-genre {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.project-progress {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.project-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.project-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
}
</style>
```

- [ ] **Step 2: Verify page loads**

Run: `cd web && pnpm run dev` — navigate to `/novels`, verify page renders.

- [ ] **Step 3: Commit**

```bash
git add web/src/views/NovelProjectList.vue
git commit -m "feat(novel): add project list page with create/delete"
```

---

## Task 5: NovelWorkspace Skeleton

**Files:**
- Create: `web/src/views/NovelWorkspace.vue`

- [ ] **Step 1: Create the workspace layout shell**

```vue
<!-- web/src/views/NovelWorkspace.vue -->
<template>
  <div class="novel-workspace">
    <div v-if="loading" class="workspace-loading">加载中...</div>
    <div v-else class="workspace-shell">
      <!-- Top bar -->
      <div class="workspace-top">
        <div class="top-left">
          <a-button type="text" size="small" @click="$router.push('/novels')">
            ← 返回
          </a-button>
          <span class="project-title">{{ store.currentProject?.title }}</span>
          <span v-if="store.currentChapter" class="chapter-title">
            · {{ store.currentChapter.title }}
          </span>
        </div>
        <div class="top-center">
          <a-segmented v-model:value="store.activeMode" :options="[
            { label: '写作', value: 'write' },
            { label: '图谱', value: 'graph' },
            { label: '审稿', value: 'review' },
          ]" size="small" />
        </div>
        <div class="top-right">
          <span class="save-status" :class="saveStatusClass">{{ saveStatusText }}</span>
          <a-button size="small" @click="handleSave" :loading="store.saving">保存</a-button>
          <a-button size="small" type="primary" @click="handleGenerate">生成</a-button>
          <a-button size="small" @click="handleReview">审稿</a-button>
          <a-button size="small" @click="handleExtract">提取图谱</a-button>
        </div>
      </div>

      <!-- Write mode -->
      <template v-if="store.activeMode === 'write'">
        <div class="workspace-left">
          <NovelOutlinePanel />
        </div>
        <div class="workspace-center">
          <NovelChapterEditor />
        </div>
        <div class="workspace-right">
          <a-tabs v-model:activeKey="store.rightTab" size="small">
            <a-tab-pane key="generation" tab="生成">
              <NovelGenerationPanel />
            </a-tab-pane>
            <a-tab-pane key="versions" tab="版本">
              <NovelVersionList />
            </a-tab-pane>
            <a-tab-pane key="context" tab="上下文">
              <NovelContextPanel />
            </a-tab-pane>
            <a-tab-pane key="review" tab="审稿">
              <NovelReviewPanel />
            </a-tab-pane>
          </a-tabs>
        </div>
      </template>

      <!-- Graph mode -->
      <template v-else-if="store.activeMode === 'graph'">
        <div class="workspace-graph">
          <NovelCharacterGraph v-if="store.graphType === 'characters'" />
          <NovelEventGraph v-else />
        </div>
        <div class="workspace-right">
          <NovelEntityInspector v-if="store.selectedEntityId && store.graphType === 'characters'" />
          <NovelRelationInspector v-else-if="store.selectedRelationId && store.graphType === 'characters'" />
          <NovelEventInspector v-else-if="store.selectedEventId && store.graphType === 'events'" />
          <div v-else class="inspector-empty">
            <p>点击图谱节点查看属性</p>
          </div>
        </div>
      </template>

      <!-- Review mode -->
      <template v-else>
        <div class="workspace-left">
          <NovelOutlinePanel />
        </div>
        <div class="workspace-center">
          <NovelChapterEditor />
        </div>
        <div class="workspace-right">
          <NovelReviewPanel />
        </div>
      </template>

      <!-- Bottom status bar -->
      <div class="workspace-bottom">
        <span>{{ store.chapterWordCount }} 字</span>
        <span v-if="store.currentChapter?.target_words">
          / 目标 {{ store.currentChapter.target_words }} 字
        </span>
        <span class="status-sep">|</span>
        <span>{{ store.currentProject?.knowledge_update_mode }}</span>
      </div>
    </div>

    <!-- Modals -->
    <NovelExtractionReviewModal />
    <NovelBlueprintWizard v-model:open="showBlueprintWizard" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../stores/novels'
import NovelOutlinePanel from '../components/novel/NovelOutlinePanel.vue'
import NovelChapterEditor from '../components/novel/NovelChapterEditor.vue'
import NovelGenerationPanel from '../components/novel/NovelGenerationPanel.vue'
import NovelVersionList from '../components/novel/NovelVersionList.vue'
import NovelContextPanel from '../components/novel/NovelContextPanel.vue'
import NovelReviewPanel from '../components/novel/NovelReviewPanel.vue'
import NovelCharacterGraph from '../components/novel/NovelCharacterGraph.vue'
import NovelEventGraph from '../components/novel/NovelEventGraph.vue'
import NovelEntityInspector from '../components/novel/NovelEntityInspector.vue'
import NovelRelationInspector from '../components/novel/NovelRelationInspector.vue'
import NovelEventInspector from '../components/novel/NovelEventInspector.vue'
import NovelExtractionReviewModal from '../components/novel/NovelExtractionReviewModal.vue'
import NovelBlueprintWizard from '../components/novel/NovelBlueprintWizard.vue'

const route = useRoute()
const store = useNovelsStore()
const loading = ref(true)
const showBlueprintWizard = ref(false)

onMounted(async () => {
  try {
    await store.loadWorkspace(route.params.id)
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  store.cleanup()
})

const saveStatusClass = computed(() => {
  if (store.saveError) return 'status-error'
  if (store.saving) return 'status-saving'
  if (store.dirty) return 'status-dirty'
  return 'status-saved'
})

const saveStatusText = computed(() => {
  if (store.saveError) return '保存失败'
  if (store.saving) return '保存中...'
  if (store.dirty) return '未保存'
  return '已保存'
})

const handleSave = async () => {
  if (!store.currentChapter) return
  try {
    await store.saveChapter(store.currentProject.id, store.currentChapter.id, store.currentChapter.content_markdown)
    message.success('已保存')
  } catch {
    message.error('保存失败')
  }
}

const handleGenerate = () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  store.rightTab = 'generation'
}

const handleReview = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  await store.startGeneration('review', {})
}

const handleExtract = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  await store.startGeneration('extract', {})
}

// Watch for chapter content changes to mark dirty
watch(() => store.currentChapter?.content_markdown, () => {
  store.dirty = true
})
</script>

<style scoped>
.novel-workspace {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}
.workspace-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.workspace-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.workspace-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  gap: 16px;
  flex-shrink: 0;
}
.top-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.project-title {
  font-weight: 600;
  font-size: 14px;
}
.chapter-title {
  color: var(--text-muted);
  font-size: 13px;
}
.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.save-status {
  font-size: 12px;
}
.status-saved { color: var(--success); }
.status-dirty { color: var(--warning); }
.status-saving { color: var(--text-muted); }
.status-error { color: var(--error); }

.workspace-left {
  width: 300px;
  border-right: 1px solid var(--surface-border);
  overflow-y: auto;
  flex-shrink: 0;
}
.workspace-center {
  flex: 1;
  overflow-y: auto;
}
.workspace-right {
  width: 380px;
  border-left: 1px solid var(--surface-border);
  overflow-y: auto;
  flex-shrink: 0;
}
.workspace-graph {
  flex: 1;
}
.workspace-bottom {
  display: flex;
  align-items: center;
  padding: 4px 16px;
  border-top: 1px solid var(--surface-border);
  font-size: 12px;
  color: var(--text-muted);
  background: var(--surface-card);
  flex-shrink: 0;
  gap: 4px;
}
.status-sep { margin: 0 8px; }
.inspector-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
}
</style>
```

- [ ] **Step 2: Verify workspace loads**

Run: `cd web && pnpm run dev` — create a project, navigate to `/novels/:id`, verify layout renders.

- [ ] **Step 3: Commit**

```bash
git add web/src/views/NovelWorkspace.vue
git commit -m "feat(novel): add workspace layout with mode switching"
```

---

## Task 6: NovelOutlinePanel

**Files:**
- Create: `web/src/components/novel/NovelOutlinePanel.vue`

- [ ] **Step 1: Create the outline panel**

The panel has 3 tabs: 大纲 (tree), 章节 (list), 设定 (links).

Outline tab renders the tree recursively with status icons and context menu (add child, rename, delete). Chapter tab shows a flat list with click-to-load. Settings tab shows quick links to graph views.

Implement with `a-tree` for the outline tree (Ant Design Vue tree component), `a-list` for chapters, and simple buttons for settings links.

Full code in spec — key structure:

```vue
<template>
  <div class="novel-outline-panel">
    <a-tabs v-model:activeKey="store.leftTab" size="small">
      <a-tab-pane key="outline" tab="大纲">
        <!-- Tree with add/rename/delete -->
        <div class="outline-actions">
          <a-button size="small" @click="handleAddRoot">新增卷</a-button>
        </div>
        <a-tree
          v-if="treeData.length"
          :tree-data="treeData"
          :field-keys="{ key: 'id', title: 'title', children: 'children' }"
          default-expand-all
          @select="handleOutlineSelect"
        />
        <a-empty v-else description="暂无大纲" />
      </a-tab-pane>

      <a-tab-pane key="chapters" tab="章节">
        <!-- Chapter list -->
        <a-list :data-source="store.chapters" size="small">
          <template #renderItem="{ item }">
            <a-list-item
              :class="{ active: store.currentChapter?.id === item.id }"
              @click="handleChapterClick(item)"
            >
              <a-list-item-meta :title="item.title" :description="`${item.word_count} 字`" />
            </a-list-item>
          </template>
        </a-list>
      </a-tab-pane>

      <a-tab-pane key="settings" tab="设定">
        <div class="settings-links">
          <a-button block @click="enterGraph('characters')">人物关系图</a-button>
          <a-button block @click="enterGraph('events')">事件因果图</a-button>
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
```

Script handles: loading outline tree, adding/renaming/deleting nodes, loading chapters, clicking to switch chapters, entering graph mode.

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelOutlinePanel.vue
git commit -m "feat(novel): add outline panel with tree, chapter list, settings"
```

---

## Task 7: NovelChapterEditor

**Files:**
- Create: `web/src/components/novel/NovelChapterEditor.vue`

- [ ] **Step 1: Create the chapter editor**

Center panel with: chapter title input, toolbar (h1-h3/bold/quote/hr), textarea for markdown, word count + progress bar, auto-save on change (debounced 2s).

```vue
<template>
  <div class="novel-chapter-editor">
    <div v-if="!store.currentChapter" class="editor-empty">
      <p>请从左侧选择一个章节</p>
    </div>
    <template v-else>
      <div class="editor-title">
        <a-input
          v-model:value="store.currentChapter.title"
          placeholder="章节标题"
          size="large"
          @change="store.dirty = true"
        />
      </div>
      <div class="editor-toolbar">
        <a-button size="small" @click="insertMarkdown('## ')">H2</a-button>
        <a-button size="small" @click="insertMarkdown('### ')">H3</a-button>
        <a-button size="small" @click="wrapMarkdown('**')">B</a-button>
        <a-button size="small" @click="insertMarkdown('> ')">引用</a-button>
        <a-button size="small" @click="insertMarkdown('---\n')">分割线</a-button>
      </div>
      <div class="editor-body">
        <a-textarea
          ref="textareaRef"
          v-model:value="store.currentChapter.content_markdown"
          :autoSize="{ minRows: 20 }"
          placeholder="开始写作..."
          @change="handleContentChange"
        />
      </div>
      <div class="editor-footer">
        <a-progress
          :percent="wordCountPercent"
          :show-info="false"
          size="small"
          style="width: 120px"
        />
        <span>{{ store.chapterWordCount }} / {{ store.currentChapter.target_words || '—' }} 字</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const textareaRef = ref(null)
let saveTimer = null

const wordCountPercent = computed(() => {
  const target = store.currentChapter?.target_words
  if (!target) return 0
  return Math.min(100, Math.round((store.chapterWordCount / target) * 100))
})

const handleContentChange = () => {
  store.dirty = true
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    if (store.dirty && store.currentChapter) {
      store.saveChapter(store.currentProject.id, store.currentChapter.id, store.currentChapter.content_markdown)
    }
  }, 2000)
}

const insertMarkdown = (prefix) => {
  // Simple insert at cursor position
  const ta = textareaRef.value?.$el?.querySelector('textarea')
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = store.currentChapter.content_markdown
  store.currentChapter.content_markdown = text.slice(0, start) + prefix + text.slice(end)
  store.dirty = true
}

const wrapMarkdown = (wrapper) => {
  const ta = textareaRef.value?.$el?.querySelector('textarea')
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = store.currentChapter.content_markdown
  const selected = text.slice(start, end)
  store.currentChapter.content_markdown = text.slice(0, start) + wrapper + selected + wrapper + text.slice(end)
  store.dirty = true
}
</script>

<style scoped>
.novel-chapter-editor {
  padding: 16px 24px;
  max-width: 800px;
  margin: 0 auto;
}
.editor-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--text-muted);
}
.editor-title { margin-bottom: 12px; }
.editor-toolbar {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.editor-body :deep(.ant-input) {
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.8;
}
.editor-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelChapterEditor.vue
git commit -m "feat(novel): add markdown chapter editor with auto-save"
```

---

## Task 8: NovelGenerationPanel & NovelVersionList

**Files:**
- Create: `web/src/components/novel/NovelGenerationPanel.vue`
- Create: `web/src/components/novel/NovelVersionList.vue`

- [ ] **Step 1: Create generation panel**

Right-side panel for generation parameters: version type selector (steady/conflict/climax/suspense/romance/polish), target words, user instruction textarea, generate button. Shows progress during generation.

```vue
<template>
  <div class="novel-generation-panel">
    <div v-if="store.generation?.status === 'running' || store.generation?.status === 'pending'" class="gen-progress">
      <a-progress :percent="store.generation.progress" status="active" />
      <p>{{ store.generation.status === 'pending' ? '等待中...' : '生成中...' }}</p>
    </div>
    <template v-else>
      <a-form layout="vertical" size="small">
        <a-form-item label="版本方向">
          <a-select v-model:value="versionType" style="width: 100%">
            <a-select-option value="steady">稳健推进</a-select-option>
            <a-select-option value="conflict">强冲突</a-select-option>
            <a-select-option value="climax">爽点爆发</a-select-option>
            <a-select-option value="suspense">悬疑反转</a-select-option>
            <a-select-option value="romance">感情拉扯</a-select-option>
            <a-select-option value="polish">文风精修</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="用户指令">
          <a-textarea v-model:value="userInstruction" placeholder="可选：对本次生成的特殊要求..." :autoSize="{ minRows: 3, maxRows: 6 }" />
        </a-form-item>
        <a-button type="primary" block @click="handleGenerate">生成 3 个版本</a-button>
      </a-form>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const versionType = ref('steady')
const userInstruction = ref('')

const handleGenerate = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择章节')
    return
  }
  await store.startGeneration('chapter_version', {
    version_types: [versionType.value],
    user_instruction: userInstruction.value,
  })
}
</script>
```

- [ ] **Step 2: Create version list**

Shows version cards with type, time, word count, accepted badge. Actions: preview, accept, delete.

```vue
<template>
  <div class="novel-version-list">
    <a-empty v-if="!store.versions.length" description="暂无版本" />
    <div v-else class="version-cards">
      <div
        v-for="v in store.versions"
        :key="v.id"
        class="version-card"
        :class="{ accepted: v.accepted }"
      >
        <div class="version-header">
          <a-tag :color="typeColor(v.version_type)">{{ typeName(v.version_type) }}</a-tag>
          <a-tag v-if="v.accepted" color="green">已采纳</a-tag>
        </div>
        <div class="version-meta">
          {{ v.content_markdown?.length || 0 }} 字 · {{ formatDate(v.created_at) }}
        </div>
        <div class="version-preview">
          {{ (v.content_markdown || '').slice(0, 120) }}...
        </div>
        <div class="version-actions">
          <a-button size="small" @click="handlePreview(v)">预览</a-button>
          <a-button size="small" type="primary" @click="handleAccept(v)" :disabled="v.accepted">采纳</a-button>
          <a-popconfirm title="删除此版本？" @confirm="handleDelete(v)">
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

const typeNames = { steady: '稳健', conflict: '强冲突', climax: '爽点', suspense: '悬疑', romance: '感情', polish: '精修', custom: '自定义' }
const typeColors = { steady: 'blue', conflict: 'red', climax: 'orange', suspense: 'purple', romance: 'pink', polish: 'cyan', custom: 'default' }
const typeName = (t) => typeNames[t] || t
const typeColor = (t) => typeColors[t] || 'default'

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handlePreview = (v) => {
  // Show version content in editor temporarily
  store.currentChapter.content_markdown = v.content_markdown
}

const handleAccept = async (v) => {
  try {
    await store.acceptVersion(store.currentProject.id, store.currentChapter.id, v.id)
    message.success('已采纳')
  } catch {
    message.error('采纳失败')
  }
}

const handleDelete = async (v) => {
  try {
    await store.deleteVersion(store.currentProject.id, store.currentChapter.id, v.id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}
</script>

<style scoped>
.version-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; }
.version-card {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 12px;
}
.version-card.accepted { border-color: var(--success); }
.version-header { display: flex; gap: 4px; margin-bottom: 4px; }
.version-meta { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.version-preview { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5; }
.version-actions { display: flex; gap: 4px; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelGenerationPanel.vue web/src/components/novel/NovelVersionList.vue
git commit -m "feat(novel): add generation panel and version list"
```

---

## Task 9: NovelContextPanel & NovelReviewPanel

**Files:**
- Create: `web/src/components/novel/NovelContextPanel.vue`
- Create: `web/src/components/novel/NovelReviewPanel.vue`

- [ ] **Step 1: Create context panel**

Shows what context AI will use: outline, summaries, characters, events, foreshadowing. Each section collapsible.

```vue
<template>
  <div class="novel-context-panel">
    <a-collapse size="small">
      <a-collapse-panel key="outline" header="本章大纲">
        <p>{{ outlineText }}</p>
      </a-collapse-panel>
      <a-collapse-panel key="characters" header="相关人物">
        <div v-for="e in store.entities.slice(0, 5)" :key="e.id">
          <strong>{{ e.name }}</strong>
          <p class="ctx-text">{{ e.summary }}</p>
        </div>
      </a-collapse-panel>
      <a-collapse-panel key="events" header="相关事件">
        <div v-for="e in store.events.slice(0, 5)" :key="e.id">
          <strong>{{ e.title }}</strong>
          <p class="ctx-text">{{ e.summary }}</p>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const outlineText = computed(() => {
  // Find outline node for current chapter
  const node = store.outlineTree.find(n =>
    n.children?.some(c => c.id === store.currentChapter?.outline_node_id)
  )
  return node?.summary || '暂无大纲信息'
})
</script>

<style scoped>
.novel-context-panel { padding: 8px; }
.ctx-text { font-size: 12px; color: var(--text-muted); margin: 2px 0 8px; }
</style>
```

- [ ] **Step 2: Create review panel**

Shows review results with severity icons, category filters, overall score.

```vue
<template>
  <div class="novel-review-panel">
    <div v-if="!reviewResult" class="review-empty">
      <p>点击顶部"审稿"按钮开始一致性检查</p>
    </div>
    <template v-else>
      <div class="review-score">
        <a-progress type="circle" :percent="reviewResult.overall_score" :width="80" />
        <p>一致性评分</p>
      </div>
      <p class="review-summary">{{ reviewResult.summary }}</p>
      <a-list :data-source="reviewResult.issues" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <a-tag :color="severityColor(item.severity)">{{ item.severity }}</a-tag>
                <a-tag>{{ item.category }}</a-tag>
              </template>
              <template #description>
                <p>{{ item.description }}</p>
                <p class="suggestion">建议：{{ item.suggestion }}</p>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const reviewResult = computed(() => {
  if (store.generation?.generation_type === 'review' && store.generation?.result) {
    return store.generation.result
  }
  return null
})

const severityColor = (s) => ({ high: 'red', medium: 'orange', low: 'blue' }[s] || 'default')
</script>

<style scoped>
.novel-review-panel { padding: 8px; }
.review-empty { text-align: center; padding: 24px; color: var(--text-muted); }
.review-score { text-align: center; margin-bottom: 12px; }
.review-summary { font-size: 13px; margin-bottom: 12px; }
.suggestion { font-size: 12px; color: var(--text-muted); }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/novel/NovelContextPanel.vue web/src/components/novel/NovelReviewPanel.vue
git commit -m "feat(novel): add context preview and review result panels"
```

---

## Task 10: NovelCharacterGraph & Node Components

**Files:**
- Create: `web/src/components/novel/NovelCharacterGraph.vue`

- [ ] **Step 1: Create character graph canvas**

Vue Flow canvas with custom character/faction nodes, colored edges by relation type, toolbar for add/filter/save.

```vue
<template>
  <div class="novel-character-graph">
    <div class="graph-toolbar">
      <a-button size="small" @click="handleAddCharacter">新增人物</a-button>
      <a-button size="small" @click="handleAddRelation">新增关系</a-button>
      <a-button size="small" @click="handleSaveLayout">保存布局</a-button>
      <a-button size="small" @click="handleAutoLayout">自动布局</a-button>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @nodes-change="handleNodesChange"
      @node-click="handleNodeClick"
      @edge-click="handleEdgeClick"
    >
      <template #node-character="nodeProps">
        <div class="char-node" :class="{ selected: nodeProps.id == store.selectedEntityId }">
          <strong>{{ nodeProps.data.name }}</strong>
          <span>{{ nodeProps.data.summary?.slice(0, 20) }}</span>
        </div>
      </template>
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

onMounted(() => {
  if (store.currentProject) {
    store.loadCharacterGraph(store.currentProject.id)
  }
})

const flowNodes = computed(() =>
  store.entities.map(e => ({
    id: String(e.id),
    type: 'character',
    position: { x: e.node_x || 0, y: e.node_y || 0 },
    data: { name: e.name, summary: e.summary, importance: e.importance },
  }))
)

const edgeColors = {
  师徒: '#1890ff', 同盟: '#52c41a', 敌对: '#ff4d4f',
  亲属: '#722ed1', 恋人: '#eb2f96', 背叛: '#fa8c16',
}
const flowEdges = computed(() =>
  store.relations.map(r => ({
    id: String(r.id),
    source: String(r.source_entity_id),
    target: String(r.target_entity_id),
    label: r.label || r.relation_type,
    style: { stroke: edgeColors[r.relation_type] || '#999' },
    animated: r.status === 'hidden',
  }))
)

const handleNodesChange = (changes) => {
  for (const c of changes) {
    if (c.type === 'position' && c.position) {
      const entity = store.entities.find(e => String(e.id) === c.id)
      if (entity) {
        entity.node_x = c.position.x
        entity.node_y = c.position.y
      }
    }
  }
}

const handleNodeClick = ({ node }) => {
  store.selectedEntityId = Number(node.id)
  store.selectedRelationId = null
  store.selectedEventId = null
}

const handleEdgeClick = ({ edge }) => {
  store.selectedRelationId = Number(edge.id)
  store.selectedEntityId = null
}

const handleAddCharacter = async () => {
  await store.createEntity(store.currentProject.id, { name: '新角色', entity_type: 'character' })
}

const handleAddRelation = async () => {
  // Simple: prompt for source/target
  if (store.entities.length < 2) return
  await store.createRelation(store.currentProject.id, {
    source_entity_id: store.entities[0].id,
    target_entity_id: store.entities[1].id,
    relation_type: '其他',
  })
}

const handleSaveLayout = async () => {
  const positions = store.entities.map(e => ({ id: e.id, x: e.node_x || 0, y: e.node_y || 0 }))
  await store.saveGraphLayout(store.currentProject.id, positions, [])
}

const handleAutoLayout = () => {
  // Simple grid layout
  const cols = Math.ceil(Math.sqrt(store.entities.length))
  store.entities.forEach((e, i) => {
    e.node_x = (i % cols) * 250
    e.node_y = Math.floor(i / cols) * 150
  })
}
</script>

<style scoped>
.novel-character-graph { height: 100%; display: flex; flex-direction: column; }
.graph-toolbar {
  display: flex; gap: 4px; padding: 8px;
  border-bottom: 1px solid var(--surface-border);
}
.char-node {
  background: white; border: 2px solid #1890ff; border-radius: 8px;
  padding: 8px 12px; min-width: 120px; text-align: center;
}
.char-node.selected { border-color: #ff4d4f; box-shadow: 0 0 0 2px rgba(255,77,79,0.2); }
.char-node strong { display: block; font-size: 13px; }
.char-node span { font-size: 11px; color: #999; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelCharacterGraph.vue
git commit -m "feat(novel): add character relationship graph canvas"
```

---

## Task 11: NovelEventGraph

**Files:**
- Create: `web/src/components/novel/NovelEventGraph.vue`

- [ ] **Step 1: Create event graph canvas**

Same pattern as CharacterGraph but with event nodes and causal edges.

```vue
<template>
  <div class="novel-event-graph">
    <div class="graph-toolbar">
      <a-button size="small" @click="handleAddEvent">新增事件</a-button>
      <a-button size="small" @click="handleSaveLayout">保存布局</a-button>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @nodes-change="handleNodesChange"
      @node-click="handleNodeClick"
      @edge-click="handleEdgeClick"
    >
      <template #node-event="nodeProps">
        <div class="event-node" :class="[nodeProps.data.event_type, { selected: nodeProps.id == store.selectedEventId }]">
          <strong>{{ nodeProps.data.title }}</strong>
          <span>{{ nodeProps.data.event_type }}</span>
        </div>
      </template>
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

onMounted(() => {
  if (store.currentProject) {
    store.loadEventGraph(store.currentProject.id)
  }
})

const flowNodes = computed(() =>
  store.events.map(e => ({
    id: String(e.id),
    type: 'event',
    position: { x: e.node_x || 0, y: e.node_y || 0 },
    data: { title: e.title, event_type: e.event_type, summary: e.summary },
  }))
)

const edgeColors = {
  causes: '#52c41a', drives: '#1890ff', blocks: '#ff4d4f',
  reverses: '#fa8c16', reveals: '#722ed1', escalates: '#eb2f96',
}
const flowEdges = computed(() =>
  store.eventRelations.map(r => ({
    id: String(r.id),
    source: String(r.source_event_id),
    target: String(r.target_event_id),
    label: r.label || r.relation_type,
    style: { stroke: edgeColors[r.relation_type] || '#999' },
  }))
)

const handleNodesChange = (changes) => {
  for (const c of changes) {
    if (c.type === 'position' && c.position) {
      const ev = store.events.find(e => String(e.id) === c.id)
      if (ev) { ev.node_x = c.position.x; ev.node_y = c.position.y }
    }
  }
}

const handleNodeClick = ({ node }) => {
  store.selectedEventId = Number(node.id)
  store.selectedEntityId = null
  store.selectedRelationId = null
}

const handleEdgeClick = ({ edge }) => {
  // Could show edge inspector
}

const handleAddEvent = async () => {
  await store.createEvent(store.currentProject.id, { title: '新事件', event_type: 'event' })
}

const handleSaveLayout = async () => {
  const positions = store.events.map(e => ({ id: e.id, x: e.node_x || 0, y: e.node_y || 0 }))
  await store.saveGraphLayout(store.currentProject.id, [], positions)
}
</script>

<style scoped>
.novel-event-graph { height: 100%; display: flex; flex-direction: column; }
.graph-toolbar { display: flex; gap: 4px; padding: 8px; border-bottom: 1px solid var(--surface-border); }
.event-node {
  background: white; border: 2px solid #1890ff; border-radius: 8px;
  padding: 8px 12px; min-width: 140px; text-align: center;
}
.event-node.selected { border-color: #ff4d4f; }
.event-node strong { display: block; font-size: 13px; }
.event-node span { font-size: 11px; color: #999; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelEventGraph.vue
git commit -m "feat(novel): add event causality graph canvas"
```

---

## Task 12: Inspector Panels

**Files:**
- Create: `web/src/components/novel/NovelEntityInspector.vue`
- Create: `web/src/components/novel/NovelRelationInspector.vue`
- Create: `web/src/components/novel/NovelEventInspector.vue`

- [ ] **Step 1: Create entity inspector**

Editable form for entity properties: name, aliases, type, summary, importance, attributes.

```vue
<template>
  <div class="novel-entity-inspector" v-if="entity">
    <h4>人物属性</h4>
    <a-form layout="vertical" size="small">
      <a-form-item label="名称">
        <a-input v-model:value="entity.name" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="类型">
        <a-select v-model:value="entity.entity_type" @change="handleUpdate">
          <a-select-option value="character">人物</a-select-option>
          <a-select-option value="faction">势力</a-select-option>
          <a-select-option value="location">地点</a-select-option>
          <a-select-option value="item">物品</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="简介">
        <a-textarea v-model:value="entity.summary" :autoSize="{ minRows: 2, maxRows: 4 }" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="重要度">
        <a-slider v-model:value="entity.importance" :min="1" :max="10" @change="handleUpdate" />
      </a-form-item>
    </a-form>
    <a-button danger size="small" @click="handleDelete">删除</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()
const entity = computed(() => store.selectedEntity)

let updateTimer = null
const handleUpdate = () => {
  clearTimeout(updateTimer)
  updateTimer = setTimeout(() => {
    if (entity.value) {
      store.updateEntity(store.currentProject.id, entity.value.id, entity.value)
    }
  }, 500)
}

const handleDelete = async () => {
  if (entity.value) {
    await store.deleteEntity(store.currentProject.id, entity.value.id)
    store.selectedEntityId = null
  }
}
</script>

<style scoped>
.novel-entity-inspector { padding: 12px; }
h4 { margin: 0 0 12px; }
</style>
```

- [ ] **Step 2: Create relation inspector**

Shows relation type, label, description, strength, status. Editable.

- [ ] **Step 3: Create event inspector**

Shows event title, summary, type, timeline_order, participants, location. Editable.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/novel/NovelEntityInspector.vue web/src/components/novel/NovelRelationInspector.vue web/src/components/novel/NovelEventInspector.vue
git commit -m "feat(novel): add entity, relation, and event inspector panels"
```

---

## Task 13: NovelExtractionReviewModal

**Files:**
- Create: `web/src/components/novel/NovelExtractionReviewModal.vue`

- [ ] **Step 1: Create extraction review modal**

Modal triggered when graph extraction completes. Shows candidates by category (人物/关系/事件/因果). Each candidate has accept/edit/reject buttons. Bottom has accept all / reject all.

```vue
<template>
  <a-modal
    v-model:open="visible"
    title="AI 图谱提取结果"
    :footer="null"
    width="700px"
  >
    <div v-if="!changes.length" class="empty">
      <a-empty description="未发现新的图谱变更" />
    </div>
    <template v-else>
      <a-tabs size="small">
        <a-tab-pane v-for="cat in categories" :key="cat.key" :tab="cat.label">
          <a-list :data-source="changesByCategory(cat.key)" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :title="changeTitle(item)" :description="changeDescription(item)" />
                <template #actions>
                  <a-button size="small" type="primary" @click="handleAccept(item)">接受</a-button>
                  <a-button size="small" danger @click="handleReject(item)">拒绝</a-button>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-tab-pane>
      </a-tabs>
      <div class="modal-footer">
        <a-button @click="handleAcceptAll">全部接受</a-button>
        <a-button danger @click="handleRejectAll">全部拒绝</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup>
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const visible = computed({
  get: () => store.graphChanges.length > 0,
  set: () => {},
})

const changes = computed(() => store.graphChanges)

const categories = [
  { key: 'entity', label: '人物' },
  { key: 'relation', label: '关系' },
  { key: 'event', label: '事件' },
  { key: 'event_relation', label: '因果' },
]

const changesByCategory = (cat) => changes.value.filter(c => c.target_type === cat)

const changeTitle = (c) => {
  if (c.after?.name) return c.after.name
  if (c.after?.title) return c.after.title
  if (c.after?.relation_type) return c.after.relation_type
  return '变更'
}

const changeDescription = (c) => {
  if (c.after?.summary) return c.after.summary
  if (c.after?.description) return c.after.description
  return JSON.stringify(c.after || {}).slice(0, 100)
}

const handleAccept = async (c) => {
  try {
    await store.acceptGraphChange(store.currentProject.id, c.id)
    message.success('已接受')
  } catch (e) {
    message.error('接受失败: ' + (e.response?.data?.error || e.message))
  }
}

const handleReject = async (c) => {
  await store.rejectGraphChange(store.currentProject.id, c.id)
}

const handleAcceptAll = async () => {
  for (const c of [...store.graphChanges]) {
    try { await store.acceptGraphChange(store.currentProject.id, c.id) } catch {}
  }
  message.success('全部处理完成')
}

const handleRejectAll = async () => {
  for (const c of [...store.graphChanges]) {
    await store.rejectGraphChange(store.currentProject.id, c.id)
  }
}
</script>

<style scoped>
.empty { padding: 24px; }
.modal-footer { display: flex; gap: 8px; margin-top: 16px; justify-content: flex-end; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelExtractionReviewModal.vue
git commit -m "feat(novel): add AI extraction review modal"
```

---

## Task 14: NovelBlueprintWizard

**Files:**
- Create: `web/src/components/novel/NovelBlueprintWizard.vue`

- [ ] **Step 1: Create blueprint wizard**

Modal with: premise input, style settings, generate button, progress display. Calls `store.startGeneration('blueprint', ...)`.

```vue
<template>
  <a-modal
    v-model:open="open"
    title="AI 生成创作蓝图"
    ok-text="生成"
    cancel-text="取消"
    :confirm-loading="generating"
    @ok="handleGenerate"
    width="560px"
  >
    <a-form layout="vertical">
      <a-form-item label="一句话创意" required>
        <a-textarea v-model:value="premise" placeholder="描述你的小说核心创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
      </a-form-item>
    </a-form>
    <div v-if="generating" class="gen-status">
      <a-progress :percent="store.generation?.progress || 0" status="active" />
      <p>正在生成蓝图，请稍候...</p>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])
const store = useNovelsStore()
const premise = ref('')
const generating = ref(false)

const handleGenerate = async () => {
  if (!premise.value.trim()) {
    message.warning('请填写创意')
    return
  }
  generating.value = true
  try {
    await store.startGeneration('blueprint', { premise: premise.value })
    emit('update:open', false)
  } catch (e) {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.gen-status { margin-top: 16px; text-align: center; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/novel/NovelBlueprintWizard.vue
git commit -m "feat(novel): add blueprint generation wizard"
```

---

## Task 15: Final Integration & Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run dev server and verify all pages load**

```bash
cd web && pnpm run dev
```

Navigate to:
- `/novels` — verify project list renders
- `/novels/:id` — verify workspace layout renders
- Test mode switching (write/graph/review)

- [ ] **Step 2: Build production bundle**

```bash
cd web && pnpm run build
```

Verify no build errors.

- [ ] **Step 3: Final commit if needed**

```bash
git status
```
