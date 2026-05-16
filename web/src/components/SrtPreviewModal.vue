<template>
  <a-modal
    :open="open"
    @update:open="$emit('update:open', $event)"
    :title="`预览：${title}.srt`"
    :footer="null"
    width="640px"
  >
    <a-spin :spinning="loading">
      <pre class="srt-preview-content">{{ content }}</pre>
    </a-spin>
  </a-modal>
</template>

<script setup>
defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  content: { type: String, default: '' },
  loading: Boolean,
})

defineEmits(['update:open'])
</script>

<style scoped>
.srt-preview-content {
  background: var(--paper-soft);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  font-family: var(--font-mono, 'Courier New', monospace);
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-primary);
  max-height: 480px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
