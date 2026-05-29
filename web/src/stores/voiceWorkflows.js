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
        const { data } = await voiceWorkflowsApi.update(this.workflow.id, {
          workflow: this.workflow,
          segments: this.segments,
          edges: this.edges,
        })
        this.applySnapshot(data)
        return data
      } finally {
        this.saving = false
      }
    },
    updateSegment(id, patch) {
      const index = this.segments.findIndex(segment => segment.id === id)
      if (index !== -1) {
        this.segments[index] = Object.assign({}, this.segments[index], patch, {
          audio_status: patch.audio_status || 'missing',
        })
      }
    },
    selectSegment(id) {
      this.selectedSegmentId = id
    },
  },
})
