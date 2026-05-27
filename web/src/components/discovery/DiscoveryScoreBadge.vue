<template>
  <span class="score-badge" :class="level">
    <span class="score-label">{{ label }}</span>
    <strong>{{ score }}</strong>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { getScoreLevel } from '../../utils/discovery'

const props = defineProps({
  label: { type: String, required: true },
  score: { type: Number, default: 0 },
})

const level = computed(() => getScoreLevel(props.score))
</script>

<style scoped>
.score-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.score-label {
  color: inherit;
}

.score-badge strong {
  color: var(--text-primary);
  font-weight: 650;
}

.score-badge.high {
  border-color: rgba(47, 111, 78, 0.26);
  color: #2f6f4e;
}

.score-badge.mid {
  border-color: rgba(138, 106, 24, 0.26);
  color: #8a6a18;
}

.score-badge.low {
  border-color: rgba(154, 63, 63, 0.24);
  color: #9a3f3f;
}
</style>
