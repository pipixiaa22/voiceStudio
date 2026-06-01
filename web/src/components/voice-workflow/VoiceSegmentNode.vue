<template>
  <div
    class="voice-node"
    :class="[
      `emotion-${data.emotion || 'neutral'}`,
      { selected, 'arrow-source': isArrowSourceActive, 'arrow-mode': arrowModeActive }
    ]"
  >
    <Handle id="left" type="target" :position="Position.Left" class="handle" />
    <Handle id="top" type="target" :position="Position.Top" class="handle" />
    <div v-if="isArrowSourceActive" class="arrow-badge source-badge">起点</div>
    <div v-if="arrowModeActive && !isArrowSourceActive" class="arrow-badge target-badge">目标</div>
    <div class="node-header">
      <strong>{{ data.order_index }}</strong>
      <span class="status-tag">{{ data.audio_status === 'ready' ? '已生成' : '需生成' }}</span>
    </div>
    <p>{{ data.text }}</p>
    <div class="node-meta">{{ emotionLabel }} · {{ data.voice_label || '默认音色' }}</div>
    <Handle id="right" type="source" :position="Position.Right" class="handle" />
    <Handle id="bottom" type="source" :position="Position.Bottom" class="handle" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isArrowSource: { type: Boolean, default: false },
  arrowMode: { type: Boolean, default: false },
})
const emotionLabel = computed(() => ({
  calm: '平静',
  suppressed: '压抑',
  angry_burst: '爆发',
  cold: '冷漠',
  neutral: '中性',
}[props.data.emotion] || '中性'))
const isArrowSourceActive = computed(() => props.isArrowSource || props.data.isArrowSource)
const arrowModeActive = computed(() => props.arrowMode || props.data.arrowMode)
</script>

<style scoped>
.voice-node {
  width: 190px;
  border: 2px solid var(--surface-border-strong);
  border-radius: var(--radius-md);
  background: var(--surface);
  padding: 10px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
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
.voice-node.arrow-mode {
  animation: arrow-pulse 2s ease-in-out infinite;
}
@keyframes arrow-pulse {
  0%, 100% { box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); }
  50% { box-shadow: 0 0 0 2px rgba(250, 140, 22, 0.15), 0 1px 3px rgba(0, 0, 0, 0.06); }
}
.voice-node.arrow-source {
  border-color: #fa8c16 !important;
  box-shadow: 0 0 0 3px rgba(250, 140, 22, 0.35), 0 2px 12px rgba(250, 140, 22, 0.15) !important;
  transform: scale(1.03);
  animation: none;
}

.node-header { display: flex; justify-content: space-between; font-size: 12px; align-items: center; }
.status-tag { font-size: 10px; color: var(--text-muted); }
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

.arrow-badge {
  position: absolute;
  top: -10px;
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 8px;
  font-weight: 600;
  letter-spacing: 0.5px;
  z-index: 1;
}
.source-badge { right: -6px; background: #fa8c16; color: #fff; }
.target-badge { left: -6px; background: #52c41a; color: #fff; opacity: 0.7; }

/* Handle styling - invisible by default, shows on hover */
.handle {
  width: 8px !important;
  height: 8px !important;
  border: 2px solid #bfbfbf !important;
  background: #fff !important;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease;
}
.voice-node:hover .handle {
  opacity: 1;
}
.handle:hover {
  background: #1677ff !important;
  border-color: #1677ff !important;
}
</style>
