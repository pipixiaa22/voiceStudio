<template>
  <div class="text-list-page">
    <a-layout>
      <a-layout-sider width="260" class="sidebar">
        <FolderTree
          :selectedFolderId="selectedFolderId"
          @select="selectedFolderId = $event"
          @moveText="fetchTexts"
        />
      </a-layout-sider>
      <a-layout-content class="main-content">
        <!-- Header Section -->
        <div class="content-header">
          <div class="header-left">
            <h1 class="page-title">
              <span class="title-accent">文</span>本库
            </h1>
            <span class="text-count">{{ filteredTexts.length }} 篇文本</span>
          </div>
          <div class="header-actions">
            <a-button class="settings-btn" @click="settingsVisible = true">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </template>
            </a-button>
            <a-input
              v-model:value="searchQuery"
              placeholder="搜索文本... (⌘K)"
              class="search-input"
              allowClear
              @keydown.escape="searchQuery = ''"
            >
              <template #prefix>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px; color: var(--text-muted)">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </template>
            </a-input>
            <a-select v-model:value="sortBy" class="sort-select">
              <a-select-option value="created_at">创建时间</a-select-option>
              <a-select-option value="updated_at">更新时间</a-select-option>
            </a-select>
            <a-select v-model:value="sortOrder" class="sort-select">
              <a-select-option value="desc">降序</a-select-option>
              <a-select-option value="asc">升序</a-select-option>
            </a-select>
            <a-button class="create-btn" @click="voiceSynthVisible = true">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                </svg>
              </template>
              语音合成
            </a-button>
            <a-button class="create-btn" @click="quickGenVisible = true">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
              </template>
              快速生成
            </a-button>
            <a-button class="create-btn" @click="batchModalVisible = true">
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </template>
              批量导入
            </a-button>
            <router-link to="/edit">
              <a-button type="primary" class="create-btn">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                </template>
                新建文本
              </a-button>
            </router-link>
          </div>
        </div>

        <div class="ink-divider"></div>

        <!-- Table Section -->
        <TextTable
          :texts="filteredTexts"
          :loading="loading"
          @preview="handlePreview"
          @export="handleExport"
          @delete="handleDelete"
        />
      </a-layout-content>
    </a-layout>

    <!-- Modals -->
    <SrtExportModal
      v-model:open="exportModalVisible"
      :content="exportContent"
      :title="exportTitle"
    />
    <ApiSettingsModal v-model:open="settingsVisible" />
    <VoiceSynthModal v-model:open="voiceSynthVisible" />
    <QuickGenerateModal v-model:open="quickGenVisible" />
    <SrtPreviewModal
      v-model:open="previewVisible"
      :title="previewTitle"
      :content="previewContent"
      :loading="previewLoading"
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
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import { useSettings } from '../stores/settings'
import { textsApi } from '../api'
import FolderTree from '../components/FolderTree.vue'
import TextTable from '../components/TextTable.vue'
import SrtPreviewModal from '../components/SrtPreviewModal.vue'
import BatchImportModal from '../components/BatchImportModal.vue'
import QuickGenerateModal from '../components/QuickGenerateModal.vue'
import VoiceSynthModal from '../components/VoiceSynthModal.vue'
import ApiSettingsModal from '../components/ApiSettingsModal.vue'
import SrtExportModal from '../components/SrtExportModal.vue'

const textsStore = useTextsStore()
const foldersStore = useFoldersStore()
const { llmKey } = useSettings()

const selectedFolderId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

const loading = computed(() => textsStore.loading)
const folders = computed(() => foldersStore.folders)

// Keyboard shortcut for search (⌘K)
const handleKeydown = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    document.querySelector('.search-input input')?.focus()
  }
}

// SRT Preview state
const previewVisible = ref(false)
const previewContent = ref('')
const previewTitle = ref('')
const previewLoading = ref(false)

// Batch Import state
const batchModalVisible = ref(false)

// Quick Generate state
const quickGenVisible = ref(false)

// Voice Synth state
const voiceSynthVisible = ref(false)

// Export Modal state
const exportModalVisible = ref(false)
const exportContent = ref('')
const exportTitle = ref('')

// Settings state
const settingsVisible = ref(false)

const fetchTexts = () => {
  textsStore.fetchTexts({
    folder_id: selectedFolderId.value,
    sort_by: sortBy.value,
    order: sortOrder.value,
  })
}

onMounted(() => {
  fetchTexts()
  foldersStore.fetchFolders()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
watch([selectedFolderId, sortBy, sortOrder], fetchTexts)

const filteredTexts = computed(() => {
  if (!searchQuery.value) return textsStore.texts
  const query = searchQuery.value.toLowerCase()
  return textsStore.texts.filter(t =>
    t.title.toLowerCase().includes(query) || t.content.toLowerCase().includes(query)
  )
})

const handlePreview = async (record) => {
  previewTitle.value = record.title
  previewContent.value = ''
  previewLoading.value = true
  previewVisible.value = true
  try {
    previewContent.value = await textsStore.previewSrt(record.id, { speed: 5, max_chars: 20 })
  } catch {
    message.error('预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

const handleExport = (record) => {
  exportContent.value = record.content
  exportTitle.value = record.title
  exportModalVisible.value = true
}

const handleDelete = async (id) => {
  await textsStore.deleteText(id)
  message.success('已删除')
}
</script>

<style scoped>
.text-list-page {
  max-width: 1400px;
  margin: 0 auto;
}

.sidebar {
  background: var(--surface) !important;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  border: 1px solid var(--surface-border);
  border-right: none;
  padding: var(--space-md);
  overflow-y: auto;
  max-height: calc(100vh - 130px);
}

.main-content {
  background: var(--surface) !important;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  border: 1px solid var(--surface-border);
  padding: var(--space-lg);
  min-height: calc(100vh - 130px);
  box-shadow: var(--shadow-sm);
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
}

.page-title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 650;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 0;
}

.title-accent {
  color: var(--text-primary);
  text-shadow: none;
}

.text-count {
  font-size: 13px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.search-input {
  width: 220px;
}

.sort-select {
  width: 110px;
}

.create-btn {
  padding: 0 16px !important;
  height: 36px;
  font-weight: 520 !important;
  letter-spacing: 0;
}

.create-btn svg {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.settings-btn {
  width: 36px !important;
  height: 36px;
  padding: 0 !important;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.settings-btn svg {
  width: 16px;
  height: 16px;
}

/* Responsive */
@media (max-width: 1200px) {
  .content-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-input {
    flex: 1;
    min-width: 200px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .main-content {
    border-radius: var(--radius-lg);
  }
}
</style>
