<template>
  <div class="srt-options">
    <div class="option-row">
      <label class="option-label">语速</label>
      <a-input-number :value="speed" @update:value="$emit('update:speed', $event)" :min="1" :max="20" :step="0.5" size="small" />
      <span class="option-unit">字/秒</span>
    </div>
    <div class="option-row">
      <label class="option-label">每段上限</label>
      <a-input-number :value="maxChars" @update:value="$emit('update:maxChars', $event)" :min="5" :max="50" size="small" />
      <span class="option-unit">字</span>
    </div>
    <div class="option-row">
      <label class="option-label">双语字幕</label>
      <span class="toggle-track" :class="{ on: bilingual }" @click="$emit('update:bilingual', !bilingual)">
        <span class="toggle-thumb" />
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  speed: { type: Number, default: 5 },
  maxChars: { type: Number, default: 20 },
  bilingual: { type: Boolean, default: false },
})

defineEmits(['update:speed', 'update:maxChars', 'update:bilingual'])
</script>

<style scoped>
.srt-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md) var(--space-lg);
  align-items: center;
}

.option-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.option-label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.option-unit {
  font-size: 12px;
  color: var(--text-muted);
}

.toggle-track {
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: var(--surface-muted);
  border: 1px solid var(--surface-border);
  position: relative;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toggle-track.on {
  background: var(--ink-black);
  border-color: var(--ink-black);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: white;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.toggle-track.on .toggle-thumb {
  left: 18px;
}
</style>
