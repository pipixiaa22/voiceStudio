<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="批量导入"
    okText="导入"
    cancelText="取消"
    :confirmLoading="importing"
    @ok="handleImport"
    @cancel="clear"
    width="520px"
  >
    <a-form layout="vertical">
      <a-form-item label="选择文件夹">
        <a-select v-model:value="folderId" placeholder="全部文本" allowClear>
          <a-select-option v-for="folder in folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="选择 .txt 文件">
        <input
          ref="fileInput"
          type="file"
          accept=".txt"
          multiple
          @change="handleFileSelect"
          style="display: none"
        />
        <a-button @click="fileInput.click()" block class="select-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </template>
          选择文件
        </a-button>
      </a-form-item>
    </a-form>
    <div v-if="files.length" class="file-list">
      <div v-for="(f, i) in files" :key="i" class="file-item">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="file-icon">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <span class="file-name">{{ f.name }}</span>
        <span class="file-size">{{ formatFileSize(f.size) }}</span>
      </div>
      <p class="file-count">共 {{ files.length }} 个文件</p>
    </div>
  </a-modal>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'

const props = defineProps({
  open: Boolean,
  folders: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:open', 'imported'])

const textsStore = useTextsStore()
const fileInput = ref(null)
const files = ref([])
const folderId = ref(null)
const importing = ref(false)

const handleFileSelect = (e) => {
  files.value = Array.from(e.target.files).filter(f => f.name.endsWith('.txt'))
}

const clear = () => {
  files.value = []
  folderId.value = null
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleImport = async () => {
  if (!files.value.length) {
    message.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    files.value.forEach(f => formData.append('files', f))
    if (folderId.value) {
      formData.append('folder_id', folderId.value)
    }
    const result = await textsStore.batchImport(formData)
    message.success(`成功导入 ${result.length} 个文件`)
    emit('update:open', false)
    emit('imported')
    clear()
  } catch {
    message.error('批量导入失败')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.file-list {
  margin-top: var(--space-md);
  max-height: 240px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 6px 0;
  border-bottom: 1px solid var(--surface-border);
}

.file-icon {
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.file-count {
  margin-top: var(--space-sm);
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;
}
</style>
