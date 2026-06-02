# Novel Frontend Design Spec

## Overview

Frontend for the novel continuation & knowledge graph module — a long-form AI novel writing workstation. Two pages: project list and creation workspace. Uses existing Vue 3 + Vite + Pinia + Ant Design Vue + Vue Flow stack.

**Key decisions:**
- Markdown editor: textarea + toolbar (simple, per spec guidance)
- Graph canvas: `@vue-flow/core` (reuses existing dependency)
- Mode switching: write / graph / review within workspace
- SSE for generation progress

## File Structure

```
web/src/
├── api/index.js                      # Add novelsApi module
├── stores/novels.js                  # Pinia store for all novel state
├── router/index.js                   # Add /novels routes
├── views/
│   ├── NovelProjectList.vue          # Project list page
│   └── NovelWorkspace.vue            # Creation workspace (main view)
└── components/novel/
    ├── NovelBlueprintWizard.vue       # Blueprint generation wizard (Modal)
    ├── NovelOutlinePanel.vue          # Left: outline tree + chapter list + settings
    ├── NovelChapterEditor.vue         # Center: textarea + toolbar + AI result
    ├── NovelGenerationPanel.vue       # Right: generation parameters
    ├── NovelVersionList.vue           # Right: version list
    ├── NovelContextPanel.vue          # Right: context preview
    ├── NovelReviewPanel.vue           # Right: review results
    ├── NovelCharacterGraph.vue        # Graph mode: character relationship canvas
    ├── NovelEventGraph.vue            # Graph mode: event causality canvas
    ├── NovelEntityInspector.vue       # Graph right: entity property panel
    ├── NovelRelationInspector.vue     # Graph right: relation property panel
    ├── NovelEventInspector.vue        # Graph right: event property panel
    └── NovelExtractionReviewModal.vue # AI extraction confirmation modal
```

## API Layer

Add `novelsApi` to `web/src/api/index.js`:

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

  // Generation status
  getGeneration: (gid) => api.get(`/novels/generations/${gid}`),
}
```

## Store

`web/src/stores/novels.js` — Single store for all novel state:

**State:**
- `projects`, `projectsLoading` — project list
- `currentProject` — active project
- `outlineTree` — outline tree (nested)
- `chapters` — chapter list
- `currentChapter` — active chapter with content
- `versions` — versions for current chapter
- `entities`, `relations` — character graph data
- `events`, `eventRelations` — event graph data
- `graphChanges` — pending AI extraction changes
- `generation` — current generation task {id, status, progress, result}
- `activeMode` — 'write' | 'graph' | 'review'
- `graphType` — 'characters' | 'events'
- `saving`, `dirty` — save state

**Key actions:**
- All CRUD operations mapping to `novelsApi`
- `startGeneration(type, params)` — creates generation + starts SSE listener
- `listenGeneration(genId)` — EventSource on `/api/novels/generations/{id}/stream`
- `loadWorkspace(projectId)` — parallel fetch project + outline + chapters
- `loadChapter(chapterId)` — fetch chapter + versions
- `loadCharacterGraph()` / `loadEventGraph()` — fetch graph data

## Router

Add to `web/src/router/index.js`:
```javascript
const NovelProjectList = () => import('../views/NovelProjectList.vue')
const NovelWorkspace = () => import('../views/NovelWorkspace.vue')

// In routes array:
{ path: '/novels', component: NovelProjectList },
{ path: '/novels/:id', component: NovelWorkspace },
```

## Navigation

Add to `App.vue` menu:
```html
<a-menu-item key="/novels">
  <template #icon><!-- book icon --></template>
  <span>剧情续写</span>
</a-menu-item>
```

Update `selectedKeys` computed to handle `/novels` path.

## Page 1: NovelProjectList.vue

Layout:
- Header: title + "新建工程" button
- Search input
- Table: title, genre, progress (chapters/words), knowledge mode, updated_at, actions (open/delete)
- Create project modal (3-step wizard: basic info → style → init method)

## Page 2: NovelWorkspace.vue

Layout (same pattern as VoiceWorkflowView):
```
.top    → NovelOutlinePanel toolbar + mode switcher
.left   → NovelOutlinePanel (outline tree / chapter list / settings tabs)
.center → NovelChapterEditor (write mode) or CharacterGraph/EventGraph (graph mode)
.right  → GenerationPanel / VersionList / ContextPanel / ReviewPanel / EntityInspector
.bottom → Status bar (word count, progress, save state)
```

Mode switching:
- `write`: left + center(editor) + right(panels)
- `graph`: full-screen graph canvas + right(inspector)
- `review`: center(editor) + right(review panel)

## Components

### NovelOutlinePanel.vue
- Tabs: 大纲 / 章节 / 设定
- Outline tab: tree with drag-reorder, status icons, add/rename/delete
- Chapter tab: list with search, click to load chapter
- Settings tab: quick links to entities, world, events, graphs

### NovelChapterEditor.vue
- Chapter title input
- Markdown toolbar (h1-h3, bold, quote, hr)
- textarea for content
- Word count + target progress bar
- AI result preview area (accept/insert/replace/discard buttons)
- Auto-save on change (debounced)

### NovelGenerationPanel.vue
- Version type selector (steady/conflict/climax/suspense/romance/polish)
- Target words input
- User instruction textarea
- Generate button → calls store.startGeneration()
- Progress display during generation

### NovelVersionList.vue
- Version cards: type, time, model, word count, accepted badge
- Actions: preview, accept, delete
- Diff view between versions (simple side-by-side)

### NovelContextPanel.vue
- Shows what context AI will use: outline, summaries, characters, events, foreshadowing
- Each section collapsible

### NovelReviewPanel.vue
- Issues list with severity icons
- Category filter (character/world/timeline/location/causality/foreshadow/progression/redundancy/padding)
- Overall score
- Click issue to highlight in editor

### NovelCharacterGraph.vue
- Vue Flow canvas with custom node types
- Toolbar: add character, add faction, add relation, auto-layout, save layout, filters
- Custom node styles: protagonist (bold border), villain (red), supporting (normal), hidden (dashed)
- Edge styles by relation type (colors: green=ally, red=enemy, blue=mentor, purple=family, pink=romance, orange-dashed=betrayal)
- Click node → NovelEntityInspector in right panel
- Click edge → NovelRelationInspector in right panel
- Right-click canvas → add node/edge

### NovelEventGraph.vue
- Same canvas pattern as CharacterGraph
- Event node types: normal,转折, 伏笔, 回收, 冲突, 解决, 揭示
- Causal edge types: 导致, 推动, 阻碍, 反转, 揭露, 回收, 升级, 解决
- Click event → NovelEventInspector

### NovelEntityInspector.vue
- Editable fields: name, aliases, type, summary, attributes (genre-specific)
- Importance slider
- Related relations list

### NovelRelationInspector.vue
- Editable fields: type, label, description, strength, status
- Evidence list

### NovelEventInspector.vue
- Editable fields: title, summary, type, timeline_order, participants, location, effects

### NovelExtractionReviewModal.vue
- Triggered after extract-graph completes
- Tabs: 人物 / 关系 / 事件 / 因果 / 状态变化
- Each candidate: accept/edit/reject buttons
- Bottom: accept all / reject all / save selected

### NovelBlueprintWizard.vue
- Modal with steps: premise → style → generate → review
- Calls generateBlueprint API
- Shows progress during generation

## SSE Generation Progress

```javascript
function listenGeneration(genId) {
  const es = new EventSource(`/api/novels/generations/${genId}/stream`)
  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    store.generation = data
  })
  es.addEventListener('completed', (e) => {
    const data = JSON.parse(e.data)
    store.generation = data
    store.handleGenerationComplete(data)
    es.close()
  })
  es.addEventListener('failed', (e) => {
    const data = JSON.parse(e.data)
    store.generation = data
    es.close()
  })
}
```

## Graph Canvas Implementation

Using `@vue-flow/core` with custom node/edge types:

```javascript
// Custom node types
const nodeTypes = {
  character: CharacterNode,
  faction: FactionNode,
  event: EventNode,
}

// Custom edge styles by relation type
const edgeStyles = {
  ally: { stroke: '#52c41a' },
  enemy: { stroke: '#ff4d4f' },
  mentor: { stroke: '#1890ff' },
  family: { stroke: '#722ed1' },
  romance: { stroke: '#eb2f96' },
  betrayal: { stroke: '#fa8c16', strokeDasharray: '5,5' },
}
```

Node positions saved via `updateGraphLayout` API on drag end.
