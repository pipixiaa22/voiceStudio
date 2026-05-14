import { defineStore } from 'pinia'
import { foldersApi } from '../api'

export const useFoldersStore = defineStore('folders', {
  state: () => ({
    folders: [],
    loading: false,
  }),
  actions: {
    async fetchFolders() {
      this.loading = true
      try {
        const { data } = await foldersApi.list()
        this.folders = data
      } finally {
        this.loading = false
      }
    },
    async createFolder(folderData) {
      const { data } = await foldersApi.create(folderData)
      this.folders.push(data)
      return data
    },
    async deleteFolder(id) {
      await foldersApi.delete(id)
      this.folders = this.folders.filter(f => f.id !== id)
    },
  },
})
