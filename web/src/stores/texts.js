import { defineStore } from 'pinia'
import { textsApi } from '../api'

export const useTextsStore = defineStore('texts', {
  state: () => ({
    texts: [],
    currentText: null,
    loading: false,
  }),
  actions: {
    async fetchTexts(params = {}) {
      this.loading = true
      try {
        const { data } = await textsApi.list(params)
        this.texts = data
      } finally {
        this.loading = false
      }
    },
    async fetchText(id) {
      const { data } = await textsApi.get(id)
      this.currentText = data
      return data
    },
    async createText(textData) {
      const { data } = await textsApi.create(textData)
      this.texts.unshift(data)
      return data
    },
    async updateText(id, textData) {
      const { data } = await textsApi.update(id, textData)
      const index = this.texts.findIndex(t => t.id === id)
      if (index !== -1) this.texts[index] = data
      this.currentText = data
      return data
    },
    async deleteText(id) {
      await textsApi.delete(id)
      this.texts = this.texts.filter(t => t.id !== id)
    },
    async importText(formData) {
      const { data } = await textsApi.import(formData)
      this.texts.unshift(data)
      return data
    },
    async batchImport(formData) {
      const { data } = await textsApi.batchImport(formData)
      this.texts.unshift(...data)
      return data
    },
    async previewSrt(id, params) {
      const response = await textsApi.previewSrt(id, params)
      return response.data
    },
    async exportSrt(id, params) {
      const response = await textsApi.exportSrt(id, params)

      // Get filename from Content-Disposition header or use text title
      let filename = 'output.srt'
      const disposition = response.headers['content-disposition']
      if (disposition) {
        // Try to extract filename from Content-Disposition header
        const filenameMatch = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i)
        if (filenameMatch) {
          filename = decodeURIComponent(filenameMatch[1])
        }
      }
      if (filename === 'output.srt' && this.currentText?.title) {
        filename = `${this.currentText.title}.srt`
      }

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
    },
  },
})
