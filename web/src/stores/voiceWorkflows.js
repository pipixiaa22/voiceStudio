import { defineStore } from 'pinia'
import { voiceWorkflowsApi } from '../api'
import { normalizeVoiceProfileId } from '../utils/voiceWorkflowProfiles'

const defaultWorkflow = () => ({
  id: null,
  title: '未命名配音工程',
  source_text_id: null,
  source_content: '',
  default_voice_profile_id: null,
  settings: { subtitle_max_chars: 20, segment_max_chars: 80 },
})

const linearOrder = (segments, edges) => {
  if (!edges.length) return Array.from(segments).sort((a, b) => a.order_index - b.order_index)
  const byId = new Map(segments.map(segment => [String(segment.id), segment]))
  const nextBySource = new Map()
  const incoming = new Set()
  for (const edge of edges) {
    const source = String(edge.source_segment_id)
    const target = String(edge.target_segment_id)
    if (!byId.has(source) || !byId.has(target)) return Array.from(segments).sort((a, b) => a.order_index - b.order_index)
    nextBySource.set(source, target)
    incoming.add(target)
  }
  const heads = segments.filter(segment => !incoming.has(String(segment.id)))
  if (heads.length !== 1) return Array.from(segments).sort((a, b) => a.order_index - b.order_index)
  const ordered = []
  const visited = new Set()
  let current = String(heads[0].id)
  while (current && !visited.has(current)) {
    const segment = byId.get(current)
    if (!segment) break
    ordered.push(segment)
    visited.add(current)
    current = nextBySource.get(current)
  }
  if (ordered.length !== segments.length) return Array.from(segments).sort((a, b) => a.order_index - b.order_index)
  return ordered
}

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
    exportingJianying: false,
    auditioningPath: false,
    preflighting: false,
    regeneratingMissing: false,
    preflight: null,
    dirty: false,
    lastSavedAt: null,
    saveError: '',
    operationError: '',
  }),
  getters: {
    selectedSegment(state) {
      return state.segments.find(segment => String(segment.id) === String(state.selectedSegmentId)) || null
    },
    orderedSegments(state) {
      return linearOrder(state.segments, state.edges)
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
      this.dirty = false
      this.saveError = ''
      this.operationError = ''
      this.lastSavedAt = new Date().toISOString()
      this.preflight = null
    },
    markDirty() {
      this.dirty = true
      this.saveError = ''
    },
    updateWorkflow(patch) {
      this.workflow = Object.assign({}, this.workflow, patch)
      this.markDirty()
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
    async duplicate(id, title) {
      const { data } = await voiceWorkflowsApi.duplicate(id, { title })
      await this.fetchList()
      return data
    },
    async remove(id) {
      await voiceWorkflowsApi.delete(id)
      this.workflows = this.workflows.filter(workflow => String(workflow.id) !== String(id))
      if (String(this.workflow.id) === String(id)) {
        this.workflow = defaultWorkflow()
        this.segments = []
        this.edges = []
        this.selectedSegmentId = null
        this.dirty = false
      }
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
      if (!this.workflow.id) return null
      this.saving = true
      this.saveError = ''
      try {
        // Keep keys as strings so temporary ids like "tmp-..." do not collapse to NaN.
        const segmentIndexById = new Map(this.segments.map((segment, index) => [String(segment.id), index]))
        const payloadEdges = this.edges
          .map(edge => ({
            ...edge,
            source_client_id: segmentIndexById.get(String(edge.source_segment_id)),
            target_client_id: segmentIndexById.get(String(edge.target_segment_id)),
          }))
          .filter(edge => edge.source_client_id != null && edge.target_client_id != null)
        const { data } = await voiceWorkflowsApi.update(this.workflow.id, {
          workflow: this.workflow,
          segments: this.segments,
          edges: payloadEdges,
        })
        this.applySnapshot(data)
        return data
      } catch (error) {
        this.saveError = error?.response?.data?.error || error.message || '保存失败'
        throw error
      } finally {
        this.saving = false
      }
    },
    updateDefaultVoiceProfile(profileId) {
      const nextId = normalizeVoiceProfileId(profileId)
      const previousId = this.workflow.default_voice_profile_id
      this.workflow.default_voice_profile_id = nextId
      if (String(previousId ?? '') === String(nextId ?? '')) return

      this.segments = this.segments.map(segment => {
        if (segment.voice_profile_id != null) return segment
        return { ...segment, audio_status: 'missing' }
      })
      this.markDirty()
    },
    updateSegment(id, patch) {
      const AUDIO_FIELDS = new Set([
        'text', 'emotion', 'intensity', 'rate', 'pitch',
        'volume_db', 'pause_before_ms', 'pause_after_ms',
        'transition', 'voice_profile_id', 'delivery_instruction',
      ])
      // Use String comparison to handle both int (DB) and string (tmp) IDs
      const index = this.segments.findIndex(segment => String(segment.id) === String(id))
      if (index !== -1) {
        const affectsAudio = Object.keys(patch).some(key => AUDIO_FIELDS.has(key))
        this.segments[index] = Object.assign({}, this.segments[index], patch, {
          audio_status: affectsAudio ? 'missing' : (patch.audio_status || this.segments[index].audio_status),
        })
        this.markDirty()
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
      this.markDirty()
      return segment
    },
    addEdge({ source_segment_id, target_segment_id }) {
      // Prevent duplicate edges
      const exists = this.edges.some(e =>
        String(e.source_segment_id) === String(source_segment_id) &&
        String(e.target_segment_id) === String(target_segment_id)
      )
      if (exists) return { ok: false, error: '这两个节点已经有连线' }
      // Prevent self-loops
      if (String(source_segment_id) === String(target_segment_id)) return { ok: false, error: '语句节点不能连接到自身' }
      const hasOutgoing = this.edges.some(e => String(e.source_segment_id) === String(source_segment_id))
      if (hasOutgoing) return { ok: false, error: '每个语句节点最多只能连接一个后继' }
      const hasIncoming = this.edges.some(e => String(e.target_segment_id) === String(target_segment_id))
      if (hasIncoming) return { ok: false, error: '每个语句节点最多只能连接一个前驱' }
      const edgeId = `tmp-edge-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      this.edges.push({
        id: edgeId,
        source_segment_id,
        target_segment_id,
        order_index: this.edges.length + 1,
      })
      this.markDirty()
      return { ok: true }
    },
    removeEdge(edgeId) {
      this.edges = this.edges.filter(e => String(e.id) !== String(edgeId))
      this.markDirty()
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
      this.markDirty()
    },
    selectSegment(id) {
      // Store as-is (string or number), comparisons use String()
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
      this.markDirty()
    },
    async auditionPath(apiKey, voiceDescription) {
      if (this.auditioningPath || !this.workflow.id) return null
      this.auditioningPath = true
      try {
        this.operationError = ''
        const { data } = await voiceWorkflowsApi.auditionPath(this.workflow.id, {
          api_key: apiKey,
          voice_description: voiceDescription,
        })
        return data
      } catch (error) {
        this.operationError = error?.response?.data?.error || error.message || '整条试听失败'
        throw error
      } finally {
        this.auditioningPath = false
      }
    },
    async runPreflight() {
      if (!this.workflow.id) return null
      this.preflighting = true
      try {
        if (this.dirty) await this.save()
        const { data } = await voiceWorkflowsApi.preflight(this.workflow.id)
        this.preflight = data
        return data
      } finally {
        this.preflighting = false
      }
    },
    async regenerateMissing(apiKey, voiceDescription) {
      if (!this.workflow.id) return null
      this.regeneratingMissing = true
      try {
        this.operationError = ''
        if (this.dirty) await this.save()
        const { data } = await voiceWorkflowsApi.regenerateMissing(this.workflow.id, {
          api_key: apiKey,
          voice_description: voiceDescription,
        })
        this.segments = data.segments || this.segments
        this.preflight = data.preflight || null
        return data
      } catch (error) {
        this.operationError = error?.response?.data?.error || error.message || '生成缺失音频失败'
        throw error
      } finally {
        this.regeneratingMissing = false
      }
    },
    async auditionSegment(segment, apiKey, voiceDescription) {
      if (!this.workflow.id) return null
      if (typeof segment.id === 'string') {
        await this.save()
        segment = this.selectedSegment
        if (!segment) return null
      }
      const { data } = await voiceWorkflowsApi.auditionSegment(this.workflow.id, segment.id, {
        api_key: apiKey,
        voice_description: voiceDescription,
      })
      this.updateSegment(segment.id, {
        audio_status: 'ready',
        audio_fingerprint: data.fingerprint,
      })
      this.dirty = false
      this.preflight = null
      return data
    },
    async exportPackage(apiKey, voiceDescription, options = {}) {
      this.exporting = true
      try {
        this.operationError = ''
        await this.save()
        const exportOptions = options.export_options || { include_segment_wavs: true, reuse_cache: true }
        const subtitleOptions = options.subtitle_options || {}
        return await voiceWorkflowsApi.exportPackage(this.workflow.id, {
          api_key: apiKey,
          voice_description: voiceDescription,
          export_options: exportOptions,
          subtitle_options: subtitleOptions,
        })
      } catch (error) {
        this.operationError = error?.response?.data?.error || error.message || '导出失败'
        throw error
      } finally {
        this.exporting = false
      }
    },
    async exportToJianying(apiKey, voiceDescription, draftDir) {
      this.exportingJianying = true
      try {
        this.operationError = ''
        await this.save()
        const { data } = await voiceWorkflowsApi.exportToJianying(this.workflow.id, {
          api_key: apiKey,
          voice_description: voiceDescription,
          draft_dir: draftDir,
        })
        return data
      } catch (error) {
        this.operationError = error?.response?.data?.error || error.message || '写入剪映失败'
        throw error
      } finally {
        this.exportingJianying = false
      }
    },
    async clearCache() {
      await voiceWorkflowsApi.clearCache(this.workflow.id)
      this.segments = this.segments.map(s => ({
        ...s,
        audio_status: 'missing',
        audio_fingerprint: null,
        audio_path: null,
      }))
      this.preflight = null
    },
  },
})
