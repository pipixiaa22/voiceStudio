<template>
  <div class="edit-page">
    <a-card class="edit-card">
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
          <a-button v-if="textId" @click="handleExport" class="export-btn">
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </template>
            导出 SRT
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

      <!-- Title Input -->
      <div class="title-section">
        <a-input
          v-model:value="title"
          placeholder="输入标题..."
          class="title-input"
          size="large"
        />
      </div>

      <!-- Meta Section -->
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

      <!-- Content Editor -->
      <div class="content-section">
        <div class="editor-toolbar">
          <span class="char-count">{{ content.length }} 字</span>
          <span class="segment-preview">预计 {{ estimatedSegments }} 段字幕</span>
        </div>
        <a-textarea
          v-model:value="content"
          placeholder="在此输入文本内容..."
          class="content-editor"
          :autoSize="{ minRows: 18, maxRows: 40 }"
        />
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import TagSelector from '../components/TagSelector.vue'

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

const folders = computed(() => foldersStore.folders)

// Estimate subtitle segments based on content length
const estimatedSegments = computed(() => {
  if (!content.value) return 0
  // Rough estimate: split by punctuation
  const segments = content.value.split(/[。？！…]+/).filter(s => s.trim())
  return Math.max(segments.length, 1)
})

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
  } catch (e) {
    message.error('加载文本失败')
    console.error('Failed to load text:', e)
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
      await textsStore.createText(data)
      message.success('创建成功')
    }
    router.push('/')
  } catch (e) {
    message.error('保存失败')
    console.error('Failed to save:', e)
  } finally {
    saving.value = false
  }
}

const handleExport = async () => {
  await textsStore.exportSrt(textId.value, { speed: 5, max_chars: 20 })
  message.success(`已导出：${title.value}.srt`)
}
</script>

<style scoped>
.edit-page {
  max-width: 1200px;
  margin: 0 auto;
  animation: pageEnter 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes pageEnter {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.edit-card {
  min-height: calc(100vh - 130px);
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

.back-btn:hover {
  color: var(--gold) !important;
}

.back-btn svg {
  width: 16px;
  height: 16px;
  margin-right: 4px;
}

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

.export-btn {
  padding: 0 16px !important;
  height: 36px;
}

.export-btn svg {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.save-btn {
  padding: 0 24px !important;
  height: 36px;
  font-weight: 600 !important;
  letter-spacing: 1px;
}

.save-btn svg {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

/* Title */
.title-section {
  margin-top: var(--space-xl);
}

.title-input {
  font-family: var(--font-display);
  font-size: 28px !important;
  font-weight: 700;
  padding: var(--space-md) 0 !important;
  border: none !important;
  border-bottom: 2px solid var(--surface-border) !important;
  border-radius: 0 !important;
  background: transparent !important;
  letter-spacing: 2px;
}

.title-input:focus {
  border-bottom-color: var(--gold) !important;
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

.tags-item {
  flex: 1;
  min-width: 300px;
}

.meta-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  padding-top: 8px;
}

.meta-label svg {
  width: 14px;
  height: 14px;
}

.folder-select {
  width: 200px !important;
}

/* Content Editor */
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

.char-count,
.segment-preview {
  font-size: 12px;
  color: var(--text-muted);
}

.segment-preview {
  color: var(--gold);
}

.content-editor {
  font-family: var(--font-body);
  font-size: 15px !important;
  line-height: 2 !important;
  padding: var(--space-lg) !important;
  background: var(--ink-medium) !important;
  border: 1px solid var(--ink-subtle) !important;
  border-radius: var(--radius-lg) !important;
  transition: all var(--transition-normal) !important;
}

.content-editor:hover {
  border-color: var(--gold) !important;
}

.content-editor:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px var(--gold-glow) !important;
}

/* Responsive */
@media (max-width: 768px) {
  .edit-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-left {
    width: 100%;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .meta-section {
    flex-direction: column;
    gap: var(--space-lg);
  }

  .meta-item {
    flex-direction: column;
    gap: var(--space-sm);
  }

  .folder-select {
    width: 100% !important;
  }

  .title-input {
    font-size: 22px !important;
  }
}
</style>
