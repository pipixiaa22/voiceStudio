<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="语音合成"
    :footer="null"
    width="800px"
  >
    <div class="voice-synth">
      <!-- Source Selection -->
      <div class="source-section">
        <div class="source-tabs">
          <button
            class="source-tab"
            :class="{ active: sourceMode === 'select' }"
            @click="sourceMode = 'select'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            选择已有文本
          </button>
          <button
            class="source-tab"
            :class="{ active: sourceMode === 'paste' }"
            @click="sourceMode = 'paste'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            手动粘贴
          </button>
        </div>

        <div v-if="sourceMode === 'select'" class="source-body">
          <a-select
            v-model:value="selectedTextId"
            placeholder="选择一篇文本"
            show-search
            :filter-option="filterOption"
            class="text-select"
            @change="handleTextSelect"
          >
            <a-select-option v-for="t in allTexts" :key="t.id" :value="t.id">
              {{ t.title }}
            </a-select-option>
          </a-select>
        </div>

        <div v-if="sourceMode === 'paste'" class="source-body">
          <a-textarea
            v-model:value="pastedText"
            placeholder="粘贴中文文字..."
            :autoSize="{ minRows: 3, maxRows: 6 }"
          />
          <a-button
            size="small"
            :disabled="!pastedText.trim()"
            @click="handlePasteLoad"
            class="load-btn"
          >
            加载并分段
          </a-button>
        </div>
      </div>

      <div v-if="segments.length" class="ink-divider"></div>

      <!-- Default Voice Description -->
      <div v-if="segments.length" class="field">
        <div class="field-header">
          <label class="field-label">默认音色描述</label>
          <a-space :size="8">
            <a-button
              size="small"
              :loading="polishingDefault"
              :disabled="!defaultVoice.trim() || !llmKey"
              @click="handlePolishDefault"
            >
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                </svg>
              </template>
              润色
            </a-button>
            <a-button size="small" type="primary" @click="applyDefaultToAll">
              应用到全部
            </a-button>
          </a-space>
        </div>
        <a-textarea
          v-model:value="defaultVoice"
          placeholder="例如：一位年轻女性，声音温柔甜美，语速缓慢，带有治愈感"
          :autoSize="{ minRows: 2, maxRows: 4 }"
        />
        <div v-if="polishedDefault" class="polish-inline">
          <span class="polish-text">{{ polishedDefault }}</span>
          <a-space :size="4">
            <a-button size="small" type="primary" @click="defaultVoice = polishedDefault; polishedDefault = ''">采纳</a-button>
            <a-button size="small" @click="polishedDefault = ''">取消</a-button>
          </a-space>
        </div>
      </div>

      <!-- Segment List -->
      <div v-if="segments.length" class="segment-list">
        <div class="segment-list-header">
          <span class="segment-count">{{ segments.length }} 段</span>
          <a-space :size="8">
            <a-button
              size="small"
              :disabled="selectedIndices.size < 2"
              @click="mergeSelected"
            >
              合并选中 ({{ selectedIndices.size }})
            </a-button>
            <a-button
              type="primary"
              :loading="batchGenerating"
              :disabled="!ttsKey"
              @click="handleBatchGenerate"
            >
              全部生成 (ZIP)
            </a-button>
            <a-button size="small" @click="clearAllAudio">清除音频</a-button>
          </a-space>
        </div>

        <div class="segment-items">
          <div
            v-for="(seg, i) in segments"
            :key="seg.id"
            class="segment-item"
            :class="{ selected: selectedIndices.has(i), merged: seg.originalTexts }"
          >
            <div class="segment-top">
              <label class="seg-checkbox" @click.prevent="toggleSelect(i)">
                <span class="checkbox-box" :class="{ checked: selectedIndices.has(i) }">
                  <svg v-if="selectedIndices.has(i)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </span>
              </label>
              <span class="segment-index">{{ i + 1 }}</span>
              <span class="segment-text">{{ seg.text }}</span>
              <a-button
                size="small"
                :loading="seg.generating"
                :disabled="!ttsKey || !getVoice(seg)"
                @click="handleGenerateOne(i)"
              >
                合成
              </a-button>
              <a-button
                v-if="seg.originalTexts"
                size="small"
                @click="unmerge(i)"
                title="拆分"
              >
                拆分
              </a-button>
            </div>

            <!-- Per-segment voice override -->
            <div class="segment-voice">
              <a-input
                v-model:value="seg.voiceDescription"
                :placeholder="defaultVoice ? `留空使用默认: ${defaultVoice.slice(0, 20)}...` : '音色描述'"
                size="small"
                class="voice-input"
              />
              <a-button
                size="small"
                :loading="seg.polishing"
                :disabled="!seg.voiceDescription.trim() || !llmKey"
                @click="handlePolishSegment(i)"
              >
                润色
              </a-button>
            </div>

            <!-- Polished result for segment -->
            <div v-if="seg.polished" class="polish-inline">
              <span class="polish-text">{{ seg.polished }}</span>
              <a-space :size="4">
                <a-button size="small" type="primary" @click="seg.voiceDescription = seg.polished; seg.polished = ''">采纳</a-button>
                <a-button size="small" @click="seg.polished = ''">取消</a-button>
              </a-space>
            </div>

            <!-- Audio player -->
            <audio v-if="seg.audioUrl" :src="seg.audioUrl" controls class="segment-audio" />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!segments.length" class="empty-hint">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40" class="empty-icon">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>
        <span>选择已有文本或手动粘贴文字开始合成</span>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { textsApi, ttsApi } from '../api'
import { useTextsStore } from '../stores/texts'
import { useSettings } from '../stores/settings'

defineProps({ open: Boolean })
defineEmits(['update:open'])

const textsStore = useTextsStore()
const { ttsKey, llmKey, systemPrompt } = useSettings()

const sourceMode = ref('select')
const selectedTextId = ref(null)
const pastedText = ref('')
const defaultVoice = ref('')
const polishedDefault = ref('')
const polishingDefault = ref(false)
const batchGenerating = ref(false)
const segments = ref([])
const selectedIndices = ref(new Set())
let segmentIdCounter = 0

const allTexts = computed(() => textsStore.texts)

onMounted(() => {
  if (!textsStore.texts.length) textsStore.fetchTexts()
})

const filterOption = (input, option) => {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase())
}

const makeSegment = (text) => ({
  id: ++segmentIdCounter,
  text,
  voiceDescription: '',
  audioUrl: null,
  generating: false,
  polishing: false,
  polished: '',
  originalTexts: null,
})

const loadSegments = async (content) => {
  try {
    const { data } = await textsApi.generateSrt({ content, speed: 5, max_chars: 20 })
    segments.value = data.segments_list.map(text => makeSegment(text))
    selectedIndices.value = new Set()
  } catch {
    message.error('分段失败')
  }
}

const handleTextSelect = async (id) => {
  const text = await textsStore.fetchText(id)
  if (text) loadSegments(text.content)
}

const handlePasteLoad = () => {
  if (pastedText.value.trim()) loadSegments(pastedText.value)
}

const getVoice = (seg) => seg.voiceDescription.trim() || defaultVoice.value.trim()

// Selection
const toggleSelect = (i) => {
  const s = new Set(selectedIndices.value)
  if (s.has(i)) s.delete(i)
  else s.add(i)
  selectedIndices.value = s
}

// Merge consecutive selected segments
const mergeSelected = () => {
  const sorted = [...selectedIndices.value].sort((a, b) => a - b)
  // Check consecutive
  for (let k = 1; k < sorted.length; k++) {
    if (sorted[k] !== sorted[k - 1] + 1) {
      message.warning('只能合并相邻的片段')
      return
    }
  }
  const first = sorted[0]
  const last = sorted[sorted.length - 1]
  const toMerge = segments.value.slice(first, last + 1)
  const mergedText = toMerge.map(s => s.text).join('')
  const mergedSeg = makeSegment(mergedText)
  mergedSeg.originalTexts = toMerge.map(s => ({
    text: s.text,
    voiceDescription: s.voiceDescription,
  }))
  // Use first segment's voice if set
  mergedSeg.voiceDescription = toMerge[0].voiceDescription || ''

  const newSegments = [...segments.value]
  newSegments.splice(first, last - first + 1, mergedSeg)
  segments.value = newSegments
  selectedIndices.value = new Set()
  message.success(`已合并 ${toMerge.length} 段`)
}

// Unmerge a merged segment
const unmerge = (i) => {
  const seg = segments.value[i]
  if (!seg.originalTexts) return
  const restored = seg.originalTexts.map(orig => {
    const s = makeSegment(orig.text)
    s.voiceDescription = orig.voiceDescription
    return s
  })
  const newSegments = [...segments.value]
  newSegments.splice(i, 1, ...restored)
  segments.value = newSegments
  selectedIndices.value = new Set()
  message.success(`已拆分为 ${restored.length} 段`)
}

// Polish default voice
const handlePolishDefault = async () => {
  polishingDefault.value = true
  try {
    const { data } = await ttsApi.polish({
      api_key: llmKey.value,
      voice_description: defaultVoice.value,
      system_prompt: systemPrompt.value,
    })
    polishedDefault.value = data.polished
  } catch (e) {
    message.error(e.response?.data?.error || '润色失败')
  } finally {
    polishingDefault.value = false
  }
}

// Polish per-segment voice
const handlePolishSegment = async (i) => {
  const seg = segments.value[i]
  seg.polishing = true
  try {
    const { data } = await ttsApi.polish({
      api_key: llmKey.value,
      voice_description: seg.voiceDescription,
      system_prompt: systemPrompt.value,
    })
    seg.polished = data.polished
  } catch (e) {
    message.error(e.response?.data?.error || '润色失败')
  } finally {
    seg.polishing = false
  }
}

const applyDefaultToAll = () => {
  segments.value.forEach(seg => { seg.voiceDescription = '' })
  message.success('已应用默认音色到全部片段')
}

// Generate single segment
const handleGenerateOne = async (i) => {
  const seg = segments.value[i]
  seg.generating = true
  try {
    const { data } = await ttsApi.synthesize({
      api_key: ttsKey.value,
      voice_description: getVoice(seg),
      text: seg.text,
    })
    const binary = atob(data.audio_base64)
    const bytes = new Uint8Array(binary.length)
    for (let j = 0; j < binary.length; j++) bytes[j] = binary.charCodeAt(j)
    if (seg.audioUrl) URL.revokeObjectURL(seg.audioUrl)
    seg.audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
    message.success(`片段 ${i + 1} 合成完成`)
  } catch (e) {
    message.error(e.response?.data?.error || `片段 ${i + 1} 合成失败`)
  } finally {
    seg.generating = false
  }
}

// Batch generate → ZIP
const handleBatchGenerate = async () => {
  batchGenerating.value = true
  try {
    const response = await ttsApi.batchSynthesize({
      api_key: ttsKey.value,
      default_voice_description: defaultVoice.value,
      segments: segments.value.map(seg => ({
        text: seg.text,
        voice_description: seg.voiceDescription || '',
      })),
    })
    const url = URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = '语音合成.zip'
    link.click()
    URL.revokeObjectURL(url)
    message.success('批量合成完成')
  } catch {
    message.error('批量合成失败')
  } finally {
    batchGenerating.value = false
  }
}

const clearAllAudio = () => {
  segments.value.forEach(seg => {
    if (seg.audioUrl) URL.revokeObjectURL(seg.audioUrl)
    seg.audioUrl = null
  })
}
</script>

<style scoped>
.voice-synth {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

/* Source Tabs */
.source-tabs {
  display: flex;
  gap: 2px;
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  padding: 3px;
  border: 1px solid var(--surface-border);
}

.source-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-body);
}

.source-tab:hover {
  color: var(--text-secondary);
  background: var(--surface-hover);
}

.source-tab.active {
  background: var(--surface);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.source-tab svg {
  flex-shrink: 0;
}

.source-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.text-select {
  width: 100%;
}

.load-btn {
  align-self: flex-end;
}

/* Field */
.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 560;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: 0;
}

.polish-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border-strong);
  border-radius: var(--radius-sm);
  padding: 6px var(--space-sm);
  margin-top: 4px;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.polish-text {
  font-size: 13px;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}

/* Segment List */
.segment-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.segment-count {
  font-size: 13px;
  font-weight: 560;
  color: var(--text-muted);
}

.segment-items {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.segment-item {
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  transition: all var(--transition-fast);
}

.segment-item.selected {
  border-color: var(--text-primary);
  box-shadow: var(--shadow-focus);
}

.segment-item.merged {
  border-left: 3px solid var(--text-primary);
}

.segment-top {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

/* Checkbox */
.seg-checkbox {
  cursor: pointer;
  display: flex;
  align-items: center;
}

.checkbox-box {
  width: 18px;
  height: 18px;
  border: 1.5px solid var(--surface-border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.checkbox-box.checked {
  background: var(--text-primary);
  border-color: var(--text-primary);
  color: var(--text-inverse);
}

.segment-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface-active);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.segment-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  min-width: 0;
}

.segment-voice {
  display: flex;
  gap: var(--space-sm);
  margin-top: 6px;
}

.voice-input {
  flex: 1;
}

.segment-audio {
  width: 100%;
  height: 36px;
  margin-top: 6px;
  border-radius: var(--radius-sm);
  outline: none;
}

/* Empty */
.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  color: var(--text-muted);
  font-size: 14px;
  padding: var(--space-2xl) 0;
}

.empty-icon {
  color: var(--text-subtle);
}
</style>
