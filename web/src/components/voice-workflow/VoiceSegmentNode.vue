<template>
  <div class="voice-node" :class="`emotion-${data.emotion || 'neutral'}`">
    <div class="node-header">
      <strong>{{ data.order_index }}</strong>
      <span>{{ data.audio_status === 'ready' ? '已生成' : '需生成' }}</span>
    </div>
    <p>{{ data.text }}</p>
    <div class="node-meta">{{ emotionLabel }} · {{ data.voice_profile_id ? `音色 ${data.voice_profile_id}` : '默认音色' }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })
const emotionLabel = computed(() => ({
  calm: '平静',
  suppressed: '压抑',
  angry_burst: '爆发',
  cold: '冷漠',
  neutral: '中性',
}[props.data.emotion] || '中性'))
</script>

<style scoped>
.voice-node { width: 190px; border: 2px solid var(--surface-border-strong); border-radius: var(--radius-md); background: var(--surface); padding: 10px; box-shadow: var(--shadow-sm); }
.node-header { display: flex; justify-content: space-between; font-size: 12px; }
.voice-node p { margin: 8px 0; font-size: 13px; line-height: 1.5; }
.node-meta { font-size: 11px; color: var(--text-muted); }
.emotion-angry_burst { border-color: #a6533f; }
.emotion-cold { border-color: #5d6875; }
.emotion-calm { border-color: #8e7f67; }
.emotion-suppressed { border-color: #6f665c; }
</style>
