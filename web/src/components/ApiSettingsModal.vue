<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="API 与模型设置"
    @ok="handleSave"
    okText="保存"
    cancelText="取消"
    width="520px"
  >
    <a-form layout="vertical" class="settings-form">
      <a-form-item label="MiMo TTS API Key">
        <a-input-password
          v-model:value="ttsKey"
          placeholder="MiMo TTS API Key"
        />
        <span class="hint">用于语音合成、音色试听、视频旁白生成</span>
      </a-form-item>

      <a-form-item label="MiMo LLM API Key">
        <a-input-password
          v-model:value="llmKey"
          placeholder="MiMo Token Plan API Key"
        />
        <span class="hint">用于音色描述优化</span>
      </a-form-item>

      <a-form-item label="润色系统提示词">
        <a-textarea
          v-model:value="systemPrompt"
          :autoSize="{ minRows: 4, maxRows: 8 }"
        />
        <span class="hint">指导 LLM 如何润色音色描述</span>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useSettings } from '../stores/settings'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])

const { ttsKey, llmKey, systemPrompt, defaultPrompt, loadFromStorage, saveAll } = useSettings()

watch(() => props.open, (val) => {
  if (val) loadFromStorage()
})

const handleSave = () => {
  saveAll(ttsKey.value, llmKey.value, systemPrompt.value || defaultPrompt)
  message.success('设置已保存')
  emit('update:open', false)
}
</script>

<style scoped>
.settings-form {
  margin-top: var(--space-md);
}

.hint {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
