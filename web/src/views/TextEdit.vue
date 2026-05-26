<template>
  <div class="edit-page">
    <!-- Header -->
    <div class="edit-header">
      <div class="header-left">
        <a-button @click="router.push('/')" class="back-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </template>
          返回列表
        </a-button>
        <div class="ink-divider-vertical"></div>
        <span class="page-hint">{{ textId ? '编辑文本' : '新建文本' }}</span>
      </div>
      <div class="header-actions">
        <a-button v-if="textId" @click="exportModalVisible = true" class="export-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </template>
          导出 SRT
        </a-button>
        <a-button v-if="textId" @click="videoModalVisible = true" class="export-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="23 7 16 12 23 17 23 7"/>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
          </template>
          生成视频
        </a-button>
        <a-button type="primary" :loading="saving" @click="handleSave" class="save-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
          </template>
          保存
        </a-button>
      </div>
    </div>

    <div class="ink-divider"></div>

    <!-- Body: Editor + Preview -->
    <div class="edit-body">
      <!-- Left: Editor -->
      <div class="editor-panel">
        <!-- Title -->
        <a-input
          v-model:value="title"
          placeholder="输入标题..."
          class="title-input"
          size="large"
        />

        <!-- Meta -->
        <div class="meta-section">
          <div class="meta-item">
            <label class="meta-label">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              文件夹
            </label>
            <a-select v-model:value="folderId" placeholder="选择文件夹" allowClear class="folder-select">
              <a-select-option v-for="folder in folders" :key="folder.id" :value="folder.id">
                {{ folder.name }}
              </a-select-option>
            </a-select>
          </div>
          <div class="meta-item tags-item">
            <label class="meta-label">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                <line x1="7" y1="7" x2="7.01" y2="7"/>
              </svg>
              标签
            </label>
            <TagSelector v-model="selectedTags" />
          </div>
        </div>

        <!-- Content -->
        <div class="content-section">
          <div class="editor-toolbar">
            <span class="char-count">{{ content.length }} 字</span>
          </div>
          <a-textarea
            v-model:value="content"
            placeholder="在此输入文本内容..."
            class="content-editor"
            :autoSize="{ minRows: 18, maxRows: 40 }"
          />
        </div>
      </div>

      <!-- Right: SRT Preview -->
      <div class="preview-panel">
        <SrtLivePreview :content="content" :speed="5" :max-chars="20" />
      </div>
    </div>

    <!-- Export Modal -->
    <SrtExportModal
      v-model:open="exportModalVisible"
      :content="content"
      :title="title"
    />

    <VideoGenerateModal
      v-model:open="videoModalVisible"
      :textId="textId"
      :textTitle="title"
      :textContent="content"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import TagSelector from '../components/TagSelector.vue'
import SrtLivePreview from '../components/SrtLivePreview.vue'
import SrtExportModal from '../components/SrtExportModal.vue'
import VideoGenerateModal from '../components/video/VideoGenerateModal.vue'

const router = useRouter()
const route = useRoute()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const textId = ref(route.params.id ? parseInt(route.params.id) : null)
const title = ref('未命名')
const content = ref('')
const folderId = ref(null)
const selectedTags = ref([])
const saving = ref(false)
const exportModalVisible = ref(false)
const videoModalVisible = ref(false)

const folders = computed(() => foldersStore.folders)

const loadText = async (id) => {
  if (!id) {
    title.value = '未命名'
    content.value = ''
    folderId.value = null
    selectedTags.value = []
    return
  }
  try {
    const text = await textsStore.fetchText(id)
    title.value = text.title
    content.value = text.content
    folderId.value = text.folder_id
    selectedTags.value = text.tags || []
  } catch {
    message.error('加载文本失败')
  }
}

onMounted(async () => {
  await foldersStore.fetchFolders()
  await loadText(textId.value)
})

watch(
  () => route.params.id,
  async (newId) => {
    const id = newId ? parseInt(newId) : null
    textId.value = id
    await loadText(id)
  }
)

const handleSave = async () => {
  saving.value = true
  try {
    const data = {
      title: title.value,
      content: content.value,
      folder_id: folderId.value,
      tag_ids: selectedTags.value.map(t => t.id),
    }
    if (textId.value) {
      await textsStore.updateText(textId.value, data)
      message.success('保存成功')
    } else {
      const created = await textsStore.createText(data)
      textId.value = created.id
      router.replace(`/edit/${created.id}`)
      message.success('创建成功')
    }
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.edit-page {
  max-width: 1400px;
  margin: 0 auto;
  animation: pageEnter 0.3s ease;
}

@keyframes pageEnter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Header */
.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.back-btn {
  color: var(--text-muted) !important;
  padding: 0 12px !important;
  height: 36px;
}

.back-btn:hover { color: var(--text-primary) !important; }
.back-btn svg { width: 16px; height: 16px; margin-right: 4px; }

.ink-divider-vertical {
  width: 1px;
  height: 20px;
  background: var(--surface-border);
}

.page-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
}

.export-btn { padding: 0 16px !important; height: 36px; }
.export-btn svg { width: 16px; height: 16px; margin-right: 6px; }

.save-btn {
  padding: 0 20px !important;
  height: 36px;
  font-weight: 560 !important;
  letter-spacing: 0;
}

.save-btn svg { width: 16px; height: 16px; margin-right: 6px; }

.ink-divider {
  height: 1px;
  background: var(--surface-border);
  margin: var(--space-lg) 0;
}

/* Body: split layout */
.edit-body {
  display: flex;
  gap: var(--space-lg);
  align-items: flex-start;
}

.editor-panel {
  flex: 1;
  min-width: 0;
}

.preview-panel {
  width: 340px;
  flex-shrink: 0;
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
}

/* Title */
.title-input {
  font-family: var(--font-display);
  font-size: 28px !important;
  font-weight: 650;
  padding: var(--space-md) 0 !important;
  border: none !important;
  border-bottom: 1px solid var(--surface-border) !important;
  border-radius: 0 !important;
  background: transparent !important;
  letter-spacing: 0;
}

.title-input:focus {
  border-bottom-color: var(--text-primary) !important;
  box-shadow: none !important;
}

/* Meta */
.meta-section {
  display: flex;
  gap: var(--space-2xl);
  margin-top: var(--space-xl);
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
}

.tags-item { flex: 1; min-width: 300px; }

.meta-label {
  font-size: 13px;
  font-weight: 560;
  color: var(--text-muted);
  letter-spacing: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  padding-top: 8px;
}

.meta-label svg { width: 14px; height: 14px; }

.folder-select { width: 200px !important; }

/* Content */
.content-section {
  margin-top: var(--space-xl);
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
  padding: 0 var(--space-xs);
}

.char-count {
  font-size: 12px;
  color: var(--text-muted);
}

.content-editor {
  font-family: var(--font-body);
  font-size: 15px !important;
  line-height: 2 !important;
  padding: var(--space-lg) !important;
  background: var(--paper-soft) !important;
  border: 1px solid var(--surface-border) !important;
  border-radius: var(--radius-lg) !important;
  transition: all var(--transition-normal) !important;
}

.content-editor:hover {
  border-color: var(--surface-border-strong) !important;
}

.content-editor:focus {
  border-color: var(--text-primary) !important;
  box-shadow: var(--shadow-focus) !important;
}

/* Responsive */
@media (max-width: 1024px) {
  .edit-body {
    flex-direction: column;
  }

  .preview-panel {
    width: 100%;
    position: static;
    max-height: none;
  }
}

@media (max-width: 768px) {
  .edit-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-left { width: 100%; }
  .header-actions { width: 100%; justify-content: flex-end; }

  .meta-section {
    flex-direction: column;
    gap: var(--space-lg);
  }

  .meta-item { flex-direction: column; gap: var(--space-sm); }
  .folder-select { width: 100% !important; }
  .title-input { font-size: 22px !important; }
}
</style>
