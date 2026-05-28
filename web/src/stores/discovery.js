import { defineStore } from 'pinia'
import { discoveryApi, textsApi } from '../api'
import {
  buildVideoPrefill,
  filterDiscoveryItems,
  normalizeDiscoveryAnalysis,
  normalizeDiscoveryItem,
  sortDiscoveryItems,
} from '../utils/discovery'

const DEFAULT_QUERY = ''

const toSearchFilters = (state) => {
  const filters = {}
  if (state.timeRange !== 'all') filters.published_days = Number(state.timeRange)
  if (state.durationRange !== 'all') filters.duration = state.durationRange
  if (state.sortBy === 'latest') filters.order = 'date'
  if (state.sortBy === 'hot') filters.order = 'viewCount'
  if (state.sortBy === 'relevance' || state.sortBy === 'recommended') filters.order = 'relevance'
  return filters
}

const mergeItems = (existing, incoming) => {
  const byId = new Map(existing.map(item => [item.id, item]))
  for (const item of incoming) {
    byId.set(item.id, { ...(byId.get(item.id) || {}), ...item })
  }
  return Array.from(byId.values())
}

export const useDiscoveryStore = defineStore('discovery', {
  state: () => ({
    sources: [],
    items: [],
    results: [],
    selectedId: null,
    loading: false,
    analyzing: false,
    generating: false,
    importing: false,
    error: '',
    query: DEFAULT_QUERY,
    platform: 'all',
    timeRange: '30',
    durationRange: 'all',
    sortBy: 'recommended',
    favoriteOnly: false,
    statusFilter: 'all',
    history: [],
    activeTab: 'overview',
    scriptDrafts: {},
    importedTexts: {},
  }),
  getters: {
    selectedItem: (state) => state.items.find(item => item.id === state.selectedId) || null,
    favoriteItems: (state) => state.items.filter(item => item.favorite),
    analyzedCount: (state) => state.items.filter(item => item.status === 'analyzed').length,
    scriptedCount: (state) => state.items.filter(item => item.status === 'scripted').length,
    searchableSources: (state) => state.sources.filter(source => source.is_enabled && source.platform_key !== 'manual'),
  },
  actions: {
    _upsertItems(rawItems) {
      const incoming = rawItems.map(normalizeDiscoveryItem)
      this.items = mergeItems(this.items, incoming)
      for (const item of incoming) {
        if (item.scriptDraft) this.scriptDrafts[item.id] = item.scriptDraft
      }
      return incoming
    },
    _refreshResults(sourceItems = null) {
      const baseItems = sourceItems || this.items
      const filtered = filterDiscoveryItems(baseItems, {
        platform: sourceItems ? 'all' : this.platform,
        query: this.query,
        favoriteOnly: this.favoriteOnly,
        statusFilter: this.statusFilter,
      })
      this.results = sortDiscoveryItems(filtered, this.sortBy)
      if (this.results.length && !this.results.some(item => item.id === this.selectedId)) {
        this.selectedId = this.results[0].id
      }
      if (!this.results.length) this.selectedId = null
    },
    async initialize() {
      this.loading = true
      this.error = ''
      try {
        const [sourcesRes, itemsRes, queriesRes] = await Promise.all([
          discoveryApi.getSources(),
          discoveryApi.listItems({ per_page: 50 }),
          discoveryApi.listQueries(),
        ])
        this.sources = sourcesRes.data || []
        if (this.platform !== 'all' && !this.sources.some(source => source.platform_key === this.platform && source.is_enabled)) {
          this.platform = this.searchableSources[0]?.platform_key || 'youtube'
        }
        this._upsertItems(itemsRes.data?.items || [])
        this.history = (queriesRes.data || []).map(query => ({
          id: query.id,
          query: query.query_text,
          platform: query.platform_key,
          resultCount: query.item_count,
          createdAt: query.created_at,
        }))
        this._refreshResults()
      } catch (error) {
        this.error = error.response?.data?.error || '加载热点采集数据失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async search(payload = {}) {
      this.loading = true
      this.error = ''
      this.query = payload.query ?? this.query
      this.platform = payload.platform ?? this.platform
      this.timeRange = payload.timeRange ?? this.timeRange
      this.durationRange = payload.durationRange ?? this.durationRange
      this.sortBy = payload.sortBy ?? this.sortBy

      try {
        if (!this.query.trim()) {
          const { data } = await discoveryApi.listItems({ per_page: 50 })
          const normalized = this._upsertItems(data?.items || [])
          this._refreshResults(normalized.length ? normalized : null)
          return normalized
        }

        const platforms = this.platform === 'all'
          ? this.searchableSources.map(source => source.platform_key)
          : [this.platform]
        const searchable = platforms.filter(platform => platform && platform !== 'manual')
        if (!searchable.length) throw new Error('请选择支持关键词搜索的平台')

        const responses = await Promise.allSettled(searchable.map(platform => (
          discoveryApi.search({
            platform,
            query: this.query,
            limit: 20,
            filters: toSearchFilters(this),
          })
        )))
        const successes = responses.filter(result => result.status === 'fulfilled')
        const failed = responses.find(result => result.status === 'rejected')

        if (!successes.length && failed) throw failed.reason

        const rawItems = successes.flatMap(result => result.value.data?.items || [])
        const normalized = this._upsertItems(rawItems)
        this.history = [
          {
            id: `query-${Date.now()}`,
            query: this.query,
            platform: this.platform,
            resultCount: normalized.length,
            createdAt: new Date().toISOString(),
          },
          ...this.history,
        ].slice(0, 20)
        this._refreshResults(normalized)
        return normalized
      } catch (error) {
        this.error = error.response?.data?.error || error.message || '搜索失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async resolveUrl(url) {
      this.loading = true
      this.error = ''
      try {
        const { data } = await discoveryApi.resolveUrl({ url })
        const [item] = this._upsertItems([data])
        this.query = ''
        this.platform = 'all'
        this.favoriteOnly = false
        this.statusFilter = 'all'
        this._refreshResults([item])
        this.selectedId = item.id
        return item
      } catch (error) {
        this.error = error.response?.data?.error || '解析链接失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    selectItem(id) {
      this.selectedId = id
      this.activeTab = 'overview'
    },
    async analyzeItem(id = this.selectedId, options = {}) {
      const item = this.items.find(entry => entry.id === id)
      if (!item) return null
      this.analyzing = true
      this.error = ''
      try {
        const { data } = await discoveryApi.analyzeItem(id, { api_key: options.api_key || '' })
        const updated = normalizeDiscoveryAnalysis(item, data)
        this.items = this.items.map(entry => entry.id === id ? updated : entry)
        if (updated.scriptDraft) this.scriptDrafts[id] = updated.scriptDraft
        this.activeTab = updated.scriptDraft ? 'script' : 'structure'
        this._refreshResults()
        return updated
      } catch (error) {
        this.error = error.response?.data?.error || '分析失败'
        throw error
      } finally {
        this.analyzing = false
      }
    },
    async generateScript(id = this.selectedId, options = {}) {
      this.generating = true
      try {
        const updated = await this.analyzeItem(id, options)
        this.activeTab = 'script'
        return updated?.scriptDraft || null
      } finally {
        this.generating = false
      }
    },
    updateScriptDraft(id, draft) {
      this.scriptDrafts[id] = { ...draft }
    },
    async toggleFavorite(id) {
      const item = this.items.find(entry => entry.id === id)
      if (!item) return
      try {
        const { data } = await discoveryApi.toggleFavorite(id)
        item.favorite = Boolean(data.is_favorited)
      } catch (error) {
        this.error = error.response?.data?.error || '收藏状态更新失败'
        throw error
      } finally {
        this._refreshResults()
      }
    },
    setFavoriteFilter(value) {
      this.favoriteOnly = value
      this._refreshResults()
    },
    setStatusFilter(value) {
      this.statusFilter = value
      this._refreshResults()
    },
    setSortBy(value) {
      this.sortBy = value
      this._refreshResults()
    },
    markImported(id, text) {
      this.importedTexts[id] = text
      const item = this.items.find(entry => entry.id === id)
      if (item) item.status = 'imported'
      this.activeTab = 'script'
      this._refreshResults()
    },
    async createText(id, draft, options = {}) {
      this.importing = true
      this.error = ''
      try {
        const { data } = await discoveryApi.createText(id, {
          folder_id: options.folderId,
          tag_names: options.tagNames,
        })
        let text = {
          id: data.text_id,
          title: data.title,
          content: draft?.content || '',
        }
        if (draft?.title || draft?.content) {
          const updateRes = await textsApi.update(data.text_id, {
            title: draft.title || data.title,
            content: draft.content || '',
          })
          text = updateRes.data
        }
        this.markImported(id, text)
        return text
      } catch (error) {
        this.error = error.response?.data?.error || '导入文本库失败'
        throw error
      } finally {
        this.importing = false
      }
    },
    getVideoPrefill(id = this.selectedId) {
      const item = this.items.find(entry => entry.id === id)
      return item ? buildVideoPrefill(item) : null
    },
  },
})
