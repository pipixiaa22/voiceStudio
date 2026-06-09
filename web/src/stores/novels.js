// web/src/stores/novels.js
import { defineStore } from 'pinia'
import { novelsApi } from '../api'
import { useModelSettings } from './modelSettings'

function getNovelModelConfig() {
  const { resolveUsage } = useModelSettings()
  const resolved = resolveUsage('novel_continuation')
  if (resolved?.api_key) {
    if (resolved.provider_key !== 'mimo') {
      return resolved
    }
  }

  const fallbackKey = localStorage.getItem('novel_deepseek_llm_key') || localStorage.getItem('deepseek_api_key') || ''
  if (!fallbackKey) return null
  return {
    provider_key: 'deepseek',
    model_key: 'deepseek-chat',
    api_key: fallbackKey,
    base_url: localStorage.getItem('novel_deepseek_base_url') || 'https://api.deepseek.com',
  }
}

function withNovelModelConfig(params = {}) {
  const modelConfig = getNovelModelConfig()
  if (!modelConfig) return params
  return {
    ...params,
    model_config: modelConfig,
  }
}

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
    _lastSavedSnapshot: null,
    _autoSaveTimer: null,
    _autoSaveChapterId: null,

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

    // Memories
    memories: [],
    memoryChanges: [],
    memorySearchResults: [],
    memoryLoading: false,

    // Generation
    generation: null,
    generationEventSource: null,

    // UI state
    activeMode: 'write', // 'write' | 'graph' | 'review' | 'memory'
    graphType: 'characters', // 'characters' | 'events'
    selectedEntityId: null,
    selectedRelationId: null,
    selectedEventId: null,
    rightTab: 'generation', // 'generation' | 'versions' | 'context' | 'review'
    leftTab: 'outline', // 'outline' | 'chapters' | 'settings'

    // Obsidian graph view state
    graphView: {
      mode: 'explore',        // 'explore' | 'edit'
      query: '',
      selectedId: null,        // namespaced: 'entity:12' or 'event:34'
      hoveredId: null,
      focusedId: null,
      neighborIds: [],
      filters: {
        nodeTypes: [],         // ['character', 'location', 'item', 'faction']
        edgeTypes: [],         // ['ally', 'enemy', 'mentor', ...]
        importanceRange: [0, 10],
        chapterRange: null,
      },
      layout: {
        running: false,
        pinned: {},            // { 'entity:12': { x, y } }
        zoom: 1,
        center: [0, 0],
      },
      stats: null,
      legend: null,
    },

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
      if (this.generationEventSource) {
        this.generationEventSource.close()
        this.generationEventSource = null
      }
      this.generation = null
      this.currentChapter = null
      this.versions = []
      this.dirty = false
      this.saveError = null
      this.activeMode = 'write'
      this.rightTab = 'generation'
      const { data } = await novelsApi.getProject(projectId)
      this.currentProject = data
      await Promise.all([
        this.fetchOutline(projectId),
        this.fetchChapters(projectId),
      ])
      if (this.chapters.length) {
        await this.loadChapter(projectId, this.chapters[0].id)
      }
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

    async createChapter(pid, chapterData) {
      const { data } = await novelsApi.createChapter(pid, chapterData)
      this.chapters.push(data)
      return data
    },

    scheduleAutoSave() {
      this.dirty = true
      this.cancelAutoSave()
      if (!this.currentChapter) return
      const cid = this.currentChapter.id
      const pid = this.currentProject.id
      const content = this.currentChapter.content_markdown
      const title = this.currentChapter.title
      this._autoSaveChapterId = cid
      this._autoSaveTimer = setTimeout(async () => {
        // Only save if still on the same chapter and still dirty
        if (this._autoSaveChapterId === cid && this.currentChapter?.id === cid) {
          try {
            await this.saveChapter(pid, cid, content, title)
          } catch {
            // saveChapter already sets saveError; keep dirty so status bar reflects unsaved state
            this.dirty = true
          }
        }
      }, 2000)
    },

    cancelAutoSave() {
      if (this._autoSaveTimer) {
        clearTimeout(this._autoSaveTimer)
        this._autoSaveTimer = null
        this._autoSaveChapterId = null
      }
    },

    async saveIfDirty() {
      this.cancelAutoSave()
      if (this.dirty && this.currentChapter) {
        await this.saveChapter(
          this.currentProject.id,
          this.currentChapter.id,
          this.currentChapter.content_markdown,
          this.currentChapter.title,
        )
      }
    },

    async loadChapter(pid, cid) {
      // Cancel pending auto-save and save dirty content before switching
      this.cancelAutoSave()
      if (this.dirty && this.currentChapter && this.currentChapter.id !== cid) {
        await this.saveChapter(
          this.currentProject.id,
          this.currentChapter.id,
          this.currentChapter.content_markdown,
          this.currentChapter.title,
        )
      }
      this.currentChapterLoading = true
      try {
        const { data } = await novelsApi.getChapter(pid, cid)
        this.currentChapter = data
        this.versions = data.versions || []
        this._lastSavedSnapshot = `${data.title}||${data.content_markdown}`
        this.dirty = false
      } finally {
        this.currentChapterLoading = false
      }
    },

    async saveChapter(pid, cid, content, title) {
      this.saving = true
      this.saveError = null
      try {
        const payload = { content_markdown: content }
        if (title !== undefined) payload.title = title
        const { data } = await novelsApi.updateChapter(pid, cid, payload)
        // Only update editor state if we're still on the same chapter
        if (this.currentChapter?.id === cid) {
          this.currentChapter = data
          this._lastSavedSnapshot = `${data.title}||${data.content_markdown}`
          this.dirty = false
        }
        // Always update the chapter list entry
        const idx = this.chapters.findIndex(c => c.id === cid)
        if (idx !== -1) this.chapters[idx] = { ...this.chapters[idx], ...data }
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
      this._lastSavedSnapshot = `${data.title}||${data.content_markdown}`
      this.dirty = false
      return data
    },

    async deleteVersion(pid, cid, vid) {
      await novelsApi.deleteVersion(pid, cid, vid)
      this.versions = this.versions.filter(v => v.id !== vid)
    },

    // --- Generation ---
    async startAutoContinue(params) {
      await this.saveIfDirty()
      const requestParams = withNovelModelConfig(params)
      this.generation = { status: 'pending', progress: 0, generation_type: 'auto_continue' }
      this.rightTab = 'generation'

      const { data } = await novelsApi.autoContinue(this.currentProject.id, requestParams)
      this.generation = data
      this.listenGeneration(data.id)
      return data
    },

    async startGeneration(type, params) {
      // Save dirty content before chapter-based generation tasks
      if (type !== 'blueprint') {
        await this.saveIfDirty()
      }
      const requestParams = withNovelModelConfig(params)
      this.generation = { status: 'pending', progress: 0 }
      this.rightTab = 'generation'

      let response
      if (type === 'blueprint') {
        response = await novelsApi.generateBlueprint(this.currentProject.id, requestParams)
      } else if (type === 'chapter_version') {
        response = await novelsApi.generateVersions(this.currentProject.id, this.currentChapter.id, requestParams)
      } else if (type === 'extract') {
        response = await novelsApi.extractGraph(this.currentProject.id, this.currentChapter.id, requestParams)
      } else if (type === 'review') {
        response = await novelsApi.reviewChapter(this.currentProject.id, this.currentChapter.id, requestParams)
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

      es.addEventListener('done', async (e) => {
        this.generation = JSON.parse(e.data)
        es.close()
        this.generationEventSource = null
        if (this.generation.status === 'completed') {
          await this.handleGenerationComplete()
        }
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

      es.addEventListener('error', () => {
        if (this.generation?.status === 'pending' || this.generation?.status === 'running') {
          this.generation = {
            ...this.generation,
            status: 'failed',
            error: '生成连接中断，请重新发起。',
          }
        }
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
        if (!this.versions.length && Array.isArray(gen.result.versions)) {
          this.versions = gen.result.versions.filter(v => v.id && v.content_markdown)
        }
        if (!this.versions.length) {
          this.generation = {
            ...this.generation,
            status: 'failed',
            error: gen.result.errors?.map(e => `${e.version_type}: ${e.error}`).join('\n') || '没有生成任何可用续写版本。',
          }
          this.rightTab = 'generation'
          return
        }
        const generatedGraphChanges = gen.result.versions
          ?.flatMap(v => v.generated_graph_changes || [])
          ?.filter(Boolean) || []
        if (generatedGraphChanges.length) {
          this.graphChanges = generatedGraphChanges
        }
        await this.fetchMemoryChanges(this.currentProject.id)
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
      const evRes = await novelsApi.getEventGraph(pid)
      this.events = evRes.data.nodes || evRes.data
      this.eventRelations = evRes.data.edges || []
    },

    async saveGraphLayout(pid, entityPositions, eventPositions) {
      await novelsApi.updateGraphLayout(pid, { entity_positions: entityPositions, event_positions: eventPositions })
    },

    // --- Graph View (Obsidian) ---
    setGraphViewMode(mode) {
      this.graphView.mode = mode
    },
    setGraphViewQuery(query) {
      this.graphView.query = query
    },
    setGraphViewSelected(id) {
      this.graphView.selectedId = id
    },
    setGraphViewHovered(id) {
      this.graphView.hoveredId = id
    },
    setGraphViewFocused(id) {
      this.graphView.focusedId = id
    },
    setGraphViewNeighborIds(ids) {
      this.graphView.neighborIds = ids
    },
    setGraphViewFilters(filters) {
      this.graphView.filters = { ...this.graphView.filters, ...filters }
    },
    setGraphViewPinned(id, pos) {
      if (pos) {
        this.graphView.layout.pinned[id] = pos
      } else {
        delete this.graphView.layout.pinned[id]
      }
    },
    setGraphViewZoom(zoom) {
      this.graphView.layout.zoom = zoom
    },
    setGraphViewStats(stats) {
      this.graphView.stats = stats
    },
    setGraphViewLegend(legend) {
      this.graphView.legend = legend
    },
    resetGraphView() {
      this.graphView.selectedId = null
      this.graphView.hoveredId = null
      this.graphView.focusedId = null
      this.graphView.neighborIds = []
      this.graphView.query = ''
    },

    // --- Graph Changes ---
    async acceptGraphChange(pid, gid) {
      const change = this.graphChanges.find(c => c.id === gid)
      const { data } = await novelsApi.acceptGraphChange(pid, gid)
      this.graphChanges = this.graphChanges.filter(c => c.id !== gid)
      // Refresh the relevant graph
      if (change && (change.target_type === 'entity' || change.target_type === 'relation')) {
        await this.loadCharacterGraph(pid)
      } else if (change && (change.target_type === 'event' || change.target_type === 'event_relation')) {
        await this.loadEventGraph(pid)
      }
      return data
    },

    async rejectGraphChange(pid, gid) {
      await novelsApi.rejectGraphChange(pid, gid)
      this.graphChanges = this.graphChanges.filter(c => c.id !== gid)
    },

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
      await this.fetchMemories(pid)
    },

    async rejectMemoryChange(pid, cid) {
      await novelsApi.rejectMemoryChange(pid, cid)
      this.memoryChanges = this.memoryChanges.filter(c => c.id !== cid)
    },

    async reindexMemories(pid) {
      await novelsApi.reindexMemories(pid)
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
      this.resetGraphView()
      this.memories = []
      this.memoryChanges = []
      this.memorySearchResults = []
      this.generation = null
      this.dirty = false
      this.saveError = null
    },
  },
})
