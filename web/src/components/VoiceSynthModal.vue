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
              :disabled="!canGroupSelected"
              @click="handleGroupSelected"
            >
              合成选中 ({{ selectedIndices.size }})
            </a-button>
            <a-button
              type="primary"
              :loading="batchGenerating"
              :disabled="!ttsKey"
              @click="handleBatchGenerate"
            >
              全部生成 (ZIP)
            </a-button>
            <a-button
              type="primary"
              :loading="syncPackaging"
              :disabled="!ttsKey"
              @click="handleSyncPackage"
            >
              生成同步包
            </a-button>
            <a-button size="small" @click="clearAllAudio">清除音频</a-button>
          </a-space>
        </div>

        <div class="segment-items">
          <template v-for="item in renderList" :key="item.type === 'segment' ? segments[item.index].id : `group-${item.group.id}`">
            <!-- Standalone segment -->
            <div v-if="item.type === 'segment'" class="segment-item" :class="{ selected: selectedIndices.has(item.index) }">
              <div class="segment-top">
                <label class="seg-checkbox" @click.prevent="toggleSelect(item.index)">
                  <span class="checkbox-box" :class="{ checked: selectedIndices.has(item.index) }">
                    <svg v-if="selectedIndices.has(item.index)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </span>
                </label>
                <span class="segment-index">{{ item.index + 1 }}</span>
                <span class="segment-text">{{ segments[item.index].text }}</span>
                <a-button
                  size="small"
                  :loading="segments[item.index].generating"
                  :disabled="!ttsKey || !getVoice(segments[item.index])"
                  @click="handleGenerateOne(item.index)"
                >
                  合成
                </a-button>
              </div>

              <!-- Per-segment voice override -->
              <div class="segment-voice">
                <a-input
                  v-model:value="segments[item.index].voiceDescription"
                  :placeholder="defaultVoice ? `留空使用默认: ${defaultVoice.slice(0, 20)}...` : '音色描述'"
                  size="small"
                  class="voice-input"
                />
                <a-button
                  size="small"
                  :loading="segments[item.index].polishing"
                  :disabled="!segments[item.index].voiceDescription.trim() || !llmKey"
                  @click="handlePolishSegment(item.index)"
                >
                  润色
                </a-button>
              </div>

              <!-- Polished result for segment -->
              <div v-if="segments[item.index].polished" class="polish-inline">
                <span class="polish-text">{{ segments[item.index].polished }}</span>
                <a-space :size="4">
                  <a-button size="small" type="primary" @click="segments[item.index].voiceDescription = segments[item.index].polished; segments[item.index].polished = ''">采纳</a-button>
                  <a-button size="small" @click="segments[item.index].polished = ''">取消</a-button>
                </a-space>
              </div>

              <!-- Audio player -->
              <audio v-if="segments[item.index].audioUrl" :src="segments[item.index].audioUrl" controls class="segment-audio" />
            </div>

            <!-- Group of segments -->
            <div v-else class="segment-group">
              <div class="group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <rect x="2" y="7" width="20" height="10" rx="2"/>
                  <path d="M16 3v4M8 3v4"/>
                </svg>
                <span>组合语音 ({{ item.group.indices.size }} 段)</span>
                <a-button size="small" @click="ungroup(item.group.id)">拆分</a-button>
              </div>
              <div
                v-for="idx in [...item.group.indices].sort((a, b) => a - b)"
                :key="segments[idx].id"
                class="segment-item grouped"
              >
                <div class="segment-top">
                  <span class="segment-index">{{ idx + 1 }}</span>
                  <span class="segment-text">{{ segments[idx].text }}</span>
                </div>
              </div>
              <div class="group-footer">
                <a-button
                  type="primary"
                  :loading="item.group.generating"
                  :disabled="!ttsKey || !defaultVoice.trim()"
                  @click="handleSynthGroup(item.group.id)"
                >
                  合成一句话
                </a-button>
                <audio v-if="item.group.audioUrl" :src="item.group.audioUrl" controls class="group-audio" />
              </div>
            </div>
          </template>
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
const syncPackaging = ref(false)
const segments = ref([])
const selectedIndices = ref(new Set())
const sourceTitle = ref('语音合成')
let segmentIdCounter = 0

// Groups: array of { id, indices: Set<number>, audioUrl: string|null, generating: boolean }
const groups = ref([])
let groupIdCounter = 0

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
})

const loadSegments = async (content) => {
  try {
    const { data } = await textsApi.generateSrt({ content, speed: 5, max_chars: 20 })
    segments.value = data.segments_list.map(text => makeSegment(text))
    selectedIndices.value = new Set()
    groups.value = []
  } catch {
    message.error('分段失败')
  }
}

const handleTextSelect = async (id) => {
  const text = await textsStore.fetchText(id)
  if (text) {
    sourceTitle.value = text.title || '语音合成'
    loadSegments(text.content)
  }
}

const handlePasteLoad = () => {
  if (pastedText.value.trim()) {
    sourceTitle.value = '手动粘贴'
    loadSegments(pastedText.value)
  }
}

const getVoice = (seg) => seg.voiceDescription.trim() || defaultVoice.value.trim()

// Selection
const toggleSelect = (i) => {
  const s = new Set(selectedIndices.value)
  if (s.has(i)) s.delete(i)
  else s.add(i)
  selectedIndices.value = s
}

// Check if a segment is in any group
const isInGroup = (i) => {
  return groups.value.some(g => g.indices.has(i))
}

// Check if selected segments can be grouped
const canGroupSelected = computed(() => {
  if (selectedIndices.value.size < 2) return false
  const sorted = [...selectedIndices.value].sort((a, b) => a - b)
  // Check if any selected indices are already in a group
  for (const idx of sorted) {
    if (isInGroup(idx)) return false
  }
  // Check consecutive
  for (let k = 1; k < sorted.length; k++) {
    if (sorted[k] !== sorted[k - 1] + 1) return false
  }
  return true
})

// Group selected segments
const handleGroupSelected = () => {
  const sorted = [...selectedIndices.value].sort((a, b) => a - b)
  const group = {
    id: ++groupIdCounter,
    indices: new Set(sorted),
    audioUrl: null,
    generating: false,
  }
  groups.value = [...groups.value, group]
  selectedIndices.value = new Set()
  message.success(`已组合 ${sorted.length} 段`)
}

// Ungroup a group
const ungroup = (groupId) => {
  const group = groups.value.find(g => g.id === groupId)
  if (group && group.audioUrl) URL.revokeObjectURL(group.audioUrl)
  groups.value = groups.value.filter(g => g.id !== groupId)
  message.success('已拆分')
}

// Synthesize a group as one continuous sentence
const handleSynthGroup = async (groupId) => {
  const group = groups.value.find(g => g.id === groupId)
  if (!group) return
  const sorted = [...group.indices].sort((a, b) => a - b)
  const combinedText = sorted.map(i => segments.value[i].text).join('')
  const voice = defaultVoice.value.trim()
  group.generating = true
  try {
    const { data } = await ttsApi.synthesize({
      api_key: ttsKey.value,
      voice_description: voice,
      text: combinedText,
    })
    const binary = atob(data.audio_base64)
    const bytes = new Uint8Array(binary.length)
    for (let j = 0; j < binary.length; j++) bytes[j] = binary.charCodeAt(j)
    if (group.audioUrl) URL.revokeObjectURL(group.audioUrl)
    group.audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
    message.success(`已合成 ${sorted.length} 段为一句话`)
  } catch (e) {
    message.error(e.response?.data?.error || '合成失败')
  } finally {
    group.generating = false
  }
}

// Render list: computed property to determine rendering order
const renderList = computed(() => {
  const items = []
  const visited = new Set()
  for (let i = 0; i < segments.value.length; i++) {
    if (visited.has(i)) continue
    const group = groups.value.find(g => g.indices.has(i))
    if (group) {
      items.push({ type: 'group', group })
      group.indices.forEach(idx => visited.add(idx))
    } else {
      items.push({ type: 'segment', index: i })
    }
  }
  return items
})

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

// Generate synchronized package with full audio, timed SRT, and per-segment wav files
const handleSyncPackage = async () => {
  syncPackaging.value = true
  try {
    const response = await ttsApi.syncPackage({
      api_key: ttsKey.value,
      title: sourceTitle.value,
      default_voice_description: defaultVoice.value,
      gap: 0.3,
      segments: segments.value.map(seg => ({
        text: seg.text,
        voice_description: seg.voiceDescription || '',
      })),
    })
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `${sourceTitle.value || '语音合成'}_同步包.zip`
    link.click()
    URL.revokeObjectURL(url)
    message.success('同步包生成完成')
  } catch (e) {
    message.error(e.response?.data?.error || '同步包生成失败')
  } finally {
    syncPackaging.value = false
  }
}

const clearAllAudio = () => {
  segments.value.forEach(seg => {
    if (seg.audioUrl) URL.revokeObjectURL(seg.audioUrl)
    seg.audioUrl = null
  })
  groups.value.forEach(g => {
    if (g.audioUrl) URL.revokeObjectURL(g.audioUrl)
    g.audioUrl = null
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

.segment-item.grouped {
  border-radius: 0;
  border: none;
  border-bottom: 1px solid var(--surface-border);
  background: transparent;
}

.segment-item.grouped:last-of-type {
  border-bottom: none;
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

/* Group */
.segment-group {
  background: var(--paper-soft);
  border: 2px solid var(--text-primary);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.group-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--surface-active);
  border-bottom: 1px solid var(--surface-border);
  font-size: 13px;
  font-weight: 560;
  color: var(--text-primary);
}

.group-header svg {
  flex-shrink: 0;
  color: var(--text-primary);
}

.group-header span {
  flex: 1;
}

.group-footer {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-top: 1px solid var(--surface-border);
}

.group-audio {
  flex: 1;
  height: 36px;
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
