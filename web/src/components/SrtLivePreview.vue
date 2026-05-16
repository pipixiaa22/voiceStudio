<template>
  <div class="live-preview">
    <div class="preview-header">
      <span class="preview-title">SRT 预览</span>
      <span v-if="segmentCount > 0" class="segment-count">{{ segmentCount }} 段</span>
      <a-spin v-if="loading" size="small" />
    </div>
    <div v-if="!content.trim()" class="preview-empty">
      输入文字后自动预览字幕分段
    </div>
    <pre v-else-if="srtContent" class="preview-content">{{ srtContent }}</pre>
    <div v-else-if="loading" class="preview-loading">正在生成预览...</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { textsApi } from '../api'

const props = defineProps({
  content: { type: String, default: '' },
  speed: { type: Number, default: 5 },
  maxChars: { type: Number, default: 20 },
})

const srtContent = ref('')
const segmentCount = ref(0)
const loading = ref(false)
let debounceTimer = null

const fetchPreview = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (!props.content.trim()) {
    srtContent.value = ''
    segmentCount.value = 0
    return
  }
  debounceTimer = setTimeout(async () => {
    loading.value = true
    try {
      const { data } = await textsApi.generateSrt({
        content: props.content,
        speed: props.speed,
        max_chars: props.maxChars,
      })
      srtContent.value = data.srt
      segmentCount.value = data.segments
    } catch {
      srtContent.value = ''
      segmentCount.value = 0
    } finally {
      loading.value = false
    }
  }, 500)
}

watch(() => [props.content, props.speed, props.maxChars], fetchPreview)
</script>

<style scoped>
.live-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--surface-border);
  margin-bottom: var(--space-sm);
}

.preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.segment-count {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--surface-muted);
  padding: 1px 8px;
  border-radius: 10px;
}

.preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.preview-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.preview-content {
  flex: 1;
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.8;
  color: var(--text-primary);
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
