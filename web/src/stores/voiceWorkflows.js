import { defineStore } from 'pinia'
import { voiceWorkflowsApi } from '../api'

const defaultWorkflow = () => ({
  id: null,
  title: '未命名配音工程',
  source_text_id: null,
  source_content: '',
  default_voice_profile_id: null,
  settings: { subtitle_max_chars: 20, segment_max_chars: 80 },
})

export const useVoiceWorkflowsStore = defineStore('voiceWorkflows', {
  state: () => ({
    workflows: [],
    workflow: defaultWorkflow(),
    segments: [],
    edges: [],
    selectedSegmentId: null,
    loading: false,
    saving: false,
    exporting: false,
  }),
  getters: {
    selectedSegment(state) {
      return state.segments.find(segment => segment.id === state.selectedSegmentId) || null
    },
    orderedSegments(state) {
      return Array.from(state.segments).sort((a, b) => a.order_index - b.order_index)
    },
  },
  actions: {
    applySnapshot(data) {
      this.workflow = {
        id: data.id,
        title: data.title,
        source_text_id: data.source_text_id,
        source_content: data.source_content || '',
        default_voice_profile_id: data.default_voice_profile_id,
        settings: data.settings || { subtitle_max_chars: 20, segment_max_chars: 80 },
      }
      this.segments = data.segments || []
      this.edges = data.edges || []
      this.selectedSegmentId = this.segments[0]?.id || null
    },
    async fetchList() {
      const { data } = await voiceWorkflowsApi.list()
      this.workflows = data
      return data
    },
    async create(payload) {
      const { data } = await voiceWorkflowsApi.create(payload)
      this.applySnapshot(data)
      return data
    },
    async fetch(id) {
      this.loading = true
      try {
        const { data } = await voiceWorkflowsApi.get(id)
        this.applySnapshot(data)
        return data
      } finally {
        this.loading = false
      }
    },
    async save() {
      this.saving = true
      try {
        const segmentIndexById = new Map(this.segments.map((segment, index) => [segment.id, index]))
        const payloadEdges = this.edges.map(edge => Object.assign({}, edge, {
          source_client_id: segmentIndexById.get(edge.source_segment_id),
          target_client_id: segmentIndexById.get(edge.target_segment_id),
        }))
        const { data } = await voiceWorkflowsApi.update(this.workflow.id, {
          workflow: this.workflow,
          segments: this.segments,
          edges: payloadEdges,
        })
        this.applySnapshot(data)
        return data
      } finally {
        this.saving = false
      }
    },
    updateSegment(id, patch) {
      const AUDIO_FIELDS = new Set([
        'text', 'emotion', 'intensity', 'rate', 'pitch',
        'volume_db', 'pause_before_ms', 'pause_after_ms',
        'transition', 'voice_profile_id', 'delivery_instruction',
      ])
      const index = this.segments.findIndex(segment => segment.id === id)
      if (index !== -1) {
        const affectsAudio = Object.keys(patch).some(key => AUDIO_FIELDS.has(key))
        this.segments[index] = Object.assign({}, this.segments[index], patch, {
          audio_status: affectsAudio ? 'missing' : (patch.audio_status || this.segments[index].audio_status),
        })
      }
    },
    addSegment(text = '', extra = {}) {
      const maxOrder = this.segments.reduce((max, s) => Math.max(max, s.order_index || 0), 0)
      const id = `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      const segment = {
        id,
        workflow_id: this.workflow.id,
        order_index: maxOrder + 1,
        text,
        node_x: 80 + this.segments.length * 240,
        node_y: 120 + (this.segments.length % 2) * 80,
        emotion: 'neutral',
        intensity: 0.5,
        rate: 1.0,
        pitch: 0,
        volume_db: 0,
        pause_before_ms: 0,
        pause_after_ms: 250,
        transition: 'normal',
        delivery_instruction: '',
        voice_profile_id: null,
        audio_status: 'missing',
        ...extra,
      }
      this.segments.push(segment)
      // Auto-create edge from the last segment to the new one
      if (this.segments.length > 1) {
        const prevSegment = this.segments[this.segments.length - 2]
        const edgeId = `tmp-edge-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
        this.edges.push({
          id: edgeId,
          source_segment_id: prevSegment.id,
          target_segment_id: id,
          order_index: this.edges.length + 1,
        })
      }
      this.selectedSegmentId = id
      return segment
    },
    addEdge({ source_segment_id, target_segment_id }) {
      // Prevent duplicate edges
      const exists = this.edges.some(e =>
        String(e.source_segment_id) === String(source_segment_id) &&
        String(e.target_segment_id) === String(target_segment_id)
      )
      if (exists) return
      // Prevent self-loops
      if (String(source_segment_id) === String(target_segment_id)) return
      const edgeId = `tmp-edge-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      this.edges.push({
        id: edgeId,
        source_segment_id,
        target_segment_id,
        order_index: this.edges.length + 1,
      })
    },
    removeEdge(edgeId) {
      this.edges = this.edges.filter(e => String(e.id) !== String(edgeId))
    },
    rebuildEdges() {
      // Rebuild edges from segment order
      const sorted = [...this.segments].sort((a, b) => a.order_index - b.order_index)
      this.edges = []
      for (let i = 0; i < sorted.length - 1; i++) {
        this.edges.push({
          id: `tmp-edge-${Date.now()}-${i}`,
          source_segment_id: sorted[i].id,
          target_segment_id: sorted[i + 1].id,
          order_index: i + 1,
        })
      }
    },
    selectSegment(id) {
      this.selectedSegmentId = id
    },
    async planSegments() {
      const { data } = await voiceWorkflowsApi.planSegments(this.workflow.id, {
        content: this.workflow.source_content,
        max_chars: this.workflow.settings.segment_max_chars || 80,
      })
      this.segments = data.segments.map((segment, index) => Object.assign({}, segment, {
        id: `tmp-${Date.now()}-${index}`,
      }))
      this.edges = this.segments.slice(0, -1).map((segment, index) => ({
        id: `tmp-edge-${index}`,
        source_client_id: index,
        target_client_id: index + 1,
        source_segment_id: segment.id,
        target_segment_id: this.segments[index + 1].id,
        order_index: index + 1,
      }))
      this.selectedSegmentId = this.segments[0]?.id || null
    },
    async auditionPath(apiKey, voiceDescription) {
      const { data } = await voiceWorkflowsApi.auditionPath(this.workflow.id, {
        api_key: apiKey,
        voice_description: voiceDescription,
      })
      return data
    },
    async auditionSegment(segment, apiKey, voiceDescription) {
      if (typeof segment.id === 'string') {
        await this.save()
        segment = this.selectedSegment
      }
      const { data } = await voiceWorkflowsApi.auditionSegment(this.workflow.id, segment.id, {
        api_key: apiKey,
        voice_description: voiceDescription,
      })
      this.updateSegment(segment.id, {
        audio_status: 'ready',
        audio_fingerprint: data.fingerprint,
      })
      return data
    },
    async exportPackage(apiKey, voiceDescription) {
      this.exporting = true
      try {
        await this.save()
        return await voiceWorkflowsApi.exportPackage(this.workflow.id, {
          api_key: apiKey,
          voice_description: voiceDescription,
          export_options: { include_segment_wavs: true, reuse_cache: true },
        })
      } finally {
        this.exporting = false
      }
    },
  },
})
