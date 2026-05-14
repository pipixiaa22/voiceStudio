import { defineStore } from 'pinia'
import { tagsApi } from '../api'

export const useTagsStore = defineStore('tags', {
  state: () => ({
    tags: [],
    loading: false,
  }),
  actions: {
    async fetchTags() {
      this.loading = true
      try {
        const { data } = await tagsApi.list()
        this.tags = data
      } finally {
        this.loading = false
      }
    },
    async createTag(tagData) {
      const { data } = await tagsApi.create(tagData)
      this.tags.push(data)
      return data
    },
  },
})
