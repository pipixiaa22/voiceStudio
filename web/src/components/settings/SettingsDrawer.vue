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
        <ProviderKeyPanel :active="open && activeTab === 'providers'" />
      </a-tab-pane>

      <a-tab-pane key="defaults" tab="默认模型">
        <UsageModelPanel :active="open && activeTab === 'defaults'" />
      </a-tab-pane>

      <a-tab-pane key="discovery" tab="视频搜索">
        <DiscoverySourcePanel :active="open && activeTab === 'discovery'" />
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
import DiscoverySourcePanel from './DiscoverySourcePanel.vue'
import ProviderKeyPanel from './ProviderKeyPanel.vue'
import UsageModelPanel from './UsageModelPanel.vue'

const props = defineProps({
  open: Boolean,
  initialTab: { type: String, default: 'providers' },
})
defineEmits(['update:open'])

const { systemPrompt, loadFromStorage } = useSettings()
const activeTab = ref('providers')

watch(() => props.open, (val) => {
  if (val) {
    activeTab.value = props.initialTab || 'providers'
    loadFromStorage()
  }
})

watch(() => props.initialTab, (tab) => {
  if (props.open && tab) activeTab.value = tab
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
