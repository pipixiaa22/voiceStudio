<template>
  <div class="source-panel">
    <div class="panel-title">素材与节点</div>
    <a-tabs v-model:activeKey="activeTab" size="small">
      <a-tab-pane key="text" tab="文本">
        <a-textarea
          :value="sourceContent"
          @update:value="$emit('update:sourceContent', $event)"
          :autoSize="{ minRows: 8, maxRows: 14 }"
          placeholder="粘贴旁白文本"
        />
        <a-button block type="primary" class="plan-btn" @click="$emit('plan')">自动切句</a-button>
      </a-tab-pane>
      <a-tab-pane key="nodes" tab="节点">
        <button class="node-preset" @click="$emit('add-segment')">+ 语句节点</button>
        <button class="node-preset" @click="$emit('add-pause')">+ 停顿节点</button>
      </a-tab-pane>
      <a-tab-pane key="presets" tab="预设">
        <button v-for="preset in presets" :key="preset.value" class="node-preset" @click="$emit('apply-emotion', preset.value)">
          {{ preset.label }}
        </button>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ sourceContent: { type: String, default: '' } })
defineEmits(['update:sourceContent', 'plan', 'add-segment', 'add-pause', 'apply-emotion'])

const activeTab = ref('text')
const presets = [
  { label: '平静', value: 'calm' },
  { label: '压抑', value: 'suppressed' },
  { label: '爆发愤怒', value: 'angry_burst' },
  { label: '冷漠', value: 'cold' },
]
</script>

<style scoped>
.source-panel { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-weight: 650; margin-bottom: var(--space-sm); }
.plan-btn { margin-top: var(--space-sm); }
.node-preset { width: 100%; text-align: left; padding: 9px; border: 1px solid var(--surface-border); background: var(--surface-muted); border-radius: var(--radius-sm); margin-bottom: 8px; cursor: pointer; }
</style>
