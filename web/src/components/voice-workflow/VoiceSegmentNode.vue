<template>
  <div class="voice-node" :class="[`emotion-${data.emotion || 'neutral'}`, { selected }]">
    <Handle type="target" :position="Position.Left" class="handle handle-target" />
    <div class="node-header">
      <strong>{{ data.order_index }}</strong>
      <span>{{ data.audio_status === 'ready' ? '已生成' : '需生成' }}</span>
    </div>
    <p>{{ data.text }}</p>
    <div class="node-meta">{{ emotionLabel }} · {{ data.voice_profile_id ? `音色 ${data.voice_profile_id}` : '默认音色' }}</div>
    <Handle type="source" :position="Position.Right" class="handle handle-source" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})
const emotionLabel = computed(() => ({
  calm: '平静',
  suppressed: '压抑',
  angry_burst: '爆发',
  cold: '冷漠',
  neutral: '中性',
}[props.data.emotion] || '中性'))
</script>

<style scoped>
.voice-node {
  width: 190px;
  border: 2px solid var(--surface-border-strong);
  border-radius: var(--radius-md);
  background: var(--surface);
  padding: 10px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
  position: relative;
}
.voice-node:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.voice-node.selected {
  border-color: #1677ff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.2), 0 2px 8px rgba(0, 0, 0, 0.12);
}
.node-header { display: flex; justify-content: space-between; font-size: 12px; }
.voice-node p { margin: 8px 0; font-size: 13px; line-height: 1.5; }
.node-meta { font-size: 11px; color: var(--text-muted); }
.emotion-angry_burst { border-color: #a6533f; }
.emotion-cold { border-color: #5d6875; }
.emotion-calm { border-color: #8e7f67; }
.emotion-suppressed { border-color: #6f665c; }
.emotion-angry_burst.selected,
.emotion-cold.selected,
.emotion-calm.selected,
.emotion-suppressed.selected { border-color: #1677ff; }

.handle {
  width: 10px !important;
  height: 10px !important;
  border: 2px solid #8e7f67 !important;
  background: var(--surface) !important;
  transition: background 0.15s ease;
}
.handle:hover {
  background: #1677ff !important;
  border-color: #1677ff !important;
}
.handle-target {
  left: -6px !important;
}
.handle-source {
  right: -6px !important;
}
</style>
