<template>
  <a-select
    :value="value"
    @change="handleChange"
    :placeholder="placeholder"
    style="width: 100%"
    :allow-clear="allowClear"
    option-label-prop="label"
  >
    <a-select-option
      v-for="model in filteredModels"
      :key="model.model_key"
      :value="model.model_key"
      :label="`${model.provider_name} / ${model.model_name}`"
      :disabled="!isProviderEnabled(model.provider_key)"
    >
      <div class="model-option">
        <span class="model-name">{{ model.provider_name }} / {{ model.model_name }}</span>
        <div class="model-caps">
          <a-tag v-for="cap in model.capabilities.slice(0, 2)" :key="cap" size="small">
            {{ CAP_LABELS[cap] || cap }}
          </a-tag>
        </div>
      </div>
    </a-select-option>
  </a-select>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { modelProvidersApi } from '../../api'
import { useModelSettings } from '../../stores/modelSettings'

const props = defineProps({
  value: String,
  capability: String,
  placeholder: { type: String, default: '选择模型' },
  allowClear: { type: Boolean, default: false },
  active: { type: Boolean, default: true },
})

const emit = defineEmits(['update:value', 'change'])

const { settings } = useModelSettings()
const allModels = ref([])

const CAP_LABELS = {
  llm_text: 'LLM',
  llm_voice_prompt_polish: '音色优化',
  tts_voice_design: '音色设计',
  tts_voice_clone: '音色复刻',
  tts_builtin_voice: '预置音色',
  tts_plain: 'TTS',
  scene_planning: '分镜',
  script_polish: '润色',
}

const filteredModels = computed(() => {
  if (!props.capability) return allModels.value
  return allModels.value.filter(m => m.capabilities.includes(props.capability))
})

const isProviderEnabled = (providerKey) => {
  return settings.value.providers.some(p => p.provider_key === providerKey && p.enabled !== false)
}

const loaded = ref(false)

const loadModels = async () => {
  if (loaded.value) return
  try {
    const { data } = await modelProvidersApi.getAllModels()
    allModels.value = data
    loaded.value = true
  } catch (e) {
    console.error('加载模型列表失败:', e)
  }
}

onMounted(loadModels)

watch(() => props.active, (val) => {
  if (val) loadModels()
})

const handleChange = (val) => {
  emit('update:value', val)
  const model = allModels.value.find(m => m.model_key === val)
  emit('change', val, model)
}
</script>

<style scoped>
.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-name {
  font-size: 13px;
}

.model-caps {
  display: flex;
  gap: 4px;
}
</style>
