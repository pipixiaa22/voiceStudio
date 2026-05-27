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

    <div v-if="selected" class="template-info">
      <a-descriptions size="small" :column="2" bordered>
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
import { ref, onMounted } from 'vue'
import { videoApi } from '../../api'

const props = defineProps({
  selectedTemplate: Object,
  preferredTemplateKey: String,
})

const emit = defineEmits(['update:selectedTemplate', 'next'])

const templates = ref([])
const selected = ref(props.selectedTemplate)

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

.template-info {
  margin-bottom: 16px;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
