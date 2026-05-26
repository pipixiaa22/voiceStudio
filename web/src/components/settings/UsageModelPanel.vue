<template>
  <div class="usage-model-panel">
    <a-divider orientation="left">语音合成</a-divider>

    <div v-for="usage in ttsUsages" :key="usage.key" class="usage-item">
      <span class="usage-label">{{ usage.label }}</span>
      <ModelSelect
        :value="getUsageModelKey(usage.key)"
        @change="(val, model) => handleUsageChange(usage.key, val, model)"
        :capability="usage.capability"
        :placeholder="usage.placeholder"
        allow-clear
      />
    </div>

    <a-divider orientation="left">文本与规划</a-divider>

    <div v-for="usage in llmUsages" :key="usage.key" class="usage-item">
      <span class="usage-label">{{ usage.label }}</span>
      <ModelSelect
        :value="getUsageModelKey(usage.key)"
        @change="(val, model) => handleUsageChange(usage.key, val, model)"
        :capability="usage.capability"
        :placeholder="usage.placeholder"
        allow-clear
      />
    </div>
  </div>
</template>

<script setup>
import { useModelSettings } from '../../stores/modelSettings'
import ModelSelect from './ModelSelect.vue'

const { setUsageDefault, getUsageDefault } = useModelSettings()

const ttsUsages = [
  { key: 'tts_audition', label: '音色试听', capability: 'tts_voice_design', placeholder: '选择 TTS 模型' },
  { key: 'tts_sync_package', label: '同步包语音', capability: 'tts_voice_design', placeholder: '选择 TTS 模型' },
  { key: 'tts_video_voiceover', label: '视频旁白', capability: 'tts_voice_design', placeholder: '选择 TTS 模型' },
]

const llmUsages = [
  { key: 'voice_prompt_polish', label: '音色描述优化', capability: 'llm_voice_prompt_polish', placeholder: '选择 LLM 模型' },
  { key: 'script_polish', label: '文案润色', capability: 'llm_text', placeholder: '选择 LLM 模型' },
  { key: 'scene_planning', label: '分镜规划', capability: 'scene_planning', placeholder: '选择 LLM 模型' },
]

const getUsageModelKey = (usage) => {
  return getUsageDefault(usage)?.model_key || undefined
}

const handleUsageChange = (usage, modelKey, modelInfo) => {
  if (!modelKey || !modelInfo) {
    setUsageDefault(usage, '', '')
    return
  }
  setUsageDefault(usage, modelInfo.provider_key, modelKey)
}
</script>

<style scoped>
.usage-model-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.usage-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.usage-label {
  min-width: 120px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}
</style>
