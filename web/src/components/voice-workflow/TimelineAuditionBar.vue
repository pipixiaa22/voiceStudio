<template>
  <div class="timeline-bar">
    <div class="timeline-actions">
      <span>{{ segments.length }} 句旁白</span>
      <a-space>
        <a-button @click="$emit('audition-selected')">试听选中</a-button>
        <a-button @click="$emit('audition-path')">试听整条路径</a-button>
        <a-button @click="$emit('export')">导出同步包</a-button>
      </a-space>
    </div>
    <div class="timeline-track">
      <button
        v-for="segment in segments"
        :key="segment.id"
        class="timeline-segment"
        :class="{ active: segment.id === selectedSegmentId }"
        @click="$emit('select', segment.id)"
      >
        {{ segment.order_index }} · {{ segment.emotion }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  segments: { type: Array, default: () => [] },
  selectedSegmentId: { type: Number, default: null },
})
defineEmits(['select', 'audition-selected', 'audition-path', 'export'])
</script>

<style scoped>
.timeline-bar { height: 100%; display: flex; flex-direction: column; gap: var(--space-sm); }
.timeline-actions { display: flex; align-items: center; justify-content: space-between; }
.timeline-track { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(140px, 1fr); gap: 6px; overflow-x: auto; }
.timeline-segment { border: 1px solid var(--surface-border); background: var(--surface-muted); border-radius: var(--radius-sm); padding: 9px; cursor: pointer; }
.timeline-segment.active { border-color: var(--text-primary); background: var(--surface-active); }
</style>
