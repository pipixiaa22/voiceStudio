<template>
  <a-drawer
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="设置"
    placement="right"
    :width="480"
    :bodyStyle="{ padding: '16px' }"
  >
    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="providers" tab="API Key">
        <ProviderKeyPanel />
      </a-tab-pane>

      <a-tab-pane key="defaults" tab="默认模型">
        <UsageModelPanel />
      </a-tab-pane>

      <a-tab-pane key="advanced" tab="高级">
        <a-form layout="vertical">
          <a-form-item label="润色系统提示词">
            <a-textarea
              v-model:value="systemPrompt"
              :autoSize="{ minRows: 4, maxRows: 8 }"
            />
            <span class="hint">指导 LLM 如何润色音色描述</span>
          </a-form-item>
        </a-form>
      </a-tab-pane>
    </a-tabs>

    <template #footer>
      <a-button @click="$emit('update:open', false)">关闭</a-button>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useSettings } from '../../stores/settings'
import ProviderKeyPanel from './ProviderKeyPanel.vue'
import UsageModelPanel from './UsageModelPanel.vue'

const props = defineProps({ open: Boolean })
defineEmits(['update:open'])

const { systemPrompt, loadFromStorage } = useSettings()
const activeTab = ref('providers')

watch(() => props.open, (val) => {
  if (val) loadFromStorage()
})
</script>

<style scoped>
.hint {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
