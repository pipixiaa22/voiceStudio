<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="导出 SRT 字幕"
    :footer="null"
    width="700px"
  >
    <div class="export-modal">
      <SrtOptionsPanel
        v-model:speed="speed"
        v-model:maxChars="maxChars"
        v-model:bilingual="bilingual"
      />

      <div class="preview-area">
        <div class="preview-bar">
          <a-spin v-if="previewing" size="small" />
          <span v-if="segmentCount > 0" class="segment-info">{{ segmentCount }} 段{{ bilingual ? ' · 中英双语' : '' }}</span>
          <span v-if="previewing" class="preview-status">正在生成预览...</span>
        </div>
        <pre v-if="srtContent" class="srt-preview">{{ srtContent }}</pre>
        <div v-else-if="!previewing" class="preview-placeholder">调整参数后自动预览</div>
      </div>

      <div class="export-actions">
        <a-button @click="$emit('update:open', false)">取消</a-button>
        <a-button
          type="primary"
          :disabled="!srtContent"
          :loading="downloading"
          @click="handleDownload"
        >
          下载 SRT
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { textsApi } from '../api'
import SrtOptionsPanel from './SrtOptionsPanel.vue'

const props = defineProps({
  open: Boolean,
  content: { type: String, default: '' },
  title: { type: String, default: '字幕' },
})

defineEmits(['update:open'])

const speed = ref(5)
const maxChars = ref(20)
const bilingual = ref(false)
const srtContent = ref('')
const segmentCount = ref(0)
const previewing = ref(false)
const downloading = ref(false)
let debounceTimer = null

const fetchPreview = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (!props.content.trim()) {
    srtContent.value = ''
    segmentCount.value = 0
    return
  }
  debounceTimer = setTimeout(async () => {
    previewing.value = true
    try {
      if (bilingual.value) {
        const { data } = await textsApi.generateBilingualSrt({
          content: props.content,
          speed: speed.value,
          max_chars: maxChars.value,
        })
        srtContent.value = data.srt
        segmentCount.value = data.segments
      } else {
        const { data } = await textsApi.generateSrt({
          content: props.content,
          speed: speed.value,
          max_chars: maxChars.value,
        })
        srtContent.value = data.srt
        segmentCount.value = data.segments
      }
    } catch {
      srtContent.value = ''
      segmentCount.value = 0
    } finally {
      previewing.value = false
    }
  }, 500)
}

watch(() => [() => props.open, props.content, speed, maxChars, bilingual], () => {
  if (props.open) fetchPreview()
})

const handleDownload = () => {
  downloading.value = true
  const blob = new Blob([srtContent.value], { type: 'text/srt;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = bilingual.value ? `${props.title}_双语.srt` : `${props.title}.srt`
  link.click()
  URL.revokeObjectURL(url)
  message.success(`已导出`)
  downloading.value = false
}
</script>

<style scoped>
.export-modal {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.preview-area {
  min-height: 200px;
}

.preview-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.segment-info {
  font-size: 12px;
  color: var(--text-muted);
}

.preview-status {
  font-size: 12px;
  color: var(--text-muted);
}

.srt-preview {
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.8;
  color: var(--text-primary);
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.preview-placeholder {
  background: var(--paper-soft);
  border: 1px dashed var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-2xl);
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.export-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}
</style>
