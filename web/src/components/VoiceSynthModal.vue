<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="语音合成"
    :footer="null"
    width="900px"
    :bodyStyle="{ padding: '24px', maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }"
  >
    <div class="voice-synth">
      <!-- Missing Key Alerts -->
      <a-alert
        v-if="!hasTtsKey"
        type="warning"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #message>
          <span>需要配置 MiMo TTS API Key 才能生成语音。</span>
          <a-button type="link" size="small" @click="handleOpenSettings">去设置</a-button>
        </template>
      </a-alert>
      <a-alert
        v-if="hasTtsKey && !hasLlmKey"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #message>
          <span>未配置 MiMo LLM API Key，音色描述优化不可用。</span>
          <a-button type="link" size="small" @click="handleOpenSettings">去设置</a-button>
        </template>
      </a-alert>

      <!-- Step Indicator -->
      <a-steps :current="activeStep" size="small" class="steps">
        <a-step title="选择文本" />
        <a-step title="音色档案" />
        <a-step title="试听确认" />
        <a-step title="生成" />
      </a-steps>

      <!-- Step 1: Source Selection -->
      <div v-if="activeStep === 1" class="step-content">
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
            :autoSize="{ minRows: 4, maxRows: 8 }"
          />
          <a-button
            type="primary"
            :disabled="!pastedText.trim()"
            @click="handlePasteLoad"
            class="load-btn"
          >
            加载
          </a-button>
        </div>

        <!-- Summary after loading -->
        <div v-if="sourceContent" class="source-summary">
          <div class="summary-title">{{ sourceTitle }}</div>
          <div class="summary-stats">
            <span>{{ sourceContent.length }} 字</span>
            <span>{{ subtitleSegments.length }} 条字幕段</span>
            <span>{{ speechChunks.length }} 个语音块</span>
          </div>
          <a-button type="primary" @click="activeStep = 2">
            下一步：设定音色
          </a-button>
        </div>
      </div>

      <!-- Step 2: Voice Profile -->
      <div v-if="activeStep === 2" class="step-content">
        <div class="field">
          <label class="field-label">选择音色档案</label>
          <VoiceProfileSelector
            v-model="selectedProfile"
            @audition="handleProfileAudition"
          />
        </div>

        <div v-if="selectedProfile" class="field">
          <div class="field-header">
            <label class="field-label">音色描述</label>
            <a-space :size="8">
              <a-button
                size="small"
                :loading="polishing"
                :disabled="!voiceProfile.description.trim() || !llmKey"
                @click="handlePolish"
              >
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                  </svg>
                </template>
                优化描述
              </a-button>
            </a-space>
          </div>
          <a-textarea
            v-model:value="voiceProfile.description"
            placeholder="音色描述..."
            :autoSize="{ minRows: 3, maxRows: 5 }"
          />
          <div v-if="polishedText" class="polish-inline">
            <span class="polish-text">{{ polishedText }}</span>
            <a-space :size="4">
              <a-button size="small" type="primary" @click="voiceProfile.description = polishedText; polishedText = ''">采纳</a-button>
              <a-button size="small" @click="polishedText = ''">取消</a-button>
            </a-space>
          </div>
        </div>

        <div v-if="selectedProfile" class="field">
          <label class="field-label">负向约束（可选）</label>
          <a-textarea
            v-model:value="voiceProfile.negativePrompt"
            placeholder="例如：不要儿童音，不要播音腔，不要情绪太夸张"
            :autoSize="{ minRows: 2, maxRows: 3 }"
          />
        </div>

        <div class="step-actions">
          <a-button @click="activeStep = 1">上一步</a-button>
          <a-button
            type="primary"
            :disabled="!selectedProfile || !voiceProfile.description.trim()"
            @click="activeStep = 3"
          >
            下一步：试听确认
          </a-button>
        </div>
      </div>

      <!-- Step 3: Audition -->
      <div v-if="activeStep === 3" class="step-content">
        <div class="audition-section">
          <div class="audition-text">
            <div class="field-label">试听文案</div>
            <p class="audition-content">{{ auditionText }}</p>
          </div>

          <div class="audition-actions">
            <a-button
              :loading="audition.generating"
              :disabled="!voiceProfile.description.trim() || !ttsKey"
              @click="handleAudition"
            >
              <template #icon>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                </svg>
              </template>
              生成试听
            </a-button>

            <audio v-if="audition.audioUrl" :src="audition.audioUrl" controls class="audition-player" />
          </div>

          <div v-if="audition.audioUrl" class="audition-confirm">
            <a-button
              type="primary"
              :class="{ confirmed: audition.confirmed }"
              @click="audition.confirmed = true"
            >
              {{ audition.confirmed ? '已确认音色' : '确认使用这个音色' }}
            </a-button>
            <a-button v-if="!audition.confirmed" size="small" @click="handleAudition">
              重新生成
            </a-button>
          </div>
        </div>

        <div class="step-actions">
          <a-button @click="activeStep = 2">上一步</a-button>
          <a-button
            type="primary"
            :disabled="!audition.confirmed"
            @click="activeStep = 4"
          >
            下一步：生成
          </a-button>
        </div>
      </div>

      <!-- Step 4: Generate -->
      <div v-if="activeStep === 4" class="step-content">
        <div class="generate-summary">
          <div class="summary-item">
            <span class="summary-label">文本</span>
            <span class="summary-value">{{ sourceTitle }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">字数</span>
            <span class="summary-value">{{ sourceContent.length }} 字</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">字幕段</span>
            <span class="summary-value">{{ subtitleSegments.length }} 条</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">语音块</span>
            <span class="summary-value">{{ speechChunks.length }} 个</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">音色</span>
            <span class="summary-value">{{ voiceProfile.description.slice(0, 30) }}...</span>
          </div>
        </div>

        <div class="generate-actions">
          <a-button
            type="primary"
            size="large"
            :loading="generation.loading"
            :disabled="!canGenerate"
            @click="handleGenerate"
            class="generate-btn"
          >
            生成同步包
          </a-button>
          <p class="generate-hint">将生成完整音频 + 同步字幕 + 语音块</p>
        </div>

        <div class="workbench-action" style="text-align: center; margin-bottom: var(--space-lg);">
          <a-button block @click="handleOpenWorkbench" :disabled="!sourceContent.trim()">
            打开高级编排（配音工作台）
          </a-button>
          <p class="generate-hint">将当前文本和音色设置导入配音工作台，支持逐句编辑</p>
        </div>

        <!-- Advanced Options -->
        <a-collapse class="advanced-collapse">
          <a-collapse-panel key="advanced" header="高级选项">
            <a-space direction="vertical" style="width: 100%">
              <a-button block @click="handleBatchGenerate" :loading="batchGenerating" :disabled="!ttsKey">
                导出逐段音频 (ZIP)
              </a-button>
              <a-button block @click="clearAllAudio">
                清除临时音频
              </a-button>
            </a-space>
          </a-collapse-panel>
        </a-collapse>

        <div class="step-actions">
          <a-button @click="activeStep = 3">上一步</a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { textsApi, ttsApi, voiceProfilesApi, voiceWorkflowsApi } from '../api'
import { useTextsStore } from '../stores/texts'
import { useSettings } from '../stores/settings'
import VoiceProfileSelector from './VoiceProfileSelector.vue'

const props = defineProps({
  open: Boolean,
  initialTextId: { type: Number, default: null },
})
defineEmits(['update:open'])

const router = useRouter()
const textsStore = useTextsStore()
const { ttsKey, llmKey, hasTtsKey, hasLlmKey, systemPrompt } = useSettings()

const handleOpenSettings = () => {
  // Emit event to parent to open settings modal
  // For now, we'll use a simple approach
  window.dispatchEvent(new CustomEvent('open-settings'))
}

// Step management
const activeStep = ref(1)

// Step 1: Source
const sourceMode = ref('select')
const selectedTextId = ref(null)
const pastedText = ref('')
const sourceContent = ref('')
const sourceTitle = ref('语音合成')
const subtitleSegments = ref([])
const speechChunks = ref([])

// Step 2: Voice Profile
const selectedProfile = ref(null)
const voiceProfile = ref({
  description: '',
  negativePrompt: '',
  confirmed: false,
})
const polishedText = ref('')
const polishing = ref(false)

// Step 3: Audition
const defaultAuditionText = '（古风 叙事）云海翻涌，仙门将启。你若踏上这条修行路，便再无回头之日。'
const auditionText = computed(() => selectedProfile.value?.audition_text || defaultAuditionText)
const audition = ref({
  generating: false,
  audioUrl: null,
  confirmed: false,
})

// Step 4: Generate
const generation = ref({
  loading: false,
})
const batchGenerating = ref(false)

const allTexts = computed(() => textsStore.texts)

const canGenerate = computed(() => {
  return sourceContent.value &&
    voiceProfile.value.description.trim() &&
    ttsKey.value &&
    audition.value.confirmed &&
    !generation.value.loading
})

// Watch for profile selection changes
watch(selectedProfile, (profile) => {
  if (profile) {
    voiceProfile.value.description = profile.canonical_prompt || profile.raw_description
    voiceProfile.value.negativePrompt = profile.negative_prompt || ''
    // Reset audition when profile changes
    audition.value.confirmed = false
    if (audition.value.audioUrl) {
      URL.revokeObjectURL(audition.value.audioUrl)
      audition.value.audioUrl = null
    }
  }
})

onMounted(() => {
  if (!textsStore.texts.length) textsStore.fetchTexts()
})

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) {
      // Reset state when closing
      activeStep.value = 1
      sourceContent.value = ''
      subtitleSegments.value = []
      speechChunks.value = []
      selectedProfile.value = null
      voiceProfile.value = { description: '', negativePrompt: '', confirmed: false }
      audition.value = { generating: false, audioUrl: null, confirmed: false }
      return
    }
    if (props.initialTextId) {
      sourceMode.value = 'select'
      selectedTextId.value = props.initialTextId
      await handleTextSelect(props.initialTextId)
    }
  }
)

const filterOption = (input, option) => {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase())
}

const loadContent = async (content, title) => {
  sourceContent.value = content
  sourceTitle.value = title || '语音合成'

  // Generate subtitle segments for preview
  try {
    const { data } = await textsApi.generateSrt({ content, speed: 5, max_chars: 20 })
    subtitleSegments.value = data.segments_list || []
  } catch {
    subtitleSegments.value = []
  }

  // Estimate speech chunks (simple estimation)
  const chunkMaxChars = 200
  let chunks = []
  let currentChunk = ''
  let currentIndices = []
  for (let i = 0; i < subtitleSegments.value.length; i++) {
    const seg = subtitleSegments.value[i]
    if (currentChunk && currentChunk.length + seg.length > chunkMaxChars) {
      chunks.push({ text: currentChunk, subtitleIndices: currentIndices })
      currentChunk = ''
      currentIndices = []
    }
    currentChunk += seg
    currentIndices.push(i)
  }
  if (currentChunk) {
    chunks.push({ text: currentChunk, subtitleIndices: currentIndices })
  }
  speechChunks.value = chunks
}

const handleTextSelect = async (id) => {
  const text = await textsStore.fetchText(id)
  if (text) {
    await loadContent(text.content, text.title)
  }
}

const handlePasteLoad = () => {
  if (pastedText.value.trim()) {
    loadContent(pastedText.value, '手动粘贴')
  }
}

const handlePolish = async () => {
  polishing.value = true
  try {
    const { data } = await ttsApi.polish({
      api_key: llmKey.value,
      voice_description: voiceProfile.value.description,
      system_prompt: systemPrompt.value,
    })
    polishedText.value = data.polished
  } catch (e) {
    message.error(e.response?.data?.error || '优化失败')
  } finally {
    polishing.value = false
  }
}

const handleProfileAudition = async (profile) => {
  audition.value.generating = true
  audition.value.confirmed = false
  try {
    const { data } = await voiceProfilesApi.audition(profile.id, {
      api_key: ttsKey.value,
      text: profile.audition_text || defaultAuditionText,
    })
    const binary = atob(data.audio_base64)
    const bytes = new Uint8Array(binary.length)
    for (let j = 0; j < binary.length; j++) bytes[j] = binary.charCodeAt(j)
    if (audition.value.audioUrl) URL.revokeObjectURL(audition.value.audioUrl)
    audition.value.audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
    message.success('试听音频已生成')
  } catch (e) {
    message.error(e.response?.data?.error || '试听生成失败')
  } finally {
    audition.value.generating = false
  }
}

const handleAudition = async () => {
  audition.value.generating = true
  audition.value.confirmed = false
  try {
    const { data } = selectedProfile.value?.id
      ? await voiceProfilesApi.audition(selectedProfile.value.id, {
          api_key: ttsKey.value,
          text: auditionText.value,
        })
      : await ttsApi.synthesize({
          api_key: ttsKey.value,
          voice_description: voiceProfile.value.description,
          text: auditionText.value,
        })
    const binary = atob(data.audio_base64)
    const bytes = new Uint8Array(binary.length)
    for (let j = 0; j < binary.length; j++) bytes[j] = binary.charCodeAt(j)
    if (audition.value.audioUrl) URL.revokeObjectURL(audition.value.audioUrl)
    audition.value.audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
    message.success('试听音频已生成')
  } catch (e) {
    message.error(e.response?.data?.error || '试听生成失败')
  } finally {
    audition.value.generating = false
  }
}

const handleGenerate = async () => {
  generation.value.loading = true
  try {
    const response = await ttsApi.syncPackageV2({
      api_key: ttsKey.value,
      title: sourceTitle.value,
      content: sourceContent.value,
      voice_profile_id: selectedProfile.value?.id || null,
      voice_profile_snapshot: selectedProfile.value || null,
      voice_description: voiceProfile.value.description,
      subtitle_options: {
        max_chars: 20,
        gap: 0.3,
      },
      synthesis_options: {
        mode: 'chunked',
        chunk_max_chars: 200,
      },
    })
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `${sourceTitle.value || '语音合成'}_同步包.zip`
    link.click()
    URL.revokeObjectURL(url)
    message.success('同步包生成完成')
  } catch (e) {
    message.error(e.response?.data?.error || '生成失败')
  } finally {
    generation.value.loading = false
  }
}

const handleBatchGenerate = async () => {
  batchGenerating.value = true
  try {
    const response = await ttsApi.batchSynthesize({
      api_key: ttsKey.value,
      default_voice_description: voiceProfile.value.description,
      segments: subtitleSegments.value.map(text => ({
        text,
        voice_description: '',
      })),
    })
    const url = URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = '逐段音频.zip'
    link.click()
    URL.revokeObjectURL(url)
    message.success('逐段音频导出完成')
  } catch {
    message.error('导出失败')
  } finally {
    batchGenerating.value = false
  }
}

const handleOpenWorkbench = async () => {
  try {
    const { data } = await voiceWorkflowsApi.create({
      title: sourceTitle.value || '未命名配音工程',
      source_content: sourceContent.value,
      default_voice_profile_id: selectedProfile.value?.id || null,
    })
    emit('update:open', false)
    router.push(`/voice-workflows/${data.id}`)
    message.success('已创建配音工程')
  } catch (e) {
    message.error(e.response?.data?.error || '创建配音工程失败')
  }
}

const clearAllAudio = () => {
  if (audition.value.audioUrl) {
    URL.revokeObjectURL(audition.value.audioUrl)
    audition.value.audioUrl = null
    audition.value.confirmed = false
  }
  message.success('已清除临时音频')
}
</script>

<style scoped>
.voice-synth {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.steps {
  margin-bottom: var(--space-md);
}

.step-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Source Tabs */
.source-tabs {
  display: flex;
  gap: 2px;
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  padding: 3px;
  border: 1px solid var(--surface-border);
  margin-bottom: var(--space-md);
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

/* Source Summary */
.source-summary {
  margin-top: var(--space-lg);
  padding: var(--space-lg);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  text-align: center;
}

.summary-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-sm);
}

.summary-stats {
  display: flex;
  justify-content: center;
  gap: var(--space-lg);
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: var(--space-lg);
}

/* Field */
.field {
  margin-bottom: var(--space-lg);
}

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
  margin-bottom: 6px;
  display: block;
}

.polish-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border-strong);
  border-radius: var(--radius-sm);
  padding: 8px var(--space-sm);
  margin-top: 8px;
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

/* Audition */
.audition-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.audition-text {
  padding: var(--space-lg);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
}

.audition-content {
  margin: var(--space-sm) 0 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
}

.audition-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.audition-player {
  flex: 1;
  height: 36px;
  border-radius: var(--radius-sm);
}

.audition-confirm {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.audition-confirm .confirmed {
  background: var(--surface-active);
  border-color: var(--surface-border);
}

/* Generate */
.generate-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: var(--text-muted);
}

.summary-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.generate-actions {
  text-align: center;
  margin-bottom: var(--space-lg);
}

.generate-btn {
  min-width: 200px;
  height: 44px;
  font-size: 15px;
}

.generate-hint {
  margin-top: var(--space-sm);
  font-size: 12px;
  color: var(--text-muted);
}

.advanced-collapse {
  margin-bottom: var(--space-lg);
}

/* Step Actions */
.step-actions {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-lg);
  border-top: 1px solid var(--surface-border);
}
</style>
