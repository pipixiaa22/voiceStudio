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

    async saveChapter(pid, cid, content, title) {
      this.saving = true
      this.saveError = null
      try {
        const payload = { content_markdown: content }
        if (title !== undefined) payload.title = title
        const { data } = await novelsApi.updateChapter(pid, cid, payload)
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

      es.addEventListener('done', async (e) => {
        this.generation = JSON.parse(e.data)
        es.close()
        this.generationEventSource = null
        if (this.generation.status === 'completed') {
          await this.handleGenerationComplete()
        }
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
      const evRes = await novelsApi.getEventGraph(pid)
      this.events = evRes.data.nodes || evRes.data
      this.eventRelations = evRes.data.edges || []
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
