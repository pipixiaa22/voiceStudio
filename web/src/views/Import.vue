<template>
  <div class="import-page">
    <a-card class="import-card">
      <div class="card-header">
        <h1 class="page-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="title-icon">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span>导入文本</span>
        </h1>
        <p class="page-desc">上传 .txt 文件，快速创建字幕文本</p>
      </div>

      <div class="ink-divider"></div>

      <!-- Upload Area -->
      <div
        class="upload-area"
        :class="{ 'has-file': file }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".txt"
          @change="handleFileSelect"
          style="display: none"
        />
        <div v-if="!file" class="upload-placeholder">
          <div class="upload-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="upload-icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p class="upload-text">拖拽文件到此处，或 <span class="upload-link">点击选择</span></p>
          <p class="upload-hint">支持 .txt 格式</p>
        </div>
        <div v-else class="file-info">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="file-icon">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <div class="file-details">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file.size) }}</span>
          </div>
          <a-button type="text" size="small" @click.stop="clearFile" class="clear-btn">
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </template>
          </a-button>
        </div>
      </div>

      <!-- Preview & Options -->
      <div v-if="previewContent" class="import-options">
        <div class="ink-divider"></div>

        <a-form layout="vertical" class="options-form">
          <a-row :gutter="24">
            <a-col :span="16">
              <a-form-item label="标题" class="form-item">
                <a-input v-model:value="title" placeholder="输入标题" size="large" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="文件夹" class="form-item">
                <a-select v-model:value="folderId" placeholder="选择文件夹" allowClear size="large">
                  <a-select-option v-for="folder in folders" :key="folder.id" :value="folder.id">
                    {{ folder.name }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>

          <a-form-item label="预览内容" class="form-item">
            <a-textarea
              v-model:value="previewContent"
              :autoSize="{ minRows: 8, maxRows: 15 }"
              class="preview-editor"
            />
          </a-form-item>

          <div class="form-actions">
            <a-button @click="clearFile" size="large">
              取消
            </a-button>
            <a-button
              type="primary"
              :loading="importing"
              @click="handleImport"
              size="large"
              class="import-btn"
            >
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </template>
              确认导入
            </a-button>
          </div>
        </a-form>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'

const router = useRouter()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const fileInput = ref(null)
const file = ref(null)
const previewContent = ref('')
const title = ref('')
const folderId = ref(null)
const importing = ref(false)
const isDragging = ref(false)

const folders = computed(() => foldersStore.folders)

onMounted(() => foldersStore.fetchFolders())

const triggerFileInput = () => {
  if (!file.value) {
    fileInput.value.click()
  }
}

const handleFileSelect = (e) => {
  const selected = e.target.files[0]
  if (selected) readFile(selected)
}

const handleDrop = (e) => {
  isDragging.value = false
  const dropped = e.dataTransfer.files[0]
  if (dropped && dropped.name.endsWith('.txt')) {
    readFile(dropped)
  } else {
    message.error('只支持 .txt 文件')
  }
}

const readFile = (f) => {
  file.value = f
  title.value = f.name.replace('.txt', '')
  const reader = new FileReader()
  reader.onload = (e) => {
    previewContent.value = e.target.result
  }
  reader.readAsText(f)
}

const clearFile = () => {
  file.value = null
  previewContent.value = ''
  title.value = ''
  folderId.value = null
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleImport = async () => {
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const text = await textsStore.importText(formData)
    if (folderId.value) {
      await textsStore.updateText(text.id, { folder_id: folderId.value })
    }
    message.success('导入成功')
    router.push('/')
  } catch (e) {
    message.error('导入失败')
    console.error('Failed to import:', e)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-page {
  max-width: 800px;
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

.import-card {
  min-height: calc(100vh - 130px);
}

.card-header {
  text-align: center;
  padding: var(--space-xl) 0;
}

.page-title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  letter-spacing: 2px;
}

.title-icon {
  width: 36px;
  height: 36px;
  color: var(--gold);
}

.page-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: var(--space-sm);
}

/* Upload Area */
.upload-area {
  border: 2px dashed var(--ink-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl) var(--space-xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  background: var(--ink-medium);
  margin-top: var(--space-lg);
}

.upload-area:hover {
  border-color: var(--gold);
  background: var(--surface-hover);
}

.upload-area.has-file {
  border-style: solid;
  border-color: var(--gold);
  cursor: default;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.upload-icon-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--gold-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-md);
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--gold);
}

.upload-text {
  font-size: 16px;
  color: var(--text-secondary);
}

.upload-link {
  color: var(--gold);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.upload-hint {
  font-size: 13px;
  color: var(--text-muted);
}

/* File Info */
.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
}

.file-icon {
  width: 40px;
  height: 40px;
  color: var(--gold);
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-name {
  display: block;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.file-size {
  font-size: 12px;
  color: var(--text-muted);
}

.clear-btn {
  color: var(--text-muted) !important;
}

.clear-btn:hover {
  color: var(--vermillion) !important;
}

/* Import Options */
.import-options {
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.options-form {
  margin-top: var(--space-lg);
}

.form-item :deep(.ant-form-item-label > label) {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.preview-editor {
  font-family: var(--font-body);
  font-size: 14px !important;
  line-height: 1.8 !important;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  margin-top: var(--space-xl);
}

.import-btn {
  padding: 0 32px !important;
  height: 44px;
  font-weight: 600 !important;
  letter-spacing: 1px;
}

.import-btn svg {
  width: 18px;
  height: 18px;
  margin-right: 8px;
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }

  .upload-area {
    padding: var(--space-xl) var(--space-md);
  }
}
</style>
