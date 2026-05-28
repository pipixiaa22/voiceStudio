<template>
  <div class="discovery-workspace">
    <DiscoverySearchBar
      :loading="loading"
      :query="query"
      :platform="platform"
      :time-range="timeRange"
      :duration-range="durationRange"
      :sort-by="sortBy"
      :config-warning="searchConfigWarning"
      @search="handleSearch"
      @resolve-url="handleResolveUrl"
      @configure-search="handleOpenDiscoverySettings"
    />

    <div class="discovery-grid">
      <DiscoverySidebar
        :history="history"
        :favorite-count="favoriteItems.length"
        :analyzed-count="analyzedCount"
        :scripted-count="scriptedCount"
        :favorite-only="favoriteOnly"
        :status-filter="statusFilter"
        @use-keyword="handleUseKeyword"
        @restore-query="handleRestoreQuery"
        @toggle-favorite-filter="discovery.setFavoriteFilter"
        @set-status-filter="discovery.setStatusFilter"
      />

      <DiscoveryResultList
        :items="results"
        :selected-id="selectedId"
        :loading="loading"
        :sort-by="sortBy"
        @select="discovery.selectItem"
        @favorite="handleToggleFavorite"
        @analyze="handleAnalyze"
        @sort="discovery.setSortBy"
        @clear-filters="handleClearFilters"
        @try-keyword="handleUseKeyword"
      />

      <DiscoveryAnalysisPanel
        :item="selectedItem"
        :active-tab="activeTab"
        :script-draft="selectedScriptDraft"
        :imported-text="selectedImportedText"
        :analyzing="analyzing"
        :generating="generating"
        :importing="importing"
        @tab-change="activeTab = $event"
        @analyze="handleAnalyze"
        @generate-script="handleGenerateScript"
        @update-script="handleUpdateScript"
        @import-text="handleImportText"
        @edit-text="handleEditText"
        @open-video="handleOpenVideo"
      />
    </div>

    <VideoGenerateModal
      v-if="videoText"
      v-model:open="videoModalOpen"
      :text-id="videoText.id"
      :text-title="videoText.title"
      :text-content="videoText.content"
      :subtitle-count="0"
      :prefill="videoPrefill"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { message } from 'ant-design-vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDiscoveryStore } from '../stores/discovery'
import { useSettings } from '../stores/settings'
import DiscoverySearchBar from '../components/discovery/DiscoverySearchBar.vue'
import DiscoverySidebar from '../components/discovery/DiscoverySidebar.vue'
import DiscoveryResultList from '../components/discovery/DiscoveryResultList.vue'
import DiscoveryAnalysisPanel from '../components/discovery/DiscoveryAnalysisPanel.vue'
import VideoGenerateModal from '../components/video/VideoGenerateModal.vue'

const router = useRouter()
const discovery = useDiscoveryStore()
const { llmKey } = useSettings()

const getDiscoveryLlmKey = () => {
  return localStorage.getItem('mimo_discovery_llm_key')?.trim() || llmKey.value || ''
}

const {
  results,
  sources,
  selectedId,
  selectedItem,
  loading,
  analyzing,
  generating,
  importing,
  query,
  platform,
  timeRange,
  durationRange,
  sortBy,
  favoriteOnly,
  statusFilter,
  history,
  activeTab,
  scriptDrafts,
  importedTexts,
  favoriteItems,
  analyzedCount,
  scriptedCount,
} = storeToRefs(discovery)

const videoModalOpen = ref(false)
const videoText = ref(null)
const videoPrefill = ref(null)

const selectedScriptDraft = computed(() => selectedId.value ? scriptDrafts.value[selectedId.value] : null)
const selectedImportedText = computed(() => selectedId.value ? importedTexts.value[selectedId.value] : null)
const missingConfigSources = computed(() => {
  const candidates = platform.value === 'all'
    ? sources.value.filter(source => source.supports_search && source.is_enabled)
    : sources.value.filter(source => source.platform_key === platform.value && source.supports_search)
  return candidates.filter(source => source.needs_api_key && !source.is_configured)
})
const searchConfigWarning = computed(() => {
  if (!missingConfigSources.value.length) return null
  const names = missingConfigSources.value.map(source => source.display_name).join('、')
  return {
    message: `${names} API Key 未配置`,
    description: '配置后即可使用平台关键词搜索，手动链接解析不受影响。',
  }
})

const handleOpenDiscoverySettings = () => {
  window.dispatchEvent(new CustomEvent('open-settings', { detail: { tab: 'discovery' } }))
}

const handleSourcesUpdated = () => {
  discovery.initialize().catch((error) => {
    message.error(error.response?.data?.error || '刷新视频搜索配置失败')
  })
}

const handleSearch = async (payload) => {
  try {
    await discovery.search(payload)
  } catch (error) {
    if (error.response?.data?.code === 'missing_config') {
      message.warning(error.response.data.message || error.response.data.error)
      return
    }
    message.error(error.response?.data?.error || error.message || '搜索失败')
  }
}

const handleResolveUrl = async (url) => {
  try {
    await discovery.resolveUrl(url)
    message.success('链接已加入候选列表')
  } catch (error) {
    message.error(error.response?.data?.error || '解析链接失败')
  }
}

const handleUseKeyword = (keyword) => {
  handleSearch({
    query: keyword,
    platform: platform.value === 'manual' ? 'youtube' : platform.value,
    timeRange: timeRange.value,
    durationRange: durationRange.value,
    sortBy: sortBy.value,
  })
}

const handleRestoreQuery = (entry) => {
  handleSearch({
    query: entry.query,
    platform: entry.platform,
    timeRange: timeRange.value,
    durationRange: durationRange.value,
    sortBy: sortBy.value,
  })
}

const handleClearFilters = () => {
  discovery.setFavoriteFilter(false)
  discovery.setStatusFilter('all')
  handleSearch({ query: '', platform: 'youtube', sortBy: 'recommended' })
}

const handleGenerateScript = async (id, options = {}) => {
  try {
    await discovery.generateScript(id, { ...options, api_key: getDiscoveryLlmKey() })
    message.success('原创脚本已生成')
  } catch (error) {
    message.error(error.response?.data?.error || '原创脚本生成失败')
  }
}

const handleUpdateScript = (id, draft) => {
  discovery.updateScriptDraft(id, draft)
}

const handleAnalyze = async (id) => {
  try {
    await discovery.analyzeItem(id, { api_key: getDiscoveryLlmKey() })
    message.success('结构分析已完成')
  } catch (error) {
    message.error(error.response?.data?.error || '分析失败')
  }
}

const handleToggleFavorite = async (id) => {
  try {
    await discovery.toggleFavorite(id)
  } catch (error) {
    message.error(error.response?.data?.error || '收藏状态更新失败')
  }
}

const handleImportText = async (id, draft) => {
  if (!draft?.content) {
    message.error('请先生成原创脚本')
    return
  }

  try {
    const item = discovery.items.find(entry => entry.id === id)
    const tagNames = ['修仙', '热点参考', '原创改写', item?.platformName || item?.platform].filter(Boolean)
    await discovery.createText(id, draft, { tagNames })
    message.success('已导入文本库')
  } catch (error) {
    message.error(error.response?.data?.error || '导入文本库失败')
  }
}

const handleEditText = (text) => {
  router.push(`/edit/${text.id}`)
}

const handleOpenVideo = (text) => {
  if (!text) {
    message.warning('请先导入文本库再生成视频')
    return
  }
  videoText.value = text
  videoPrefill.value = discovery.getVideoPrefill()
  videoModalOpen.value = true
}

onMounted(() => {
  window.addEventListener('discovery-sources-updated', handleSourcesUpdated)
  discovery.initialize().catch((error) => {
    message.error(error.response?.data?.error || '加载热点采集数据失败')
  })
})

onUnmounted(() => {
  window.removeEventListener('discovery-sources-updated', handleSourcesUpdated)
})
</script>

<style scoped>
.discovery-workspace {
  min-height: calc(100vh - 64px);
  background: var(--paper);
}

.discovery-grid {
  display: grid;
  grid-template-columns: 260px minmax(420px, 1fr) minmax(360px, 410px);
  min-height: calc(100vh - 196px);
  background: var(--surface);
  border-top: 1px solid transparent;
}

@media (max-width: 1180px) {
  .discovery-grid {
    grid-template-columns: 220px minmax(360px, 1fr);
  }

  .discovery-grid :deep(.analysis-panel) {
    grid-column: 1 / -1;
    border-top: 1px solid var(--surface-border);
    min-height: 520px;
  }
}

@media (max-width: 760px) {
  .discovery-grid {
    display: block;
  }

  .discovery-grid :deep(.discovery-sidebar) {
    border-right: 0;
    border-bottom: 1px solid var(--surface-border);
  }

  .discovery-grid :deep(.result-panel) {
    min-height: 460px;
    border-right: 0;
  }
}
</style>
