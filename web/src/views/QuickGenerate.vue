<template>
  <div class="quick-gen-page">
    <div class="page-header">
      <h1 class="page-title">快速生成 SRT</h1>
      <p class="page-desc">粘贴中文文字，直接生成 SRT 字幕文件</p>
    </div>

    <div class="content-wrapper">
      <!-- Input Section -->
      <div class="input-section">
        <a-textarea
          v-model:value="content"
          placeholder="在此粘贴中文文字..."
          :autoSize="{ minRows: 10, maxRows: 20 }"
          class="content-input"
        />
        <div class="options-row">
          <SrtOptionsPanel
            v-model:speed="speed"
            v-model:maxChars="maxChars"
            v-model:bilingual="bilingual"
          />
          <a-button type="primary" :loading="generating" :disabled="!content.trim()" @click="handleGenerate">
            生成预览
          </a-button>
        </div>
      </div>

      <!-- Preview Section -->
      <div v-if="srtContent" class="preview-section">
        <div class="preview-header">
          <span class="preview-info">共 {{ segmentCount }} 段字幕{{ bilingual ? '（中英双语）' : '' }}</span>
          <a-button type="primary" size="small" @click="handleDownload">
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </template>
            下载 SRT
          </a-button>
        </div>
        <pre class="srt-preview">{{ srtContent }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { textsApi } from '../api'
import SrtOptionsPanel from '../components/SrtOptionsPanel.vue'

const content = ref('')
const speed = ref(5)
const maxChars = ref(20)
const bilingual = ref(false)
const generating = ref(false)
const srtContent = ref('')
const segmentCount = ref(0)

const handleGenerate = async () => {
  generating.value = true
  try {
    if (bilingual.value) {
      const { data } = await textsApi.generateBilingualSrt({
        content: content.value,
        speed: speed.value,
        max_chars: maxChars.value,
      })
      srtContent.value = data.srt
      segmentCount.value = data.segments
    } else {
      const { data } = await textsApi.generateSrt({
        content: content.value,
        speed: speed.value,
        max_chars: maxChars.value,
      })
      srtContent.value = data.srt
      segmentCount.value = data.segments
    }
  } catch {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}

const handleDownload = () => {
  const blob = new Blob([srtContent.value], { type: 'text/srt;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = bilingual.value ? '字幕_双语.srt' : '字幕.srt'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.quick-gen-page {
  max-width: 1200px;
  margin: 0 auto;
  animation: pageEnter 0.3s ease;
}

@keyframes pageEnter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-header {
  margin-bottom: var(--space-xl);
}

.page-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 650;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.input-section {
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
}

.content-input {
  font-size: 15px !important;
  line-height: 2 !important;
}

.options-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  margin-top: var(--space-lg);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--surface-border);
}

.preview-section {
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.preview-info {
  font-size: 13px;
  color: var(--text-muted);
}

.srt-preview {
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  font-family: var(--font-mono, 'Courier New', monospace);
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-primary);
  max-height: 500px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
