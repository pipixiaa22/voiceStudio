<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="选择剪映工程目录"
    @ok="handleConfirm"
    ok-text="选择此文件夹"
    cancel-text="取消"
    width="520px"
  >
    <div class="folder-browser">
      <div class="breadcrumb">
        <span
          v-for="(seg, i) in breadcrumbSegments"
          :key="i"
          class="crumb"
          :class="{ active: i === breadcrumbSegments.length - 1 }"
          @click="navigateTo(seg.path)"
        >{{ seg.name }}</span>
      </div>

      <div class="folder-list" v-if="!loading">
        <div
          v-if="parentPath"
          class="folder-row"
          @click="navigateTo(parentPath)"
        >
          <span class="folder-icon">..</span>
          <span class="folder-name">上一级</span>
        </div>
        <div
          v-for="entry in entries"
          :key="entry.path"
          class="folder-row"
          :class="{ selected: selectedPath === entry.path }"
          @click="selectedPath = entry.path"
          @dblclick="navigateTo(entry.path)"
        >
          <span class="folder-icon">📁</span>
          <span class="folder-name">{{ entry.name }}</span>
        </div>
        <div v-if="!entries.length && !parentPath" class="empty-hint">
          此目录为空
        </div>
      </div>

      <div v-if="loading" class="loading-hint">
        <a-spin size="small" /> 加载中...
      </div>

      <div v-if="error" class="error-hint">
        {{ error }}
        <a-button size="small" @click="load(currentPath)">重试</a-button>
      </div>

      <div class="current-path">
        当前目录：<code>{{ currentPath || '未选择' }}</code>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { systemApi } from '../api'

const props = defineProps({
  open: Boolean,
  startPath: { type: String, default: '' },
})

const emit = defineEmits(['update:open', 'select'])

const DEFAULT_PATH = ''

const currentPath = ref('')
const parentPath = ref(null)
const entries = ref([])
const selectedPath = ref('')
const loading = ref(false)
const error = ref('')

const breadcrumbSegments = computed(() => {
  if (!currentPath.value) return []
  const parts = currentPath.value.split('/').filter(Boolean)
  return parts.map((part, i) => ({
    name: part,
    path: '/' + parts.slice(0, i + 1).join('/'),
  }))
})

const load = async (path) => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await systemApi.ls(path || '')
    currentPath.value = data.current
    parentPath.value = data.parent
    entries.value = data.entries
    selectedPath.value = ''
  } catch (err) {
    error.value = err.response?.data?.error || '加载失败'
  } finally {
    loading.value = false
  }
}

const navigateTo = (path) => {
  load(path)
}

const handleConfirm = () => {
  const path = selectedPath.value || currentPath.value
  if (!path) return
  emit('select', path)
  emit('update:open', false)
}

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    const initial = props.startPath || localStorage.getItem('jianying_draft_dir') || DEFAULT_PATH
    load(initial)
  }
})
</script>

<style scoped>
.folder-browser {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  font-size: 12px;
  padding: var(--space-xs) 0;
}

.crumb {
  cursor: pointer;
  color: var(--text-muted);
  padding: 2px 4px;
  border-radius: 3px;
}

.crumb:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.crumb.active {
  color: var(--text-primary);
  font-weight: 500;
}

.crumb::after {
  content: ' / ';
  color: var(--text-muted);
  margin-left: 2px;
}

.crumb:last-child::after {
  content: '';
}

.folder-list {
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  max-height: 300px;
  overflow-y: auto;
  background: var(--paper-soft);
}

.folder-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid var(--surface-border);
}

.folder-row:last-child {
  border-bottom: none;
}

.folder-row:hover {
  background: var(--surface-hover);
}

.folder-row.selected {
  background: var(--primary-bg);
  color: var(--primary);
}

.folder-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-hint,
.empty-hint {
  padding: var(--space-lg);
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.error-hint {
  padding: var(--space-sm);
  text-align: center;
  color: var(--error);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
}

.current-path {
  font-size: 12px;
  color: var(--text-muted);
  padding-top: var(--space-xs);
}

.current-path code {
  background: var(--paper-soft);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  word-break: break-all;
}
</style>
