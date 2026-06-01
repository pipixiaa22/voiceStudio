<template>
  <div class="template-step">
    <h4>选择视频模板</h4>
    <div class="template-grid">
      <div
        v-for="template in templates"
        :key="template.template_key"
        class="template-card"
        :class="{ selected: selected?.template_key === template.template_key }"
        @click="selectTemplate(template)"
      >
        <div class="template-icon">{{ getTemplateIcon(template.template_key) }}</div>
        <div class="template-name">{{ template.name }}</div>
        <div class="template-desc">{{ getTemplateDesc(template.template_key) }}</div>
      </div>
    </div>

    <div class="ratio-section">
      <h4>选择画面比例</h4>
      <a-radio-group
        :value="selectedRatio"
        class="ratio-grid"
        @change="handleRatioChange"
      >
        <a-radio-button
          v-for="option in ASPECT_RATIO_OPTIONS"
          :key="option.value"
          :value="option.value"
          class="ratio-option"
        >
          <span class="ratio-preview" :class="`ratio-${option.className}`"></span>
          <span class="ratio-copy">
            <span class="ratio-name">{{ option.label }}</span>
            <span class="ratio-desc">{{ option.description }}</span>
          </span>
        </a-radio-button>
      </a-radio-group>
    </div>

    <div v-if="selected" class="template-info">
      <a-descriptions size="small" :column="2" bordered>
        <a-descriptions-item label="画面比例">{{ selectedRatioLabel }}</a-descriptions-item>
        <a-descriptions-item label="分辨率">{{ selectedResolutionText }}</a-descriptions-item>
        <a-descriptions-item label="画面节奏">{{ selected.config?.visual_effects?.motion }}</a-descriptions-item>
        <a-descriptions-item label="帧率">{{ selected.config?.fps }}fps</a-descriptions-item>
        <a-descriptions-item label="BGM 音量">{{ Math.round((selected.config?.audio?.bgm_volume || 0) * 100) }}%</a-descriptions-item>
        <a-descriptions-item label="环境音">{{ Math.round((selected.config?.audio?.ambient_volume || 0) * 100) }}%</a-descriptions-item>
      </a-descriptions>
    </div>

    <div class="step-actions">
      <a-button type="primary" :disabled="!selected" @click="$emit('next')">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { videoApi } from '../../api'

const props = defineProps({
  selectedTemplate: Object,
  aspectRatio: { type: String, default: '9:16' },
  preferredTemplateKey: String,
})

const emit = defineEmits(['update:selectedTemplate', 'update:aspectRatio', 'next'])

const templates = ref([])
const selected = ref(props.selectedTemplate)
const selectedRatio = ref(props.aspectRatio || '9:16')

const ASPECT_RATIO_OPTIONS = [
  {
    value: '9:16',
    label: '抖音短视频',
    description: '9:16 竖屏 1080x1920',
    resolution: '1080x1920',
    className: 'vertical',
  },
  {
    value: '16:9',
    label: 'B站横屏',
    description: '16:9 横屏 1920x1080',
    resolution: '1920x1080',
    className: 'wide',
  },
  {
    value: '1:1',
    label: '方形通用',
    description: '1:1 方形 1080x1080',
    resolution: '1080x1080',
    className: 'square',
  },
]

const selectedRatioOption = () => ASPECT_RATIO_OPTIONS.find(option => option.value === selectedRatio.value) || ASPECT_RATIO_OPTIONS[0]
const selectedRatioLabel = computed(() => `${selectedRatioOption().label}（${selectedRatio.value}）`)
const selectedResolutionText = computed(() => selectedRatioOption().resolution)

onMounted(async () => {
  try {
    const response = await videoApi.getTemplates()
    templates.value = response.data
    chooseInitialTemplate()
  } catch (error) {
    console.error('加载模板失败:', error)
  }
})

watch(() => props.preferredTemplateKey, chooseInitialTemplate)
watch(() => props.aspectRatio, (value) => {
  if (value && value !== selectedRatio.value) {
    selectedRatio.value = value
  }
})

function chooseInitialTemplate() {
  if (!templates.value.length) return
  const preferred = props.preferredTemplateKey
    ? templates.value.find(template => template.template_key === props.preferredTemplateKey)
    : null
  if (preferred) {
    selectTemplate(preferred)
    return
  }
  if (!selected.value) selectTemplate(templates.value[0])
}

const selectTemplate = (template) => {
  selected.value = template
  emit('update:selectedTemplate', template)
  if (!props.aspectRatio && template.config?.aspect_ratio) {
    selectedRatio.value = template.config.aspect_ratio
    emit('update:aspectRatio', selectedRatio.value)
  }
}

const handleRatioChange = (event) => {
  selectedRatio.value = event.target.value
  emit('update:aspectRatio', selectedRatio.value)
}

const TEMPLATE_ICONS = {
  xianxia_narration: '📖',
  character_monologue: '🎭',
  chapter_title: '📑',
  battle_transition: '⚔️',
  technique_explain: '🔮',
}

const TEMPLATE_DESCS = {
  xianxia_narration: '慢推近、云雾、低音量BGM',
  character_monologue: '单图慢推、音色优先',
  chapter_title: '标题卡、淡入淡出',
  battle_transition: '快速缩放、闪白、剑鸣',
  technique_explain: '稳定画面、清晰旁白',
}

const getTemplateIcon = (key) => TEMPLATE_ICONS[key] || '🎬'
const getTemplateDesc = (key) => TEMPLATE_DESCS[key] || ''
</script>

<style scoped>
.template-step h4 {
  margin-bottom: 16px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.template-card {
  border: 2px solid var(--border-color, #e8e8e8);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: var(--primary-color, #1890ff);
}

.template-card.selected {
  border-color: var(--primary-color, #1890ff);
  background: var(--primary-bg, #e6f7ff);
}

.template-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.template-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.template-desc {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.ratio-section {
  margin-bottom: 16px;
}

.ratio-section h4 {
  margin: 0 0 12px;
}

.ratio-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
}

.ratio-grid :deep(.ant-radio-button-wrapper) {
  height: auto;
  min-height: 86px;
  border-inline-start-width: 1px;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: normal;
}

.ratio-grid :deep(.ant-radio-button-wrapper::before) {
  display: none;
}

.ratio-grid :deep(.ant-radio-button-wrapper-checked) {
  border-color: var(--primary-color, #1890ff);
  background: var(--primary-bg, #e6f7ff);
}

.ratio-preview {
  display: inline-block;
  flex: 0 0 auto;
  border: 2px solid currentColor;
  border-radius: 4px;
  opacity: 0.8;
}

.ratio-vertical {
  width: 18px;
  height: 32px;
}

.ratio-wide {
  width: 34px;
  height: 20px;
}

.ratio-square {
  width: 26px;
  height: 26px;
}

.ratio-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}

.ratio-name {
  font-weight: 500;
  color: var(--text-color, rgba(0, 0, 0, 0.88));
}

.ratio-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.template-info {
  margin-bottom: 16px;
}

@media (max-width: 640px) {
  .template-grid,
  .ratio-grid {
    grid-template-columns: 1fr;
  }
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
