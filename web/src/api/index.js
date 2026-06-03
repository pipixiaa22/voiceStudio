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
  batchImport: (formData) => api.post('/texts/batch-import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  generateSrt: (data) => api.post('/texts/generate-srt', data),
  generateBilingualSrt: (data) => api.post('/texts/generate-bilingual-srt', data),
  exportSrt: (id, params) => api.get(`/texts/${id}/srt`, { params, responseType: 'blob' }),
  previewSrt: (id, params) => api.get(`/texts/${id}/srt`, { params, responseType: 'text' }),
  srtToJianying: (data) => api.post('/texts/srt-to-jianying', data),
}

export const foldersApi = {
  list: () => api.get('/folders'),
  create: (data) => api.post('/folders', data),
  update: (id, data) => api.put(`/folders/${id}`, data),
  delete: (id) => api.delete(`/folders/${id}`),
}

export const tagsApi = {
  list: () => api.get('/tags'),
  create: (data) => api.post('/tags', data),
}

export const ttsApi = {
  synthesize: (data) => api.post('/tts/synthesize', data),
  batchSynthesize: (data) => api.post('/tts/batch-synthesize', data, { responseType: 'blob' }),
  syncPackage: (data) => api.post('/tts/sync-package', data, { responseType: 'blob' }),
  syncPackageV2: (data) => api.post('/tts/sync-package-v2', data, { responseType: 'blob' }),
  polish: (data) => api.post('/tts/polish', data),
}

export const voiceProfilesApi = {
  list: (params) => api.get('/voice-profiles', { params }),
  get: (id) => api.get(`/voice-profiles/${id}`),
  create: (data) => api.post('/voice-profiles', data),
  update: (id, data) => api.put(`/voice-profiles/${id}`, data),
  delete: (id) => api.delete(`/voice-profiles/${id}`),
  audition: (id, data) => api.post(`/voice-profiles/${id}/audition`, data),
}

export const videoApi = {
  generate: async (formData) => {
    try {
      const response = await api.post('/video/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
      return response
    } catch (error) {
      // 如果是 blob 响应中的 JSON 错误
      if (error.response && error.response.data instanceof Blob) {
        const reader = new FileReader()
        return new Promise((resolve, reject) => {
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result)
              error.response.data = errorData
              reject(error)
            } catch {
              reject(error)
            }
          }
          reader.onerror = () => reject(error)
          reader.readAsText(error.response.data)
        })
      }
      throw error
    }
  },

  getTemplates: () => api.get('/video/templates'),

  getTemplate: (key) => api.get(`/video/templates/${key}`),

  createJob: (data) => api.post('/video/jobs', data),

  getJob: (jobId) => api.get(`/video/jobs/${jobId}`),

  downloadJob: (jobId) => api.get(`/video/jobs/${jobId}/download`, { responseType: 'blob' }),

  uploadImage: (formData) => api.post('/video/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),

  uploadAudio: (formData) => api.post('/video/upload-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),

  listJobs: () => api.get('/video/jobs'),
}

export const discoveryApi = {
  getSources: () => api.get('/discovery/sources'),
  updateSourceConfig: (platform, data) => api.put(`/discovery/sources/${platform}/config`, data),
  search: (data) => api.post('/discovery/search', data),
  listItems: (params) => api.get('/discovery/items', { params }),
  listQueries: () => api.get('/discovery/queries'),
  resolveUrl: (data) => api.post('/discovery/resolve-url', data),
  analyzeItem: (id, data) => api.post(`/discovery/items/${id}/analyze`, data),
  createText: (id, data) => api.post(`/discovery/items/${id}/create-text`, data),
  toggleFavorite: (id) => api.put(`/discovery/items/${id}/favorite`),
  deleteItem: (id) => api.delete(`/discovery/items/${id}`),
  deleteQuery: (id) => api.delete(`/discovery/queries/${id}`),
  clearQueries: () => api.delete('/discovery/queries'),
  clearItems: () => api.delete('/discovery/items'),
}

export const modelProvidersApi = {
  getPresets: () => api.get('/model-providers/presets'),
  getAllModels: () => api.get('/models'),
  testConnection: (data) => api.post('/model-providers/test', data),
  llmComplete: (data) => api.post('/models/llm/complete', data),
  ttsSynthesize: (data) => api.post('/models/tts/synthesize', data),
}

export const customProvidersApi = {
  list: () => api.get('/model-providers/custom'),
  create: (data) => api.post('/model-providers/custom', data),
  update: (id, data) => api.put(`/model-providers/custom/${id}`, data),
  delete: (id) => api.delete(`/model-providers/custom/${id}`),
}

export const voiceWorkflowsApi = {
  list: () => api.get('/voice-workflows'),
  create: (data) => api.post('/voice-workflows', data),
  get: (id) => api.get(`/voice-workflows/${id}`),
  update: (id, data) => api.put(`/voice-workflows/${id}`, data),
  delete: (id) => api.delete(`/voice-workflows/${id}`),
  duplicate: (id, data) => api.post(`/voice-workflows/${id}/duplicate`, data),
  planSegments: (id, data) => api.post(`/voice-workflows/${id}/segments/plan`, data),
  preflight: (id) => api.get(`/voice-workflows/${id}/preflight`),
  auditionSegment: (id, segmentId, data) => api.post(`/voice-workflows/${id}/segments/${segmentId}/audition`, data),
  auditionPath: (id, data) => api.post(`/voice-workflows/${id}/audition-path`, data),
  regenerateMissing: (id, data) => api.post(`/voice-workflows/${id}/segments/regenerate-missing`, data),
  exportPackage: (id, data) => api.post(`/voice-workflows/${id}/export`, data, { responseType: 'blob' }),
  exportToJianying: (id, data) => api.post(`/voice-workflows/${id}/export-to-jianying`, data),
  clearCache: (id) => api.delete(`/voice-workflows/${id}/cache`),
}

export const systemApi = {
  ls: (path) => api.get('/system/ls', { params: { path } }),
  getConfig: () => api.get('/system/config'),
  updateConfig: (data) => api.put('/system/config', data),
  testConfig: (data) => api.post('/system/config/test', data),
  checkTables: () => api.get('/system/config/tables'),
  createTables: () => api.post('/system/config/tables/create'),
  getDdl: () => api.get('/system/config/tables/ddl'),
}

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
  generateWorkflow: (pid, cid, params) => api.post(`/novels/${pid}/chapters/${cid}/generate-workflow`, params),

  // Generation
  getGeneration: (gid) => api.get(`/novels/generations/${gid}`),

  // Memories
  listMemories: (pid, params) => api.get(`/novels/${pid}/memories`, { params }),
  createMemory: (pid, data) => api.post(`/novels/${pid}/memories`, data),
  updateMemory: (pid, mid, data) => api.patch(`/novels/${pid}/memories/${mid}`, data),
  deleteMemory: (pid, mid) => api.delete(`/novels/${pid}/memories/${mid}`),
  searchMemories: (pid, data) => api.post(`/novels/${pid}/memories/search`, data),
  reindexMemories: (pid) => api.post(`/novels/${pid}/memories/reindex`),
  listMemoryChanges: (pid) => api.get(`/novels/${pid}/memory-changes`),
  confirmMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/confirm`),
  rejectMemoryChange: (pid, cid) => api.post(`/novels/${pid}/memory-changes/${cid}/reject`),
}

export default api
