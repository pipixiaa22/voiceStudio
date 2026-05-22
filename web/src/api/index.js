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
}

export default api
