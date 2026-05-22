<template>
  <div class="text-workspace">
    <a-layout class="workspace-layout">
      <div
        class="sidebar-wrapper"
        :class="{ collapsed: sidebarCollapsed, hovered: sidebarHovered }"
        @mouseenter="sidebarHovered = true"
        @mouseleave="sidebarHovered = false"
      >
        <a-layout-sider
          :width="sidebarCollapsed ? 0 : 260"
          :collapsedWidth="0"
          :collapsed="sidebarCollapsed"
          class="sidebar"
        >
          <FolderTree
            :selectedFolderId="selectedFolderId"
            @select="handleFolderSelect"
            @moveText="fetchTexts"
          />
        </a-layout-sider>

        <!-- Sidebar Toggle Button -->
        <div class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ rotated: sidebarCollapsed }">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </div>
      </div>

      <a-layout-content class="workspace-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <section class="text-index-panel">
          <div class="index-header">
            <div>
              <h1 class="page-title">文本库</h1>
              <span class="text-count">{{ filteredTexts.length }} 篇文本</span>
            </div>
            <a-dropdown
              :trigger="['click']"
              :open="createMenuOpen"
              @openChange="createMenuOpen = $event"
            >
              <a-button type="primary" class="new-btn">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                </template>
                新建
              </a-button>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="new">
                    <router-link to="/edit" @click="createMenuOpen = false">新建文本</router-link>
                  </a-menu-item>
                  <a-menu-item key="import">
                    <router-link to="/import" @click="createMenuOpen = false">导入文本</router-link>
                  </a-menu-item>
                  <a-menu-item key="batch" @click="openBatchImport">
                    批量导入
                  </a-menu-item>
                  <a-menu-item key="quick" @click="openQuickGenerate">
                    快速生成 SRT
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>

          <div class="index-tools">
            <a-input
              v-model:value="searchQuery"
              placeholder="搜索文本... (⌘K)"
              class="search-input"
              allowClear
              @keydown.escape="searchQuery = ''"
            >
              <template #prefix>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="input-icon">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </template>
            </a-input>
            <div class="sort-row">
              <a-select v-model:value="sortBy" class="sort-select">
                <a-select-option value="created_at">创建时间</a-select-option>
                <a-select-option value="updated_at">更新时间</a-select-option>
              </a-select>
              <a-select v-model:value="sortOrder" class="sort-select order-select">
                <a-select-option value="desc">降序</a-select-option>
                <a-select-option value="asc">升序</a-select-option>
              </a-select>
            </div>
          </div>

          <a-spin :spinning="loading" tip="载入中...">
            <div v-if="filteredTexts.length" class="text-list">
              <article
                v-for="text in filteredTexts"
                :key="text.id"
                class="text-list-item"
                :class="{ active: selectedTextId === text.id }"
                draggable="true"
                @click="selectText(text.id)"
                @dragstart="handleTextDragStart(text.id, $event)"
              >
                <div class="item-main">
                  <h2 class="item-title">{{ text.title }}</h2>
                  <p class="item-excerpt">{{ excerpt(text.content) }}</p>
                </div>
                <div class="item-meta">
                  <span>{{ formatDate(text.updated_at || text.created_at) }}</span>
                  <span v-if="text.tags?.length" class="tag-count">{{ text.tags.length }} 标签</span>
                </div>
              </article>
            </div>

            <div v-else class="empty-list">
              <span>当前文件夹暂无文本</span>
              <router-link to="/edit">新建第一篇</router-link>
            </div>
          </a-spin>
        </section>

        <section class="text-detail-panel">
          <template v-if="selectedText">
            <div class="detail-toolbar">
              <div class="detail-title-block">
                <span class="folder-label">{{ selectedFolderName }}</span>
                <h2 class="detail-title">{{ selectedText.title }}</h2>
              </div>
              <div class="detail-actions">
                <a-tooltip title="API 设置">
                  <a-button class="icon-btn" @click="settingsVisible = true">
                    <template #icon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                      </svg>
                    </template>
                  </a-button>
                </a-tooltip>
                <a-button @click="openVoiceSynth">
                  <template #icon>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                    </svg>
                  </template>
                  语音合成
                </a-button>
                <a-button @click="openVideoGenerate">
                  <template #icon>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="23 7 16 12 23 17 23 7"/>
                      <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                  </template>
                  生成视频
                </a-button>
                <a-button @click="handleExport(selectedText)">
                  <template #icon>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                  </template>
                  导出字幕
                </a-button>
                <router-link :to="`/edit/${selectedText.id}`">
                  <a-button type="primary">
                    编辑
                  </a-button>
                </router-link>
              </div>
            </div>

            <div class="detail-grid">
              <div class="reader-pane">
                <div class="pane-header">
                  <span>正文</span>
                  <span>{{ selectedText.content.length }} 字</span>
                </div>
                <article class="content-preview">{{ selectedText.content }}</article>
              </div>

              <div class="subtitle-pane">
                <div class="pane-header">
                  <span>字幕预览</span>
                  <span v-if="segmentCount">{{ segmentCount }} 段</span>
                  <a-spin v-else-if="previewLoading" size="small" />
                </div>
                <pre v-if="srtContent" class="srt-preview">{{ srtContent }}</pre>
                <div v-else class="preview-placeholder">
                  {{ previewLoading ? '正在生成字幕预览...' : '暂无字幕预览' }}
                </div>
              </div>
            </div>
          </template>

          <div v-else class="empty-detail">
            <h2>选择一篇文本</h2>
            <p>左侧选择文件夹，中间选择文本后，可在这里查看正文和字幕预览。</p>
          </div>
        </section>
      </a-layout-content>
    </a-layout>

    <SrtExportModal
      v-model:open="exportModalVisible"
      :content="exportContent"
      :title="exportTitle"
    />
    <ApiSettingsModal v-model:open="settingsVisible" />
    <VoiceSynthModal
      v-model:open="voiceSynthVisible"
      :initialTextId="selectedText?.id || null"
    />
    <QuickGenerateModal v-model:open="quickGenVisible" />
    <VideoGenerateModal
      v-if="selectedText"
      v-model:open="videoModalVisible"
      :textId="selectedText.id"
      :textTitle="selectedText.title"
    />
    <BatchImportModal
      v-model:open="batchModalVisible"
      :folders="folders"
      @imported="fetchTexts"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import { textsApi } from '../api'
import FolderTree from '../components/FolderTree.vue'
import BatchImportModal from '../components/BatchImportModal.vue'
import QuickGenerateModal from '../components/QuickGenerateModal.vue'
import VoiceSynthModal from '../components/VoiceSynthModal.vue'
import VideoGenerateModal from '../components/VideoGenerateModal.vue'
import ApiSettingsModal from '../components/ApiSettingsModal.vue'
import SrtExportModal from '../components/SrtExportModal.vue'

const textsStore = useTextsStore()
const foldersStore = useFoldersStore()
const route = useRoute()
const router = useRouter()

const sidebarCollapsed = ref(false)
const sidebarHovered = ref(false)
const selectedFolderId = ref(null)
const selectedTextId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')
const createMenuOpen = ref(false)
const srtContent = ref('')
const segmentCount = ref(0)
const previewLoading = ref(false)
const batchModalVisible = ref(false)
const quickGenVisible = ref(false)
const voiceSynthVisible = ref(false)
const videoModalVisible = ref(false)
const exportModalVisible = ref(false)
const exportContent = ref('')
const exportTitle = ref('')
const settingsVisible = ref(false)
let previewTimer = null

const loading = computed(() => textsStore.loading)
const folders = computed(() => foldersStore.folders)

const selectedFolderName = computed(() => {
  if (selectedFolderId.value === null) return '全部文本'
  return folders.value.find(folder => folder.id === selectedFolderId.value)?.name || '当前文件夹'
})

const filteredTexts = computed(() => {
  if (!searchQuery.value) return textsStore.texts
  const query = searchQuery.value.toLowerCase()
  return textsStore.texts.filter(text =>
    text.title.toLowerCase().includes(query) || text.content.toLowerCase().includes(query)
  )
})

const selectedText = computed(() => {
  return filteredTexts.value.find(text => text.id === selectedTextId.value) || null
})

const ensureSelection = () => {
  if (!filteredTexts.value.length) {
    selectedTextId.value = null
    return
  }
  const queryTextId = route.query.text ? parseInt(route.query.text) : null
  if (queryTextId && filteredTexts.value.some(text => text.id === queryTextId)) {
    selectedTextId.value = queryTextId
    router.replace({ path: '/', query: {} })
    return
  }
  if (!filteredTexts.value.some(text => text.id === selectedTextId.value)) {
    selectedTextId.value = filteredTexts.value[0].id
  }
}

const fetchTexts = async () => {
  await textsStore.fetchTexts({
    folder_id: selectedFolderId.value,
    sort_by: sortBy.value,
    order: sortOrder.value,
  })
  ensureSelection()
}

const handleFolderSelect = (folderId) => {
  selectedFolderId.value = folderId
}

const selectText = (id) => {
  selectedTextId.value = id
}

const handleKeydown = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    document.querySelector('.search-input input')?.focus()
  }
}

const fetchSrtPreview = () => {
  if (previewTimer) clearTimeout(previewTimer)
  srtContent.value = ''
  segmentCount.value = 0

  if (!selectedText.value?.content) {
    previewLoading.value = false
    return
  }

  previewLoading.value = true
  previewTimer = setTimeout(async () => {
    try {
      const { data } = await textsApi.generateSrt({
        content: selectedText.value.content,
        speed: 5,
        max_chars: 20,
      })
      srtContent.value = data.srt
      segmentCount.value = data.segments
    } catch {
      srtContent.value = ''
      segmentCount.value = 0
    } finally {
      previewLoading.value = false
    }
  }, 250)
}

const handleExport = (record) => {
  exportContent.value = record.content
  exportTitle.value = record.title
  exportModalVisible.value = true
}

const openBatchImport = () => {
  createMenuOpen.value = false
  batchModalVisible.value = true
}

const openQuickGenerate = () => {
  createMenuOpen.value = false
  quickGenVisible.value = true
}

const openVoiceSynth = () => {
  createMenuOpen.value = false
  voiceSynthVisible.value = true
}

const openVideoGenerate = () => {
  createMenuOpen.value = false
  videoModalVisible.value = true
}

const handleTextDragStart = (textId, event) => {
  event.dataTransfer.setData('textId', textId)
  event.dataTransfer.effectAllowed = 'move'
}

const excerpt = (content) => {
  const compact = content.replace(/\s+/g, ' ').trim()
  return compact.length > 72 ? `${compact.slice(0, 72)}...` : compact || '暂无正文'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return minutes <= 1 ? '刚刚' : `${minutes} 分钟前`
    }
    return `${hours} 小时前`
  }
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  fetchTexts()
  foldersStore.fetchFolders()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (previewTimer) clearTimeout(previewTimer)
  document.removeEventListener('keydown', handleKeydown)
})

watch([selectedFolderId, sortBy, sortOrder], fetchTexts)
watch(searchQuery, ensureSelection)
watch(selectedText, fetchSrtPreview)
</script>

<style scoped>
.text-workspace {
  max-width: 1480px;
  margin: 0 auto;
}

.workspace-layout {
  min-height: calc(100vh - 130px);
}

.sidebar {
  background: var(--surface) !important;
  border: 1px solid var(--surface-border);
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  padding: var(--space-md);
  overflow-y: auto;
  max-height: calc(100vh - 130px);
}

.workspace-content {
  display: grid;
  grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
  background: var(--surface) !important;
  border: 1px solid var(--surface-border);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  min-height: calc(100vh - 130px);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.text-index-panel {
  border-right: 1px solid var(--surface-border);
  background: var(--paper-soft);
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.index-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-lg) var(--space-lg) var(--space-md);
}

.page-title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 650;
  color: var(--text-primary);
  margin: 0 0 4px;
  letter-spacing: 0;
}

.text-count,
.folder-label {
  font-size: 12px;
  color: var(--text-muted);
}

.new-btn,
.detail-actions :deep(.ant-btn) {
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
}

.new-btn svg,
.detail-actions svg,
.icon-btn svg {
  width: 15px;
  height: 15px;
  display: block;
}

.index-tools {
  padding: 0 var(--space-lg) var(--space-md);
  border-bottom: 1px solid var(--surface-border);
}

.search-input {
  width: 100%;
  height: 36px;
  display: inline-flex;
  align-items: center;
}

.search-input :deep(.ant-input) {
  height: auto;
  padding: 0;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.search-input :deep(.ant-input-prefix),
.search-input :deep(.ant-input-clear-icon) {
  display: inline-flex;
  align-items: center;
}

.search-input :deep(.ant-input-prefix) {
  margin-inline-end: 8px;
}

.input-icon {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
}

.sort-row {
  display: grid;
  grid-template-columns: 1fr 96px;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.sort-select {
  width: 100%;
}

.text-list {
  padding: var(--space-sm);
  max-height: calc(100vh - 310px);
  overflow-y: auto;
}

.text-list-item {
  padding: 13px 14px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.text-list-item:hover {
  background: var(--surface);
  border-color: var(--surface-border);
}

.text-list-item.active {
  background: var(--surface);
  border-color: var(--surface-border-strong);
  box-shadow: var(--shadow-sm);
}

.item-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 620;
  line-height: 1.35;
  margin: 0 0 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-excerpt {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-top: 10px;
  color: var(--text-subtle);
  font-size: 11px;
}

.tag-count {
  white-space: nowrap;
}

.empty-list,
.empty-detail,
.preview-placeholder {
  color: var(--text-muted);
  font-size: 13px;
}

.empty-list {
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  align-items: center;
}

.empty-list a {
  color: var(--text-primary);
}

.text-detail-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--surface);
}

.detail-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-lg);
  padding: var(--space-lg);
  border-bottom: 1px solid var(--surface-border);
}

.detail-title-block {
  min-width: 0;
}

.detail-title {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 650;
  line-height: 1.3;
  margin: 4px 0 0;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.icon-btn {
  width: 34px !important;
  padding: 0 !important;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 42%);
  min-height: 0;
  flex: 1;
}

.reader-pane,
.subtitle-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.reader-pane {
  border-right: 1px solid var(--surface-border);
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  height: 46px;
  padding: 0 var(--space-lg);
  border-bottom: 1px solid var(--surface-border);
  color: var(--text-muted);
  font-size: 12px;
}

.content-preview {
  padding: var(--space-lg);
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 2;
  font-size: 15px;
  overflow-y: auto;
  max-height: calc(100vh - 250px);
}

.srt-preview {
  flex: 1;
  margin: 0;
  padding: var(--space-lg);
  color: var(--text-secondary);
  background: var(--paper-soft);
  white-space: pre-wrap;
  word-break: break-all;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.8;
  overflow-y: auto;
  max-height: calc(100vh - 250px);
}

.preview-placeholder {
  padding: var(--space-lg);
}

.empty-detail {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  text-align: center;
}

.empty-detail h2 {
  color: var(--text-primary);
  font-size: 20px;
  margin: 0;
}

.empty-detail p {
  margin: 0;
}

@media (max-width: 1180px) {
  .workspace-content {
    grid-template-columns: 320px minmax(0, 1fr);
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .reader-pane {
    border-right: none;
    border-bottom: 1px solid var(--surface-border);
  }

  .content-preview,
  .srt-preview {
    max-height: 360px;
  }
}

@media (max-width: 820px) {
  .workspace-layout {
    display: block;
    width: 100%;
  }

  .sidebar {
    display: none;
  }

  .workspace-content {
    grid-template-columns: 1fr;
    border-radius: var(--radius-lg);
    width: 100% !important;
  }

  .text-index-panel {
    border-right: none;
    border-bottom: 1px solid var(--surface-border);
  }

  .text-list {
    max-height: 360px;
  }

  .detail-toolbar {
    flex-direction: column;
  }

  .detail-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .sidebar-toggle {
    display: none;
  }
}

/* Sidebar Wrapper */
.sidebar-wrapper {
  display: flex;
  position: relative;
  transition: all var(--transition-normal);
}

/* Sidebar Toggle Button */
.sidebar-toggle {
  width: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  border-left: 1px solid var(--surface-border);
  transition: all var(--transition-fast);
  flex-shrink: 0;
  opacity: 0;
}

.sidebar-wrapper:hover .sidebar-toggle,
.sidebar-wrapper.hovered .sidebar-toggle {
  opacity: 1;
  background: var(--surface);
}

.sidebar-toggle:hover {
  background: var(--surface-hover) !important;
}

.sidebar-toggle svg {
  width: 12px;
  height: 12px;
  color: var(--text-muted);
  transition: transform var(--transition-fast);
}

.sidebar-toggle svg.rotated {
  transform: rotate(180deg);
}

/* Sidebar collapsed state */
.sidebar-wrapper.collapsed {
  width: 0;
  overflow: visible;
}

.sidebar-wrapper.collapsed .sidebar {
  overflow: hidden;
  border: none;
  padding: 0;
}

.sidebar-wrapper.collapsed .sidebar-toggle {
  position: absolute;
  right: -16px;
  top: 0;
  height: 100%;
  width: 16px;
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-left: none;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  opacity: 0;
  z-index: 10;
}

.sidebar-wrapper.collapsed:hover .sidebar-toggle {
  opacity: 1;
}

/* Content expands when sidebar collapsed */
.workspace-content.sidebar-collapsed {
  border-radius: var(--radius-lg);
}
</style>
